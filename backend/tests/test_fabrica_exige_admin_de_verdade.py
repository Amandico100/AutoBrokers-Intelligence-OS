"""A Fábrica de Auxiliares não instala software na corretora de estranho.

O que a auditoria da SPEC-064 mediu, em 02/08/2026
--------------------------------------------------
`lib/admin/factory.ts` guardava a Fábrica inteira com isto::

    export async function hasAdminCookie(): Promise<boolean> {
      const store = await cookies();
      return Boolean(store.get('smith_admin_session'));
    }

**Presença. Só presença.** Sem assinatura, sem expiração, sem conferir se o
admin ainda existe. Qualquer cookie com aquele nome — e qualquer valor dentro
dele — passava.

E não guardava pouca coisa. A auditoria mapeou **sete pontos de chamada em
cinco arquivos**::

    POST   /api/admin/auxiliaries/templates                     criar template global
    GET    /api/admin/auxiliaries/templates                     listar
    PATCH  /api/admin/auxiliaries/templates/[id]                editar o global
    POST   /api/admin/auxiliaries/templates/[id]/install        instalar em QUALQUER corretora
    GET    /api/admin/auxiliaries/templates/[id]/installations  quem tem instalado
    POST   /api/admin/auxiliaries/templates/from-agent          publicar agente como template

Traduzindo para o que importa: **quem conseguisse escrever um cookie chamado
`smith_admin_session` instalava software na corretora de outra pessoa**, e
descobria quais corretoras existem.

A SPEC-064 classificou como P1 e disse que poderia sair "na frente ou junto"
com os blocos de ontologia. A auditoria discordou do *junto*: o conserto é
pequeno, isolado, não depende de nenhuma decisão de produto, e o buraco está
aberto agora. Virou o primeiro commit da SPEC.

O conserto não inventou padrão
------------------------------
`requireMasterAdmin()` já existia em `lib/admin/admin-auth.ts` e faz as três
coisas que faltavam: decodifica a sessão iron-session (que é assinada e
expira), confere o papel, e confirma **no banco** que o admin não foi revogado
— porque sessão válida de admin demitido ainda é sessão válida.

Mutação também passa a exigir same-origin, por defesa em profundidade.

O que este teste protege
------------------------
Que o guard fraco não volte — nem com o mesmo nome, nem com outro. É o tipo de
regressão que não quebra tela nenhuma: tudo continua funcionando, e a porta
fica destrancada de novo sem ninguém perceber.
"""

from __future__ import annotations

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FALHAS: list[str] = []

# As rotas que o guard protege. Se uma rota nova entrar na Fábrica sem passar
# por aqui, o caso [3] acusa.
ROTAS_DA_FABRICA = os.path.join(RAIZ, "app", "api", "admin", "auxiliaries")


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
    """Tira comentário — senão a docstring que EXPLICA o defeito faz o teste passar."""
    sem_linha = "\n".join(
        l for l in fonte.split("\n") if not l.lstrip().startswith(("//", "*", "/*"))
    )
    return re.sub(r"/\*.*?\*/", "", sem_linha, flags=re.S)


def teste_o_guard_fraco_nao_existe_mais():
    print("\n[1] O guard que só olhava a presença do cookie não existe mais")
    fonte = _sem_comentario(_ler("lib", "admin", "factory.ts"))

    checar(
        "hasAdminCookie" not in fonte,
        "hasAdminCookie foi removido",
        "enquanto a função existir, alguém volta a usá-la",
    )
    # A assinatura exata do defeito: ler o cookie e devolver Boolean da presença.
    checar(
        not re.search(r"Boolean\(\s*\w+\.get\(\s*['\"]smith_admin_session", fonte),
        "ninguém mais decide autorização pela presença do cookie",
    )
    checar(
        "cookies" not in fonte,
        "o arquivo nem importa mais `cookies` do next/headers",
        "quem não lê cookie cru não tem como julgar cookie cru",
    )


def teste_o_guard_novo_valida_de_verdade():
    print("\n[2] O guard novo decodifica, confere papel e confirma no banco")
    fonte = _sem_comentario(_ler("lib", "admin", "factory.ts"))

    checar("requireFactoryAdmin" in fonte, "existe um guard nomeado para a Fábrica")
    checar(
        "requireMasterAdmin" in fonte,
        "ele delega para requireMasterAdmin",
        "é o caminho que decodifica iron-session e valida admin_users no banco",
    )
    checar(
        "assertSameOrigin" in fonte,
        "mutação exige same-origin",
        "defesa em profundidade contra requisição de outro site",
    )

    # A ordem importa: same-origin ANTES de qualquer trabalho.
    pos_origin = fonte.find("assertSameOrigin")
    pos_master = fonte.find("requireMasterAdmin(")
    checar(
        pos_origin != -1 and pos_master != -1 and pos_origin < pos_master,
        "a checagem de origem vem antes da de sessão",
    )

    # E o guard de verdade tem de estar do lado do servidor, com service role.
    checar(
        "SUPABASE_SERVICE_ROLE_KEY" in fonte,
        "o cliente com service role continua sendo só do servidor",
    )


