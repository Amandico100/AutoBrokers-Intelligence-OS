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

# Páginas alcançadas por link DENTRO de outra tela, e não pelo menu.
#
# Não é a mesma coisa que subpágina: o endereço não é filho de ninguém. É uma
# tela que responde a mesma pergunta que outra, num recorte diferente — e dois
# itens de menu para a mesma pergunta é como um menu vira lista.
#
# Cada entrada nomeia DE ONDE se chega. Sem isso, a exceção viraria a desculpa
# para deixar qualquer tela sem link.
ALCANCADAS_POR_OUTRA_TELA = {
    "/admin/prompt-effective":
        "linkada de /admin/capacidades — é o mesmo diagnóstico, por agente",

    # SPEC-064 Bloco B — as três que saíram do menu de sete pilares.
    #
    # Sair do menu não pode virar sumir. Cada uma nomeia de onde se chega, e o
    # caso do §3 CONFERE o link de verdade: exceção que promete alcance e
    # entrega órfã é pior que exceção nenhuma.
    "/dashboard/entregas/pesquisas":
        "linkada do filtro 'Pesquisas' em /dashboard/entregas — pesquisa é "
        "Skill do chat, e o resultado se reencontra em Entregas",
    "/dashboard/configuracoes":
        "linkada como 'Meu perfil' no rodapé do TenantNav — é a camada do "
        "USUÁRIO (nome, senha, avatar, consumo), não da corretora. Não é "
        "trabalho do dia, então não é pilar; mora junto de quem ela pertence",
}

# DÍVIDA HERDADA — páginas do Admin que já estavam órfãs antes da SPEC-059.
#
# Elas ficam listadas, e não filtradas por uma regra genérica, de propósito:
# uma exceção nominal é uma dívida visível; uma regra genérica é uma dívida
# que some. O Founder já registrou em CA-014 que o Admin será reorganizado na
# SPEC-061 — é lá que esta lista deve encolher até desaparecer.
#
# O que este teste impede a partir de agora: que a lista CRESÇA.
#
# Corrigida em 27/07/2026, durante a SPEC-061. A lista tinha nove entradas
# porque este teste lia apenas `masterMenuItems`. Cinco delas são alcançadas
# normalmente pelo administrador da corretora, por `companyAdminMenuItems`:
# `/admin/team`, `/admin/conversations`, `/admin/agent`, `/admin/documents` e
# `/admin/billing`.
#
# A dívida real é de QUATRO páginas — e uma delas, `/admin/integrations`, tem
# o item de menu comentado com `// HIDDEN`. Um teste que superestima a dívida
# é tão ruim quanto um que a esconde: no primeiro caso alguém "conserta" o que
# não estava quebrado.
#
# Zerada em 27/07/2026, na SPEC-061 Bloco C: `/admin/conversation-logs`,
# `/admin/costs` e `/admin/logs` ganharam link no submenu a que já pertenciam.
# Não foram recriadas nem apagadas — apagar tela que alguém escreveu e ninguém
# achou resolve o sintoma errado.
ORFAS_ANTERIORES_A_SPEC059: set[str] = set()

# Página que só REDIRECIONA não é órfã: pôr link de menu para ela seria um
# item que não leva a lugar nenhum.
#
# Em vez de manter esta lista à mão — e ela envelhecer em silêncio — o teste
# LÊ o arquivo e reconhece o padrão. Uma página que importa `redirect` do
# Next e não renderiza nada é, por definição, uma ponte para outro endereço.
SEM_MENU_POR_REDIRECIONAR = {
    "/admin/integrations": "redireciona para /admin; não é destino",
}


