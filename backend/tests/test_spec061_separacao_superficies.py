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

# As cinco telas que mudaram de casa, e para onde foram.
MUDARAM_DE_CASA = {
    "/admin/team": "/dashboard/equipe",
    "/admin/conversations": "/dashboard/conversas",
    "/admin/agent": "/dashboard/agente",
    "/admin/documents": "/dashboard/documentos",
    "/admin/billing": "/dashboard/plano",
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


def teste_dashboard_recebeu_as_telas():
    print("\n[4] A corretora encontra as telas na casa dela")
    fonte = _ler(os.path.join(RAIZ, "lib", "navigation.ts"))
    checar("ADMINISTRACAO_DA_CORRETORA" in fonte,
           "existe um grupo de administração da corretora")
    for novo in MUDARAM_DE_CASA.values():
        checar(f"href: '{novo}'" in fonte, f"{novo} tem link no dashboard")


def teste_admin_expulsa_quem_nao_e_plataforma():
    print("\n[5] Quem não é plataforma não fica em /admin")
    fonte = _ler(os.path.join(APP, "admin", "layout.tsx"))
    # A regra de exclusão, com o redirecionamento para a casa certa.
    padrao = re.search(
        r"if\s*\(\s*role\s*&&\s*role\s*!==\s*'master'\s*\)\s*\{\s*\n?\s*router\.push\('/dashboard'\)",
        fonte)
    checar(padrao is not None,
           "papel diferente de plataforma é mandado para /dashboard",
           "a regra de exclusão sumiu do layout")


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
                  teste_admin_expulsa_quem_nao_e_plataforma,
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
