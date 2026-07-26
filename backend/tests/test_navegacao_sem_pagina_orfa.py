"""Toda página tem link, e nenhum rótulo se repete.

Por que este teste existe
-------------------------
Na SPEC-059 eu criei `/admin/inteligencia` com 589 linhas e **esqueci de pôr
no menu**. O Founder seguiu a instrução "abra /admin/inteligencia" e não
achou. No mesmo commit, criei um item chamado "Inteligência" sem notar que já
existia outro com o rótulo idêntico — e um menu com dois itens de mesmo nome
não é confuso, é AMBÍGUO: não há como o usuário saber qual abrir.

As duas falhas são de classe, não de descuido:

* **página órfã** — tela sem link é tela que não existe para quem usa;
* **rótulo duplicado** — o usuário acerta por sorte.

Boa intenção não impede que voltem. Um teste, sim.

Regra que este arquivo cobra:
1. Toda página nova precisa de link no menu do papel que a usa.
2. Nenhum rótulo de menu pode repetir dentro do mesmo papel.
3. Todo link do menu precisa apontar para uma página que existe.
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


# ---------------------------------------------------------------------------
# Descoberta de páginas
# ---------------------------------------------------------------------------

# Páginas que legitimamente não têm link de menu, com o motivo. Toda entrada
# aqui é uma decisão consciente — a lista existe para que a exceção seja
# declarada, e não para silenciar o teste.
SEM_MENU_POR_DESENHO = {
    "/admin": "é a raiz do portal; o próprio logo leva até ela",
    "/admin/login": "tela de entrada, anterior ao menu",
    "/dashboard": "é a raiz do dashboard (chat), alcançada pelo logo",
    "/dashboard/chat": "mesma experiência da raiz",
    "/dashboard/loading": "estado de carregamento, não é destino",
    "/admin/loading": "estado de carregamento, não é destino",
}

# Prefixos de subpágina: alcançadas a partir da página-mãe, que tem link.
PREFIXOS_DE_SUBPAGINA = (
    "/dashboard/auxiliares/",
    "/dashboard/personalizacao/",
    "/dashboard/configuracoes/",
    "/dashboard/atendimentos/",
    "/admin/auxiliares/",
    "/admin/inteligencia/",
    "/admin/companies/",
    "/admin/finops/",
    "/admin/knowledge-base/",
    "/admin/connectors/",
)

# DÍVIDA HERDADA — páginas do Admin que já estavam órfãs antes da SPEC-059.
#
# Elas ficam listadas, e não filtradas por uma regra genérica, de propósito:
# uma exceção nominal é uma dívida visível; uma regra genérica é uma dívida
# que some. O Founder já registrou em CA-014 que o Admin será reorganizado na
# SPEC-061 — é lá que esta lista deve encolher até desaparecer.
#
# O que este teste impede a partir de agora: que a lista CRESÇA.
ORFAS_ANTERIORES_A_SPEC059 = {
    "/admin/agent",
    "/admin/billing",
    "/admin/conversation-logs",
    "/admin/conversations",
    "/admin/costs",
    "/admin/documents",
    "/admin/integrations",
    "/admin/logs",
    "/admin/team",
}


def paginas(base: str, prefixo: str) -> list[str]:
    """Rotas de página do Next (`page.tsx`), sem rotas dinâmicas."""
    encontradas: list[str] = []
    for pasta, _, arquivos in os.walk(base):
        if "page.tsx" not in arquivos:
            continue
        rel = os.path.relpath(pasta, base).replace(os.sep, "/")
        rota = prefixo if rel == "." else f"{prefixo}/{rel}"
        if "[" in rota or "(" in rota:
            continue  # rota dinâmica não é destino de menu
        encontradas.append(rota)
    return sorted(encontradas)


def _ler(caminho: str) -> str:
    with open(caminho, encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# Menus
# ---------------------------------------------------------------------------


def menu_tenant() -> list[tuple[str, str]]:
    """(rótulo, href) da navegação da corretora.

    O `short:` opcional entra no meio de alguns itens — por isso o grupo
    intermediário. Sem ele, o par sai trocado e o teste acusa erro onde não há.
    """
    fonte = _ler(os.path.join(RAIZ, "lib", "navigation.ts"))
    return re.findall(
        r"label:\s*'([^']+)',\s*(?:short:\s*'[^']*',\s*)?href:\s*'([^']+)'",
        fonte)


def menu_admin() -> list[tuple[str, str]]:
    """(rótulo, href) do portal admin, incluindo submenus."""
    fonte = _ler(os.path.join(APP, "admin", "layout.tsx"))
    inicio = fonte.find("const masterMenuItems")
    if inicio < 0:
        return []
    bloco = fonte[inicio:fonte.find("\n  ];", inicio)]
    saida: list[tuple[str, str]] = []
    # Item simples: href antes de label.
    for href, rotulo in re.findall(
            r"href:\s*'([^']+)',\s*icon:\s*\w+,\s*label:\s*'([^']+)'", bloco):
        saida.append((rotulo, href))
    # Item de submenu: href depois de label.
    for href, rotulo in re.findall(r"\{\s*href:\s*'([^']+)',\s*label:\s*'([^']+)'\s*\}",
                                   bloco):
        saida.append((rotulo, href))
    return saida


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------


def teste_nenhum_rotulo_duplicado():
    print("\n[1] Nenhum rótulo de menu se repete")
    for papel, itens in (("corretora", menu_tenant()), ("admin", menu_admin())):
        vistos: dict[str, list[str]] = {}
        for rotulo, href in itens:
            vistos.setdefault(rotulo.strip().lower(), []).append(href)
        duplicados = {r: hs for r, hs in vistos.items() if len(hs) > 1}
        checar(not duplicados,
               f"menu da {papel} não tem rótulo repetido",
               "; ".join(f"'{r}' aponta para {hs}" for r, hs in duplicados.items()))


def teste_todo_link_leva_a_pagina_existente():
    print("\n[2] Todo link do menu leva a uma página que existe")
    rotas_tenant = set(paginas(os.path.join(APP, "dashboard"), "/dashboard"))
    rotas_admin = set(paginas(os.path.join(APP, "admin"), "/admin"))
    todas = rotas_tenant | rotas_admin

    for papel, itens in (("corretora", menu_tenant()), ("admin", menu_admin())):
        quebrados = [href for _, href in itens if href not in todas]
        checar(not quebrados,
               f"menu da {papel} não aponta para página inexistente",
               ", ".join(quebrados))


def teste_nenhuma_pagina_orfa():
    print("\n[3] Nenhuma página fica sem link no menu do papel que a usa")
    ligados = {href for _, href in menu_tenant()} | {href for _, href in menu_admin()}

    for papel, base, prefixo in (("corretora", os.path.join(APP, "dashboard"), "/dashboard"),
                                 ("admin", os.path.join(APP, "admin"), "/admin")):
        orfas = []
        for rota in paginas(base, prefixo):
            if rota in ligados or rota in SEM_MENU_POR_DESENHO:
                continue
            if rota in ORFAS_ANTERIORES_A_SPEC059:
                continue
            if any(rota.startswith(p) for p in PREFIXOS_DE_SUBPAGINA):
                continue
            orfas.append(rota)
        checar(not orfas,
               f"nenhuma página órfã NOVA no {papel}",
               ", ".join(orfas))

    # A dívida herdada não pode crescer, e também não some sozinha: se uma
    # delas ganhar link, some da lista — e o teste avisa para atualizá-la.
    ja_resolvidas = [r for r in ORFAS_ANTERIORES_A_SPEC059 if r in ligados]
    checar(not ja_resolvidas,
           "a lista de dívida herdada está atualizada",
           f"já têm link e podem sair da lista: {', '.join(ja_resolvidas)}")


def teste_paginas_das_specs_recentes_estao_no_menu():
    print("\n[4] As telas das SPECs 059 e 060 estão alcançáveis")
    ligados = {href for _, href in menu_tenant()} | {href for _, href in menu_admin()}
    for rota, spec in (("/dashboard/briefing", "SPEC-059"),
                       ("/admin/inteligencia", "SPEC-059"),
                       ("/dashboard/pesquisas", "SPEC-060"),
                       ("/admin/pesquisa", "SPEC-060")):
        checar(rota in ligados, f"{rota} tem link no menu ({spec})",
               "tela sem link é tela que não existe para quem usa")


def main() -> int:
    print("=" * 68)
    print("NAVEGAÇÃO — nenhuma página órfã, nenhum rótulo ambíguo")
    print("=" * 68)
    for teste in (teste_nenhum_rotulo_duplicado,
                  teste_todo_link_leva_a_pagina_existente,
                  teste_nenhuma_pagina_orfa,
                  teste_paginas_das_specs_recentes_estao_no_menu):
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
    print("NAVEGAÇÃO ÍNTEGRA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
