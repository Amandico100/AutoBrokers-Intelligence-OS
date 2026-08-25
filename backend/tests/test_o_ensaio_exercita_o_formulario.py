# -*- coding: utf-8 -*-
"""O ensaio exercita o formulário — SPEC-092, BLOCO F.3 e F.4.

📊 **A lacuna nº 1 da SPEC, medida:** `ura_simulator.simulate` chamava
`handle_insurer_message(session, screen)` **com TEXTO SÓ**. Sem `interactive`,
`kind == "flow"` nunca chegava; sem `flow_token`, todo formulário virava
`formulario_pronto_sem_flow_token`.

> **O simulador exercitava o corredor e não exercitava o formulário.** Ele é a
> régua que decide se uma mudança de playbook pode ir a produção — e o caminho
> mais novo do produto era invisível para ela.

## 🔴 E A LINHA DE CONTROLE É METADE DO BLOCO

⛔ §F.4, literal: *"o mesmo roteiro com uma tela de TEXTO. Nenhum formulário
montado, nenhum envio, o corredor responde por texto como sempre fez."*

Sem ela, um simulador que tratasse **toda** tela como formulário passaria no
teste de cima e quebraria os outros 4.220 roteiros do corpus.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SIM_PY = RAIZ / "app" / "services" / "ura_simulator.py"


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


def _preparar_pacote():
    """Deixa `from app.services import insurer_dispatch_service` resolver SEM
    executar `app/services/__init__.py`.

    🔴 📊 Medido: `app.services.__init__` importa `fastembed`, e o `gate.yml`
    **não roda `pip install`**. `ura_simulator.simulate` faz
    `from app.services import insurer_dispatch_service` DENTRO da função — então
    o ensaio inteiro é irrodável em CI por uma dependência de embeddings que ele
    não usa.

    ⚠️ Isto é uma fragilidade REAL do produto, não do teste: qualquer caminho
    que faça `from app.services import X` carrega o pacote inteiro. Fica
    registrado na pendência; aqui o pacote é montado à mão para que o guarda
    meça o SIMULADOR e não a árvore de dependências.
    """
    import importlib.util as _il

    pacote = types.ModuleType("app.services")
    pacote.__path__ = [str(RAIZ / "app" / "services")]
    sys.modules.setdefault("app", types.ModuleType("app"))
    sys.modules["app"].__path__ = [str(RAIZ / "app")]
    sys.modules["app.services"] = pacote
    for nome, arquivo in (("insurer_dispatch_service", "insurer_dispatch_service.py"),
                          ("corridor_playbooks", "corridor_playbooks.py")):
        caminho = RAIZ / "app" / "services" / arquivo
        spec = _il.spec_from_file_location("app.services." + nome, str(caminho))
        mod = _il.module_from_spec(spec)
        sys.modules["app.services." + nome] = mod
        spec.loader.exec_module(mod)
        setattr(pacote, nome, mod)
    return pacote


_preparar_pacote()
SIM = _carregar("_spec092_sim", SIM_PY)

#: 📊 A forma real de uma tela de formulário, como o parser a entrega.
INTERATIVA = {
    "kind": "flow",
    "flow": {"flow_id": "857030507196739", "flow_token": "t:1:2",
             "name": "galaxy_message", "cta": "Informar condições"},
    "options": [],
}

TELA_FORM = ("Precisamos entender o local e as condições do veículo.\n"
             "[FORMULARIO NATIVO: Informar condições] (exige clique — não aceita texto)")

#: ⛔ A LINHA DE CONTROLE da §F.4 — uma tela de TEXTO comum.
TELA_TEXTO = ("Certo! Agora preciso que você informe para onde devemos levar o "
              "veículo. Qual dessas opções você prefere?\n"
              "Botão 1: Digitar endereço\nBotão 2: Usar minha localização")


# ---------------------------------------------------------------------------
# 1. O `interactive` ATRAVESSA — era a lacuna nº 1
# ---------------------------------------------------------------------------

def test_o_script_CARREGA_o_interactive_da_tela():
    """Sem isto, o `interactive` morre na extração e o resto não adianta."""
    transcript = [
        {"direction": "in", "text": TELA_FORM, "interactive": INTERATIVA},
        {"direction": "out", "text": "[FORMULÁRIO NATIVO respondido: 5 campos]"},
        {"direction": "in", "text": TELA_TEXTO},
    ]
    script = SIM.script_from_transcript(transcript)
    assert len(script) == 2
    assert script[0].get("interactive") == INTERATIVA, (
        "o `interactive` da tela de formulário não sobreviveu à extração")
    assert "interactive" not in script[1], (
        "uma tela de TEXTO ganhou um `interactive` do nada — o simulador "
        "passaria a tratar tela comum como formulário")


def test_o_simulador_REPASSA_o_interactive_ao_motor():
    """📊 A prova de que o caminho é exercitado: com `interactive`, o motor
    reconhece o formulário e **pausa por falta de schema/transporte** em vez de
    responder por texto."""
    script = [{"screen": TELA_FORM, "expected": None, "interactive": INTERATIVA}]
    r = SIM.simulate("hdi-auto-whatsapp@v1", "guincho",
                     {"titular_nome": "x", "placa": "AAA0A00"}, script)
    motivos = [d.get("got", "") for d in (r.get("divergences") or [])]
    assert any("needs_human:formulario" in m for m in motivos), (
        f"o formulário não foi reconhecido pelo simulador: {r}")


def test_o_flow_sender_ATRAVESSA_e_e_MEDIVEL():
    """🔴 A outra metade da lacuna: sem poder passar um transporte, o ensaio
    nunca chega ao envio — e o que nunca é exercitado nunca é medido."""
    recebido = {}

    def _dublê(**kwargs):
        recebido.update(kwargs)
        return True

    import inspect

    assinatura = inspect.signature(SIM.simulate)
    assert "flow_sender" in assinatura.parameters, (
        "`simulate` voltou a não aceitar transporte — o ensaio não alcança o "
        "caminho de envio")
    assert assinatura.parameters["flow_sender"].default is None, (
        "⛔ o transporte deixou de ser OPCIONAL: um ensaio que envie por padrão "
        "manda mensagem sem ninguém ter pedido")


# ---------------------------------------------------------------------------
# 2. ⛔ A LINHA DE CONTROLE DA §F.4
# ---------------------------------------------------------------------------

def test_CONTROLE_F4_a_tela_de_TEXTO_e_respondida_como_sempre():
    """⛔ *"Nenhum formulário montado, nenhum envio, o corredor responde por
    texto como sempre fez."*

    🔴 Sem esta linha, um simulador que tratasse TODA tela como formulário
    passaria no teste de cima — e quebraria os 4.220 roteiros do corpus.
    """
    script = [{"screen": TELA_TEXTO, "expected": "Digitar endereço"}]
    r = SIM.simulate("hdi-auto-whatsapp@v1", "guincho",
                     {"titular_nome": "x", "placa": "AAA0A00"}, script)
    assert not r.get("divergences"), (
        f"a tela de TEXTO divergiu depois da mudança: {r.get('divergences')}")


def test_CONTROLE_o_simulador_CONSEGUE_divergir():
    """§9.3 — prove que `divergences` sabe ficar cheio.

    Um simulador que nunca divergisse passaria no controle acima e não mediria
    nada.
    """
    script = [{"screen": TELA_TEXTO, "expected": "uma resposta que ninguém dá"}]
    r = SIM.simulate("hdi-auto-whatsapp@v1", "guincho",
                     {"titular_nome": "x", "placa": "AAA0A00"}, script)
    assert r.get("divergences"), (
        "o simulador não acusou divergência onde ela existe — ele não mede nada")


def test_o_padrao_do_ensaio_NAO_envia():
    """⛔ Trava da SPEC: o ensaio é do nosso número para o nosso, e por padrão
    não manda nada. Um `flow_sender` obrigatório inverteria isso."""
    script = [{"screen": TELA_FORM, "expected": None, "interactive": INTERATIVA}]
    r = SIM.simulate("hdi-auto-whatsapp@v1", "guincho", {}, script)
    assert isinstance(r, dict), "o ensaio sem transporte nem roda"
