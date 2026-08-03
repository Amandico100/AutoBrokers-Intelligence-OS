"""A tabela de rotas do Next.js precisa MONTAR — não basta o build passar.

O que aconteceu em 02/08/2026
-----------------------------
A SPEC-064 criou `app/api/dashboard/auxiliaries/[slug]/config/` ao lado de
`app/api/dashboard/auxiliaries/[templateId]/`, que existia desde 25/07.

O `next build` **passou** — 287 rotas, 135 páginas, gate verde. O `tsc` passou.
Os 111 testes passaram. A imagem Docker foi construída com sucesso. O contêiner
subiu e escreveu `Ready in 1253ms`.

E na linha seguinte:

    [Error: You cannot use different slug names for the same dynamic path
            ('templateId' !== 'slug').]
        at getSortedRoutes (next/dist/shared/lib/router/utils/sorted-routes.js)
        at DefaultRouteMatcherManager.reload (...)

O Next.js exige **um único nome de parâmetro por posição** na árvore de rotas.
Com dois nomes, `getSortedRoutes` lança, a tabela de rotas não monta, e o
servidor passa a devolver **500 em TODAS as rotas** — páginas, APIs e até a
página de 404.

O site ficou **1h40 fora do ar**. Do lado de fora o sintoma enganava: arquivo
estático em `public/` continuava servindo com 200, porque o servidor de
estáticos não passa pelo roteador. Parecia "algumas telas quebradas". Era o
produto inteiro.

Por que nenhum gate pegou
-------------------------
Porque **todos os gates paravam antes de ligar o servidor**:

    next build     compila e escreve .next     → não monta a tabela de rotas
    tsc --noEmit   confere tipos               → nomes de pasta não são tipo
    111 testes     leem código e banco         → nenhum sobe o Next

*Build verde não é prova de que a aplicação sobe.* Este teste fecha a metade
estática dessa lacuna: valida a invariante da árvore de rotas lendo o disco,
sem precisar de servidor.

O que este teste protege
------------------------
Que nenhuma pasta contenha dois segmentos dinâmicos com nomes diferentes — a
falha exata que derrubou o produto — e que catch-all e segmento simples não
disputem a mesma posição, que é a outra forma de quebrar a mesma montagem.
"""

from __future__ import annotations

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP = os.path.join(RAIZ, "app")
FALHAS: list[str] = []


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _nome_do_parametro(pasta: str) -> str:
    """`[slug]` -> slug · `[...path]` -> path · `[[...path]]` -> path."""
    return pasta.strip("[]").lstrip(".")


def _dinamicas(nomes: list[str]) -> list[str]:
    return sorted(n for n in nomes if n.startswith("["))


def teste_um_nome_de_parametro_por_posicao():
    """Duas pastas dinâmicas irmãs precisam ter o MESMO nome de parâmetro.

    Esta é a regra que foi violada. Ela não é estética: `getSortedRoutes` lança
    ao encontrar a segunda, e o `DefaultRouteMatcherManager` nunca termina de
    carregar. Sem tabela de rotas, o servidor não tem o que responder.
    """
    print("\n[1] Nenhuma pasta tem dois segmentos dinamicos com nomes diferentes")
    conflitos: list[str] = []
    total_dinamicos = 0

    for dirpath, dirnames, _ in os.walk(APP):
        dyn = _dinamicas(dirnames)
        total_dinamicos += len(dyn)
        nomes = {_nome_do_parametro(d) for d in dyn}
        if len(nomes) > 1:
            rel = os.path.relpath(dirpath, RAIZ).replace("\\", "/")
            conflitos.append(f"{rel}: {dyn}")

    checar(not conflitos,
           "nenhum conflito de nome de parametro",
           " | ".join(conflitos))
    print(f"      segmentos dinamicos varridos: {total_dinamicos}")


def teste_catch_all_nao_disputa_posicao_com_segmento_simples():
    """`[id]` e `[...path]` na mesma pasta também impedem a montagem.

    É a mesma classe de defeito por um caminho diferente — e igualmente
    invisível para o build.
    """
    print("\n[2] Catch-all nao divide posicao com segmento simples")
    conflitos: list[str] = []

    for dirpath, dirnames, _ in os.walk(APP):
        dyn = _dinamicas(dirnames)
        if len(dyn) < 2:
            continue
        formas = {("catch_all" if d.startswith(("[...", "[[...")) else "simples")
                  for d in dyn}
        if len(formas) > 1:
            rel = os.path.relpath(dirpath, RAIZ).replace("\\", "/")
            conflitos.append(f"{rel}: {dyn}")

    checar(not conflitos, "nenhuma disputa catch-all vs simples", " | ".join(conflitos))


