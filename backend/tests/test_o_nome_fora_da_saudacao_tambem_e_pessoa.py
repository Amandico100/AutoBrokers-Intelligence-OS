"""O nome do segurado não está só na saudação — e o menu não pode ser apagado.

A HISTÓRIA
==========
📊 07/08/2026, medido nos 10 mapas de URA de produção: **115 nós carregam nome
próprio não mascarado**, 95 deles só no mapa da Porto. E **24 nós** carregam
marca de corretora — a raiz do mapa `tokio` literalmente estampa o nome de uma
corretora, porque a URA da Tokio Marine é white-label.

O formato que escapava:

    Oi, sou assistente virtual da Porto Seguro 👋

    Fulano, estou aqui para ajudar você

`NOME_NA_SAUDACAO` exige o nome COLADO na saudação. Aqui a saudação está na
primeira linha e o nome na terceira: ele passa direto.

📊 O que vem depois do nome, no acervo da Porto: "estou aqui" (44), "a
vistoria" (20), "os reparos" (11), "você optou" (4). **Não há pronome
consistente** — a primeira tentativa (exigir "você/sua/seu") pegava 7 de 95.

O PERIGO É O OPOSTO DO ÓBVIO
============================
Este mascarador pode apagar CONHECIMENTO. Ao calibrar, produzi estes falsos
positivos, todos reais:

    "Digite, por favor, o CPF"        → instrução do menu virava {NOME}
    "Guincho, reboque ou pane seca"   → opção do menu
    "Pronto, sua solicitação..."      → interjeição
    "Florianópolis, SC"               → cidade
    "Marina, assistente virtual..."   → a PERSONAGEM da seguradora

E uma tentativa de fazer o remascaramento direto por SQL produziu
`"{NOME}, te ajudar?"` onde o original era *"Fulano, como posso te ajudar?"* —
duas palavras de conhecimento comidas por um regex sem teste. Foi por isso que
a regra veio para cá, onde ela pode ser exercitada.

Três travas, e cada uma nasceu de um desses erros: não é palavra comum · não é
a personagem da URA · é uma frase (minúscula, ≥3 palavras), não item de lista.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROBLEMAS: list = []


def checar(condicao: bool, o_que: str, evidencia: str = "") -> None:
    if condicao:
        print(f"  OK  {o_que}" + (f"  ({evidencia})" if evidencia else ""))
    else:
        print(f"  X   {o_que}" + (f"  ({evidencia})" if evidencia else ""))
        _PROBLEMAS.append(o_que)


def _carregar():
    nome = "_teste_templater"
    if nome in sys.modules:
        return sys.modules[nome]
    for pai in ("app", "app.services", "app.services.atlas"):
        if pai not in sys.modules:
            m = types.ModuleType(pai)
            m.__path__ = [os.path.join(RAIZ, "backend", *pai.split(".")[1:])]
            sys.modules[pai] = m
    caminho = os.path.join(RAIZ, "backend", "app", "services", "atlas", "templater.py")
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nome] = modulo
    spec.loader.exec_module(modulo)
    return modulo


# ---------------------------------------------------------------------------
def teste_o_nome_fora_da_saudacao_e_mascarado():
    print("\n[1] O que ESCAPAVA — os formatos reais da Porto")
    T = _carregar()

    # Os quatro formatos medidos no acervo, com a contagem de cada um. Todos
    # trazem a apresentação da URA na frente, como no dado real.
    reais = [
        ("Oi, sou assistente virtual da Porto Seguro\n\nJoao, estou aqui para "
         "ajudar voce", "'estou aqui' — 44 nós"),
        ("Ola! Sou a assistente da Azul\n\nMariana, a vistoria do seu carro "
         "foi agendada", "'a vistoria' — 20 nós"),
        ("Bom dia! Assistente virtual\n\nCristiane, os reparos do veiculo ja "
         "comecaram", "'os reparos' — 11 nós"),
        ("Oi! Sou o atendimento virtual\n\nRoberto, voce optou pela vistoria "
         "digital", "'você optou' — 4 nós"),
    ]
    for texto, quantos in reais:
        saida = T.templatize(texto)
        checar("{NOME}" in saida and texto != saida,
               f"mascara o vocativo: {quantos}", saida.strip().replace("\n", " ")[:64])

    # 🔴 O PREÇO DA QUARTA TRAVA, escrito de propósito.
    #
    # Sem a apresentação da URA na frente, o vocativo NÃO é mascarado. 📊 São
    # 11 das 95 telas da Porto (12%) que ficam de fora.
    #
    # É uma escolha, não um esquecimento: sem essa trava o mascarador come
    # português ("Roubo, furto e incêndio…", "Agora, me informe…"). Nenhuma
    # lista de palavras cobre o idioma inteiro, e apagar o menu da seguradora
    # em silêncio é pior do que deixar 11 nomes num mapa que ninguém lê até ser
    # promovido. O que sobra é tratado na revisão antes da promoção.
    solto = "Roberto, estou aqui para ajudar voce hoje"
    checar(T.templatize(solto) == solto,
           "CONTROLE — sem a URA se apresentando, o vocativo NÃO é tocado",
           "📊 11 de 95 ficam de fora; é o preço de não comer português")


def teste_a_marca_da_corretora_some_do_mapa_global():
    print("\n[2] A marca de uma corretora não entra no mapa que todas leem")
    T = _carregar()

    for texto in ("Marcia - Autofleet Seguros",
                  "Ola, {NOME}  - Autofleet Seguros!",
                  "Joana - Resulta Seguros"):
        saida = T.templatize(texto)
        checar("{CORRETORA}" in saida,
               "assinatura vira {NOME} - {CORRETORA}", saida)

    # 📊 24 nós em 3 mapas (hdi 10, yelum 8, tokio 6). A URA da Tokio é
    # white-label e ECOA a marca; promover o mapa publicaria a identidade de um
    # cliente para os outros (CLAUDE.md §7).
    checar("Autofleet" not in T.templatize("Ola, {NOME}  - Autofleet Seguros!"),
           "e o nome da corretora não sobra em lugar nenhum")


def teste_o_menu_nao_e_apagado():
    print("\n[3] CONTROLE — o conhecimento do menu SOBREVIVE")
    T = _carregar()

    # Cada um destes foi um falso positivo real durante a calibragem.
    intocaveis = [
        ("Digite, por favor, o seu CPF", "instrução do menu"),
        ("Guincho, reboque ou pane seca", "opção do menu"),
        ("Pronto, sua solicitacao foi registrada", "interjeição + pronome"),
        ("Certo, seu pedido foi enviado agora", "confirmação"),
        ("Florianopolis, SC", "cidade"),
        ("Auto, Residencial ou Vida", "opções capitalizadas"),
        ("Escolha, entre as opcoes abaixo", "verbo de instrução"),
        ("Taxi, guincho ou chaveiro disponivel", "serviço"),
        # 🔴 Estes três só a trava da FRASE protege — a marca do carro não está
        # (nem pode estar) na lista de palavras comuns, e não é a personagem da
        # URA. 📊 São linhas reais do menu da Porto: "*1* - CHEVROLET, {PLACA},
        # placa R#####9 *2* - PEUGEOT…". Sem exigir minúscula e três palavras
        # depois da vírgula, a marca do veículo virava {NOME} e o menu de
        # escolha de carro deixava de fazer sentido.
        ("Chevrolet, {PLACA}, placa R", "marca de veículo no menu"),
        ("Ram, prata", "marca + cor, duas palavras"),
        ("Jeep, {PLACA}", "item de lista curto"),
    ]
    for texto, o_que in intocaveis:
        checar(T.templatize(texto) == texto,
               f"CONTROLE — {o_que} fica intacto", texto)


def teste_a_personagem_da_ura_nao_e_uma_pessoa():
    print("\n[4] CONTROLE — a assistente virtual continua tendo nome")
    T = _carregar()

    # 🔴 A trava que o auditor exigiu: `Marina` e `Maitê` são PERSONAGENS da
    # seguradora, não segurados. Mascará-las quebraria a identidade da tela — e
    # a identidade da tela é justamente o conhecimento que o Atlas guarda.
    for texto, quem in (
        ("Marina, assistente virtual da Tokio Marine", "Tokio"),
        ("Maite, assistente virtual da MAPFRE Seguros", "MAPFRE"),
        ("Sofia, sou a assistente digital da seguradora", "genérica"),
    ):
        saida = T.templatize(texto)
        checar(saida == texto,
               f"CONTROLE — a personagem da URA ({quem}) sobrevive", texto[:44])


def teste_a_ordem_dos_padroes_importa():
    print("\n[5] A assinatura é tratada ANTES do vocativo")
    T = _carregar()

    # Se o vocativo passasse primeiro, `Fulana - Autofleet Seguros` viraria
    # `{NOME} - Autofleet Seguros` e a MARCA sobraria solta — que é exatamente
    # o que não pode ficar num mapa global.
    fonte_caminho = os.path.join(RAIZ, "backend", "app", "services", "atlas", "templater.py")
    with open(fonte_caminho, encoding="utf-8") as arquivo:
        fonte = arquivo.read()
    i_assin = fonte.find("(ASSINATURA_DE_CORRETORA,")
    i_voc = fonte.find("(NOME_NO_VOCATIVO,")
    checar(0 < i_assin < i_voc,
           "a assinatura vem antes do vocativo na lista de padrões",
           "invertido, a marca da corretora sobraria solta")


def main() -> int:
    print("=" * 70)
    print("O NOME FORA DA SAUDAÇÃO TAMBÉM É PESSOA")
    print("=" * 70)
    teste_o_nome_fora_da_saudacao_e_mascarado()
    teste_a_marca_da_corretora_some_do_mapa_global()
    teste_o_menu_nao_e_apagado()
    teste_a_personagem_da_ura_nao_e_uma_pessoa()
    teste_a_ordem_dos_padroes_importa()

    print("\n" + "=" * 70)
    if _PROBLEMAS:
        print(f"{len(_PROBLEMAS)} PROBLEMA(S):")
        for p in _PROBLEMAS:
            print(f"  - {p}")
        return 1
    print("TUDO VERDE — o nome sai, o menu fica, a assistente continua tendo nome.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
