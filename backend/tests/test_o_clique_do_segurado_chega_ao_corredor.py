"""O clique do segurado chega ao corredor — o mesmo defeito, no caminho AO VIVO.

P-56. O defeito de leitura que apagou 937 cliques tinha um irmão gêmeo vivo.
-----------------------------------------------------------------------------
📊 Medido em 03/08/2026 (`observed_events`, projeto de produção
`dcajcvlzcjbmyapmklil`): dos 947 cliques de botão do histórico, 937 chegaram
na forma::

    ["Response", "contextInfo", "selectedButtonID", "type"]

O observador procurava três chaves e nenhuma delas era essa. **98,9% dos
cliques de botão da corretora foram apagados na leitura.** Isso foi consertado
em `observer_intake.py`.

O que ficou: ``evolution_inbound._text_from_message`` — o caminho AO VIVO, o
que decide o que o corredor e o atendente veem — procurava::

    _clean(btn_resp.get("selectedButtonId"))    # d minúsculo

e o campo real é ``selectedButtonID``, com D maiúsculo. Mesmo defeito, outro
arquivo, ainda em pé.

Por que dói MAIS aqui do que no observador
-------------------------------------------
No observador o clique vira uma aresta pobre num mapa. Aqui, texto vazio vira
``skip:no_text`` e a mensagem inteira é **descartada**: o corredor não vê o
clique do segurado, o atendente humano não vê, e o acionamento fica esperando
uma resposta que chegou e foi jogada fora.

E o defeito é silencioso nos dois sentidos: nada estoura, nada é logado como
erro. Só existe uma conversa que não anda.

A regra que este teste guarda
-----------------------------
Quem serializa o protobuf do WhatsApp escolhe o nome das chaves e não avisa.
Portanto **não se confere nome exato**: normaliza (minúsculas, sem ``_``) e
procura. `selectedButtonID`, `selectedButtonId` e `selected_button_id` são o
mesmo campo, e uma grafia nova deixa de ser incidente.

E a lista de grafias mora em UM lugar só. Duas listas em dois arquivos é
exatamente como a segunda fica para trás — foi assim que este defeito
sobreviveu três semanas ao conserto do primeiro.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(*partes: str) -> str:
    with open(os.path.join(RAIZ, *partes), encoding="utf-8") as fh:
        return fh.read()


def _carregar():
    """Carrega o parser REAL pelo caminho, sem arrastar a aplicação junto."""
    for pacote in ("app", "app.services", "app.services.whatsapp"):
        if pacote not in sys.modules:
            vazio = types.ModuleType(pacote)
            vazio.__path__ = []  # type: ignore[attr-defined]
            sys.modules[pacote] = vazio
    caminho = os.path.join(RAIZ, "app", "services", "whatsapp", "evolution_inbound.py")
    spec = importlib.util.spec_from_file_location("app.services.whatsapp.evolution_inbound", caminho)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["app.services.whatsapp.evolution_inbound"] = modulo
    spec.loader.exec_module(modulo)  # type: ignore[union-attr]
    return modulo


INBOUND = _carregar()


# --------------------------------------------------------------------------- #
# As formas MEDIDAS em produção, montadas como o WhatsApp as entrega
# --------------------------------------------------------------------------- #
# A tela citada dentro de `contextInfo` é real e é uma armadilha: traz o `title`
# e os botões da tela ANTERIOR. Um extrator que varra o payload sem excluí-la
# rotula a resposta com o nome da pergunta — e o corredor casaria a âncora
# errada, achando que o segurado respondeu o que na verdade lhe foi perguntado.
_MENU_CITADO = {"quotedMessage": {"listMessage": {"title": "MENU DE ASSISTENCIA"},
                                  "buttonsMessage": {"contentText": "MENU DE ASSISTENCIA"}}}

# 937 eventos — a grafia que o código do inbound NÃO conhecia.
BOTAO_GO = {"buttonsResponseMessage": {
    "selectedButtonID": "btn_vidro", "Response": {"SelectedDisplayText": "Vidros"},
    "type": "DISPLAY_TEXT", "contextInfo": _MENU_CITADO}}

# O pior caso: rótulo nenhum, só o id opaco. Texto vazio aqui = mensagem sumida.
BOTAO_SO_COM_ID = {"buttonsResponseMessage": {
    "selectedButtonID": "btn_0f3a91", "Response": {}, "type": 1,
    "contextInfo": _MENU_CITADO}}

# A grafia que o código conhecia — não pode regredir.
BOTAO_MINUSCULO = {"buttonsResponseMessage": {
    "selectedButtonId": "btn_guincho", "selectedDisplayText": "Guincho"}}

# 633 eventos — lista com título. Já funcionava.
LISTA = {"listResponseMessage": {
    "title": "Guincho", "listType": 1,
    "singleSelectReply": {"selectedRowId": "row_guincho"},
    "contextInfo": _MENU_CITADO}}

# 10 eventos — botão de template com rótulo.
BOTAO_COM_TITULO = {"templateButtonReplyMessage": {
    "selectedDisplayText": "Chaveiro", "selectedID": "btn_chaveiro",
    "selectedIndex": 1, "contextInfo": _MENU_CITADO}}

# 23 eventos — formulário nativo; o texto mora em `body`.
FORMULARIO = {"interactiveResponseMessage": {
    "body": {"text": "Formulario enviado"}, "contextInfo": _MENU_CITADO}}

# Uma grafia que NUNCA foi vista. Se ela passar, o defeito deixou de ser
# possível — e não só o caso conhecido deixou de acontecer.
BOTAO_SNAKE_CASE = {"buttons_response_message": {
    "selected_button_id": "btn_pane_seca", "selected_display_text": "Pane seca"}}


# --------------------------------------------------------------------------- #
# Casos
# --------------------------------------------------------------------------- #

def teste_a_grafia_de_937_cliques_nao_se_perde_mais():
    print("\n[1] A grafia real (D maiusculo) produz texto")
    lido = INBOUND._text_from_message(BOTAO_GO)
    checar(lido == "Vidros",
           "o clique de 937 eventos vira o ROTULO que o humano leu",
           f"lido={lido!r} — antes vinha None, e None vira skip:no_text")

    lido_id = INBOUND._text_from_message(BOTAO_SO_COM_ID)
    checar(lido_id == "btn_0f3a91",
           "e clique SEM rotulo ainda produz texto (o id opaco)",
           f"lido={lido_id!r} — aqui texto vazio APAGA a mensagem inteira, "
           "entao o id opaco vale mais que o silencio")


def teste_a_grafia_antiga_nao_regrediu():
    print("\n[2] O que ja funcionava continua funcionando")
    casos = {
        "botao d minusculo (o que o codigo conhecia)": (BOTAO_MINUSCULO, "Guincho"),
        "lista com titulo (633)": (LISTA, "Guincho"),
        "botao de template (10)": (BOTAO_COM_TITULO, "Chaveiro"),
        "formulario nativo (23)": (FORMULARIO, "Formulario enviado"),
    }
    for nome, (payload, esperado) in casos.items():
        lido = INBOUND._text_from_message(payload)
        checar(lido == esperado, f"{nome} → {esperado!r}", f"lido={lido!r}")


def teste_o_rotulo_ganha_do_id():
    print("\n[3] O rotulo tem precedencia sobre o id")
    # Se o id ganhasse, o atendente leria `btn_vidro` na tela em vez de "Vidros",
    # e a ancora do playbook (que casa texto legivel) deixaria de bater.
    checar(INBOUND._text_from_message(BOTAO_GO) != "btn_vidro",
           "com rotulo disponivel, o id NAO e usado",
           "id no lugar do texto quebraria as ancoras dos corredores")
    checar(INBOUND._text_from_message(BOTAO_MINUSCULO) == "Guincho",
           "idem na grafia minuscula")


def teste_o_contexto_citado_nao_contamina():
    print("\n[4] A tela CITADA nao empresta o titulo dela ao clique")
    for nome, payload in (("botao do GO", BOTAO_GO), ("so id", BOTAO_SO_COM_ID),
                          ("lista", LISTA), ("formulario", FORMULARIO)):
        lido = str(INBOUND._text_from_message(payload) or "")
        checar("MENU DE ASSISTENCIA" not in lido,
               f"{nome}: o contextInfo ficou de fora",
               f"lido={lido!r} — a resposta passaria a se chamar como a pergunta")


def teste_uma_grafia_nunca_vista_tambem_passa():
    print("\n[5] Grafia nova deixa de ser incidente")
    lido = INBOUND._text_from_message(BOTAO_SNAKE_CASE)
    checar(lido == "Pane seca",
           "snake_case (nunca visto em producao) tambem e lido",
           f"lido={lido!r} — conferir nome exato so conserta o caso conhecido")


def teste_o_texto_normal_nao_foi_afetado():
    print("\n[6] O caminho comum continua intacto")
    checar(INBOUND._text_from_message({"conversation": "Bati o carro"}) == "Bati o carro",
           "texto simples")
    checar(INBOUND._text_from_message({"extendedTextMessage": {"text": "Preciso de guincho"}})
           == "Preciso de guincho", "texto estendido")
    checar(INBOUND._text_from_message({"imageMessage": {"caption": "foto do para-choque"}})
           == "foto do para-choque", "legenda de imagem")
    checar(INBOUND._text_from_message({"audioMessage": {"seconds": 12}}) is None,
           "audio sem legenda continua sem texto",
           "inventar texto aqui faria o corredor responder a um silencio")
    checar(INBOUND._text_from_message({}) is None, "payload vazio devolve None")
    checar(INBOUND._text_from_message("nao sou dict") is None, "entrada invalida devolve None")


def teste_a_lista_de_grafias_mora_num_lugar_so():
    print("\n[7] Uma lista de grafias, nao duas")
    parser = _ler("app", "services", "whatsapp", "evolution_inbound.py")
    intake = _ler("app", "services", "atlas", "observer_intake.py")

    checar('"selectedButtonId"' not in parser,
           "a grafia errada de nome exato saiu do inbound",
           "era ela que devolvia None para 937 de cada 947 cliques")
    for nome in ("_CHAVES_DE_ID", "_CHAVES_DE_ROTULO", "_niveis_de", "_primeiro_valor"):
        checar(f"{nome}" in parser, f"{nome} vive no parser canonico")

    antes_do_import = intake.split("from app.services.whatsapp.evolution_inbound", 1)[0]
    checar("_CHAVES_DE_ID = (" not in antes_do_import
           and "def _niveis_de(" not in antes_do_import,
           "e o observador nao guarda uma SEGUNDA copia delas",
           "duas listas em dois arquivos e como a segunda fica para tras — "
           "foi assim que este defeito durou tres semanas a mais (CLAUDE.md §5)")
    checar("_CHAVES_DE_ID" in intake and "_niveis_de" in intake,
           "o observador continua usando as mesmas — importadas")


def teste_o_guarda_tem_como_falhar():
    print("\n[8] CONTROLE — o extrator de ANTES reprova nos mesmos casos")

    def extrator_antigo(message):
        """O código como era até 03/08/2026, verbatim."""
        def _clean(t):
            return str(t).strip() if isinstance(t, str) and t.strip() else ""
        btn = message.get("buttonsResponseMessage")
        if isinstance(btn, dict):
            picked = _clean(btn.get("selectedDisplayText")) or _clean(btn.get("selectedButtonId"))
            if picked:
                return picked
        tpl = message.get("templateButtonReplyMessage")
        if isinstance(tpl, dict) and _clean(tpl.get("selectedDisplayText")):
            return _clean(tpl.get("selectedDisplayText"))
        lst = message.get("listResponseMessage")
        if isinstance(lst, dict):
            picked = _clean(lst.get("title")) or _clean((lst.get("singleSelectReply") or {}).get("selectedRowId"))
            if picked:
                return picked
        inter = message.get("interactiveResponseMessage")
        if isinstance(inter, dict):
            picked = _clean((inter.get("body") or {}).get("text"))
            if picked:
                return picked
        return None

    checar(extrator_antigo(BOTAO_GO) is None,
           "o extrator de ANTES devolve None para a forma de 937 eventos",
           "se este caso ficar vermelho, o caso [1] passaria com ou sem o "
           "conserto — e nao guarda nada (CLAUDE.md §9.3)")
    checar(extrator_antigo(BOTAO_SO_COM_ID) is None,
           "e None tambem para o clique so-com-id")
    checar(extrator_antigo(BOTAO_SNAKE_CASE) is None,
           "e None para a grafia nunca vista")

    # E a linha de controle propriamente dita: nos casos que JA funcionavam, o
    # antigo e o novo dao o MESMO resultado. Sem isso, um "conserto" que apenas
    # trocasse o comportamento de tudo passaria por melhoria.
    for nome, payload in (("lista", LISTA), ("botao de template", BOTAO_COM_TITULO),
                          ("formulario", FORMULARIO), ("d minusculo", BOTAO_MINUSCULO)):
        antigo = extrator_antigo(payload)
        novo = INBOUND._text_from_message(payload)
        checar(antigo == novo,
               f"controle: {nome} le igual no antigo e no novo",
               f"antigo={antigo!r} novo={novo!r} — o conserto acrescenta, nao troca")


def main() -> int:
    print("=" * 70)
    print("O CLIQUE DO SEGURADO CHEGA AO CORREDOR — P-56")
    print("=" * 70)

    for teste in (teste_a_grafia_de_937_cliques_nao_se_perde_mais,
                  teste_a_grafia_antiga_nao_regrediu,
                  teste_o_rotulo_ganha_do_id,
                  teste_o_contexto_citado_nao_contamina,
                  teste_uma_grafia_nunca_vista_tambem_passa,
                  teste_o_texto_normal_nao_foi_afetado,
                  teste_a_lista_de_grafias_mora_num_lugar_so,
                  teste_o_guarda_tem_como_falhar):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 70)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O CLIQUE NAO SE PERDE MAIS — NEM NO HISTORICO, NEM AO VIVO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
