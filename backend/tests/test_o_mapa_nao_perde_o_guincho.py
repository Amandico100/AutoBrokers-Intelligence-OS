"""O mapa do Atlas não pode perder a opção que aciona o GUINCHO.

📊 O DEFEITO, medido em produção em 15/08/2026 nos 10 mapas ativos:

    zurich/a8087cb9567d   texto "Assistência {VALOR}"   options começa em "Assistência a vidros"
    mapfre/e3bc3dfdca75   texto "Assistência {VALOR}"   options começa em "Sinistro"
    tokio/b1b457af6ca6    texto "Assistência {VALOR}"   options começa em "Informações de sinistro"
    yelum/f372a91db870    "Botão 1: ASSISTENCIA 24H"    options tem 2 de 3

    "Assistência 24h": 52 vezes emitida pela URA · 0 vezes no options[]

Um corredor que leia a primeira opção aperta **"Assistência a vidros"** achando
que apertou **"Assistência 24h"**. É o erro que só aparece com um segurado
parado na estrada esperando guincho.

A CAUSA — uma só, com dois formatos de render
==============================================
`_LABELED_VALUE` está ancorado em `^` e lista `assistência` como palavra-rótulo.
O título de menu chega ao `templatize` **sozinho**, então o `^` alcança a sua
primeira palavra sempre. Vindo um dígito depois (`24h`), `_aplicar_rotulo`
devolve `Assistência {VALOR}` — e `_real_options` descarta rótulo com
placeholder.

📊 As três medições que fecham a causa (e estão testadas abaixo):

    "Assistência 24h"          -> {VALOR}   descartado
    "Assistência a vidros"     -> intacto   (casa o MESMO rótulo; `a` não é dígito)
    "Acionar assistência 24h"  -> intacto   (o `^` não a alcança)

Logo o fator causal é **dígito logo depois da palavra-rótulo na posição 0** —
não a palavra, não o `24h`.

E O SEGUNDO DEFEITO, no mesmo pipeline
=======================================
📊 141 CPF, 34 CNPJ, 105 placas e 52 telefones gravados como **rótulo de
aresta**: `5b7ca670e1f1|110.014.961-91 -> 2bd9b17f842c`. A URA pediu o CPF, o
segurado digitou, e o que ele digitou virou a aresta. Os nós eram mascarados;
a escolha do humano não passava por lugar nenhum.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}" + (f"  ({detalhe})" if detalhe else ""))
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _screen_node():
    """O `screen_node` REAL — a montagem do nó, não só a peça.

    Ele importa `cartographer` e `ura_map_service` por dentro; os dois entram
    reais, por caminho, porque dublá-los validaria a minha suposição sobre o
    formato do nó em vez do produto.
    """
    T = _templater()
    for nome, rel in (("app.services.cartographer",
                       ("app", "services", "cartographer.py")),
                      ("app.services.ura_map_service",
                       ("app", "services", "ura_map_service.py"))):
        if nome in sys.modules:
            continue
        spec = importlib.util.spec_from_file_location(
            nome, os.path.join(RAIZ, *rel))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[nome] = mod
        spec.loader.exec_module(mod)
    return T.screen_node


def _templater():
    """O templater REAL do Atlas, carregado por caminho.

    ⚠️ Não confundir com `scripts/destilacao_max/mascarar.py`, que tem uma
    função de mesmo nome e outro propósito. O que está sob teste é o do Atlas.
    """
    nome = "app.services.atlas.templater"
    if nome in sys.modules:
        return sys.modules[nome]
    # 🔴 Pacotes-sombra com `__path__` REAL.
    #
    # `app/services/__init__.py` importa o app inteiro (e `openai`, que não está
    # neste ambiente), então não dá para importar `app.services` de verdade. Mas
    # um `ModuleType` puro **não é pacote** e `from app.services.x import y`
    # explode com "is not a package". Dando `__path__`, o import normal do
    # Python encontra os submódulos sem executar o `__init__` pesado.
    for pkg, partes in (("app", ("app",)),
                        ("app.services", ("app", "services")),
                        ("app.services.atlas", ("app", "services", "atlas"))):
        if pkg not in sys.modules:
            mod = types.ModuleType(pkg)
            mod.__path__ = [os.path.join(RAIZ, *partes)]  # type: ignore[attr-defined]
            sys.modules[pkg] = mod
    caminho = os.path.join(RAIZ, "app", "services", "atlas", "templater.py")
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


# ── 1 · a opção do guincho sobrevive ─────────────────────────────────────────

def teste_a_opcao_do_guincho_nao_e_descartada() -> None:
    """🔴 Passa pelo `screen_node` REAL — é ele que monta o nó do mapa.

    A primeira versão deste teste chamava `templatize` direto, e a mutação que
    tirava `rotulo_de_campo=False` de dentro do `screen_node` ficou **VERDE**:
    eu testava a peça, não a montagem. O defeito de produção mora exatamente na
    montagem.
    """
    print("\n[1] A opção que aciona o guincho sobrevive ao mascaramento")
    T = _templater()
    _no = _screen_node()

    def opcoes(titulo: str) -> list:
        """As opções que o MAPA recebe para um menu com este título."""
        no = _no(f"Escolha um dos serviços\n{titulo}\nSinistro\nCarro reserva",
                 {"kind": "list", "options": [{"title": titulo},
                                              {"title": "Sinistro"},
                                              {"title": "Carro reserva"}]})
        return [o["label"] for o in no.get("options") or []]

    for titulo in ("Assistência 24h", "ASSISTENCIA 24H", "Assistência 24H"):
        rotulos = opcoes(titulo)
        checar(titulo in rotulos,
               f"🔴 '{titulo}' chega ao MAPA como opção, inteira",
               f"opções do nó: {rotulos}")
        checar(len(rotulos) == 3,
               "e as três opções do menu chegam",
               f"{len(rotulos)} de 3")

    # 🔴 OS CONTROLES QUE DÃO DIREITO À CONCLUSÃO.
    #
    # Sem eles, o teste acima passaria se alguém simplesmente desligasse todo o
    # mascaramento — e aí a correção teria trocado um defeito por um vazamento.
    checar("{CPF}" in T.templatize("110.014.961-91", rotulo_de_campo=False),
           "🔴 CONTROLE — CPF continua sendo mascarado neste modo",
           T.templatize("110.014.961-91", rotulo_de_campo=False))
    checar("{TELEFONE}" in T.templatize("(47) 99627-4743", rotulo_de_campo=False),
           "🔴 CONTROLE — telefone continua sendo mascarado",
           T.templatize("(47) 99627-4743", rotulo_de_campo=False))
    checar(not T._real_options([T.templatize("Placa: QJQ0A91")]),
           "🔴 CONTROLE — eco de dado do cliente CONTINUA sendo descartado",
           "'Placa: QJQ0A91' não é clique de menu")

    # 🔴 E o caso que SÓ o filtro de placeholder segura.
    #
    # O controle acima é derrubado por DUAS regras — `_DATA_ECHO` também pega
    # "Rótulo: valor". Medido por mutação: apagando o filtro de placeholder o
    # teste ficava VERDE, porque a outra regra cobria o caso. Um controle
    # coberto por duas regras não prova nenhuma das duas.
    #
    # Um `{CPF}` sozinho não tem forma de "Rótulo: valor" — só o filtro de
    # placeholder o descarta. É o segurado que digitou o documento aparecendo
    # como se fosse um botão do menu.
    checar(not T._real_options(["{CPF}"]),
           "🔴 CONTROLE — placeholder solto não vira opção de menu",
           "e SÓ o filtro de placeholder segura este caso")
    checar(T._real_options(["Sinistro"]) == ["Sinistro"],
           "CONTROLE — e opção de verdade continua passando")

    # A tela inteira (não o título solto) mantém a rede antiga ligada.
    checar(T.templatize("Placa: QJQ0A91") != "Placa: QJQ0A91",
           "CONTROLE — em TELA, o rótulo de campo continua valendo")


# ── 2 · a causa, medida nos três casos que a isolam ──────────────────────────

def teste_a_causa_e_o_digito_depois_do_rotulo() -> None:
    print("\n[2] A causa isolada: dígito logo depois da palavra-rótulo")
    T = _templater()

    # Com o rótulo de campo LIGADO — o modo antigo, que é onde o defeito mora.
    com_rotulo = lambda s: T.templatize(s)  # noqa: E731

    checar(com_rotulo("Assistência 24h") == "Assistência {VALOR}",
           "🔴 o defeito é reproduzível: 'Assistência 24h' vira {VALOR}",
           com_rotulo("Assistência 24h"))
    checar(com_rotulo("Assistência a vidros") == "Assistência a vidros",
           "🔴 CONTROLE — 'Assistência a vidros' casa o MESMO rótulo e sobrevive",
           "logo o culpado não é a palavra 'assistência'")
    checar(com_rotulo("Acionar assistência 24h") == "Acionar assistência 24h",
           "🔴 CONTROLE — com a palavra fora da posição 0, sobrevive",
           "logo o culpado não é o '24h'")

    checar(com_rotulo("Assistência 24h") != com_rotulo("Assistência a vidros"),
           "CONTROLE — os dois casos CONSEGUEM ser diferentes",
           "um guarda que compara duas coisas iguais não guarda nada")


# ── 3 · o CPF não vira aresta ────────────────────────────────────────────────

def teste_o_que_o_segurado_digitou_nao_vira_aresta() -> None:
    print("\n[3] O que o segurado digitou não vira rótulo de aresta")
    fonte = open(os.path.join(RAIZ, "app", "services", "atlas", "weaver.py"),
                 encoding="utf-8").read()

    i = fonte.find("def _choice_label")
    j = fonte.find("\ndef ", i + 10)
    corpo = fonte[i:j]
    checar(len(corpo) > 200, "CONTROLE — recortei o corpo real de _choice_label",
           f"{len(corpo)} caracteres")

    # Executa a função REAL, com o templater real injetado.
    T = _templater()
    ns = {"Optional": object, "Dict": dict, "Any": object}
    exec(compile(corpo, "_choice_label", "exec"), ns)  # noqa: S102
    rotulo = ns["_choice_label"]

    checar("{CPF}" in (rotulo({"text": "110.014.961-91"}) or ""),
           "🔴 o CPF digitado vira {CPF} na aresta, não o número",
           str(rotulo({"text": "110.014.961-91"})))
    checar("{CPF}" in (rotulo({"interactive": {"title": "110.014.961-91"}}) or ""),
           "e pelo caminho do interativo também",
           str(rotulo({"interactive": {"title": "110.014.961-91"}})))

    # 🔴 O CONTROLE: mascarar não pode comer a navegação.
    checar(rotulo({"text": "2"}) == "2",
           "🔴 CONTROLE — a TECLA digitada continua intacta",
           "se a tecla virasse placeholder, o mapa perderia a navegação inteira")
    checar(rotulo({"interactive": {"title": "Assistência 24h"}}) == "Assistência 24h",
           "🔴 CONTROLE — e o título de botão chega inteiro na aresta")
    checar(rotulo({"text": "Guincho"}) == "Guincho",
           "CONTROLE — palavra comum passa intacta")
    checar(rotulo(None) is None and rotulo({"text": "  "}) is None,
           "CONTROLE — sem escolha, não há rótulo")

    # 🔴 A ORDEM IMPORTA, e este caso é construído para provar isso.
    #
    # O CPF começa no caractere 51 e termina no 65 — ele ATRAVESSA o corte de
    # 60. Mascarando primeiro, o `{CPF}` cabe inteiro. Cortando primeiro, o que
    # sobra é `110.014.9`, que não é CPF para regex nenhum: o número fica em
    # claro, picado, e nada avisa.
    #
    # ⚠️ A primeira versão deste controle era
    # `"{CPF}" in longo or len(longo) <= 60` — e o `or` a deixava passar de
    # graça. A mutação "mascarar DEPOIS de cortar" ficou VERDE. Guarda com
    # `or` frouxo é guarda que não guarda.
    atravessa = "x" * 50 + " 110.014.961-91"
    longo = rotulo({"text": atravessa}) or ""
    checar("{CPF}" in longo,
           "🔴 CONTROLE — mascara ANTES de cortar em 60",
           f"o CPF atravessa o corte; resultado: {longo!r}")
    checar("110.014" not in longo,
           "CONTROLE — e nenhum pedaço do CPF sobra em claro", longo)


def teste_o_mapa_e_neutro_de_corretora() -> None:
    """O Atlas é UM só e é de TODAS — logo não pode nomear nenhuma.

    Doutrina: `docs/canon/O-ATLAS-E-UM-SO-E-E-DE-TODAS.md`. O agente de
    atendimento é global; quem personaliza é o dashboard, com dados de
    configuração. Um nó que já traz "Resulta" escrito dentro faz o agente da
    próxima corretora se apresentar com o nome de outra empresa.

    📊 Os quatro literais abaixo foram medidos em mapas ATIVOS em 15/08/2026.
    """
    print("\n[4] O mapa não nomeia corretora nem atendente")
    T = _templater()

    # A configuração — em produção vem de `companies`; aqui é injetada, porque
    # o que está sob teste é a REGRA, não o acesso ao banco.
    T._CACHE_MARCAS = ("Resulta Seguros", "AutoFleet", "Resulta", "Amandus")
    try:
        casos = [
            ("*Saionara - Resulta*, por ser um item essencial, vou te transferir",
             ("Saionara", "Resulta")),
            ("Olá RESULTA CORRETORA DE SEGUROS LTDA, Nos ajude a continuar",
             ("RESULTA",)),
            ("Maria Regina - Autofleet Seguros", ("Maria", "Regina", "Autofleet")),
            ("Olá Maria Regina - Autofleet Seguros, seja bem-vindo(a)",
             ("Maria", "Regina", "Autofleet")),
        ]
        for bruto, proibidos in casos:
            saida = T.templatize(bruto)
            sobrou = [p for p in proibidos if p in saida]
            checar(not sobrou,
                   f"🔴 nada de '{proibidos[0]}…' sobra no mapa",
                   f"{saida!r}" + (f" — SOBROU {sobrou}" if sobrou else ""))
            # 🔴 E o lugar da pessoa fica MARCADO, não apagado.
            #
            # Medido por mutação: apagar o `{NOME}` da regra também remove o
            # nome — o teste de vazamento passava, e a frase virava "- {CORRETORA}".
            # Quem ler o mapa depois não saberia que ali havia uma saudação, e o
            # corredor perderia a estrutura da tela.
            checar("{CORRETORA}" in saida,
                   "e o lugar da corretora fica marcado", saida)

        checar("{NOME}" in T.templatize("*Saionara - Resulta*, vou te transferir"),
               "🔴 e o lugar da ATENDENTE também fica marcado, não apagado",
               T.templatize("*Saionara - Resulta*, vou te transferir"))

        # 🔴 A GUARDA QUE IMPEDE O TIRO NO PÉ, testada isolada.
        #
        # Uma corretora chamada "Porto Seguros" não pode fazer o mascarador
        # comer "Porto Seguro". Esta decisão estava enterrada dentro de uma
        # função que precisa de banco — e por isso a mutação que a removia
        # ficava VERDE. Agora ela é pura e tem como falhar.
        proibidas = T._marcas_das_seguradoras()
        checar("porto" in proibidas and "yelum" in proibidas,
               "CONTROLE — o registro de seguradoras alimenta a lista de proibidas",
               f"{len(proibidas)} nomes protegidos")
        checar(not T.pode_virar_marca("Porto", proibidas),
               "🔴 corretora com nome de SEGURADORA não vira marca")
        checar(not T.pode_virar_marca("Porto Seguros Corretora", proibidas),
               "🔴 nem quando a colisão está só na primeira palavra")
        checar(T.pode_virar_marca("Resulta", proibidas),
               "🔴 CONTROLE — e uma corretora de nome próprio VIRA marca",
               "senão a guarda barraria tudo e não guardaria nada")
        checar(not T.pode_virar_marca("Seguros", proibidas)
               and not T.pode_virar_marca("Ltda", proibidas),
               "CONTROLE — palavra genérica nunca vira marca")

        # 🔴 OS CONTROLES — sem eles isto vira licença para comer o produto.
        #
        # O mascarador que engole conhecimento é pior que o vazamento: o
        # vazamento se conserta, o conhecimento perdido não volta.
        intocaveis = [
            ("Porto Seguro", "SEGURADORA não é corretora"),
            ("A Yelum permanece a sua disposição", "nome de seguradora fica"),
            ("Roubo, furto e incêndio têm franquia própria", "prosa fica"),
            ("Guincho para pane mecânica", "conhecimento de produto fica"),
            ("Assistência a vidros", "opção de menu fica"),
        ]
        for texto, porque in intocaveis:
            checar(T.templatize(texto) == texto,
                   f"🔴 CONTROLE — {porque}",
                   f"{texto!r} -> {T.templatize(texto)!r}")

    finally:
        T._CACHE_MARCAS = None

    # 🔴 AGORA SEM A CONFIGURAÇÃO — a regex sozinha, isolada.
    #
    # Medido por mutação: com a lista de marcas preenchida, a regex vira
    # REDUNDANTE — apagar a alternância de sufixo mantinha o teste verde,
    # porque `_apagar_marcas_de_corretora` cobria o caso. Duas defesas para o
    # mesmo caso não provam nenhuma das duas.
    #
    # Este bloco roda com a configuração VAZIA, que é o estado de qualquer
    # ambiente sem banco — e é justamente onde a regex é a única defesa.
    T._CACHE_MARCAS = ()
    try:
        checar(T.templatize("Maria Regina - Autofleet Seguros") == "{NOME} - {CORRETORA}",
               "🔴 SEM configuração, a regex ainda pega nome COMPOSTO",
               T.templatize("Maria Regina - Autofleet Seguros"))
        checar(T.templatize("Joana - Beta Corretora") == "{NOME} - {CORRETORA}",
               "🔴 SEM configuração, a regex pega o sufixo 'Corretora'",
               "só a alternância de sufixo segura este caso")
        checar(T.templatize("Paulo - Gama Ltda") == "{NOME} - {CORRETORA}",
               "🔴 SEM configuração, a regex pega o sufixo 'Ltda'",
               T.templatize("Paulo - Gama Ltda"))
        checar("Porto Seguro" in T.templatize("Cotação na Porto Seguro"),
               "CONTROLE — e continua não comendo seguradora sem configuração")
    finally:
        T._CACHE_MARCAS = ("Resulta Seguros", "AutoFleet", "Resulta", "Amandus")

    try:
        # E o portão de promoção precisa CONSEGUIR dizer não.
        sujo = {"nodes": {"a": {"text": "Olá RESULTA CORRETORA DE SEGUROS LTDA"}},
                "edges": {}}
        limpo = {"nodes": {"a": {"text": "Olá {CORRETORA}"}}, "edges": {}}
        UMS = _ura_map_service()
        checar(UMS._tem_marca_de_corretora(sujo) >= 1,
               "🔴 o portão de promoção RECONHECE razão social",
               "antes era uma lista de 3 literais e dava False para os 4 casos")
        checar(UMS._tem_marca_de_corretora(limpo) == 0,
               "🔴 CONTROLE — e deixa passar o mapa limpo",
               "um portão que barra tudo não é portão")

        # A aresta, que era o ponto cego.
        com_aresta = {"nodes": {}, "edges": {"a|Resulta Seguros": {"label": "Resulta Seguros"}}}
        checar(UMS._tem_marca_de_corretora(com_aresta) >= 1,
               "🔴 e o portão olha a ARESTA, não só o texto do nó",
               "era ali que estavam os 141 CPF")
    finally:
        T._CACHE_MARCAS = None


def _ura_map_service():
    nome = "app.services.ura_map_service"
    if nome in sys.modules:
        return sys.modules[nome]
    _templater()  # garante os pacotes-sombra
    spec = importlib.util.spec_from_file_location(
        nome, os.path.join(RAIZ, "app", "services", "ura_map_service.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    print("=" * 74)
    print("O MAPA NÃO PERDE O GUINCHO — e o CPF não vira aresta")
    print("=" * 74)
    for teste in (teste_a_opcao_do_guincho_nao_e_descartada,
                  teste_a_causa_e_o_digito_depois_do_rotulo,
                  teste_o_que_o_segurado_digitou_nao_vira_aresta,
                  teste_o_mapa_e_neutro_de_corretora):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 74)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("A OPÇÃO DO GUINCHO CHEGA AO MAPA — E O CPF NÃO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
