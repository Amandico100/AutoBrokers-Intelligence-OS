"""O menu não cresce, e nenhuma rota antiga vira 404.

A regra já existia — e foi violada duas vezes
---------------------------------------------
`lib/navigation.ts` trazia, escrito, o princípio::

    A regra que fica: **o menu não cresce.** Coisa nova entra DENTRO de um
    item que já existe. Se não couber em nenhum, a pergunta certa é se o
    desenho dos itens está errado — não se falta um item.

E o menu tinha sete pilares, dois dos quais eram Auxiliares disfarçados:

* **Briefing** (SPEC-059) — é um Auxiliar. Tinha agenda, configuração por
  empresa, execução durável e saída própria.
* **Pesquisas** (SPEC-060) — é uma Skill do chat. Sete skills registradas e
  ativas, zero pesquisas feitas.

As duas entraram com o mesmo argumento, e o argumento estava certo: *"tela sem
link é tela que não existe para quem usa"*. A conclusão é que estava errada —
a solução era colocá-las DENTRO de um pilar, não criar dois pilares.

E no secundário havia três itens respondendo a MESMA pergunta — "o que já
aconteceu aqui?": Atividades, Histórico e Conversas.

Por que isto virou teste
------------------------
Porque comentário que ninguém é obrigado a obedecer é decoração. A regra
existia por escrito, no arquivo, e não impediu nada.

O segundo caso é o que protege o corretor: **mover é barato, sumir não é.**
Toda rota antiga tem de continuar existindo e redirecionar — link salvo não
some quando a rota muda.
"""

from __future__ import annotations

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FALHAS: list[str] = []

# Rota antiga -> destino. Toda entrada aqui foi um endereço real do produto.
ROTAS_QUE_MUDARAM = {
    "app/dashboard/briefing": "/dashboard/auxiliares/checklist-6h/hoje",
    "app/dashboard/pesquisas": "/dashboard/entregas/pesquisas",
    "app/dashboard/memorias": "/dashboard/personalizacao/memorias",
    "app/dashboard/atividades": "/dashboard/entregas",
    "app/dashboard/historico": "/dashboard/entregas",
    "app/dashboard/auxiliares/galeria": "/dashboard/auxiliares",
    "app/dashboard/auxiliares/meus": "/dashboard/auxiliares",
    "app/dashboard/auxiliares/execucoes": "/dashboard/entregas",
    "app/dashboard/auxiliares/galeria/[slug]": "/dashboard/auxiliares/",
}

# As telas que MUDARAM DE CASA com conteúdo — o destino tem de existir de
# verdade, e não pode ser uma casca. Redirecionar para uma tela que não existe
# é trocar um 404 por outro.
CONTEUDO_MUDOU_DE_CASA = {
    "app/dashboard/auxiliares/checklist-6h/hoje/page.tsx": 400,
    "app/dashboard/entregas/pesquisas/page.tsx": 300,
    "app/dashboard/personalizacao/memorias/page.tsx": 200,
}


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(*partes: str) -> str:
    with open(os.path.join(RAIZ, *partes), encoding="utf-8") as fh:
        return fh.read()


def teste_cinco_pilares():
    print("\n[1] O menu tem exatamente cinco pilares")
    fonte = _ler("lib", "navigation.ts")

    bloco = fonte.split("export const PILLARS", 1)[1].split("];", 1)[0]
    pilares = re.findall(r"key:\s*'([a-z0-9-]+)'", bloco)
    checar(len(pilares) == 5, "cinco pilares", f"{len(pilares)}: {pilares}")

    esperados = {"autobrokers", "atendimentos", "auxiliares", "entregas", "personalizacao"}
    checar(set(pilares) == esperados,
           "os pilares são os cinco decididos",
           f"achado={sorted(pilares)}")

    # Os dois que voltariam se alguém esquecesse a regra.
    for proibido, porque in (
        ("briefing", "é um Auxiliar — o Checklist das 6h"),
        ("pesquisas", "é uma Skill do chat; o resultado vai para Entregas"),
        ("memorias", "é configuração — mora em Personalização"),
    ):
        checar(proibido not in pilares, f"'{proibido}' não é pilar — {porque}")

    checar("MENU_NAO_CRESCE = 5" in fonte,
           "o número faz parte do contrato do arquivo",
           "sem constante, o teste vira opinião contra o código")


