"""A cobertura conta opção distinta, não ocorrência de opção. SPEC-038.

O defeito
---------
`compute_coverage` somava `+= 1` por nó. E a MESMA tela da URA aparece como
vários nós, porque a assinatura do nó é o texto inteiro e o texto muda de uma
sessão para outra — um nome, um "bom dia", uma linha a mais no cabeçalho.

Cada cópia trazia as mesmas opções outra vez, e as duas parcelas da fração
cresciam. Só que **não na mesma proporção**: a tela que mais duplica é justamente
a mais percorrida — duplicou porque apareceu em muitas sessões — então o
numerador inflava mais que o denominador.

Resultado: **a cobertura mentia PARA CIMA.** Medido em 29/07/2026 com dado real,
deduplicando por (menu, rótulo):

    Allianz   painel 63%  ->  real 37%       Porto    29% -> 21%
    Yelum         32%     ->      24%        HDI      33% -> 23%
    Zurich        31%     ->      15%        Bradesco 14% -> 11%

Vinte e seis pontos de otimismo na Allianz. O Founder olhava 63% e via um mapa
quase explorado; ele está em pouco mais de um terço.

Por que isso é pior que cobertura baixa
---------------------------------------
Cobertura baixa manda continuar explorando. Cobertura que mente para cima manda
**parar** — e o que fica sem explorar é rota que o agente vai precisar achar no
meio de um atendimento e não vai encontrar.

A chave é (conjunto de opções da tela, rótulo da opção). Duas telas que oferecem
exatamente as mesmas escolhas são a mesma tela do ponto de vista de navegação,
ainda que o cabeçalho traga um protocolo diferente.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALHAS: list[str] = []

for _n, _p in (("app", ("app",)), ("app.services", ("app", "services")),
               ("app.services.atlas", ("app", "services", "atlas"))):
    if _n not in sys.modules:
        _m = types.ModuleType(_n)
        _m.__path__ = [os.path.join(RAIZ, *_p)]
        _m.__package__ = _n
        sys.modules[_n] = _m


def _carregar(caminho: str, nome: str):
    spec = importlib.util.spec_from_file_location(nome, os.path.join(RAIZ, *caminho.split("/")))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nome] = mod
    spec.loader.exec_module(mod)
    return mod


# `cartographer` é importado dentro de `compute_coverage`; carregá-lo antes
# evita arrastar o `app/__init__` real, que depende de openai.
_carregar("app/services/cartographer.py", "app.services.cartographer")
W = _carregar("app/services/atlas/weaver.py", "app.services.atlas.weaver")


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _menu(opcoes):
    return {"options": [{"label": o} for o in opcoes], "kind": "menu",
            "pre_handoff": 1, "pos_handoff": 0}


def _mapa(nodes, edges):
    return {"nodes": nodes, "edges": edges}


OPCOES = ["1 - Guincho", "2 - Chaveiro", "3 - Falar com atendente"]


def teste_a_mesma_tela_duplicada_nao_infla_a_conta():
    print("\n[1] Cinco cópias da mesma tela = um menu, não cinco")
    # A tela apareceu com cabeçalho diferente em cada sessão, então virou cinco
    # nós. É exatamente o que acontece em produção.
    nodes = {f"copia{i}": _menu(OPCOES) for i in range(5)}
    # Numa das cópias, a pessoa escolheu Guincho. É a mesma opção nas outras.
    edges = {"e1": {"src": "copia0", "to": "destino", "label": "Guincho",
                    "count": 3, "dests": {"destino": 3}}}
    nodes["destino"] = {"options": [], "pre_handoff": 1, "pos_handoff": 0}

    cov = W.compute_coverage(_mapa(nodes, edges))["coverage"]
    checar(cov["options_total"] == 3,
           "o universo é de 3 opções, não 15",
           f"deu {cov['options_total']}")
    # Guincho foi percorrida; "Falar com atendente" é ação conhecida (navegação)
    # e também conta. Chaveiro é lacuna real.
    checar(cov["options_covered"] < cov["options_total"],
           "sobra lacuna real para explorar",
           f"{cov['options_covered']}/{cov['options_total']}")
    checar(cov["pct"] <= 100, "a porcentagem não passa de 100", str(cov["pct"]))


def teste_duplicar_a_tela_percorrida_nao_sobe_a_cobertura():
    print("\n[2] Duplicar a tela mais percorrida não melhora o número")
    # ESTE é o defeito. Antes, cada cópia da tela percorrida somava no
    # numerador e a cobertura subia sem ninguém ter explorado nada.
    edges = {"e1": {"src": "a", "to": "destino", "label": "Guincho",
                    "count": 3, "dests": {"destino": 3}}}
    destino = {"options": [], "pre_handoff": 1, "pos_handoff": 0}

    uma = W.compute_coverage(_mapa({"a": _menu(OPCOES), "destino": dict(destino)}, edges))["coverage"]
    # A MESMA tela, agora em quatro cópias, com a mesma aresta percorrida.
    muitas_nodes = {f"c{i}": _menu(OPCOES) for i in range(4)}
    muitas_nodes["a"] = _menu(OPCOES)
    muitas_nodes["destino"] = dict(destino)
    muitas = W.compute_coverage(_mapa(muitas_nodes, edges))["coverage"]

    checar(uma["pct"] == muitas["pct"],
           "a porcentagem é a mesma com 1 ou com 5 cópias",
           f"1 cópia={uma['pct']}% · 5 cópias={muitas['pct']}%")
    checar(uma["options_total"] == muitas["options_total"],
           "e o denominador também")


def teste_menus_diferentes_continuam_separados():
    print("\n[3] Menus diferentes NÃO podem ser fundidos")
    # O risco do conserto é o oposto: colapsar telas distintas e apagar rota.
    # A chave inclui o conjunto de opções, então menu diferente é tela diferente.
    nodes = {
        "ramo": _menu(["1 - Auto", "2 - Residencial"]),
        "servico": _menu(["1 - Guincho", "2 - Chaveiro"]),
    }
    cov = W.compute_coverage(_mapa(nodes, {}))["coverage"]
    checar(cov["options_total"] == 4,
           "dois menus de duas opções somam quatro",
           f"deu {cov['options_total']} — se der 2, fundiu tela distinta")


def teste_tela_sem_opcao_nao_entra_na_conta():
    print("\n[4] Texto livre do especialista não é rota a percorrer")
    # "Boa tarde!", "Ok um momento" — não tem o que clicar. Contar isso faria a
    # lacuna nunca fechar.
    nodes = {
        "menu": _menu(["1 - Auto", "2 - Residencial"]),
        "fala": {"options": [], "pre_handoff": 0, "pos_handoff": 3},
    }
    cov = W.compute_coverage(_mapa(nodes, {}))["coverage"]
    checar(cov["options_total"] == 2, "só o menu conta",
           f"deu {cov['options_total']}")
    checar(nodes["fala"].get("fase") == "humano",
           "e a fala fica marcada como fase humana")


def main() -> int:
    print("=" * 70)
    print("A COBERTURA NÃO PODE MENTIR PARA CIMA")
    print("=" * 70)
    for teste in (teste_a_mesma_tela_duplicada_nao_infla_a_conta,
                  teste_duplicar_a_tela_percorrida_nao_sobe_a_cobertura,
                  teste_menus_diferentes_continuam_separados,
                  teste_tela_sem_opcao_nao_entra_na_conta):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} explodiu: {type(exc).__name__}: {exc}")
    print("\n" + "=" * 70)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("OPÇÃO DISTINTA, NÃO OCORRÊNCIA DE OPÇÃO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