def e_redirecionamento(rota: str, base: str, prefixo: str) -> bool:
    """A página só existe para levar a outro lugar?

    SPEC-061 §6.3: as cinco telas da corretora saíram de `/admin` e viraram
    redirecionamento para `/dashboard`. Elas PRECISAM continuar existindo —
    link salvo não some quando a rota muda — e não podem ter item de menu.
    """
    sub = rota[len(prefixo):].lstrip("/")
    caminho = os.path.join(base, *sub.split("/"), "page.tsx") if sub else \
        os.path.join(base, "page.tsx")
    if not os.path.exists(caminho):
        return False
    try:
        fonte = _ler(caminho)
    except Exception:  # noqa: BLE001
        return False
    # `redirect(...)` do Next, e nenhum JSX de conteúdo.
    return ("from 'next/navigation'" in fonte
            and re.search(r"\bredirect\(\s*['\"]/", fonte) is not None
            and "return (" not in fonte)


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


def _sem_comentario(fonte: str) -> str:
    """Link comentado não é link.

    `// { href: '/admin/integrations', ... } // HIDDEN` é código desligado. Sem
    esta limpeza, o teste declarava a página alcançável e ela não estava em
    lugar nenhum do menu — o defeito exato que ele existe para pegar, passando
    despercebido por causa de uma barra dupla.
    """
    return "\n".join(l for l in fonte.split("\n")
                     if not l.lstrip().startswith("//"))


def _itens_do_bloco(bloco: str) -> list[tuple[str, str]]:
    bloco = _sem_comentario(bloco)
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


def _bloco(fonte: str, nome: str) -> str:
    inicio = fonte.find(nome)
    if inicio < 0:
        return ""
    return fonte[inicio:fonte.find("\n  ];", inicio)]


def menu_admin() -> list[tuple[str, str]]:
    """(rótulo, href) do portal admin — os DOIS menus, com submenus.

    O Admin serve a dois papéis com menus diferentes: `masterMenuItems` para a
    plataforma e `companyAdminMenuItems` para o administrador da corretora.
    Ler só o primeiro fazia este teste declarar órfãs cinco páginas que o
    administrador de corretora alcança normalmente — `/admin/team`,
    `/admin/conversations`, `/admin/agent`, `/admin/documents` e
    `/admin/billing`.

    Um teste que superestima a dívida é tão ruim quanto um que a esconde: no
    primeiro caso alguém "conserta" o que não estava quebrado.
    """
    return [item for menu in menus_admin().values() for item in menu]


def menus_admin() -> dict[str, list[tuple[str, str]]]:
    """Os dois menus, SEPARADOS por papel.

    A distinção importa para rótulo duplicado: o layout escolhe um menu ou o
    outro (`role === 'master' ? masterMenuItems : companyAdminMenuItems`), e
    ninguém vê os dois. "Conversas" existir nos dois não é ambiguidade — é a
    mesma ideia dita para públicos diferentes. Comparar os menus somados
    acusaria um problema que o usuário nunca encontra.
    """
    fonte = _ler(os.path.join(APP, "admin", "layout.tsx"))
    return {
        "admin (plataforma)": _itens_do_bloco(_bloco(fonte, "const masterMenuItems")),
        "admin (corretora)": _itens_do_bloco(_bloco(fonte, "const companyAdminMenuItems")),
    }


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------


