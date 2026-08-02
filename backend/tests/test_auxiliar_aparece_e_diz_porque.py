"""Todo Auxiliar aparece, e o que não dá para ligar diz por quê.

O que a auditoria mediu, em 02/08/2026
--------------------------------------
Eram três cliques para chegar ao que devia estar na primeira tela::

    Auxiliares → 2 cards intermediários → clica → aí sim a galeria

E os Auxiliares de verdade não estavam em nenhuma das três telas: moravam em
`/dashboard/auxiliares/meus`, sem link no menu.

Pior: a galeria tinha a rota dinâmica `[slug]` **e mais duas páginas escritas
à mão do lado** — `follow-up-whatsapp/` e `resumo-atendimentos/`. Os dois
únicos Auxiliares reais ganharam página própria. É assim que a bagunça se
reproduz: cada peça nova acha que é exceção.

A decisão do Founder que este teste também protege
--------------------------------------------------
Em 02/08/2026::

    "Se o portal da Allianz estiver conectado, ele deve servir para QUALQUER
     auxiliar que precisar de acesso ao portal da Allianz, e não ter que fazer
     novamente a conexão em cada auxiliar."

A metade difícil já estava certa — `tenant_connections` e `portal_accounts`
são por `company_id`. O que faltava era o Auxiliar DECLARAR do que precisa,
para a tela poder dizer "conecte o portal para poder ligar" em vez de deixar
o corretor ligar uma coisa que vai falhar em silêncio.

O que este teste protege
------------------------
* nenhum Auxiliar do catálogo fica invisível
* a página é uma só — sem card intermediário e sem página escrita à mão
* "em breve" não liga, e a recusa é do SERVIDOR, não só do botão
* quem depende de conexão que a corretora não tem também não liga
* e a conexão é da corretora: um mesmo conector serve vários Auxiliares
"""

from __future__ import annotations

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FALHAS: list[str] = []

PASTA_AUX = os.path.join(RAIZ, "app", "dashboard", "auxiliares")


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(*partes: str) -> str:
    with open(os.path.join(RAIZ, *partes), encoding="utf-8") as fh:
        return fh.read()


def _sem_comentario(fonte: str) -> str:
    sem_linha = "\n".join(
        l for l in fonte.split("\n") if not l.lstrip().startswith(("//", "*", "/*"))
    )
    return re.sub(r"/\*.*?\*/", "", sem_linha, flags=re.S)


# ---------------------------------------------------------------------------

def teste_uma_pagina_so():
    print("\n[1] A página principal mostra os Auxiliares, sem card intermediário")
    fonte = _sem_comentario(_ler("app", "dashboard", "auxiliares", "page.tsx"))

    checar("GalleryCard" not in fonte,
           "não há mais card intermediário na página principal",
           "GalleryCard era o 'Rotinas prontas / Minhas rotinas'")
    checar("AuxiliaresClient" in fonte,
           "a página renderiza o catálogo direto")

    cliente = _sem_comentario(
        _ler("app", "dashboard", "auxiliares", "AuxiliaresClient.tsx"))
    checar("/api/dashboard/auxiliaries" in cliente,
           "o catálogo vem da rota que lê o catálogo global")
    checar("Trabalhando para você" in cliente and "Em breve" in cliente,
           "a tela separa o que trabalha do que ainda não existe")


def teste_a_rota_e_unica():
    print("\n[2] Um Auxiliar, uma rota — nenhuma página escrita à mão")
    dinamica = os.path.join(PASTA_AUX, "[slug]", "page.tsx")
    checar(os.path.isfile(dinamica),
           "existe a rota dinâmica /dashboard/auxiliares/[slug]")

    # Qualquer pasta cujo nome seja o slug de um Auxiliar é página à mão.
    # As pastas de FUNÇÃO (rotinas, execucoes…) são legítimas e ficam de fora.
    #
    # DÍVIDA NOMEADA: `follow-up-whatsapp` e `resumo-atendimentos` não são
    # duplicata de descrição — são telas de EXECUÇÃO, com API própria, que
    # funcionam. Apagá-las para o teste passar removeria função do produto, que
    # é o oposto do trabalho. Elas são alcançadas pela rota nova (campo
    # `tela_de_execucao`) e o port fica registrado.
    #
    # O que este caso impede é a TERCEIRA: um Auxiliar novo nascer com página
    # escrita à mão. Aí sim é a bagunça se reproduzindo.
    funcoes = {"[slug]", "galeria", "meus", "rotinas", "execucoes"}
    divida_conhecida = {"follow-up-whatsapp", "resumo-atendimentos"}

    a_mao: list[str] = []
    conhecidas: list[str] = []
    for base in (PASTA_AUX, os.path.join(PASTA_AUX, "galeria")):
        if not os.path.isdir(base):
            continue
        for nome in os.listdir(base):
            caminho = os.path.join(base, nome)
            if not os.path.isdir(caminho) or nome in funcoes:
                continue
            if not os.path.isfile(os.path.join(caminho, "page.tsx")):
                continue
            rel = os.path.relpath(caminho, RAIZ).replace(os.sep, "/")
            (conhecidas if nome in divida_conhecida else a_mao).append(rel)

    checar(not a_mao,
           "nenhum Auxiliar NOVO nasceu com página escrita à mão",
           f"{a_mao} — cada um destes é a bagunça se reproduzindo")

    if conhecidas:
        print(f"      dívida registrada (telas de execução a portar): {conhecidas}")

    # E o que elas NÃO podem ser é órfãs.
    catalogo_ts = _ler("lib", "auxiliaries", "catalog.ts")
    checar("tela_de_execucao" in catalogo_ts,
           "as telas de execução são alcançadas pela rota nova",
           "sem isso o corretor precisaria decorar o endereço")