def teste_nenhuma_rota_antiga_some():
    print("\n[2] Toda rota antiga continua existindo e redireciona")
    for pasta, destino in ROTAS_QUE_MUDARAM.items():
        alvo = os.path.join(RAIZ, pasta, "page.tsx")
        rel = f"{pasta}/page.tsx"
        if not os.path.isfile(alvo):
            checar(False, f"{rel} existe", "apagar rota transforma link salvo em 404")
            continue
        fonte = _ler(*pasta.split("/"), "page.tsx")
        checar("redirect(" in fonte, f"{rel} redireciona")
        checar(destino in fonte,
               f"{rel} aponta para {destino}",
               "destino diferente do combinado")


def teste_o_destino_tem_conteudo():
    print("\n[3] Quem mudou de casa levou a mobília junto")
    for caminho, minimo in CONTEUDO_MUDOU_DE_CASA.items():
        completo = os.path.join(RAIZ, caminho)
        if not os.path.isfile(completo):
            checar(False, f"{caminho} existe",
                   "redirecionar para tela inexistente é trocar um 404 por outro")
            continue
        linhas = len(_ler(*caminho.split("/")).split("\n"))
        checar(linhas >= minimo,
               f"{caminho} tem a tela inteira",
               f"{linhas} linhas, esperado ao menos {minimo} — "
               "casca no lugar da tela é pior que redirect")


def teste_a_duplicata_de_conversas_sumiu_sem_sobra():
    print("\n[4] A tela duplicada de conversas foi removida sem deixar sobra")
    checar(not os.path.isdir(os.path.join(RAIZ, "app", "dashboard", "conversas")),
           "/dashboard/conversas não existe mais")
    checar(not os.path.isdir(os.path.join(RAIZ, "app", "api", "admin", "conversations")),
           "as três rotas de API que só ela usava foram junto",
           "API sem consumidor é superfície de ataque sem dono")

    # E o redirect do admin tem de apontar para a tela que sobrou.
    admin = _ler("app", "admin", "conversations", "page.tsx")
    checar("/dashboard/atendimentos/conversas" in admin,
           "o redirect do admin aponta para a tela canônica")

    # Nenhuma referência pendurada no código.
    pendentes: list[str] = []
    for pasta, _, arquivos in os.walk(os.path.join(RAIZ, "app")):
        if "node_modules" in pasta:
            continue
        for arq in arquivos:
            if not arq.endswith((".ts", ".tsx")):
                continue
            caminho = os.path.join(pasta, arq)
            with open(caminho, encoding="utf-8") as fh:
                fonte = fh.read()
            sem_comentario = "\n".join(
                l for l in fonte.split("\n") if not l.lstrip().startswith("//")
            )
            if "/api/admin/conversations" in sem_comentario:
                pendentes.append(os.path.relpath(caminho, RAIZ).replace(os.sep, "/"))
    checar(not pendentes, "ninguém mais chama /api/admin/conversations", f"{pendentes}")


def teste_o_secundario_nao_deixou_divisoria_orfa():
    print("\n[5] Menu secundário vazio não deixa divisória sozinha")
    nav = _ler("components", "layout", "TenantNav.tsx")
    checar("SECONDARY.length > 0" in nav,
           "a divisória só aparece se houver item no secundário",
           "linha horizontal sozinha no meio da barra é sujeira visível")


def main() -> int:
    print("=" * 68)
    print("O MENU NÃO CRESCE, E NENHUMA ROTA ANTIGA VIRA 404")
    print("=" * 68)
    for teste in (teste_cinco_pilares,
                  teste_nenhuma_rota_antiga_some,
                  teste_o_destino_tem_conteudo,
                  teste_a_duplicata_de_conversas_sumiu_sem_sobra,
                  teste_o_secundario_nao_deixou_divisoria_orfa):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 68)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("CINCO PILARES, E NINGUEM PERDE O CAMINHO DE VOLTA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
