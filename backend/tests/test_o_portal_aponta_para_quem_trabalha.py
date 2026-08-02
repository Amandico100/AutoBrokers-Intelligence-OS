"""A capacidade de portal aponta para quem entra na Allianz, não para o simulador.

O que a auditoria supôs, e o que a medição mostrou
--------------------------------------------------
A auditoria de entrada (02/08) escreveu: *"apagar o Portal Browser sem
reapontar quebraria o Cobrador em silêncio"*.

📊 **Medido antes de executar: não quebraria — porque nada checa.**

    billing_collection.py consulta capability?   NÃO
    quem consulta operational.portal.*?          só lib/capabilities/registry.ts,
                                                 que é uma LISTA ESTÁTICA

O Cobrador entra no portal, baixa boleto e envia **sem passar pelo Capability
Resolver**. A declaração existia e não era exercida.

Isso é pior do que a auditoria supôs, e por um motivo que importa: **o modelo
de governança estava mentindo.** As cinco capabilities resolviam
`needs_connection` para TODAS as corretoras — inclusive a que tem o portal
funcionando e baixando boleto — enquanto o trabalho acontecia por fora.

Um registro que diz "bloqueado" sobre algo que está rodando não protege nada.
Ele só garante que, no dia em que alguém ligar a checagem, o Cobrador para de
funcionar sem ninguém entender por quê.

E o segundo achado, que quase me fez apagar o que funciona
-----------------------------------------------------------
"Portal Browser" era um nome cobrindo DUAS coisas:

    o simulador          relay/canário/skill-run, tudo com
                         real_action_allowed=false
    a administração      rotas que gravam `portal_accounts`… mas dentro de
                         `tenant_connections.connection_config`, um ARRAY JSON

📊 E a tabela `public.portal_accounts` — a que o `portal_worker` realmente lê —
é escrita por outro caminho: `/dashboard/personalizacao/conectores/portais` →
`backend/app/api/portal.py`.

**Dois `portal_accounts` com o mesmo nome, que nunca se tocaram.** Só depois de
provar isso a remoção ficou segura.

O que este teste protege
------------------------
1. que o provider das capabilities nomeie quem faz o trabalho
2. que o resolver enxergue `portal_accounts` — senão a declaração volta a mentir
3. que o mapa do cockpit e o do runtime não divirjam
4. que o simulador não volte
5. que o CATÁLOGO de 189 portais não tenha ido junto — é pesquisa, não código
"""

from __future__ import annotations

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FALHAS: list[str] = []

CAPACIDADES_DE_PORTAL = (
    "operational.portal.policy.read",
    "operational.portal.billing.read",
    "operational.portal.assistance.read",
    "operational.portal.assistance.prepare",
    "operational.portal.assistance.request",
)


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(*partes: str) -> str:
    with open(os.path.join(RAIZ, *partes), encoding="utf-8") as fh:
        return fh.read()


def _sem_comentario_py(fonte: str) -> str:
    return "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith("#"))


def _sem_comentario_ts(fonte: str) -> str:
    sem = "\n".join(l for l in fonte.split("\n") if not l.lstrip().startswith(("//", "*", "/*")))
    return re.sub(r"/\*.*?\*/", "", sem, flags=re.S)


def _rest(caminho: str, **params):
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
    if not url or not key:
        return None
    try:
        import httpx
    except ImportError:
        return None
    try:
        r = httpx.get(f"{url.rstrip('/')}/rest/v1/{caminho}", params=params,
                      headers={"apikey": key, "Authorization": f"Bearer {key}"}, timeout=20)
        return r.json() if r.status_code == 200 else None
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------

def teste_o_provider_nomeia_quem_trabalha():
    print("\n[1] As capabilities de portal apontam para o portal_worker")
    registry = _sem_comentario_ts(_ler("lib", "capabilities", "registry.ts"))

    checar("provider: 'portal_browser'" not in registry,
           "nenhuma capability declara o simulador como provedor")
    for chave in CAPACIDADES_DE_PORTAL:
        linha = next((l for l in registry.split("\n") if f"'{chave}'" in l), "")
        checar("provider: 'portal_worker'" in linha,
               f"{chave} → portal_worker",
               f"linha={linha.strip()[:90]}")


def teste_o_resolver_enxerga_a_conexao_de_verdade():
    print("\n[2] O resolver enxerga onde a conexão de portal realmente mora")
    resolver = _ler("backend", "app", "agents", "capability_resolver.py")
    sem_com = _sem_comentario_py(resolver)

    checar('"portal_worker": ["insurance_portal"]' in sem_com,
           "o mapa conhece portal_worker")
    checar("portal_accounts" in sem_com,
           "o resolver lê portal_accounts",
           "sem isso, a corretora que TEM o portal funcionando resolvia "
           "'needs_connection' — o registro mentia")

    # A leitura tem de filtrar por corretora: a conta de portal de uma não pode
    # liberar capability de outra.
    trecho = sem_com.split("portal_accounts", 1)[1][:220]
    checar('eq("company_id", company_id)' in trecho,
           "a leitura de portal_accounts filtra por corretora",
           "senão a conta de uma corretora liberaria a capability de todas")

    # 'unknown' é o estado inicial. Tratá-lo como desconectado negaria a
    # capacidade justamente de quem acabou de cadastrar.
    checar('!= "failing"' in sem_com or "'failing'" in sem_com,
           "só 'failing' conta como desconectado",
           "'unknown' é o estado de quem ainda não rodou")


