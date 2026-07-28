"""O Tecelão enxerga a URA de TEXTO — não só a de botão. SPEC-038.

O que foi medido em 28/07/2026
------------------------------
Com o histórico da Resulta já importado, o mapa da Allianz mostrava:

    930 telas capturadas
    170 com opções detectadas     ← 760 telas cegas
    592 opções, 27 percorridas    ← 4% de cobertura
  1.899 arestas

Mil e oitocentas arestas com vinte e sete opções cobertas é uma contradição: o
sistema SABIA que depois da tela A veio a tela B, e não sabia que foi porque
alguém digitou "2".

A leitura do Founder estava certa
---------------------------------
> "NÃO É POSSÍVEL QUE EM MILHARES DE ATENDIMENTOS AS PESSOAS PEÇAM SÓ A MESMA
>  COISA DE RESIDENCIAL. TALVEZ O AGENTE ESTEJA CEGO."

Estava. Três defeitos somados, todos no mesmo lugar:

**1. O negrito do WhatsApp escondia o número.** A Allianz manda
`*1 -* Automóvel, Moto ou Caminhão` — asterisco ANTES do dígito. O regex de
menu numerado esperava o dígito logo após a quebra de linha e não casava nada.

**2. O rótulo perdia o número.** Onde o parser casava, ele guardava só o texto
("Residência, Condomínio ou Empresa") e jogava fora o "2". Mas a atendente
digita **"2"** — e "2" nunca casa com "Residência…".

**3. O menu de ramo caía por 8 caracteres.** A heurística de linhas curtas
aceitava até 48; `*1 - Residencial:* Para sua casa ou apartamento individual`
tem 56. Justamente a tela que escolhe Residencial, Condomínio ou Empresarial —
a mais importante para a Resulta — ficava com ZERO opções.

Estes casos usam o texto REAL capturado do WhatsApp da Allianz.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

for _n, _p in (("app", ("app",)),
               ("app.services", ("app", "services")),
               ("app.services.atlas", ("app", "services", "atlas"))):
    if _n not in sys.modules:
        m = types.ModuleType(_n)
        m.__path__ = [os.path.join(RAIZ, *_p)]
        m.__package__ = _n
        sys.modules[_n] = m


def carregar(nome: str):
    caminho = os.path.join(RAIZ, *nome.split(".")) + ".py"
    spec = importlib.util.spec_from_file_location(nome, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


C = carregar("app.services.cartographer")
W = carregar("app.services.atlas.weaver")

# Texto REAL, copiado de `observed_events` da Allianz.
MENU_PRINCIPAL = (
    "Olá! Sou a *assistente virtual da Allianz*. \n"
    "Você precisa de Assistência 24h para qual seguro?\n\n"
    "*1 -* Automóvel, Moto ou Caminhão\n"
    "*2 -* Residência, Condomínio ou Empresa\n"
    "*3 -* Vida ou Acidentes Pessoais\n"
    "*4 -* Viagem\n"
    "*5 -* Outros assuntos do seguro")

SUBMENU_RAMO = (
    "Qual seguro deseja utilizar?\n\n"
    "*1 - Residencial:* Para sua casa ou apartamento individual\n"
    "*2 - Condomínio:* Para áreas comuns e estrutura do condomínio\n"
    "*3 - Empresarial:* Para proteger seu negócio")

TELA_DE_DICAS = (
    "Tenho algumas dicas importantes para conseguir te atender da melhor forma!\n\n"
    "- Escolha a opção desejada digitando o número;\n"
    "- Ainda não consigo entender fotos, vídeos ou áudios;\n"
    "- Digite SAIR em qualquer momento caso queira finalizar nossa conversa.")

PERGUNTA_ABERTA = "Digite o *CNPJ* do titular ou pressione 9 para voltar."


def teste_menu_com_negrito_e_lido():
    print("\n[1] O negrito do WhatsApp não esconde mais o menu")
    ops = C.parse_options(MENU_PRINCIPAL)
    checar(len(ops) == 5, "as 5 opções do menu principal aparecem",
           f"achou {len(ops)}: {ops}")
    checar(any("Automóvel" in o for o in ops), "e o texto do rótulo vem junto")


def teste_o_menu_de_ramo_da_resulta():
    print("\n[2] O menu que escolhe Residencial/Condomínio/Empresarial")
    # Esta é A tela da Resulta. Ela ficava com ZERO opções por 8 caracteres.
    ops = C.parse_options(SUBMENU_RAMO)
    checar(len(ops) == 3, "as 3 opções aparecem", f"achou {len(ops)}: {ops}")
    for esperado in ("Residencial", "Condomínio", "Empresarial"):
        checar(any(esperado in o for o in ops), f"'{esperado}' está lá")
    # E o rótulo é o que se ESCOLHE, sem a explicação colada.
    checar(all(len(o) < 40 for o in ops),
           "o rótulo é a escolha, não a explicação inteira", str(ops))


def teste_o_numero_fica_no_rotulo():
    print("\n[3] O número da opção não é jogado fora")
    ops = C.parse_options(MENU_PRINCIPAL)
    checar(all(C.numero_da_opcao(o) for o in ops),
           "toda opção numerada sabe o próprio número",
           str([(o, C.numero_da_opcao(o)) for o in ops[:2]]))
    checar(C.numero_da_opcao(ops[1]) == "2",
           "a segunda opção é a '2'", str(ops[1]))


def teste_o_que_nao_e_menu_continua_nao_sendo():
    print("\n[4] Tela que não é menu não vira menu")
    # Opção que não existe vira lacuna eterna: a cobertura nunca fecha porque
    # ninguém pode escolher o que não é escolha.
    checar(C.parse_options(TELA_DE_DICAS) == [],
           "a tela de dicas (lista com '-') não tem opções",
           str(C.parse_options(TELA_DE_DICAS)))
    checar(C.parse_options(PERGUNTA_ABERTA) == [],
           "a pergunta aberta não tem opções",
           str(C.parse_options(PERGUNTA_ABERTA)))


def teste_digitar_o_numero_percorre_a_opcao():
    print("\n[5] Digitar '2' percorre a opção 2")
    ops = C.parse_options(MENU_PRINCIPAL)
    op2 = [o for o in ops if C.numero_da_opcao(o) == "2"][0]
    op3 = [o for o in ops if C.numero_da_opcao(o) == "3"][0]

    checar(W.labels_match(op2, "2"), "a opção 2 casa com o que foi digitado")
    checar(not W.labels_match(op3, "2"),
           "e a opção 3 NÃO casa",
           "sem isso, uma escolha marcaria a rota errada como percorrida")


def teste_resposta_que_nao_e_escolha_de_menu():
    print("\n[6] CPF e endereço não são escolha de menu")
    # A conversa real tem `out` com "81.578.783/0001-97" logo depois de uma
    # tela. Tratar isso como clique inventaria rota.
    ops = C.parse_options(MENU_PRINCIPAL)
    for resposta in ("81.578.783/0001-97", "02414523921", "Rua das Flores 190"):
        casou = any(W.labels_match(o, resposta) for o in ops)
        checar(not casou, f"'{resposta[:20]}' não vira escolha de menu")


def teste_clique_de_botao_continua_funcionando():
    print("\n[7] O que já funcionava não quebrou")
    # Seguradoras com lista/botão do WhatsApp mandam o rótulo inteiro de volta.
    checar(W.labels_match("Guincho", "Guincho"), "clique idêntico casa")
    checar(W.labels_match("Assistência 24h", "assistencia 24h"),
           "e o casamento continua tolerante a acento e caixa")
    ops = C.parse_options("Escolha:\nBotão 1: Guincho\nBotão 2: Chaveiro")
    checar(len(ops) == 2, "botões da Evolution continuam sendo lidos", str(ops))


def main() -> int:
    print("=" * 70)
    print("O TECELÃO ENXERGA A URA DE TEXTO, NÃO SÓ A DE BOTÃO")
    print("=" * 70)
    for teste in (teste_menu_com_negrito_e_lido,
                  teste_o_menu_de_ramo_da_resulta,
                  teste_o_numero_fica_no_rotulo,
                  teste_o_que_nao_e_menu_continua_nao_sendo,
                  teste_digitar_o_numero_percorre_a_opcao,
                  teste_resposta_que_nao_e_escolha_de_menu,
                  teste_clique_de_botao_continua_funcionando):
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
    print("NENHUM ATENDIMENTO SE PERDE POR CAUSA DO FORMATO DA SEGURADORA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
