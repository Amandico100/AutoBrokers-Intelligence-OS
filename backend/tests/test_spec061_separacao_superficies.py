"""SPEC-061 §6 — `/admin` é da plataforma, `/dashboard` é da corretora.

Por que este arquivo existe
---------------------------
Até esta SPEC, as duas superfícies moravam no mesmo lugar. Um administrador de
corretora entrava em `/admin` — endereço que soa como "administração da
plataforma" — e o sistema **escondia** os itens que não eram dele, com uma
lista chamada `masterOnlyRoutes` mantida **no navegador**.

Duas coisas estavam erradas ali:

1. **Esconder item de menu não protege nada.** Quem digitasse o endereço
   chegava lá. §8.4 já dizia isso com todas as letras.
2. **A lista era enumerativa.** Toda tela nova precisava lembrar de entrar
   nela — e o esquecimento não produzia erro nenhum, produzia acesso.

A regra agora é de exclusão, não de enumeração: quem não é plataforma não
entra em `/admin`. Não há lista para manter.

Este teste protege três coisas que, se voltarem atrás, voltam em silêncio.
"""

from __future__ import annotations

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP = os.path.join(RAIZ, "app")
FALHAS: list[str] = []

# As cinco telas que saíram do `/admin`, e onde a corretora as encontra.
#
# Quatro delas apontam para dentro da Personalização, e não para um endereço
# novo na raiz do dashboard. O motivo está registrado em `lib/navigation.ts`:
# a casa já existia desde a SPEC-045, e criar um segundo endereço para a mesma
# coisa não é organizar — é duplicar.
#
# `/admin/conversations` mudou de destino em 02/08/2026, na SPEC-064 Bloco B.
# A §6 tinha movido a tela para `/dashboard/conversas`, e a auditoria da 064
# mediu o efeito colateral: passaram a existir DUAS telas de conversa da
# corretora. A que veio do admin continuou chamando `/api/admin/conversations`
# de dentro da casa da corretora — a mesma mistura que a §6 mandou desfazer.
# A duplicata foi removida; o destino agora é a tela de tenant da SPEC-043.
#
# O propósito deste caso não mudou: rota antiga leva à casa nova, nunca a 404.
MUDARAM_DE_CASA = {
    "/admin/team": "/dashboard/personalizacao/equipe",
    "/admin/conversations": "/dashboard/atendimentos/conversas",
    "/admin/agent": "/dashboard/personalizacao/agentes/autobrokers",
    "/admin/documents": "/dashboard/personalizacao/conhecimento",
    "/admin/billing": "/dashboard/personalizacao/custos",
}

# Os quatro endereços que eu criei na raiz do dashboard e que ficaram órfãos.
# Continuam existindo como redirecionamento — link salvo não pode virar 404.
RAIZ_DUPLICADA = {
    "/dashboard/equipe": "/dashboard/personalizacao/equipe",
    "/dashboard/agente": "/dashboard/personalizacao/agentes/autobrokers",
    "/dashboard/documentos": "/dashboard/personalizacao/conhecimento",
    "/dashboard/plano": "/dashboard/personalizacao/custos",
}


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(caminho: str) -> str:
    with open(caminho, encoding="utf-8") as fh:
        return fh.read()


def teste_telas_da_corretora_vivem_no_dashboard():
    print("\n[1] As cinco telas da corretora moram na casa dela")
    for antigo, novo in MUDARAM_DE_CASA.items():
        destino = os.path.join(APP, *novo.strip("/").split("/"), "page.tsx")
        checar(os.path.exists(destino), f"{novo} existe", destino)


def teste_endereco_antigo_redireciona():
    print("\n[2] Link salvo não vira 404")
    # E-mail de convite, favorito, mensagem antiga no WhatsApp. Apagar a rota
    # transformaria cada um num 404 — e a corretora não tem a quem perguntar.
    for antigo, novo in MUDARAM_DE_CASA.items():
        caminho = os.path.join(APP, *antigo.strip("/").split("/"), "page.tsx")
        if not os.path.exists(caminho):
            checar(False, f"{antigo} continua existindo como redirecionamento",
                   "o arquivo sumiu — link salvo vira 404")
            continue
        fonte = _ler(caminho)
        checar(f"redirect('{novo}')" in fonte,
               f"{antigo} redireciona para {novo}",
               "não encontrei o redirect com o destino certo")