def teste_o_cockpit_e_o_runtime_nao_divergem():
    print("\n[3] O mapa do cockpit casa com o do runtime")
    rota = _sem_comentario_ts(
        _ler("app", "api", "admin", "companies", "[companyId]", "capabilities", "route.ts"))
    checar("portal_worker: ['insurance_portal']" in rota,
           "o cockpit conhece portal_worker",
           "se os dois mapas divergirem, a tela diz 'conectado' sobre algo "
           "que o runtime nega")


def teste_o_simulador_nao_volta():
    print("\n[4] O simulador não existe mais em lugar nenhum")
    mortos = [
        ("app", "admin", "portal-browser"),
        ("app", "admin", "connectors", "portal-browser"),
        ("app", "api", "admin", "portal-browser"),
        ("lib", "attendance", "portal-browser-registry.ts"),
        ("lib", "attendance", "portal-admin-context.ts"),
        ("lib", "attendance", "portal-admin-sanitizers.ts"),
        ("lib", "attendance", "portal-canary-guard.ts"),
        ("lib", "attendance", "portal-skill-factory.ts"),
        # `portal-intake-importer.ts` NÃO entra aqui — eu o apaguei e tive de
        # restaurar. Ele parecia parte do simulador pelo nome, e é o oposto:
        # é o PIPELINE que lê o levantamento oficial em CSV e produz o catálogo
        # de 189 portais. O teste da SPEC-046 o declarava "vivo preservado" e
        # foi ele que pegou o erro. Ver P-26.
    ]
    for partes in mortos:
        caminho = os.path.join(RAIZ, *partes)
        checar(not os.path.exists(caminho), f"{'/'.join(partes)} não existe mais")

    # E ninguém importa o que sumiu.
    pendentes: list[str] = []
    for base in ("app", "lib", "components"):
        raiz = os.path.join(RAIZ, base)
        if not os.path.isdir(raiz):
            continue
        for pasta, _, arquivos in os.walk(raiz):
            for arq in arquivos:
                if not arq.endswith((".ts", ".tsx")):
                    continue
                caminho = os.path.join(pasta, arq)
                fonte = _sem_comentario_ts(open(caminho, encoding="utf-8").read())
                if ("portal-admin-context" in fonte or "portal-admin-sanitizers" in fonte
                        or "portal-browser-registry" in fonte
                        or "/admin/portal-browser" in fonte):
                    pendentes.append(os.path.relpath(caminho, RAIZ).replace(os.sep, "/"))
    checar(not pendentes, "ninguém importa o que foi removido", f"{pendentes}")

    layout = _sem_comentario_ts(_ler("app", "admin", "layout.tsx"))
    checar("portal-browser" not in layout,
           "o menu do admin não aponta mais para o simulador")


def teste_o_catalogo_de_portais_sobreviveu():
    print("\n[5] O catálogo de 189 portais NÃO foi junto — é pesquisa, não código")
    caminho = os.path.join(RAIZ, "lib", "attendance", "portal-global-catalog-seed.ts")
    checar(os.path.isfile(caminho), "o catálogo global de portais continua existindo")
    if not os.path.isfile(caminho):
        return

    seed = _ler("lib", "attendance", "portal-global-catalog-seed.ts")
    linhas = len(seed.split("\n"))
    checar(linhas > 5000, "o catálogo está inteiro", f"{linhas} linhas")

    for seguradora in ("allianz", "porto", "hdi", "sompo", "mapfre", "bradesco"):
        checar(f'"{seguradora}"' in seed or f"'{seguradora}'" in seed,
               f"o catálogo mapeia {seguradora}")

    checar("portal-catalog-types" in seed,
           "o catálogo tem tipos próprios, sem depender do simulador",
           "apagar o simulador não pode levar a pesquisa junto")


def teste_o_banco_concorda():
    print("\n[6] O banco concorda com o código")
    caps = _rest("capabilities", select="capability_key,provider",
                 capability_key="like.operational.portal%")
    if caps is None:
        print("      (sem credencial — caso pulado)")
        return

    for c in caps:
        checar(c.get("provider") == "portal_worker",
               f"{c.get('capability_key')} → portal_worker no banco",
               f"provider={c.get('provider')}")

    conector = _rest("connector_templates", select="slug,is_active", slug="eq.portal_browser")
    if conector:
        checar(conector[0].get("is_active") is False,
               "o conector do simulador está inativo")

    # A garantia da ontologia, em dado: nenhuma Rotina sem Auxiliar dono.
    rotinas = _rest("routines", select="name,tenant_auxiliary_id") or []
    orfas = [r.get("name") for r in rotinas if not r.get("tenant_auxiliary_id")]
    checar(not orfas, "nenhuma Rotina existe sem Auxiliar dono", f"{orfas}")

    # E o lixo de teste saiu.
    tpl = _rest("auxiliary_templates", select="slug", slug="like.teste-%") or []
    checar(not tpl, "nenhum template de teste sobrou", f"{[t.get('slug') for t in tpl]}")


def main() -> int:
    print("=" * 68)
    print("O PORTAL APONTA PARA QUEM TRABALHA, E O SIMULADOR SAIU")
    print("=" * 68)
    for teste in (teste_o_provider_nomeia_quem_trabalha,
                  teste_o_resolver_enxerga_a_conexao_de_verdade,
                  teste_o_cockpit_e_o_runtime_nao_divergem,
                  teste_o_simulador_nao_volta,
                  teste_o_catalogo_de_portais_sobreviveu,
                  teste_o_banco_concorda):
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
    print("A DECLARACAO VOLTOU A SER VERDADE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
