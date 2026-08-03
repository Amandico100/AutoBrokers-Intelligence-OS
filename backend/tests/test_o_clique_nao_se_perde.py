"""Três de cada quatro cliques da corretora eram apagados na leitura.

📊 Medido em 03/08/2026 sobre `observed_events`, projeto de produção
`dcajcvlzcjbmyapmklil`:

    fonte         tipo           cliques   sem texto   ilegível
    history_sync  button_reply       947         937      98,9%
    history_sync  flow_reply          23          23     100,0%
    history_sync  list_reply         633           0       0,0%
    live          button_reply        10           0       0,0%

O extrator de `observer_intake.py` procurava três chaves:

    title = (m.get("title") or (m.get("singleSelectReply") or {}).get("selectedRowId")
             or (m.get("selectedDisplayText")) or "")

E as formas que a produção realmente entrega são quatro — a coluna
`interactive->>'raw_keys'` guardou todas elas:

    ["contextInfo", "listType", "singleSelectReply", "title"]        633  ok
    ["contextInfo", "selectedDisplayText", "selectedID", "selectedIndex"] 10  ok
    ["Response", "contextInfo", "selectedButtonID", "type"]          937  VAZIO
    ["InteractiveResponseMessage", "body", "contextInfo"]             23  VAZIO

O `listResponseMessage` tem `title` e sobreviveu. O `buttonsResponseMessage` do
histórico não traz **nenhuma** das três chaves procuradas, e virou string
vazia. O `interactiveResponseMessage` guarda o texto em `body` — ninguém olhava.

Não é defeito exclusivo do histórico: a MESMA forma
`["Response", "contextInfo", "selectedButtonID", "type"]` aparece com
`source='live'` em `attendance_transcripts` (4 eventos, 4 sem texto). Os 10
cliques ao vivo que funcionam no Atlas chegam por outro caminho — o evento
`ButtonClick` do GO, que já lia `buttonId`.

O que a string vazia custou
---------------------------
O Tecelão nomeia a aresta com `label = prev_choice or "→"` e a arquiva em
`edges[f"{origem}|{label}"]`. Sem rótulo, **todos** os cliques distintos de um
mesmo menu colapsam numa única aresta chamada "→": o mapa deixa de saber que
existem dois caminhos, e passa a mostrar um.

📊 Nos mapas mais recentes de cada seguradora, em 03/08/2026:

    seguradora   arestas   sem rótulo
    allianz         1894          481   25,4%
    porto            977          436   44,6%
    yelum            821          303   36,9%
    hdi              609          276   45,3%
    tokio             55           35   63,6%
    ------------------------------------------
    total           4999         1805   36,1%

E o estrago não parava no rótulo: com `text` vazio, a identidade da mensagem
histórica — `sha1(from_me|msg_type|text)` — era a MESMA para dois cliques
diferentes no mesmo segundo, e o `ignore_duplicates=True` do upsert descartava o
segundo **em silêncio**. Que segundos com mensagens distintas existem neste
histórico está medido: 367 grupos (counterparty, segundo, direção, tipo) com
textos diferentes, 738 linhas. O defeito de leitura virava perda de linha.

O que este teste garante
------------------------
1. as quatro formas medidas produzem identificação de aresta;
2. um clique que só tem id — sem texto nenhum — ainda distingue a aresta;
3. rótulo não se inventa: sem texto legível, `text` fica vazio e o id NUNCA é
   promovido a rótulo;
4. o `contextInfo`, que carrega a tela CITADA, não empresta o título dela ao
   clique;
5. dois cliques diferentes no mesmo segundo têm identidades diferentes;
6. e a identidade de quem NÃO tem id continua byte a byte a de sempre — senão a
   próxima sincronização gravaria uma cópia de cada mensagem de texto.
"""

from __future__ import annotations

import importlib.util
import io
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FALHAS: list[str] = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(*p: str) -> str:
    with io.open(os.path.join(RAIZ, *p), encoding="utf-8") as fh:
        return fh.read()


def _sem_comentario(f: str) -> str:
    return "\n".join(l for l in f.split("\n") if not l.lstrip().startswith("#"))


