"""Sem corredor de WhatsApp para vidro não é beco — é o portal. Sinistro é handoff.

O que a medição mostrou
------------------------
📊 04/08/2026, varrendo os 13 corredores de WhatsApp com
`missing_slots_for_subservice(pb, "vidros", {})`: **`vidros` cai em
`subservico_invalido` em 10 deles.** Só Azul, Porto e Zurich atendem vidros
pelo WhatsApp da seguradora.

E a resposta do sistema para `subservico_invalido` era, literalmente:
*"Chame `request_human_agent` agora."*

Só que o portal público de vidros — `abraseuatendimento.com.br` — atende
**dezenas** de seguradoras. Yelum, Tokio, HDI, Allianz, Bradesco, Mapfre, Itaú,
Mitsui… 📊 o dropdown começa em ALFA, ALIRO, ALLIANZ, AXA, AZUL e segue.

> **Em 10 de 13 seguradoras, quem dizia "quebrei o vidro" ia para um humano —
> enquanto existia um caminho automático servindo exatamente aquela
> seguradora.** O produto entregava handoff onde tinha serviço.

O guarda que este arquivo existe para proteger
-----------------------------------------------
É o **[2]**, e ele vale mais que o [1].

Alargar a fronteira do "tem outro caminho" é tentador e perigoso: cada item que
entra na lista faz o sistema oferecer o portal em vez de um humano. Se sinistro
entrar ali por descuido, um segurado que sofreu **colisão, roubo ou incêndio**
seria mandado para um formulário de troca de vidro em vez de para uma pessoa.

Essa é a pior falha que este produto consegue cometer. O caso [2] existe para
que ela seja impossível de introduzir em silêncio.
"""

from __future__ import annotations

import importlib.util
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "backend"))

FALHAS: list[str] = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _carregar(*partes: str):
    """Pelo caminho: `app.agents` importa o grafo inteiro (langgraph)."""
    caminho = os.path.join(RAIZ, "backend", *partes)
    spec = importlib.util.spec_from_file_location("_" + partes[-1][:-3], caminho)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


TOOL = _carregar("app", "agents", "tools", "insurer_dispatch_tool.py")


def teste_a_familia_do_portal_e_reconhecida():
    print("\n[1] O que o portal conserta é reconhecido como 'tem outro caminho'")

    # 📊 A tela da Porto: "Vidros, faróis/lanternas (E retrovisores)".
    for trabalho in ("vidros", "vidro da porta", "parabrisa", "para-brisa",
                     "retrovisor", "espelho retrovisor", "farol", "lanterna",
                     "vidro vigia", "troca de vidro com insulfilm"):
        checar(TOOL._e_familia_de_vidros(trabalho) is True,
               f"'{trabalho}' tem portal")


def teste_sinistro_nunca_vira_portal():
    print("\n[2] CONTROLE DO PRODUTO — sinistro NUNCA é portal, é gente")
    print("     (se este caso ficar verde por engano, o dano é real)")

    # Um segurado que bateu, foi roubado ou teve o carro incendiado precisa de
    # uma PESSOA. Mandá-lo a um formulário de troca de vidro seria a pior falha
    # que este produto consegue cometer.
    for sinistro in ("colisao", "colisão", "roubo", "furto", "incendio",
                     "incêndio", "perda total", "sinistro"):
        checar(TOOL._e_familia_de_vidros(sinistro) is False,
               f"'{sinistro}' NÃO vira portal — é handoff",
               "sinistro sempre vai para humano")

    # E o resto da assistência também não tem portal.
    for outro in ("guincho", "pane seca", "chaveiro", "eletricista", "encanador",
                  "carro reserva", "residencia", "eletrodomestico"):
        checar(TOOL._e_familia_de_vidros(outro) is False,
               f"'{outro}' NÃO vira portal")

    # Vazio/None não decide nada.
    checar(TOOL._e_familia_de_vidros(None) is False, "None não vira portal")
    checar(TOOL._e_familia_de_vidros("") is False, "vazio não vira portal")
    checar(TOOL._e_familia_de_vidros("   ") is False, "só espaço não vira portal")


