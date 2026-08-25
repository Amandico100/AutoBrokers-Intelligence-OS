# -*- coding: utf-8 -*-
"""A tela de formulário não é respondida por texto — SPEC-092, BLOCO D.2.

📊 **P-084-68, reproduzida ponta a ponta.** A âncora do passo `destino_como` é

```python
{"step": "destino_como", "anchor": r"para onde devemos levar o ve[íi]culo",
 "reply": "Digitar endereço"}                  # corridor_playbooks.py:2596
```

e `match_ura_step` usa `re.search` com `IGNORECASE|DOTALL` — **a âncora é uma
substring**. As duas telas a contêm:

```
tela de BOTÕES  (7×)  "…informe PARA ONDE DEVEMOS LEVAR O VEÍCULO.
                       Qual dessas opções você prefere? Botão 1: Digitar endereço…"
tela de FORM.   (1×)  "…preencha o formulário para informar
                       PARA ONDE DEVEMOS LEVAR O VEÍCULO."
```

🔴 Rodando o passo primeiro, o corredor responde **"Digitar endereço" como
TEXTO** para uma tela que só aceita clique. A URA descarta, e a janela queima.

## 🔴 POR QUE ESTE ARQUIVO EXISTE

📊 Medido antes da inversão: **nenhum teste da suíte ficava vermelho com ela.**
Isso não é alívio — é o alerta. Significa que **não havia guarda nenhuma para
este invariante**, e a inversão poderia ser desfeita amanhã sem nada acusar.

## 📊 E a inversão é estreita, não larga

```
4.220 telas reais · 14 corredores
   formulários REGISTRADOS que casam passo de URA ......  0
   telas que mudam de comportamento ....................  1
```

Uma tela em 4.279 — e ela muda de **resposta errada** para `needs_human` **com
motivo escrito**.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
MOTOR_PY = RAIZ / "app" / "services" / "insurer_dispatch_service.py"
PLAYBOOKS_PY = RAIZ / "app" / "services" / "corridor_playbooks.py"


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


M = _carregar("_spec092_motor_d2", MOTOR_PY)
PB = _carregar("_spec092_pb_d2", PLAYBOOKS_PY)

#: 📊 O texto REAL da tela, corpus `yelum-auto.jsonl`, sessão `8a0d25a4`,
#: 2026-08-03T19:28:38Z — a mesma citada na P-084-68.
TELA_DO_FORMULARIO_DE_DESTINO = (
    "Certo! Agora preciso que você informe para onde devemos levar o veículo.\n"
    "Por favor, selecione no botão abaixo e preencha o formulário para informar "
    "para onde devemos levar o veículo.\n"
    "[FORMULARIO NATIVO: Informar endereço] (exige clique — não aceita texto)")

#: 📊 A tela de BOTÕES, que casa a MESMA âncora e **deve** continuar sendo
#: respondida por texto. 7 ocorrências no corpus.
TELA_DE_BOTOES_DE_DESTINO = (
    "Certo! Agora preciso que você informe para onde devemos levar o veículo. "
    "Qual dessas opções você prefere?\n"
    "Botão 1: Digitar endereço\nBotão 2: Usar minha localização")

INTERATIVA_DO_FORMULARIO = {
    "kind": "flow",
    "flow": {"flow_id": "1579547063352571", "flow_token": "t:1:2",
             "name": "galaxy_message", "cta": "Informar endereço"},
    "options": [],
}


def _sessao(ref: str):
    """O playbook vem do `playbook_ref` da sessao, nao por argumento."""
    return {"state": "ura", "slots": {}, "subservice": "guincho",
            "case_id": "c-teste", "transcript": [], "playbook_ref": ref}


#: Os dois corredores que recebem `_YELUM_FAMILY_STEPS` — e sao os UNICOS em
#: que o passo `destino_como` existe (medido: `corridor_playbooks.py:2982` e
#: `:3010`).
CORREDORES = ("hdi-auto-whatsapp@v1", "yelum-auto-whatsapp@v3")


def test_os_corredores_deste_arquivo_EXISTEM():
    """A premissa, conferida em vez de suposta: um `playbook_ref` que nao
    resolve faria todo teste abaixo passar por `needs_human:playbook_not_found`
    — verde pelo motivo errado."""
    refs = set(PB.list_playbooks())
    for r in CORREDORES:
        assert r in refs, f"{r} sumiu; refs disponiveis: {sorted(refs)}"


# ---------------------------------------------------------------------------
# 1. O DEFEITO DA P-084-68
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("nome", CORREDORES)
def test_a_tela_de_formulario_NAO_recebe_texto(nome):
    """🔴 O caso concreto: sem a inversão, sai `"Digitar endereço"` como texto."""
    enviadas = []
    saida = M.handle_insurer_message(
        _sessao(nome), TELA_DO_FORMULARIO_DE_DESTINO,
        interactive=INTERATIVA_DO_FORMULARIO,
        sender=lambda *a, **k: enviadas.append(a))
    assert saida["state"] == "needs_human", (
        f"[{nome}] o corredor respondeu a tela de formulário e seguiu em "
        f"`{saida['state']}` — a URA descarta texto nessa tela e a janela queima")
    assert saida.get("reason") == "formulario_nativo_desconhecido", (
        f"[{nome}] motivo={saida.get('reason')!r} — sem o motivo certo, quem "
        "tria não sabe que faltou schema")
    assert not enviadas, (
        f"[{nome}] MANDOU {enviadas!r} para uma tela que só aceita clique")


@pytest.mark.parametrize("nome", CORREDORES)
def test_CONTROLE_a_tela_de_BOTOES_continua_sendo_respondida(nome):
    """🔴 A metade que impede o conserto de virar regressão.

    📊 A MESMA âncora casa 7 telas de botão legítimas. Se a inversão as
    silenciasse, o corredor pararia de responder o passo `destino_como` e todo
    acionamento de guincho travaria ali — trocando um defeito de 1 tela por um
    de 7.
    """
    saida = M.handle_insurer_message(_sessao(nome), TELA_DE_BOTOES_DE_DESTINO)
    assert saida["state"] == "ura", (
        f"[{nome}] a tela de BOTÕES parou de ser respondida: {saida.get('reason')!r}")
    # ⚠️ A resposta se mede no TRANSCRIPT, não no `sender`.
    #
    # 🔴 A primeira versão deste controle afirmava `enviadas` — e ficou vermelha
    # com o produto CERTO. Com o freio de envio fechado, `_emit` grava a
    # resposta no transcript com `dry_run: True` e **não chama o `sender`**.
    # Medir o `sender` seria medir o freio, não o corredor.
    respostas = [t for t in (saida.get("transcript") or [])
                 if t.get("direction") == "out"]
    assert respostas, f"[{nome}] o corredor não respondeu nada"
    assert respostas[-1].get("text") == "Digitar endereço", (
        f"[{nome}] a resposta mudou: {respostas[-1]!r}")
    assert respostas[-1].get("step") == "destino_como"


# ---------------------------------------------------------------------------
# 2. A GUARDA — as duas condições, e por que a segunda não é redundância
# ---------------------------------------------------------------------------

def test_a_guarda_reconhece_pelo_KIND():
    assert M.a_tela_e_formulario("qualquer texto", {"kind": "flow"}) is True


def test_a_guarda_reconhece_pelo_MARCADOR_sem_interactive():
    """🔴 📊 `ura_simulator.py` e `replay.py` chamam `handle_insurer_message`
    **sem** o argumento `interactive`. Sem esta metade, o ensaio e a régua
    mediriam um produto diferente do que roda em produção."""
    assert M.a_tela_e_formulario(
        "[FORMULARIO NATIVO: Informar endereço]", None) is True
    assert M.a_tela_e_formulario("[formulario nativo: x]", None) is True, (
        "a guarda ficou sensível a caixa — o marcador chega em maiúscula, mas "
        "depender disso é uma aposta de graça")


def test_CONTROLE_a_guarda_CONSEGUE_dizer_NAO():
    """§9.3 — uma guarda que dissesse SIM sempre mandaria toda mensagem da URA
    para o caminho do formulário, e o corredor pararia de funcionar."""
    for texto, inter in (("bom dia", None),
                         ("Botão 1: Guincho", {"kind": "buttons", "options": []}),
                         ("Escolha uma opção", {"kind": "list", "options": []}),
                         ("", None)):
        assert M.a_tela_e_formulario(texto, inter) is False, (
            f"{texto!r} + {inter} foi tratado como formulário")


# ---------------------------------------------------------------------------
# 3. A ORDEM, NO FONTE — para a inversão não ser desfeita em silêncio
# ---------------------------------------------------------------------------

def test_a_INVERSAO_esta_no_lugar():
    """📊 Antes deste arquivo, **nenhum teste da suíte** ficava vermelho ao
    desfazer a inversão. Este fica."""
    fonte = MOTOR_PY.read_text(encoding="utf-8")
    i_guarda = fonte.index("if a_tela_e_formulario(insurer_message, interactive):")
    i_passo = fonte.index("step = match_ura_step(playbook, insurer_message")
    assert i_guarda < i_passo, (
        "a inversão foi desfeita: `match_ura_step` voltou a decidir antes de a "
        "tela de formulário ser reconhecida (P-084-68)")


def test_a_SEGUNDA_chamada_continua_existindo():
    """Ela cobre o formulário reconhecido por `prompt_anchor`, sem marcador —
    📊 o caso do corpus colhido ANTES do conserto do `galaxy_message`."""
    fonte = MOTOR_PY.read_text(encoding="utf-8")
    assert fonte.count("_responder_formulario_nativo(") >= 3, (
        "sobrou uma chamada só — ou a inversão engoliu a segunda, e o "
        "formulário sem marcador deixou de ser reconhecido pela âncora")


# ---------------------------------------------------------------------------
# 4. ⛔ O CONTROLE DO GATE D — o freio fechado não pode PARECER resposta
# ---------------------------------------------------------------------------

def test_com_o_freio_fechado_o_transcript_NAO_diz_respondido():
    """⛔ A trava que a SPEC-092 §D escreve por extenso.

    Com `INSURER_DISPATCH_LIVE` fechado, `flow_sender` **nunca é chamado** e a
    sessão segue para `state="ura"` — exatamente como se tivesse respondido. O
    campo `dry_run` já era honesto; **a frase ao lado dele não era**.

    🔴 É o mesmo defeito da SPEC-085 noutro arquivo: a flag foi consertada e o
    texto ao lado dela não. Quem lê o dossiê precisa distinguir *"não enviei
    porque o freio está fechado"* de *"enviei e deu certo"*.
    """
    fonte = MOTOR_PY.read_text(encoding="utf-8")
    assert "NÃO enviado — envio real desligado" in fonte, (
        "o transcript voltou a dizer `respondido` para um formulário que "
        "ninguém enviou")
    i_cond = fonte.index("if live else")
    i_resp = fonte.index("[FORMULÁRIO NATIVO respondido")
    assert i_resp < i_cond, (
        "a frase de sucesso deixou de estar sob a condição de `live`")


def test_as_DUAS_frases_do_transcript_sao_DIFERENTES():
    """§9.3 — prove que os dois casos conseguem ser distinguidos.

    Se as duas frases fossem iguais, o teste acima passaria e o dossiê
    continuaria sem dizer se a mensagem saiu.
    """
    fonte = MOTOR_PY.read_text(encoding="utf-8")
    assert "[FORMULÁRIO NATIVO respondido" in fonte
    assert "[FORMULÁRIO NATIVO pronto, NÃO enviado" in fonte
    assert fonte.count("dry_run") >= 1, (
        "o campo `dry_run` sumiu do transcript — a frase sozinha não basta "
        "para quem consulta por campo")
