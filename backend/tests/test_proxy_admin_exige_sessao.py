"""O proxy do Admin não empresta a chave de master para quem passar na rua.

O que foi medido em produção, em 27/07/2026, sem cookie nenhum
-------------------------------------------------------------
    GET /dashboard                                 -> 307 para /login
    GET /admin/companies                           -> 307 para /admin/login
    GET /api/admin/proxy/agents/company/<id>/...   -> 200 com o prompt da corretora

As duas primeiras linhas provam que a proteção do produto existe e funciona. A
terceira prova que ela não passava pelo proxy.

Por que
-------
`middleware.ts` decide assim:

    const isApiRoute = apiRoutes.includes(pathname) || pathname.startsWith('/api/');
    if (isPublicRoute || isPublicPrefix || isApiRoute) return response;

Ou seja: **todo** `/api/` é liberado sem olhar sessão. Isso é razoável para as
rotas que conferem sessão por conta própria — e é uma porta aberta para as que
não conferem. `lib/admin-proxy.ts` era uma das que não conferiam: pegava a
requisição de qualquer pessoa, carimbava `X-Admin-API-Key` (a chave de
plataforma) e entregava ao backend, que via chave válida e obedecia. GET, PUT e
DELETE.

Veio no primeiro commit do repositório (`6274293`, 04/06/2026). Não é regressão
de SPEC nenhuma: é dívida que ninguém olhou porque a rota funcionava.

O que este teste protege
------------------------
Que o proxy volte a confiar no chamador sem perguntar quem é. É uma garantia
que, se cair, cai em silêncio — a tela continua funcionando exatamente igual.
"""

from __future__ import annotations

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FALHAS: list[str] = []


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
    sem_linha = "\n".join(l for l in fonte.split("\n")
                          if not l.lstrip().startswith(("//", "*", "/*")))
    return re.sub(r"/\*.*?\*/", "", sem_linha, flags=re.S)


def teste_proxy_confere_quem_chama():
    print("\n[1] O proxy pergunta quem está chamando antes de carimbar a chave")
    fonte = _sem_comentario(_ler("lib", "admin-proxy.ts"))

    checar("getIronSession" in fonte,
           "lê a sessão do cookie",
           "sem isso, o proxy aceita qualquer um")
    checar("adminSessionOptions" in fonte and "sessionOptions" in fonte,
           "considera as duas sessões — plataforma e corretora")
    checar("status: 401" in fonte,
           "sem sessão, responde 401",
           "é isso que fecha a exposição pública")

    # A chave de master só pode ser carimbada DEPOIS da checagem. Se o 401
    # aparecer abaixo do header, a ordem está errada e a checagem é decorativa.
    pos_401 = fonte.find("status: 401")
    pos_chave = fonte.find("X-Admin-API-Key")
    checar(pos_401 != -1 and pos_chave != -1 and pos_401 < pos_chave,
           "a checagem vem ANTES de carimbar a chave de plataforma",
           f"401 em {pos_401}, chave em {pos_chave}")


def teste_so_a_plataforma_passa():
    print("\n[2] Só sessão de plataforma passa — corretora nenhuma")
    fonte = _sem_comentario(_ler("lib", "admin-proxy.ts"))
    checar("status: 403" in fonte,
           "existe recusa para quem não é plataforma")
    checar("!== 'plataforma'" in fonte,
           "a recusa é por NÃO SER plataforma, não por empresa errada",
           "a versão por empresa deixava `agents/<id>` em aberto: o UUID do "
           "agente não diz de quem ele é")
    # 404 aqui viraria oráculo: quem chuta UUID descobre quais existem.
    checar("status: 404" not in fonte,
           "a recusa não é 404 — 404 revelaria quais UUIDs existem")