def teste_o_que_o_portal_nao_conserta_fica_de_fora():
    print("\n[3] O que o portal NÃO garante fica de fora, de propósito")

    # 📊 A Porto oferece "Roda, pneu (e suspensão)". Yelum e Tokio, não — o
    # Founder verificou tela a tela em 06/07. Prometer portal para roda/pneu
    # numa seguradora que não tem troca um handoff honesto por um beco.
    for nao_medido in ("roda", "pneu", "suspensao", "lataria", "pintura",
                       "amassado", "martelinho de ouro"):
        checar(TOOL._e_familia_de_vidros(nao_medido) is False,
               f"'{nao_medido}' fica fora enquanto não for medido",
               "prometer caminho que não existe é pior que handoff")


def teste_o_desfecho_muda_no_codigo_e_nao_so_na_lista():
    print("\n[4] O código realmente desvia para o portal — e não só a lista")
    with open(os.path.join(RAIZ, "backend", "app", "agents", "tools",
                           "insurer_dispatch_tool.py"), encoding="utf-8") as fh:
        fonte = fh.read()
    sem_com = "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))

    checar("_e_familia_de_vidros(subservice)" in sem_com,
           "o desvio consulta a fronteira",
           "lista sem uso é decoração")
    checar('"status": "use_portal"' in sem_com, "existe um desfecho use_portal")
    checar("portal_action" in sem_com,
           "o desvio nomeia a ferramenta a chamar",
           "dizer 'não é beco' sem dizer por onde ir é um beco com outro nome")

    # CONTROLE — o caminho de handoff continua existindo para o resto.
    checar('"status": "sem_corredor"' in sem_com,
           "CONTROLE — o handoff continua existindo",
           "somar um desfecho não pode apagar o outro")
    checar('"handoff_necessario": True' in sem_com,
           "CONTROLE — sinistro ainda tem para onde ir")

    # A ordem importa, e a primeira versão deste guarda mediu errado: comparou a
    # PRIMEIRA ocorrência de cada status no arquivo inteiro, e havia um
    # `sem_corredor` anterior, de outro ramo. O detector acusava um código
    # correto. Agora cada ramo é medido dentro de si.
    #
    # São DOIS ramos, e o de cima é o maior: 📊 existem 13 corredores de
    # WhatsApp e o portal atende dezenas de seguradoras — a maioria delas nem
    # chega no segundo ramo, para no primeiro por não ter corredor nenhum.
    ramos = (("if not playbook_ref:", "seguradora sem corredor nenhum"),
             ("if SUBSERVICO_INVALIDO in", "corredor existe mas não faz vidro"))
    for marca, nome in ramos:
        i = sem_com.find(marca)
        checar(i > 0, f"o ramo '{nome}' existe", marca)
        if i <= 0:
            continue
        trecho = sem_com[i:i + 2600]
        i_portal = trecho.find('"status": "use_portal"')
        i_handoff = trecho.find('"status": "sem_corredor"')
        checar(0 < i_portal < i_handoff,
               f"'{nome}': o desvio do portal vem ANTES do handoff",
               f"portal={i_portal} handoff={i_handoff} — depois do return seria código morto")


def main() -> int:
    print("=" * 70)
    print("SEM CORREDOR DE VIDRO NAO E BECO — E SINISTRO CONTINUA SENDO GENTE")
    print("=" * 70)
    for teste in (teste_a_familia_do_portal_e_reconhecida,
                  teste_sinistro_nunca_vira_portal,
                  teste_o_que_o_portal_nao_conserta_fica_de_fora,
                  teste_o_desfecho_muda_no_codigo_e_nao_so_na_lista):
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
    print("O VIDRO VAI PARA O PORTAL; O SINISTRO VAI PARA UMA PESSOA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