# --------------------------------------------------------------------------- #
# Carga dos módulos REAIS, sem o pacote
# --------------------------------------------------------------------------- #
# `app/services/__init__.py` importa `openai` e mais meia dúzia de coisas que
# este teste não precisa e que a máquina pode não ter. Carregar os três arquivos
# pelo caminho, com os pacotes vazios registrados antes, executa o código de
# verdade — não uma cópia dele — sem arrastar a aplicação inteira junto.
def _carregar():
    for pacote in ("app", "app.services", "app.services.atlas",
                   "app.services.whatsapp"):
        if pacote not in sys.modules:
            vazio = types.ModuleType(pacote)
            vazio.__path__ = []  # type: ignore[attr-defined]
            sys.modules[pacote] = vazio

    def _do_arquivo(nome: str, *caminho: str):
        spec = importlib.util.spec_from_file_location(nome, os.path.join(RAIZ, *caminho))
        modulo = importlib.util.module_from_spec(spec)
        sys.modules[nome] = modulo
        spec.loader.exec_module(modulo)  # type: ignore[union-attr]
        return modulo

    _do_arquivo("app.services.whatsapp.evolution_inbound",
                "backend", "app", "services", "whatsapp", "evolution_inbound.py")
    intake = _do_arquivo("app.services.atlas.observer_intake",
                         "backend", "app", "services", "atlas", "observer_intake.py")
    historia = _do_arquivo("app.services.atlas.history_ingest",
                           "backend", "app", "services", "atlas", "history_ingest.py")
    tecelao = _do_arquivo("app.services.atlas.weaver",
                          "backend", "app", "services", "atlas", "weaver.py")
    return intake, historia, tecelao


INTAKE, HISTORIA, TECELAO = _carregar()


# --------------------------------------------------------------------------- #
# As quatro formas MEDIDAS em produção, montadas como o WhatsApp as entrega
# --------------------------------------------------------------------------- #
# A tela citada dentro de `contextInfo` é real e é uma armadilha: ela traz o
# `title` e os botões da tela ANTERIOR. Um extrator que varra o payload sem
# excluí-la rotula a resposta com o nome da pergunta.
_MENU_CITADO = {"quotedMessage": {"listMessage": {"title": "MENU DE ASSISTENCIA"},
                                  "buttonsMessage": {"contentText": "MENU DE ASSISTENCIA"}}}

# 633 eventos — ["contextInfo", "listType", "singleSelectReply", "title"]
LISTA = {"listResponseMessage": {
    "title": "Guincho", "listType": 1,
    "singleSelectReply": {"selectedRowId": "row_guincho"},
    "contextInfo": _MENU_CITADO}}

# 10 eventos — ["contextInfo", "selectedDisplayText", "selectedID", "selectedIndex"]
BOTAO_COM_TITULO = {"templateButtonReplyMessage": {
    "selectedDisplayText": "Chaveiro", "selectedID": "btn_chaveiro",
    "selectedIndex": 1, "contextInfo": _MENU_CITADO}}

# 937 eventos — ["Response", "contextInfo", "selectedButtonID", "type"]
# 💭 O miolo de `Response` é INFERÊNCIA: o banco guardou as chaves, não os
# valores. Por isso o extrator não confere nome exato — e por isso o caso
# BOTAO_SO_COM_ID abaixo existe, para provar que a aresta sobrevive mesmo se a
# inferência estiver errada.
BOTAO_GO = {"buttonsResponseMessage": {
    "selectedButtonID": "btn_vidro", "Response": {"SelectedDisplayText": "Vidros"},
    "type": "DISPLAY_TEXT", "contextInfo": _MENU_CITADO}}

# O pior caso: rótulo nenhum, só o id opaco.
BOTAO_SO_COM_ID = {"buttonsResponseMessage": {
    "selectedButtonID": "btn_0f3a91", "Response": {}, "type": 1,
    "contextInfo": _MENU_CITADO}}

# 23 eventos — ["InteractiveResponseMessage", "body", "contextInfo"]
FORMULARIO = {"interactiveResponseMessage": {
    "body": {"text": "Formulario enviado"},
    "InteractiveResponseMessage": {
        "nativeFlowResponseMessage": {"name": "flow_sinistro", "paramsJSON": "{}"}},
    "contextInfo": _MENU_CITADO}}


def _aresta(payload: dict):
    """O caminho inteiro: payload → captura → o rótulo que o Tecelão arquiva."""
    msg_type, text, interactive, _ = INTAKE._extract_content(payload)
    escolha = {"text": text, "interactive": interactive}
    return msg_type, text, interactive, TECELAO._choice_label(escolha)