def teste_admin_nao_tem_mais_menu_de_corretora():
    print("\n[3] O Admin não monta mais menu para a corretora")
    fonte = _ler(os.path.join(APP, "admin", "layout.tsx"))
    # O comentário que EXPLICA a remoção cita o nome antigo — e deve citar,
    # senão a próxima pessoa recria a lista sem saber por que ela saiu. O que
    # o teste cobra é o CÓDIGO, não a explicação.
    sem_comentario = "\n".join(l for l in fonte.split("\n")
                               if not l.lstrip().startswith("//"))

    checar("companyAdminMenuItems = [" not in sem_comentario,
           "`companyAdminMenuItems` não existe mais")
    checar("masterOnlyRoutes" not in sem_comentario,
           "a lista `masterOnlyRoutes` sumiu — a regra virou de exclusão")
    for antigo in MUDARAM_DE_CASA:
        checar(f"href: '{antigo}'" not in sem_comentario,
               f"'{antigo}' não é item de menu do Admin")


def _menu_renderizado() -> tuple[list[str], list[str]]:
    """Os endereços que o corretor REALMENTE vê, lidos do componente que pinta.

    A versão anterior deste teste lia `lib/navigation.ts` e conferia se o link
    existia lá. Passou verde enquanto quatro telas estavam órfãs — porque o
    grupo onde os links moravam nunca foi importado por componente nenhum.
    Provar que o dado existe não prova que ele aparece.

    Agora o caminho é o mesmo do navegador: descobrir quais grupos o
    `TenantNav.tsx` renderiza, e só então ler os itens desses grupos.
    """
    nav = _ler(os.path.join(RAIZ, "components", "layout", "TenantNav.tsx"))
    grupos = re.findall(r"\{([A-Z_]{3,})\.map\(", nav)

    fonte = _ler(os.path.join(RAIZ, "lib", "navigation.ts"))
    enderecos: list[str] = []
    for grupo in grupos:
        bloco = re.search(rf"export const {grupo}[^=]*=\s*\[(.*?)\n\];", fonte, re.S)
        if bloco:
            enderecos += re.findall(r"href:\s*'([^']+)'", bloco.group(1))
    return grupos, enderecos


def teste_dashboard_recebeu_as_telas():
    print("\n[4] A corretora ALCANÇA as telas pelo menu que ela vê")
    grupos, enderecos = _menu_renderizado()
    checar(bool(grupos), "o TenantNav renderiza pelo menos um grupo", str(grupos))
    print(f"      grupos renderizados: {', '.join(grupos)}")
    print(f"      itens no menu: {len(enderecos)}")

    # Alcançável = o próprio endereço está no menu, OU ele mora DENTRO de um
    # item do menu. `/dashboard/personalizacao/equipe` é alcançável porque
    # "Personalização" está no menu e a tela vive dentro dela.
    def alcancavel(destino: str) -> bool:
        return any(destino == e or destino.startswith(e.rstrip("/") + "/")
                   for e in enderecos)

    for destino in MUDARAM_DE_CASA.values():
        checar(alcancavel(destino), f"{destino} é alcançável pelo menu",
               "tela sem caminho no menu é tela que não existe para quem usa")


def teste_o_menu_nao_cresce():
    print("\n[4b] O menu não cresceu para acomodar as telas que mudaram")
    # A regra que ficou: coisa nova entra DENTRO de um item que já existe. Foi
    # criar quatro itens de primeiro nível que produziu o problema anterior —
    # e ainda por cima nenhum deles chegou a aparecer.
    _, enderecos = _menu_renderizado()
    for destino in list(MUDARAM_DE_CASA.values()) + list(RAIZ_DUPLICADA):
        if destino == "/dashboard/conversas":
            continue  # já era item do menu antes de tudo isso
        checar(destino not in enderecos,
               f"'{destino}' não virou item de primeiro nível",
               "o menu tem que caber na cabeça; ele não cresce a cada tela")

    # O comentário que EXPLICA a remoção cita o nome antigo, e deve citar —
    # senão a próxima pessoa recria o grupo sem saber por que ele saiu. O que
    # se cobra aqui é o CÓDIGO.
    nav = _ler(os.path.join(RAIZ, "lib", "navigation.ts"))
    nav_sem_comentario = re.sub(r"/\*.*?\*/", "", nav, flags=re.S)
    nav_sem_comentario = "\n".join(l for l in nav_sem_comentario.split("\n")
                                   if not l.lstrip().startswith("//"))
    checar("ADMINISTRACAO_DA_CORRETORA" not in nav_sem_comentario,
           "o grupo órfão foi removido de vez",
           "declarar grupo que ninguém renderiza é como não ter feito nada")