def teste_nenhuma_tela_da_corretora_usa_o_proxy():
    print("\n[2b] Nenhuma tela do /dashboard depende deste proxy")
    # É isto que sustenta a regra do caso [2]. Se uma tela da corretora voltar a
    # chamar o proxy, a regra "só plataforma" quebra aquela tela — e o teste
    # avisa AQUI, com o nome do arquivo, em vez de o corretor descobrir com um
    # 403 na cara.
    #
    # A checagem é transitiva de propósito: a tela raramente chama o proxy
    # direto, ela importa um componente que chama.
    import re as _re

    componentes: set[str] = set()
    base_comp = os.path.join(RAIZ, "components")
    for pasta, _, arquivos in os.walk(base_comp):
        for arq in arquivos:
            if not arq.endswith((".tsx", ".ts")):
                continue
            caminho = os.path.join(pasta, arq)
            with open(caminho, encoding="utf-8") as fh:
                if "api/admin/proxy/" in fh.read():
                    componentes.add(os.path.splitext(arq)[0])

    suspeitos: list[str] = []
    base_dash = os.path.join(RAIZ, "app", "dashboard")
    for pasta, _, arquivos in os.walk(base_dash):
        for arq in arquivos:
            if not arq.endswith((".tsx", ".ts")):
                continue
            caminho = os.path.join(pasta, arq)
            with open(caminho, encoding="utf-8") as fh:
                fonte = fh.read()
            rel = os.path.relpath(caminho, RAIZ).replace(os.sep, "/")
            if "api/admin/proxy/" in fonte:
                suspeitos.append(f"{rel} (chama direto)")
                continue
            for comp in componentes:
                if _re.search(rf"\b{_re.escape(comp)}\b", fonte):
                    suspeitos.append(f"{rel} (via {comp})")
                    break

    checar(not suspeitos,
           "nenhuma tela da corretora alcança o proxy da plataforma",
           f"alcançam: {suspeitos}")
    print(f"      componentes que falam com o proxy: {sorted(componentes)}")


def teste_nenhuma_rota_de_proxy_escapa():
    print("\n[3] Toda rota de proxy passa pelo mesmo portão")
    base = os.path.join(RAIZ, "app", "api", "admin", "proxy")
    if not os.path.isdir(base):
        checar(False, "a pasta do proxy existe", base)
        return

    encontradas = 0
    for pasta, _, arquivos in os.walk(base):
        for arq in arquivos:
            if arq != "route.ts":
                continue
            encontradas += 1
            caminho = os.path.join(pasta, arq)
            fonte = _sem_comentario(open(caminho, encoding="utf-8").read())
            rel = os.path.relpath(caminho, RAIZ).replace(os.sep, "/")
            checar("authenticatedProxy" in fonte,
                   f"{rel} usa o portão único",
                   "uma rota que fala com o backend por fora reabre o buraco")
            checar("ADMIN_API_KEY" not in fonte,
                   f"{rel} não carimba a chave por conta própria")
    checar(encontradas >= 1, "há rotas de proxy para conferir",
           f"{encontradas} encontradas")


def teste_middleware_continua_liberando_api():
    print("\n[4] A causa de raiz continua registrada")
    # Este caso não FALHA se o middleware liberar `/api/` — liberar é uma
    # decisão defensável, já que muitas rotas conferem sessão sozinhas. Ele
    # existe para que ninguém leia o middleware e conclua que `/api/` está
    # protegido. Se um dia o middleware passar a conferir, este aviso muda de
    # texto e o portão do proxy continua valendo — cinto e suspensório.
    fonte = _ler("middleware.ts")
    libera = "pathname.startsWith('/api/')" in fonte
    print(f"      middleware libera todo /api/ sem sessão: "
          f"{'SIM — o portão do proxy é a única defesa' if libera else 'não'}")
    checar(True, "causa de raiz documentada")


def main() -> int:
    print("=" * 68)
    print("O PROXY DO ADMIN NÃO EMPRESTA A CHAVE DE MASTER")
    print("=" * 68)
    for teste in (teste_proxy_confere_quem_chama,
                  teste_so_a_plataforma_passa,
                  teste_nenhuma_tela_da_corretora_usa_o_proxy,
                  teste_nenhuma_rota_de_proxy_escapa,
                  teste_middleware_continua_liberando_api):
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
    print("A CHAVE DE PLATAFORMA SÓ É CARIMBADA PARA QUEM TEM SESSÃO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
