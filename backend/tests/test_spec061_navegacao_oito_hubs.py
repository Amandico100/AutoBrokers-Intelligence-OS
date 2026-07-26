"""SPEC-061 §10 — o Admin tem OITO hubs, e nenhum a mais.

Por que este arquivo existe
---------------------------
O Admin chegou a **quinze** grupos de primeiro nível e 34 links, e o Founder
disse a frase que resume o problema: *"é uma bagunça e não consigo entender de
fato tudo"*.

Quinze grupos obrigam a pessoa a saber **onde uma coisa mora** antes de
procurá-la. Oito hubs nomeados pelo assunto deixam eliminar sete de cara.

E o menu cresce sozinho: cada SPEC entrega telas, cada tela quer um lugar, e
"só mais um item no topo" é sempre a saída mais fácil. §10 é explícita — *"não
adicionar novo item de primeiro nível sem revisão canônica"*. Este teste é
essa revisão, automatizada.

Ele NÃO impede o Admin de crescer: submenu é livre. Ele impede o **primeiro
nível** de crescer, que é o que custa ao usuário.
"""

from __future__ import annotations

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LAYOUT = os.path.join(RAIZ, "app", "admin", "layout.tsx")
FALHAS: list[str] = []

# §10, na ordem em que a SPEC os lista. A ordem importa: é a do dia de
# trabalho — o que exige decisão primeiro, o que só se mexe de vez em quando
# por último.
HUBS_CANONICOS = [
    "Visão geral",
    "Corretoras",
    "Operação",
    "Inteligência",
    "Conexões",
    "Conhecimento",
    "Financeiro",
    "Governança",
]

# Palavras que denunciam rótulo escrito para quem construiu, não para quem usa.
# O Founder foi direto: "linguagem técnica". Um rótulo é bom quando responde
# "o que eu encontro aqui?" para alguém que nunca leu a SPEC.
JARGAO = (
    "rbac", "cockpit 360", "read model", "bff", "gateway", "endpoint",
    "payload", "webhook", "cron", "backlog", "cutover", "shadow",
    "role binding", "capability pack", "work run", "outcome",
)


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _sem_comentario(fonte: str) -> str:
    return "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("//"))


def menu_master() -> tuple[list[str], list[tuple[str, str]]]:
    """(rótulos de primeiro nível, todos os pares rótulo/href)."""
    with open(LAYOUT, encoding="utf-8") as fh:
        fonte = _sem_comentario(fh.read())
    inicio = fonte.find("const masterMenuItems")
    bloco = fonte[inicio:fonte.find("\n  ];", inicio)]

    # Primeiro nível: os que declaram `icon:`. Submenu não declara ícone.
    topo = re.findall(r"icon:\s*\w+,\s*\n?\s*label:\s*'([^']+)'", bloco)
    todos = [(r, h) for h, r in
             re.findall(r"href:\s*'([^']+)',\s*icon:\s*\w+,\s*label:\s*'([^']+)'", bloco)]
    todos += [(r, h) for h, r in
              re.findall(r"\{\s*href:\s*'([^']+)',\s*label:\s*'([^']+)'\s*\}", bloco)]
    return topo, todos


def teste_oito_hubs():
    print("\n[1] Oito hubs, exatamente os da §10")
    topo, _ = menu_master()
    checar(len(topo) == 8, "são oito itens de primeiro nível",
           f"{len(topo)}: {topo}")
    checar(topo == HUBS_CANONICOS,
           "e são os oito da SPEC, na ordem dela",
           f"obtido: {topo}")


def teste_menu_cabe_na_cabeca():
    print("\n[2] Nenhum hub esconde mais do que alguém consegue varrer")
    with open(LAYOUT, encoding="utf-8") as fh:
        fonte = _sem_comentario(fh.read())
    inicio = fonte.find("const masterMenuItems")
    bloco = fonte[inicio:fonte.find("\n  ];", inicio)]

    # Submenus, por hub.
    for hub, corpo in re.findall(
            r"label:\s*'([^']+)',\s*\n\s*submenu:\s*\[(.*?)\]", bloco, re.S):
        n = len(re.findall(r"href:", corpo))
        # Nove é o limite prático de uma lista que se varre sem reler. Acima
        # disso o submenu vira a mesma bagunça, um nível abaixo.
        checar(n <= 9, f"'{hub}' tem {n} item(ns)",
               "acima de 9 o submenu vira a mesma bagunça um nível abaixo")


def teste_rotulos_em_linguagem_humana():
    print("\n[3] Rótulo diz o que a página RESPONDE")
    _, todos = menu_master()
    for rotulo, href in todos:
        baixo = rotulo.lower()
        achado = [j for j in JARGAO if j in baixo]
        checar(not achado, f"'{rotulo}' sem jargão",
               f"({href}) contém: {achado}")


def teste_nenhum_rotulo_repetido():
    print("\n[4] Nenhum rótulo se repete — nem entre hub e submenu")
    _, todos = menu_master()
    vistos: dict[str, list[str]] = {}
    for rotulo, href in todos:
        vistos.setdefault(rotulo.strip().lower(), []).append(href)
    dup = {r: h for r, h in vistos.items() if len(h) > 1}
    checar(not dup, "nenhum rótulo ambíguo",
           "; ".join(f"'{r}' → {h}" for r, h in dup.items()))


def teste_hub_abre_em_pagina_util():
    print("\n[5] Clicar no hub leva a algum lugar, e ao primeiro filho")
    with open(LAYOUT, encoding="utf-8") as fh:
        fonte = _sem_comentario(fh.read())
    inicio = fonte.find("const masterMenuItems")
    bloco = fonte[inicio:fonte.find("\n  ];", inicio)]

    # Cabeçalho e primeiro filho apontando para lugares diferentes é o defeito
    # que o CA-013 registrou: clicar no título levava a um assunto, clicar nos
    # filhos, a outro.
    for href_hub, corpo in re.findall(
            r"href:\s*'([^']+)',\s*\n\s*icon:\s*\w+,\s*\n\s*label:\s*'[^']+',\s*\n\s*submenu:\s*\[(.*?)\]",
            bloco, re.S):
        filhos = re.findall(r"href:\s*'([^']+)'", corpo)
        checar(bool(filhos) and filhos[0] == href_hub,
               f"o hub '{href_hub}' abre no próprio primeiro filho",
               f"primeiro filho é {filhos[0] if filhos else '(nenhum)'}")


def main() -> int:
    print("=" * 68)
    print("SPEC-061 §10 — OITO HUBS, EM LINGUAGEM HUMANA")
    print("=" * 68)
    for teste in (teste_oito_hubs, teste_menu_cabe_na_cabeca,
                  teste_rotulos_em_linguagem_humana,
                  teste_nenhum_rotulo_repetido, teste_hub_abre_em_pagina_util):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 68)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S) DE NAVEGAÇÃO:")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O ADMIN CABE NA CABEÇA DE QUEM USA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
