# -*- coding: utf-8 -*-
"""O convite do formulário vira linha — SPEC-092, BLOCO A.

📊 **O defeito, medido em 25/08/2026 sobre os DOIS acervos:**

```
observed_events         list     6.726 opções    `id` preenchido: 0
observed_events         buttons  3.832           0
attendance_transcripts  list     3.318           0
attendance_transcripts  buttons  1.397           0
────────────────────────────────────────────────────────
                                15.273 opções, e NENHUMA com id
```

🔴 **A causa, lida no cru:** o fio manda **`buttonID`** e **`rowID`**, com **D
maiúsculo**. O parser lia `buttonId` e `rowId`.

```sql
-- amostra de 50 button_reply e 28 list_reply, coluna interactive->>'raw_out'
button_reply →  "buttonID" | "selectedButtonID" | "stanzaID"
list_reply   →  "rowID"    | "selectedRowID"    | "stanzaID"
```

⚠️ **O título sempre veio; só o id caía.** Um acervo que guarda o rótulo e perde
o identificador **não permite responder**: 📊 as respostas trazem id opaco de
servidor (`pd-dc-<ts>-<hash>-0`), que não se reconstrói a partir do título.

## 🔴 E é o MESMO defeito que o `observer_intake.py:203` já contava

Aquele comentário descreve `selectedButtonId` com d minúsculo apagando **98,9%
dos cliques** — do lado da RESPOSTA. A busca tolerante que o curou mudou de casa
para o parser canônico. **Nunca foi aplicada ao lado do CONVITE.** É a mesma
cura, no gêmeo esquecido.

## O que este arquivo guarda, em uma frase

> **Nenhuma tela que a seguradora mandou some sem deixar de onde reconstruí-la.**

📊 A FORMA dos payloads aqui é medida (as chaves, as grafias, os aninhamentos).
💭 Os VALORES são sintéticos — nenhum telefone, nome ou documento real entra num
arquivo de teste.
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
    """Carrega o parser sem passar por `app.services.__init__` — e DESFAZ o que injeta.

    ⚠️ O mesmo motivo dos guardas da SPEC-085: `app.services.__init__` importa
    `fastembed`, e o `gate.yml` não roda `pip install`. Guarda que não roda em
    CI não guarda nada.
    """
    nomes = ("app", "app.services", "app.services.whatsapp")
    injetados = [n for n in nomes if n not in sys.modules]
    anteriores = {n: sys.modules.get(n) for n in nomes}
    try:
        for nome in injetados:
            mod = types.ModuleType(nome)
            mod.__path__ = [str(RAIZ / Path(*nome.split(".")))]
            sys.modules[nome] = mod
        spec = importlib.util.spec_from_file_location(
            "_spec092_parser", str(PARSER_PY))
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


# ---------------------------------------------------------------------------
# OS PAYLOADS — 📊 forma medida, 💭 valores sintéticos
# ---------------------------------------------------------------------------

def _botoes(grafia_do_id: str) -> dict:
    """Uma tela de botões. `grafia_do_id` é o parâmetro do experimento."""
    return {"buttonsMessage": {
        "contentText": "Como podemos ajudar?",
        "buttons": [
            {grafia_do_id: "op_guincho", "buttonText": {"displayText": "Guincho"}},
            {grafia_do_id: "op_chaveiro", "buttonText": {"displayText": "Chaveiro"}},
        ],
    }}


def _lista(grafia_do_id: str) -> dict:
    return {"listMessage": {
        "description": "Escolha o serviço",
        "buttonText": "Ver opções",
        "sections": [{"rows": [
            {grafia_do_id: "row_pneu", "title": "Troca de pneu",
             "description": "Estepe do próprio veículo"},
        ]}],
    }}


#: 📊 A FORMA do convite de formulário nativo, lida no `quotedMessage` das
#: quatro capturas `live` da Yelum (03, 07, 17 e 19/08/2026). Nas quatro o
#: botão se chama `galaxy_message`, e `"flow"` não aparece em nenhuma.
#: 💭 Os valores são inventados.
CONVITE_DE_FORMULARIO = {"interactiveMessage": {
    "body": {"text": "Precisamos de mais detalhes do atendimento."},
    # 🔴 DOIS NÍVEIS, COM MAIÚSCULAS, E `buttonParamsJSON` — a forma do FIO.
    #
    # A primeira versão deste fixture escrevia UM nível, tudo minúsculo, e
    # `buttonParamsJson` — enquanto o outro arquivo de teste desta MESMA SPEC
    # declarava a forma de dois níveis. 📊 O painel achou a contradição: dois
    # fixtures do mesmo diff descrevendo o mesmo payload de jeitos diferentes, e
    # o corte de `contextInfo` sendo provado sobre a forma que **não acontece**.
    "InteractiveMessage": {"NativeFlowMessage": {"buttons": [{
        "name": "galaxy_message",
        "buttonParamsJSON": json.dumps({
            "flow_id": "000000000000001",
            "flow_cta": "Informar condições",
            "flow_token": "00000000-0000-0000-0000-000000000000:5500000000000:5500000000000",
            "flow_action": "navigate",
            "flow_action_payload": {"screen": "scr_SituacaoVeiculo"},
        }),
    }]}},
    # ⚠️ O `contextInfo` mora no nível de FORA aqui; o teste do corte também
    # o exercita **dentro** do nível extra e com C maiúsculo, que era por onde
    # ele escapava.
    "contextInfo": {"quotedMessage": {"conversation": "SEGREDO DO ATENDIMENTO"}},
}}


# ---------------------------------------------------------------------------
# 1. O ID DAS OPÇÕES — o defeito de 15.273 linhas
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("grafia", ["buttonID", "buttonId", "buttonid", "id"])
def test_o_id_do_botao_sobrevive_a_QUALQUER_grafia(grafia):
    """🔴 `buttonID` é a grafia REAL do fio. As outras são o controle.

    Um guarda que testasse só `buttonID` passaria com um parser que só
    entendesse `buttonID` — e o acervo tem as duas famílias de grafia, porque
    o Evolution mudou de linguagem no meio do caminho.
    """
    _, meta = P._interactive_from_message(_botoes(grafia))
    ids = [o["id"] for o in meta["options"]]
    assert ids == ["op_guincho", "op_chaveiro"], (
        f"a grafia {grafia!r} produziu {ids} — o convite perdeu o "
        "identificador, e sem ele o corredor não sabe o que clicar")


@pytest.mark.parametrize("grafia", ["rowID", "rowId", "rowid", "id"])
def test_o_id_da_linha_de_lista_sobrevive_a_QUALQUER_grafia(grafia):
    _, meta = P._interactive_from_message(_lista(grafia))
    assert [o["id"] for o in meta["options"]] == ["row_pneu"], (
        f"a grafia {grafia!r} de linha de lista perdeu o id")


def test_CONTROLE_o_titulo_NUNCA_foi_o_problema():
    """§9.3 — prove que o guarda mede o id, e não a existência da opção.

    📊 O título veio em 15.273 de 15.273 opções. Um teste que só contasse
    opções ficaria verde com o defeito inteiro de pé.
    """
    _, meta = P._interactive_from_message(_botoes("buttonID"))
    assert [o["title"] for o in meta["options"]] == ["Guincho", "Chaveiro"]
    _, meta_quebrada = P._interactive_from_message(_botoes("chave_que_ninguem_usa"))
    assert [o["title"] for o in meta_quebrada["options"]] == ["Guincho", "Chaveiro"], (
        "o título deixou de vir — este guarda passou a medir outra coisa")
    assert [o["id"] for o in meta_quebrada["options"]] == ["", ""], (
        "🔴 uma chave que NÃO é id virou id: o leitor tolerante ficou tolerante "
        "demais e vai inventar identificador a partir de qualquer campo")


def test_CONTROLE_o_nome_do_botao_NAO_vira_id_da_opcao():
    """🔴 `_CHAVES_DE_ID` inclui `name`, e numa opção `name` não é id.

    📊 Num botão de formulário nativo `name` vale `galaxy_message` — ele
    viraria o "id" de toda opção da tela, e o corredor clicaria em nada.
    """
    assert "name" in P._CHAVES_DE_ID, (
        "a lista do CLIQUE mudou; confira se a exclusão abaixo ainda faz sentido")
    assert "name" not in P._CHAVES_DE_ID_DE_OPCAO, (
        "`name` voltou para as chaves de id de OPÇÃO")
    _, meta = P._interactive_from_message({"buttonsMessage": {
        "contentText": "x",
        "buttons": [{"name": "galaxy_message",
                     "buttonText": {"displayText": "Guincho"}}],
    }})
    assert meta["options"][0]["id"] == "", (
        "o nome do botão virou o id da opção")


# ---------------------------------------------------------------------------
# 2. O CRU — a memória que permite consertar depois
# ---------------------------------------------------------------------------

def test_a_tela_do_formulario_guarda_o_CRU():
    """🔴 É isto que faz o BLOCO B deixar de ser aposta.

    Hoje o convite de `galaxy_message` não é reconhecido como formulário — o
    parser conhece `flow`, `mpm`, `wa_payment_details`, `review_and_pay`. Sem o
    cru, ele vira uma linha de `buttons` com zero opções e **nada de onde
    partir**. 📊 Foi o que aconteceu 50 vezes de 62.
    """
    _, meta = P._interactive_from_message(CONVITE_DE_FORMULARIO)
    cru = meta.get("cru")
    assert cru, "a tela do formulário virou linha SEM o cru"
    # ⚠️ Comparação SEM CAIXA, porque a caixa é justamente o que varia — foi ela
    # que produziu o defeito que este arquivo inteiro conserta.
    texto = json.dumps(cru, ensure_ascii=False).lower()
    for marcador in ("nativeflowmessage", "galaxy_message", "buttonparamsjson",
                     "flow_token", "flow_id", "flow_cta"):
        assert marcador in texto, (
            f"o cru perdeu `{marcador}` — sem ele não dá para responder nem "
            "para descobrir a forma do convite")


def test_o_cru_DEIXA_DE_FORA_o_contextInfo():
    """🔴 A decisão de PII do BLOCO A, e ela é verificável.

    O invólucro de tela é o que a SEGURADORA escreveu. `contextInfo` cita a
    mensagem anterior — que pode ser qualquer coisa que a pessoa do atendimento
    digitou. Guardar a mensagem inteira seria mais fácil e traria dado de
    segurado para uma tabela durável **sem ninguém decidir isso**.
    """
    _, meta = P._interactive_from_message(CONVITE_DE_FORMULARIO)
    texto = json.dumps(meta.get("cru"), ensure_ascii=False)
    assert "SEGREDO DO ATENDIMENTO" not in texto, (
        "o cru levou junto a mensagem citada — é dado de segurado numa tabela "
        "durável, e ninguém decidiu isso")
    assert "contextInfo" not in texto


def test_CONTROLE_o_contextInfo_ESTAVA_no_payload():
    """§9.3 — prove que o teste acima consegue falhar.

    Sem esta linha, um `cru` sempre vazio passaria no teste anterior.
    """
    bruto = json.dumps(CONVITE_DE_FORMULARIO, ensure_ascii=False)
    assert "SEGREDO DO ATENDIMENTO" in bruto and "contextInfo" in bruto, (
        "o payload de teste não tem mais o que o corte deveria remover — "
        "o teste do corte virou tautologia")


def test_o_cru_TEM_TETO_e_o_teto_guarda_as_chaves():
    """Acima do teto guarda-se o nome das gavetas. 📊 É pior que o conteúdo —
    foi o que aconteceu com Porto e Azul (P-084-38) — e melhor que nada."""
    gigante = {"listMessage": {"description": "x" * 60_000, "sections": []}}
    cru = P.cru_da_tela(gigante)
    assert cru and cru.get("_truncado") is True, "o teto do cru sumiu"
    assert "listMessage" in (cru.get("chaves") or []), (
        "truncou e não disse nem quais eram as gavetas")


def test_CONTROLE_abaixo_do_teto_o_conteudo_VEM_INTEIRO():
    cru = P.cru_da_tela(_lista("rowID"))
    assert cru and not cru.get("_truncado"), "truncou uma tela pequena"
    assert "Troca de pneu" in json.dumps(cru, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 3. OS DOIS CONTROLES DO GATE A
# ---------------------------------------------------------------------------

def test_CONTROLE_1_texto_comum_NAO_vira_convite():
    """⛔ Gate A, controle 1. Um parser que virasse tudo em convite passaria em
    todos os testes acima e encheria o acervo de linhas falsas."""
    for payload in ({"conversation": "bom dia, preciso de guincho"},
                    {"extendedTextMessage": {"text": "o carro parou na via"}},
                    {"imageMessage": {"caption": "foto do veículo"}},
                    {}):
        assert P._interactive_from_message(payload) is None, (
            f"{list(payload)} virou convite — não é uma tela")


def test_CONTROLE_2_forma_DESCONHECIDA_guarda_o_cru():
    """⛔ Gate A, controle 2. Forma que ninguém previu não pode virar linha em
    branco: quando alguém for consertar, não haverá do que partir."""
    estranho = {"interactiveMessage": {
        "algoQueNinguemViu": {"campo": "valor"},
        "nativeFlowMessage": {"buttons": [
            {"name": "forma_do_futuro", "buttonParamsJson": '{"x":1}'}]},
    }}
    resultado = P._interactive_from_message(estranho)
    assert resultado is not None, (
        "a tela desconhecida foi DESCARTADA — é a perda que o A.2 existe para "
        "impedir")
    _, meta = resultado
    assert meta["kind"] == "desconhecido", f"kind={meta['kind']!r}"
    assert "forma_do_futuro" in json.dumps(meta.get("cru"), ensure_ascii=False), (
        "marcou como desconhecido e não guardou o cru — é o pior dos dois "
        "mundos: sabe que perdeu, e perdeu")


def test_o_desconhecido_NAO_engole_o_que_JA_funciona():
    """🔴 O ramo novo é o ÚLTIMO, e este guarda prova que ele não roubou nada.

    ⚠️ Um `if` novo num parser que classifica 28 mil eventos é o tipo de
    mudança que parece trivial e reclassifica o acervo (SPEC §B.2).
    """
    casos = [(_botoes("buttonID"), "buttons"),
             (_lista("rowID"), "list"),
             ({"templateMessage": {"hydratedTemplate": {
                 "hydratedContentText": "oi",
                 "hydratedButtons": [{"quickReplyButton": {
                     "id": "qr1", "displayText": "Sim"}}]}}}, "buttons")]
    for payload, esperado in casos:
        _, meta = P._interactive_from_message(payload)
        assert meta["kind"] == esperado, (
            f"{list(payload)[0]} virou {meta['kind']!r}, era {esperado!r} — "
            "o ramo do desconhecido reclassificou uma tela que já funcionava")