def teste_as_quatro_formas_identificam_a_aresta():
    print("\n[C1] As quatro formas medidas em producao viram aresta")
    formas = {"lista (633)": LISTA, "botao com titulo (10)": BOTAO_COM_TITULO,
              "botao do GO (937)": BOTAO_GO, "formulario nativo (23)": FORMULARIO}
    rotulos = {}
    for nome, payload in formas.items():
        tipo, texto, inter, rotulo = _aresta(payload)
        checar(bool(rotulo), f"{nome} produz rotulo de aresta",
               f"tipo={tipo} texto={texto!r} interactive={inter}")
        checar(bool((inter or {}).get("id")), f"{nome} guarda o id do clique",
               "id opaco distingue arestas; string vazia nao distingue nada")
        rotulos[nome] = rotulo

    checar(len(set(rotulos.values())) == len(rotulos),
           "as quatro formas geram rotulos DIFERENTES entre si",
           f"{rotulos}")
    # A chave da aresta é `origem|rótulo`: rótulos iguais fundem caminhos.
    chaves = {f"no_menu|{r}" for r in rotulos.values()}
    checar(len(chaves) == 4, "quatro cliques = quatro arestas no mapa",
           f"{sorted(chaves)}")


def teste_o_id_sozinho_ja_distingue():
    print("\n[C2] Clique sem rotulo nenhum ainda distingue a aresta")
    tipo, texto, inter, rotulo = _aresta(BOTAO_SO_COM_ID)
    checar(tipo == "button_reply", "o tipo continua sendo reconhecido", tipo)
    checar((inter or {}).get("id") == "btn_0f3a91",
           "o id opaco foi guardado em interactive.id", str(inter))
    checar(bool(rotulo), "o Tecelao tem o que casar", f"rotulo={rotulo!r}")

    # E dois ids opacos distintos NÃO podem virar a mesma aresta.
    outro = {"buttonsResponseMessage": {"selectedButtonID": "btn_ff0021",
                                        "Response": {}, "type": 1}}
    checar(_aresta(outro)[3] != rotulo,
           "dois ids opacos diferentes geram arestas diferentes",
           "era exatamente isto que colapsava em uma aresta '->' unica")


def teste_o_rotulo_nao_se_inventa():
    print("\n[C3] Rotulo nao se inventa")
    _, texto, inter, _ = _aresta(BOTAO_SO_COM_ID)
    checar(not texto,
           "sem texto legivel, o texto do evento fica VAZIO",
           f"texto={texto!r} — o id nao vira rotulo para o corretor ler")
    checar("title" not in (inter or {}),
           "e nenhum 'title' e fabricado a partir do id",
           str(inter))

    # E quando o texto EXISTE, ele é o texto de verdade — não o id.
    _, texto_real, inter_real, _ = _aresta(BOTAO_GO)
    checar(texto_real == "Vidros",
           "quando o rotulo existe, ele e o que o humano leu",
           f"texto={texto_real!r}")
    checar((inter_real or {}).get("id") == "btn_vidro",
           "e o id continua guardado ao lado dele, nao no lugar dele")


def teste_o_contexto_citado_nao_contamina():
    print("\n[C4] A tela CITADA nao empresta o titulo dela ao clique")
    for nome, payload in (("lista", LISTA), ("botao do GO", BOTAO_GO),
                          ("so id", BOTAO_SO_COM_ID), ("formulario", FORMULARIO)):
        _, texto, inter, rotulo = _aresta(payload)
        sujo = "MENU DE ASSISTENCIA"
        checar(sujo not in str(texto) and sujo not in str(inter),
               f"{nome}: o contextInfo ficou de fora",
               "descer no contextInfo faria a resposta se chamar como a pergunta")

    fonte = _sem_comentario(_ler("backend", "app", "services", "atlas", "observer_intake.py"))
    checar("_CHAVE_DE_CONTEXTO" in fonte and 'nk == _CHAVE_DE_CONTEXTO' in fonte,
           "a exclusao do contextInfo e explicita no codigo, nao acidental")