def teste_duplicata_da_raiz_redireciona():
    print("\n[4c] Os endereços duplicados da raiz levam para a casa única")
    for antigo, novo in RAIZ_DUPLICADA.items():
        caminho = os.path.join(APP, *antigo.strip("/").split("/"), "page.tsx")
        if not os.path.exists(caminho):
            checar(False, f"{antigo} continua existindo como redirecionamento",
                   "o arquivo sumiu — link salvo vira 404")
            continue
        fonte = _ler(caminho)
        checar(f"redirect('{novo}')" in fonte,
               f"{antigo} leva para {novo}")
        # E não pode ter sobrado tela de verdade junto com o redirect: duas
        # telas para a mesma coisa é o defeito que este bloco desfaz.
        checar("'use client'" not in fonte,
               f"{antigo} não renderiza mais uma segunda tela",
               "sobrou interface junto com o redirecionamento")


def teste_admin_expulsa_quem_nao_e_plataforma():
    print("\n[5] Quem não é plataforma não fica em /admin — e quem é, FICA")
    # Este caso já cobrou a regra de exclusão escrita como `role !== 'master'`,
    # e essa versão trancou o Founder para fora do próprio Admin.
    #
    # O papel resolvido no NAVEGADOR vem de três sessões com vocabulários e
    # prazos diferentes (localStorage diz "master" e dura 8h; o cookie diz
    # "master_admin" e morre ao fechar o navegador; a sessão de usuário diz
    # "admin"). Quando as duas primeiras expiram, sobra a terceira — e ela
    # responde "corretora", que é verdade e é a resposta errada para a pergunta
    # "você é a plataforma?". Valendo para todo `/admin/*`, isso vira um pulo
    # para o `/dashboard` sem saída.
    #
    # O que o teste protege agora é a FORMA da decisão, não a string do papel:
    # quem decide é o servidor, e há três destinos, não dois.
    fonte = _ler(os.path.join(APP, "admin", "layout.tsx"))
    sem_comentario = "\n".join(l for l in fonte.split("\n")
                               if not l.lstrip().startswith("//"))

    checar("router.push('/dashboard')" in sem_comentario,
           "quem é corretora é mandado para a casa dela",
           "a regra de exclusão sumiu do layout")
    checar("router.push('/admin/login')" in sem_comentario,
           "quem não tem sessão recebe o login do Admin",
           "sem isso, quem pede /admin é deportado e não tem como voltar")
    checar("sessionType" in sem_comentario and "master_admin" in sem_comentario,
           "quem decide é a sessão no servidor, não o papel do navegador",
           "voltou a decidir por string de papel no cliente")
    checar(re.search(r"if\s*\(\s*role\s*&&\s*role\s*!==\s*'master'\s*\)\s*\{\s*\n?\s*router\.push\('/dashboard'\)",
                     sem_comentario) is None,
           "não expulsa mais pelo papel adivinhado no navegador",
           "esta é exatamente a regra que trancou o dono para fora")


def teste_nenhuma_tela_do_dashboard_empurra_para_admin():
    print("\n[7] Nenhuma tela da corretora empurra o visitante para /admin")
    # Esta é a versão FORTE do caso anterior, e existe porque a versão fraca
    # não bastou: eu conferia se o guard abria exceção para `master`, e o
    # Founder relatou o mesmo defeito duas vezes.
    #
    # A causa era comparar NOME DE PAPEL entre três vocabulários — a sessão
    # grava `master_admin`, o hook devolve `master`, e cada tela comparava com
    # uma coisa diferente. Igualdade de string entre vocabulários que ninguém
    # unificou é frágil por natureza.
    #
    # A regra agora é de forma, não de conteúdo: uma tela do `/dashboard` NÃO
    # empurra ninguém para `/admin`. Se falta corretora para mostrar, ela DIZ
    # isso. Mensagem explica; redirecionamento silencioso vira vaivém.
    dash = os.path.join(APP, "dashboard")
    for pasta, _, arquivos in os.walk(dash):
        for arq in arquivos:
            if not arq.endswith((".tsx", ".ts")):
                continue
            caminho = os.path.join(pasta, arq)
            fonte = "\n".join(l for l in _ler(caminho).split("\n")
                              if not l.lstrip().startswith("//"))
            empurra = ("push('/admin')" in fonte or 'push("/admin")' in fonte
                       or "redirect('/admin')" in fonte)
            rel = os.path.relpath(caminho, os.path.dirname(APP)).replace(os.sep, "/")
            checar(not empurra, f"{rel} não empurra para /admin",
                   "quem chega pelo redirecionamento volta ao ponto de partida")