def teste_nenhuma_rota_da_fabrica_escapa():
    print("\n[3] Toda rota da Fábrica passa pelo mesmo portão")
    if not os.path.isdir(ROTAS_DA_FABRICA):
        checar(False, "a pasta de rotas da Fábrica existe", ROTAS_DA_FABRICA)
        return

    encontradas = 0
    for pasta, _, arquivos in os.walk(ROTAS_DA_FABRICA):
        for arq in arquivos:
            if arq != "route.ts":
                continue
            encontradas += 1
            caminho = os.path.join(pasta, arq)
            rel = os.path.relpath(caminho, RAIZ).replace(os.sep, "/")
            with open(caminho, encoding="utf-8") as fh:
                fonte = _sem_comentario(fh.read())

            checar("requireFactoryAdmin" in fonte, f"{rel} usa o portão único")
            checar(
                "hasAdminCookie" not in fonte,
                f"{rel} não usa mais o guard fraco",
            )

            # Cada handler exportado tem de ter o seu próprio guard: um GET
            # protegido não protege o POST do lado.
            handlers = re.findall(r"export async function (GET|POST|PATCH|PUT|DELETE)\b", fonte)
            guards = fonte.count("requireFactoryAdmin(")
            checar(
                guards >= len(handlers),
                f"{rel} guarda os {len(handlers)} handler(s)",
                f"{guards} guard(s) para {len(handlers)} handler(s): {handlers}",
            )

            # Mutação recebe `req` — sem ele não há same-origin.
            for h in ("POST", "PATCH", "PUT", "DELETE"):
                if f"export async function {h}" not in fonte:
                    continue
                trecho = fonte.split(f"export async function {h}", 1)[1][:400]
                checar(
                    "requireFactoryAdmin(req" in trecho,
                    f"{rel} · {h} passa a requisição para o same-origin",
                    "requireFactoryAdmin() sem argumento pula a checagem de origem",
                )

    checar(encontradas >= 5, "há rotas da Fábrica para conferir", f"{encontradas} encontradas")


def teste_o_padrao_fraco_nao_esta_espalhado():
    print("\n[4] O mesmo padrão fraco não sobrou em outro canto do admin")
    # O comentário do arquivo original dizia "mesmo padrão das rotas /api/admin
    # existentes" — o que sugeria que a fraqueza tinha sido copiada. Este caso
    # varre e mostra. Ele NÃO falha por encontrar: falha se encontrar dentro de
    # /api/admin/auxiliaries, que é o escopo desta SPEC. O resto vira registro
    # para a SPEC que cuidar daquele pedaço.
    suspeitos: list[str] = []
    base = os.path.join(RAIZ, "app", "api", "admin")
    padrao = re.compile(r"Boolean\(\s*\w+\.get\(\s*['\"]smith_admin_session")
    for pasta, _, arquivos in os.walk(base):
        for arq in arquivos:
            if not arq.endswith(".ts"):
                continue
            caminho = os.path.join(pasta, arq)
            with open(caminho, encoding="utf-8") as fh:
                fonte = _sem_comentario(fh.read())
            if padrao.search(fonte) or "hasAdminCookie" in fonte:
                suspeitos.append(os.path.relpath(caminho, RAIZ).replace(os.sep, "/"))

    da_fabrica = [s for s in suspeitos if "/auxiliaries/" in s]
    checar(not da_fabrica, "nenhuma rota da Fábrica usa o padrão fraco", f"{da_fabrica}")
    if suspeitos and not da_fabrica:
        print(f"      registro (fora do escopo desta SPEC): {suspeitos}")


def main() -> int:
    print("=" * 68)
    print("A FÁBRICA EXIGE ADMIN DE VERDADE, NÃO UM COOKIE COM O NOME CERTO")
    print("=" * 68)
    for teste in (
        teste_o_guard_fraco_nao_existe_mais,
        teste_o_guard_novo_valida_de_verdade,
        teste_nenhuma_rota_da_fabrica_escapa,
        teste_o_padrao_fraco_nao_esta_espalhado,
    ):
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
    print("INSTALAR AUXILIAR EM CORRETORA EXIGE SER ADMIN DE PLATAFORMA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