def teste_a_busca_cega_antiga_sumiu():
    print("\n[C5] A busca que so conhecia tres chaves nao existe mais")
    fonte = _ler("backend", "app", "services", "atlas", "observer_intake.py")
    codigo = _sem_comentario(fonte)
    checar('m.get("title") or (m.get("singleSelectReply") or {}).get("selectedRowId")'
           not in codigo,
           "a expressao de tres chaves saiu",
           "ela era cega para 937 dos 947 cliques de botao")
    for chave in ("selectedbuttonid", "selectedid", "selectedrowid"):
        checar(chave in codigo, f"a chave real '{chave}' e procurada")
    for chave in ("selecteddisplaytext", "title", "text"):
        checar(chave in codigo, f"a chave de rotulo '{chave}' e procurada")
    checar('"selected"' in codigo,
           "o id tambem vai para 'selected'",
           "e onde weaver._choice_label procura — e ninguem escrevia ali")

    # O contrato com o Tecelão tem de continuar valendo do outro lado.
    tec = _sem_comentario(_ler("backend", "app", "services", "atlas", "weaver.py"))
    checar('for k in ("title", "selected")' in tec,
           "o Tecelao continua lendo 'title' e depois 'selected'",
           "se esta linha mudar, o id opaco para de rotular aresta")


def teste_a_identidade_do_historico_separa_cliques():
    print("\n[C6] Dois cliques no mesmo segundo sao duas mensagens")
    mid = HISTORIA._history_message_id
    a = mid("5511999", 1754200000, 0, True, "button_reply", "", "btn_vidro")
    b = mid("5511999", 1754200000, 1, True, "button_reply", "", "btn_guincho")
    checar(a != b,
           "ids de clique diferentes no mesmo segundo geram identidades diferentes",
           f"{a} vs {b}")
    checar(a == mid("5511999", 1754200000, 7, True, "button_reply", "", "btn_vidro"),
           "e a MESMA mensagem gera o MESMO id, com outro indice",
           "identidade instavel foi o que gerou 2,66x de copias em 28/07")


def teste_a_identidade_de_quem_nao_tem_id_nao_mudou():
    print("\n[C7] Quem nao tem id mantem a identidade de sempre")
    mid = HISTORIA._history_message_id
    # O valor abaixo foi calculado com o codigo ANTERIOR a esta correcao.
    # Se ele mudar, a proxima sincronizacao grava uma copia de cada uma das
    # 13.659 mensagens de texto do historico.
    checar(mid("5511", 1700000000, 0, True, "button_reply", "")
           == "hist-5511-1700000000-b845f2def997",
           "id sem interativo e byte a byte o mesmo de antes",
           "um '|' a mais no fim do corpo do hash duplicaria o historico inteiro")
    checar(mid("5511", 1700000000, 0, True, "text", "Oi")
           == mid("5511", 1700000000, 0, True, "text", "Oi", ""),
           "ident vazio e ident ausente sao a mesma coisa")
    checar(mid("5511", 1700000000, 0, True, "text", "Oi")
           != mid("5511", 1700000000, 0, True, "text", "Oi", "x"),
           "e ident presente muda a identidade (senao nao separaria nada)")


def teste_o_historico_nao_descarta_o_clique():
    print("\n[C8] O caminho do historico nao joga o clique fora")
    fonte = _ler("backend", "app", "services", "atlas", "history_ingest.py")
    codigo = _sem_comentario(fonte)
    checar("if not text and not media_meta and not interactive:" in codigo,
           "o descarte exige AUSENCIA das tres coisas",
           "clique sem texto ainda tem interactive — e por isso nao e descartado")
    checar('(interactive or {}).get("id")' in codigo,
           "o id do clique entra na identidade da mensagem")
    checar('"interactive": (dict(interactive) if interactive else None)' in codigo,
           "e o interactive inteiro e gravado, nao um resumo dele")

    # Prova funcional do descarte: o clique so-id passa pelo guarda.
    _, texto, inter, _ = _aresta(BOTAO_SO_COM_ID)
    checar(not (not texto and not None and not inter),
           "o clique so-com-id sobrevive ao guarda de descarte",
           f"texto={texto!r} interactive={bool(inter)}")


def main() -> int:
    print("=" * 68)
    print("O CLIQUE NAO SE PERDE — 937 DE 947 VOLTAM A TER IDENTIDADE")
    print("=" * 68)
    for t in (teste_as_quatro_formas_identificam_a_aresta,
              teste_o_id_sozinho_ja_distingue,
              teste_o_rotulo_nao_se_inventa,
              teste_o_contexto_citado_nao_contamina,
              teste_a_busca_cega_antiga_sumiu,
              teste_a_identidade_do_historico_separa_cliques,
              teste_a_identidade_de_quem_nao_tem_id_nao_mudou,
              teste_o_historico_nao_descarta_o_clique):
        try:
            t()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{t.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {t.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 68)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("TODO CLIQUE MEDIDO EM PRODUCAO VIRA ARESTA IDENTIFICAVEL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