def teste_nenhum_rotulo_duplicado():
    print("\n[1] Nenhum rótulo de menu se repete")
    papeis = [("corretora", menu_tenant())] + list(menus_admin().items())
    for papel, itens in papeis:
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
            if (rota in ligados or rota in SEM_MENU_POR_DESENHO
                    or rota in SEM_MENU_POR_REDIRECIONAR
                    or rota in ALCANCADAS_POR_OUTRA_TELA
                    or e_redirecionamento(rota, base, prefixo)):
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

    # A exceção de "alcançada por outra tela" precisa ser VERIFICADA, não
    # confiada: uma exceção que declara um link que não existe é pior que
    # nenhuma exceção — ela promete alcançabilidade e entrega órfã.
    # `components/` entra na varredura desde a SPEC-064: a barra de navegação
    # é um componente, e um link que mora nela é tão real quanto um que mora
    # numa página. Sem isso, o teste declararia órfã uma tela linkada do menu.
    ONDE_PODE_HAVER_LINK = (APP, os.path.join(RAIZ, "components"))

    for rota, motivo in ALCANCADAS_POR_OUTRA_TELA.items():
        achou = False
        for base in ONDE_PODE_HAVER_LINK:
            if achou:
                break
            for pasta, _, arquivos in os.walk(base):
                for arq in arquivos:
                    if not arq.endswith((".tsx", ".ts")):
                        continue
                    caminho = os.path.join(pasta, arq)
                    # A própria página não conta como link para si mesma.
                    if os.path.dirname(caminho).replace(os.sep, "/").endswith(
                            rota.replace("/admin", "admin").replace("/dashboard", "dashboard")):
                        continue
                    try:
                        fonte = _ler(caminho)
                    except Exception:  # noqa: BLE001
                        continue
                    if f'"{rota}"' in fonte or f"'{rota}'" in fonte:
                        achou = True
                        break
                if achou:
                    break
        checar(achou, f"{rota} é realmente linkada de alguma tela", motivo)


def teste_paginas_das_specs_recentes_estao_no_menu():
    """As telas das SPECs recentes continuam alcançáveis — no lugar certo.

    ATUALIZADO EM 02/08/2026, SPEC-064 Bloco B.

    Este caso exigia que `/dashboard/briefing` e `/dashboard/pesquisas`
    tivessem link NO MENU. O princípio está certo — *tela sem link é tela que
    não existe para quem usa* — e foi ele que fez as duas virarem PILARES nas
    SPECs 059 e 060.

    A conclusão é que estava errada. Briefing é um **Auxiliar** e Pesquisa é
    uma **Skill**: o lugar delas é DENTRO de um pilar, não como pilar. Sete
    itens de menu, dois deles Auxiliares disfarçados, é como um menu vira lista
    — e o próprio `navigation.ts` trazia escrito que "o menu não cresce".

    O que este caso protege continua idêntico: **alcançável**. Mudou só o que
    conta como alcance — link no menu OU dentro do pilar que a contém.
    """
    print("\n[4] As telas das SPECs 059-061 continuam alcançáveis")
    ligados = {href for _, href in menu_tenant()} | {href for _, href in menu_admin()}

    for rota, spec in (("/admin/inteligencia", "SPEC-059"),
                       ("/admin/pesquisa", "SPEC-060"),
                       ("/admin/governanca", "SPEC-061")):
        checar(rota in ligados, f"{rota} tem link no menu ({spec})",
               "tela sem link é tela que não existe para quem usa")

    # As duas que saíram do menu: continuam alcançáveis, por dentro do pilar.
    for rota, de_onde, spec in (
        ("/dashboard/auxiliares/checklist-6h/hoje",
         "da ficha do Auxiliar 'Checklist das 6h'", "SPEC-059 → 064"),
        ("/dashboard/entregas/pesquisas",
         "do filtro 'Pesquisas' em Entregas", "SPEC-060 → 064"),
    ):
        achou = False
        for pasta, _, arquivos in os.walk(os.path.join(RAIZ, "app")):
            if "node_modules" in pasta:
                continue
            for arq in arquivos:
                if not arq.endswith((".ts", ".tsx")):
                    continue
                caminho = os.path.join(pasta, arq)
                # A própria página não conta como link para si mesma.
                if os.path.normpath(caminho).endswith(
                        os.path.normpath(rota.replace("/dashboard", "dashboard") + "/page.tsx")):
                    continue
                try:
                    fonte = _ler(caminho)
                except Exception:  # noqa: BLE001
                    continue
                if f'"{rota}"' in fonte or f"'{rota}'" in fonte:
                    achou = True
                    break
            if achou:
                break
        checar(achou, f"{rota} é alcançável {de_onde} ({spec})",
               "saiu do menu não pode virar sumiu")


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