def teste_destino_nao_devolve_o_master():
    print("\n[7b] E se houver guard de papel, ele admite o master")
    # O defeito que o Founder encontrou: `/admin/documents` redirecionava
    # CERTO, e o destino mandava o `master` de volta para `/admin`. Da cadeira
    # de quem testa, isso é indistinguível de "não redireciona" — você volta ao
    # ponto de partida.
    #
    # A causa: o guard `role !== 'company_admin'` nasceu quando a tela morava em
    # /admin, onde queria dizer "não é seu". Depois da mudança de casa, o efeito
    # virou o oposto.
    #
    # Três das cinco telas foram tratadas de formas diferentes no MESMO commit:
    # `equipe` já excluía o master, `plano` e `conversas` nunca checavam papel,
    # e `agente` e `documentos` mantiveram o guard antigo. Este caso existe para
    # que as cinco tenham o mesmo comportamento.
    import re as _re
    for novo in MUDARAM_DE_CASA.values():
        caminho = os.path.join(APP, *novo.strip("/").split("/"), "page.tsx")
        if not os.path.exists(caminho):
            continue
        fonte = _ler(caminho)
        # Sem guard de papel: nada a conferir — a tela não expulsa ninguém.
        if "role !== 'company_admin'" not in fonte:
            checar(True, f"{novo} não expulsa por papel")
            continue
        # Com guard: ele PRECISA abrir exceção para o master.
        tem_excecao = _re.search(
            r"role\s*!==\s*'company_admin'\s*&&\s*role\s*!==\s*'master'", fonte)
        checar(tem_excecao is not None,
               f"{novo} deixa o master entrar",
               "o guard devolve o master para /admin, e quem chega pelo "
               "redirecionamento volta ao ponto de partida")


def teste_link_interno_nao_atravessa_superficie():
    print("\n[8] Link do Admin não joga o operador na casa da corretora")
    # `/admin/knowledge-base/sanitize` tinha um "voltar" para `/admin/documents`
    # — resíduo da época em que aquela era a Base de Conhecimento do Admin.
    # Depois da separação, esse "voltar" atravessava para o /dashboard.
    for pasta, _, arquivos in os.walk(os.path.join(APP, "admin")):
        for arq in arquivos:
            if not arq.endswith((".tsx", ".ts")):
                continue
            caminho = os.path.join(pasta, arq)
            fonte = "\n".join(l for l in _ler(caminho).split("\n")
                              if not l.lstrip().startswith("//"))
            achados = [antigo for antigo in MUDARAM_DE_CASA
                       if f'href="{antigo}"' in fonte or f"href='{antigo}'" in fonte]
            rel = os.path.relpath(caminho, os.path.dirname(APP)).replace(os.sep, "/")
            checar(not achados, f"{rel} não linka tela que mudou de casa",
                   f"aponta para {achados}")


def teste_hubs_do_admin_nao_embutem_tela_de_corretora():
    print("\n[6] Nenhum hub do Admin embute a visão da corretora")
    # `/admin/conversas` importava `conversations` (o inbox da corretora) e
    # `/admin/financeiro` importava `billing` ("Meu Plano"). Renderizar isso
    # dentro do Admin da plataforma é a mistura que a §6 manda desfazer: o
    # operador abria "conversas" e via o atendimento de um segurado.
    for hub, proibido in (("conversas", "conversations"),
                          ("financeiro", "billing")):
        caminho = os.path.join(APP, "admin", hub, "page.tsx")
        if not os.path.exists(caminho):
            continue
        fonte = "\n".join(l for l in _ler(caminho).split("\n")
                          if not l.lstrip().startswith("//"))
        checar(f"import('../{proibido}/page')" not in fonte,
               f"/admin/{hub} não embute a tela '{proibido}' da corretora")


def main() -> int:
    print("=" * 68)
    print("SPEC-061 §6 — CADA SUPERFÍCIE NA SUA CASA")
    print("=" * 68)
    for teste in (teste_telas_da_corretora_vivem_no_dashboard,
                  teste_endereco_antigo_redireciona,
                  teste_admin_nao_tem_mais_menu_de_corretora,
                  teste_dashboard_recebeu_as_telas,
                  teste_o_menu_nao_cresce,
                  teste_duplicata_da_raiz_redireciona,
                  teste_admin_expulsa_quem_nao_e_plataforma,
                  teste_nenhuma_tela_do_dashboard_empurra_para_admin,
                  teste_destino_nao_devolve_o_master,
                  teste_link_interno_nao_atravessa_superficie,
                  teste_hubs_do_admin_nao_embutem_tela_de_corretora):
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
    print("AS SUPERFÍCIES ESTÃO SEPARADAS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
