# -*- coding: utf-8 -*-
"""O convite de formulário é reconhecido na LEITURA — SPEC-092, BLOCO B.

📊 **O caminho real do convite**, lido no `quotedMessage` das quatro capturas
`live` da Yelum (03, 07, 17 e 19/08/2026):

```
quotedMessage
  .interactiveMessage
    .InteractiveMessage          ← 🔴 NÍVEL EXTRA, e com I maiúsculo
      .NativeFlowMessage         ← 🔴 N maiúsculo
        .buttons[0].name              = "galaxy_message"
        .buttons[0].buttonParamsJSON  ← 🔴 JSON todo em maiúscula
```

E o parser procurava `interactiveMessage.nativeFlowMessage` e
`buttonParamsJson`. **Ele nunca chegava aos botões**: caía no ramo final com
`options` vazio e `body` preenchido, devolvendo `{"kind":"buttons","options":[]}`.

⚠️ 📊 É o sintoma exato do acervo: **50 das 62** respostas de formulário têm,
de 13 a 20 segundos antes, uma linha `buttons` com ZERO opções.

## 🔴 SÃO TRÊS DIVERGÊNCIAS, E O RÓTULO É A TERCEIRA

A SPEC-092 §B.1 pede *"reconhecer o rótulo `galaxy_message`"*. **Sozinho, ele
não conserta nada** — o parser não chega ao botão para ler o nome dele. Este
arquivo prova as três, uma a uma, e prova que cada uma é necessária.

## 📊 O controle sobre payload REAL, e ele já rodou

82 convites crus do acervo, parser de `8b49fdb` contra o da árvore::

    buttons → buttons   50      intacto
    list    → list      28      intacto
    buttons → flow       4      <== os quatro formulários
    opções     330 → 330        nenhuma opção inventada
    ids          0 → 330
    flow_id      0 →   4
    flow_token   0 →   4

💭 Os VALORES deste arquivo são sintéticos. 📊 A FORMA é medida.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
PARSER_PY = RAIZ / "app" / "services" / "whatsapp" / "evolution_inbound.py"


def _carregar_parser():
    nomes = ("app", "app.services", "app.services.whatsapp")
    injetados = [n for n in nomes if n not in sys.modules]
    anteriores = {n: sys.modules.get(n) for n in nomes}
    try:
        for nome in injetados:
            mod = types.ModuleType(nome)
            mod.__path__ = [str(RAIZ / Path(*nome.split(".")))]
            sys.modules[nome] = mod
        spec = importlib.util.spec_from_file_location("_spec092_parser_b", str(PARSER_PY))
        parser = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(parser)
        return parser
    finally:
        for nome in injetados:
            if anteriores.get(nome) is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = anteriores[nome]


P = _carregar_parser()

#: 💭 sintético, na 📊 forma medida do fio.
PARAMS = json.dumps({
    "flow_id": "000000000000001",
    "flow_cta": "Informar condicoes",
    "flow_token": "00000000-0000-0000-0000-000000000000:5500000000000:5500000000000",
    "flow_action": "navigate",
})


def convite(*, nivel_extra: bool, maiusculas: bool, rotulo: str,
            chave_params: str) -> dict:
    """Um convite, com CADA uma das três divergências como parâmetro.

    🔴 É o desenho do experimento: variar UM fator por vez (`CLAUDE.md` §9.2).
    """
    botao = {"name": rotulo, chave_params: PARAMS}
    nfm_key = "NativeFlowMessage" if maiusculas else "nativeFlowMessage"
    miolo = {nfm_key: {"buttons": [botao]},
             "body": {"text": "Precisamos de mais detalhes."}}
    if nivel_extra:
        interno = "InteractiveMessage" if maiusculas else "interactiveMessage"
        return {"interactiveMessage": {**miolo, interno: dict(miolo)}}
    return {"interactiveMessage": miolo}


#: 📊 O convite REAL: os três fatores na forma que o fio manda.
COMO_O_FIO_MANDA = dict(nivel_extra=True, maiusculas=True,
                        rotulo="galaxy_message", chave_params="buttonParamsJSON")


# ---------------------------------------------------------------------------
# 1. O CONVITE REAL É LIDO
# ---------------------------------------------------------------------------

def test_o_convite_REAL_vira_formulario():
    """O caso que o acervo mostra 50 vezes, e que hoje virava `buttons` vazio."""
    texto, meta = P._interactive_from_message(convite(**COMO_O_FIO_MANDA))
    assert meta["kind"] == "flow", (
        f"o convite real continua sendo lido como {meta['kind']!r} — "
        "é a linha `buttons` com zero opções que o acervo tem 50 vezes")
    flow = meta["flow"]
    assert flow["flow_id"] == "000000000000001", "o `flow_id` não foi lido"
    assert flow["flow_token"], (
        "🔴 o `flow_token` não foi lido — sem ele NÃO EXISTE resposta possível: "
        "ele não é derivável, só ecoável")
    assert flow["cta"] == "Informar condicoes"
    assert flow["name"] == "galaxy_message", (
        "o envelope não foi ecoado — quem responde precisa devolver o mesmo "
        "rótulo, e adivinhá-lo faz a seguradora descartar em silêncio")


def test_o_marcador_de_texto_APARECE():
    """⛔ Gate B: `[FORMULARIO NATIVO]` deixa de ser zero.

    📊 Varredura de 23/08 sobre 28.096 eventos: o marcador aparecia **zero**
    vezes (P-084-67). É ele que diz ao corredor *"isto exige clique, não
    aceita texto"*.
    """
    texto, _ = P._interactive_from_message(convite(**COMO_O_FIO_MANDA))
    assert "[FORMULARIO NATIVO" in texto, f"o marcador sumiu do texto: {texto!r}"
    assert "não aceita texto" in texto or "nao aceita texto" in texto


# ---------------------------------------------------------------------------
# 2. AS TRÊS DIVERGÊNCIAS, UMA POR VEZ — 🔴 e cada uma sozinha bastava para matar
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fator,mudanca", [
    ("o nível extra",   {"nivel_extra": False}),
    ("as maiúsculas",   {"maiusculas": False}),
    ("o rótulo legado", {"rotulo": "flow"}),
    ("a grafia de params", {"chave_params": "buttonParamsJson"}),
])
def test_cada_fator_ISOLADO_continua_sendo_lido(fator, mudanca):
    """🔴 O conserto não pode depender de os quatro chegarem juntos.

    O acervo tem só quatro capturas, todas da mesma família. Uma seguradora
    que mande o mesmo formulário sem o nível extra, ou com o rótulo atual da
    Meta, **tem de continuar sendo lida** — senão o conserto vale para a Yelum
    e para mais ninguém.
    """
    _, meta = P._interactive_from_message(convite(**{**COMO_O_FIO_MANDA, **mudanca}))
    assert meta["kind"] == "flow", (
        f"variando {fator} o convite deixou de ser reconhecido "
        f"({meta['kind']!r}) — o conserto ficou preso a uma única forma")


def test_CONTROLE_o_rotulo_SOZINHO_nao_bastaria():
    """🔴 A correção mais importante que este bloco faz à SPEC.

    A §B.1 pede *"reconhecer o rótulo `galaxy_message`"*. Este teste mostra
    por que sozinho ele não chegaria a lugar nenhum: com o nível extra e as
    maiúsculas do fio, **o parser nem alcança o botão para ler o nome**.

    A prova é por ausência: um payload com o rótulo CERTO e um nome de botão
    que ninguém conhece cai igual — porque a diferença não está no nome.
    """
    # rótulo desconhecido, mas caminho legível → cai no ramo genérico, não em `flow`
    _, meta = P._interactive_from_message(
        convite(**{**COMO_O_FIO_MANDA, "rotulo": "rotulo_que_ninguem_viu"}))
    assert meta["kind"] != "flow", (
        "qualquer rótulo virou formulário — a allowlist deixou de filtrar, e "
        "uma tela de pagamento viraria um formulário de acionamento")
    assert meta.get("cru"), (
        "e o cru sumiu justo no caso desconhecido, que é quando ele mais vale")


def test_CONTROLE_botao_e_lista_comuns_NAO_viram_formulario():
    """⛔ Gate B, controle: as outras classificações ficam idênticas.

    📊 Provado também sobre payload real: 78 de 82 convites do acervo saíram
    com a MESMA classificação de antes.
    """
    botoes = {"buttonsMessage": {"contentText": "Como ajudar?", "buttons": [
        {"buttonID": "b1", "buttonText": {"displayText": "Guincho"}}]}}
    lista = {"listMessage": {"description": "Serviços", "buttonText": "Ver",
                             "sections": [{"rows": [
                                 {"rowID": "r1", "title": "Pneu"}]}]}}
    _, m1 = P._interactive_from_message(botoes)
    _, m2 = P._interactive_from_message(lista)
    assert m1["kind"] == "buttons", f"botão virou {m1['kind']!r}"
    assert m2["kind"] == "list", f"lista virou {m2['kind']!r}"
    assert m1["options"][0]["id"] == "b1" and m2["options"][0]["id"] == "r1", (
        "o BLOCO A parou de recuperar o id enquanto o B mexia ao lado")


def test_CONTROLE_o_experimento_CONSEGUE_dar_negativo():
    """§9.3 — prove que `convite()` sabe produzir algo que NÃO é formulário.

    Sem esta linha, um parser que dissesse `flow` para tudo passaria em todos
    os testes acima.
    """
    sem_botao = {"interactiveMessage": {"body": {"text": "só texto"}}}
    r = P._interactive_from_message(sem_botao)
    assert r is None or r[1]["kind"] != "flow", (
        "uma tela sem botão nenhum virou formulário")


# ---------------------------------------------------------------------------
# 3. O QUE A LEITURA ENTREGA AO MOTOR
# ---------------------------------------------------------------------------

def test_o_motor_consegue_REGISTRAR_o_que_a_leitura_devolve():
    """🔴 A ponte: `registrar_formulario_nativo` exige `kind == "flow"` e lê
    `flow.flow_token`, `flow.flow_id` e `flow.name`.

    Se a leitura devolvesse a forma certa com nomes diferentes, o bloco B
    ficaria verde e o produto continuaria parado — que é o defeito que esta
    SPEC inteira existe para matar.
    """
    _, meta = P._interactive_from_message(convite(**COMO_O_FIO_MANDA))
    assert meta.get("kind") == "flow"
    flow = meta.get("flow") or {}
    for campo in ("flow_token", "flow_id", "name", "cta"):
        assert campo in flow, (
            f"`{campo}` sumiu do contrato que `registrar_formulario_nativo` lê")
    assert isinstance(flow["flow_token"], str) and flow["flow_token"], (
        "o token veio vazio ou não-string; o motor pausa com "
        "`formulario_pronto_sem_flow_token`")