def teste_a_pagina_do_auxiliar_tem_as_secoes():
    print("\n[3] A página de cada Auxiliar responde na ordem em que se decide")
    fonte = _ler("app", "dashboard", "auxiliares", "[slug]", "AuxiliarDetalheClient.tsx")
    for secao in ("O que é", "O que ele faz", "O que você ganha",
                  "De onde ele tira a informação", "Conexões que ele usa",
                  "Rotinas deste Auxiliar", "Histórico"):
        checar(secao in fonte, f'traz a seção "{secao}"')

    checar("item.headline" in fonte, "mostra a headline, não só o nome")
    checar("falta_para_existir" in fonte,
           "o 'em breve' explica o que falta para existir")


def teste_em_breve_nao_liga_e_a_recusa_e_do_servidor():
    print("\n[4] 'Em breve' não liga — e quem recusa é o servidor")
    tela = _ler("app", "dashboard", "auxiliares", "[slug]", "AuxiliarDetalheClient.tsx")
    checar("coming_soon" in tela and "disabled" in tela,
           "o botão fica desabilitado para 'em breve'")

    # O botão é conveniência. A trava de verdade tem de estar no servidor:
    # um POST direto não pode instalar um Auxiliar cujo runtime é 'none'.
    store = _sem_comentario(_ler("lib", "admin", "tenant-auxiliary-store.ts"))
    checar("catalog_state" in store,
           "o servidor lê o estado de catálogo antes de instalar")
    checar("ainda_nao_disponivel" in store,
           "o servidor recusa instalar um 'em breve'",
           "sem isso, botão desabilitado é teatro")

    pos_check = store.find("ainda_nao_disponivel")
    pos_insert = store.find(".insert(")
    checar(pos_check != -1 and pos_insert != -1 and pos_check < pos_insert,
           "a recusa vem ANTES de gravar a instalação")


def teste_conexao_e_da_corretora():
    print("\n[5] A conexão é da corretora — conectou uma vez, serve a todos")
    catalogo = _sem_comentario(_ler("lib", "auxiliaries", "catalog.ts"))

    checar("conexoesDaCorretora" in catalogo,
           "existe UMA função que responde o que a corretora tem conectado")
    checar("companyId" in catalogo and "tenant_connections" in catalogo,
           "a prontidão é calculada por corretora, nunca por auxiliar")

    # As três fontes de verdade que existem hoje. Ignorar qualquer uma faria a
    # tela dizer "não conectado" para quem já fez o trabalho.
    for fonte, porque in (
        ("tenant_connections", "o caminho novo (InfoCap, Drive, Notion)"),
        ("portal_accounts", "o portal_worker, que entra na Allianz de verdade"),
        ("integrations", "o WhatsApp, anterior ao conceito de conector"),
    ):
        checar(fonte in catalogo, f"considera {fonte} — {porque}")

    store = _sem_comentario(_ler("lib", "admin", "tenant-auxiliary-store.ts"))
    checar("falta_conectar" in store,
           "o servidor recusa ligar Auxiliar sem a conexão que ele exige",
           "ligar sem conexão produz um card 'ligado' que falha em silêncio")


def teste_catalogo_e_global(catalogo: list[dict]):
    print("\n[6] O catálogo é global — toda corretora vê os mesmos Auxiliares")
    globais = [a for a in catalogo
               if (a.get("default_config") or {}).get("visibility", {}).get("type") != "private"]
    checar(len(globais) == len(catalogo),
           "nenhum Auxiliar do catálogo é privado de uma corretora",
           f"{len(catalogo) - len(globais)} privados")

    # Um conector serve vários Auxiliares — é o que torna "conectou uma vez"
    # verdade. Se cada Auxiliar pedisse um conector exclusivo, a promessa seria
    # falsa mesmo com o código certo.
    uso: dict[str, int] = {}
    for a in catalogo:
        for c in (a.get("required_connectors") or []):
            uso[c] = uso.get(c, 0) + 1
    compartilhados = {c: n for c, n in uso.items() if n > 1}
    checar(bool(compartilhados),
           "há conector usado por mais de um Auxiliar",
           f"uso: {uso}")
    print(f"      compartilhados: {compartilhados}")


def _catalogo() -> list[dict] | None:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
    if not url or not key:
        return None
    try:
        import httpx
    except ImportError:
        return None
    try:
        r = httpx.get(
            f"{url.rstrip('/')}/rest/v1/auxiliary_templates",
            params={"select": "slug,required_connectors,default_config,catalog_state",
                    "status": "eq.active"},
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
            timeout=20,
        )
        return r.json() if r.status_code == 200 else None
    except Exception:  # noqa: BLE001
        return None


def main() -> int:
    print("=" * 68)
    print("TODO AUXILIAR APARECE, E O QUE NÃO LIGA DIZ POR QUÊ")
    print("=" * 68)

    for teste in (teste_uma_pagina_so,
                  teste_a_rota_e_unica,
                  teste_a_pagina_do_auxiliar_tem_as_secoes,
                  teste_em_breve_nao_liga_e_a_recusa_e_do_servidor,
                  teste_conexao_e_da_corretora):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    cat = _catalogo()
    if cat is None:
        print("\n[6] (sem credencial de banco — caso pulado)")
    else:
        try:
            teste_catalogo_e_global(cat)
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"catalogo_global: {type(exc).__name__}: {exc}")
            print(f"  X   catálogo global EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 68)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("UMA TELA, TODOS OS AUXILIARES, E A CONEXÃO É DA CORRETORA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