def teste_o_parametro_declarado_no_codigo_bate_com_a_pasta():
    """O `params: Promise<{ x }>` do handler tem de usar o nome da PASTA.

    Renomear a pasta e esquecer o handler devolve `undefined` em silêncio — a
    rota responde 200 e trabalha com o identificador vazio. É o defeito que a
    correção de 02/08 poderia ter introduzido ao consertar o primeiro.
    """
    print("\n[3] O nome do parametro no handler bate com o nome da pasta")
    verificados = 0

    for dirpath, _, filenames in os.walk(APP):
        if "route.ts" not in filenames and "page.tsx" not in filenames:
            continue

        # O parâmetro que vale é o da pasta dinâmica mais próxima acima.
        partes = os.path.relpath(dirpath, APP).split(os.sep)
        dinamicas_acima = [p for p in partes if p.startswith("[")]
        if not dinamicas_acima:
            continue
        esperados = {_nome_do_parametro(p) for p in dinamicas_acima}

        for arquivo in ("route.ts", "page.tsx"):
            if arquivo not in filenames:
                continue
            caminho = os.path.join(dirpath, arquivo)
            with open(caminho, encoding="utf-8") as fh:
                fonte = fh.read()

            # `params: Promise<{ nome: string }>` / `params: { nome: string }`
            declarados = set(re.findall(r"params:\s*(?:Promise<)?\{\s*(\w+)\s*:", fonte))
            if not declarados:
                continue

            verificados += 1
            invalidos = declarados - esperados
            rel = os.path.relpath(caminho, RAIZ).replace("\\", "/")
            checar(not invalidos, f"{rel}",
                   f"declara {sorted(invalidos)}, a pasta oferece {sorted(esperados)}")

    print(f"      handlers dinamicos conferidos: {verificados}")


def teste_a_rota_que_derrubou_o_site_esta_consertada():
    """A regressão específica, nomeada — para ninguém desfazer sem perceber."""
    print("\n[4] A regressao de 02/08 esta fechada")
    base = os.path.join(APP, "api", "dashboard", "auxiliaries")

    checar(not os.path.isdir(os.path.join(base, "[slug]")),
           "a pasta [slug] nao voltou",
           "ela conviveu com [templateId] e derrubou o site")
    checar(not os.path.isdir(os.path.join(base, "[templateId]")),
           "a pasta [templateId] deu lugar ao nome unico")
    checar(os.path.isfile(os.path.join(base, "[auxiliar]", "route.ts")),
           "install/pause/resume vive em [auxiliar]/route.ts")
    checar(os.path.isfile(os.path.join(base, "[auxiliar]", "config", "route.ts")),
           "a config da corretora vive em [auxiliar]/config/route.ts")


def teste_a_funcao_do_next_aceita_a_arvore():
    """A prova final: chamar a MESMA função que estourou em produção.

    As verificações acima leem nomes de pasta — batem com a regra tal como eu a
    entendi. Esta chama `getSortedRoutes` do próprio Next.js com as rotas reais.
    Se o Next mudar a regra, ou se ela tiver um caso que eu não previ, é esta
    que descobre — as outras continuariam verdes mentindo.

    Roda `scripts/rotas-montam.test.mjs`. Se o node não estiver disponível, isto
    FALHA em vez de pular: guarda que se cala em silêncio não guarda nada, e foi
    justamente um gate silencioso que deixou o site cair.
    """
    print("\n[5] getSortedRoutes, do proprio Next.js, aceita a arvore")
    script = os.path.join(RAIZ, "scripts", "rotas-montam.test.mjs")
    checar(os.path.isfile(script), "scripts/rotas-montam.test.mjs existe")
    if not os.path.isfile(script):
        return

    import subprocess
    try:
        r = subprocess.run(["node", script], cwd=RAIZ, capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           timeout=120, shell=(os.name == "nt"))
    except Exception as exc:  # noqa: BLE001
        checar(False, "o node conseguiu rodar a prova", f"{type(exc).__name__}: {exc}")
        return

    saida = (r.stdout or "") + (r.stderr or "")
    linha = next((l.strip() for l in saida.split("\n") if "different slug names" in l), "")
    checar(r.returncode == 0,
           "o Next.js monta a tabela de rotas",
           linha or (saida.strip().split("\n") or [""])[-1][:150])


def main() -> int:
    print("=" * 68)
    print("A TABELA DE ROTAS MONTA — BUILD VERDE NAO E PROVA DE QUE SOBE")
    print("=" * 68)
    for teste in (teste_um_nome_de_parametro_por_posicao,
                  teste_catch_all_nao_disputa_posicao_com_segmento_simples,
                  teste_o_parametro_declarado_no_codigo_bate_com_a_pasta,
                  teste_a_rota_que_derrubou_o_site_esta_consertada,
                  teste_a_funcao_do_next_aceita_a_arvore):
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
    print("A TABELA DE ROTAS MONTA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
