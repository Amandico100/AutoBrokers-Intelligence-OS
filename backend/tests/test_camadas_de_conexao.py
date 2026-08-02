"""O corretor não é convidado a assinar o que a plataforma já paga.

O defeito, e ele foi meu
------------------------
Na migration 064_04 eu declarei `firecrawl` como conector exigido por dois
Auxiliares — Primeira Mão e o Radar. Nenhuma corretora tem o Firecrawl
"conectado", porque **a chave é do AutoBrokers e vive no ambiente desde
sempre**.

Consequência: a tela do Bloco C passaria a dizer, para TODAS as corretoras::

    Falta conectar: Firecrawl

E travaria o botão de ligar num Auxiliar que funciona perfeitamente. Pior: um
card de Firecrawl aparecia em Conectores, sugerindo que a corretora precisava
assinar um serviço para usar o produto que ela já paga.

O erro não foi o campo. Foi a falta de um conceito.

A regra que passou a existir
----------------------------
    A DEFINIÇÃO do conector é sempre global.
    O que muda é QUEM SEGURA A CREDENCIAL.

        platform   a AutoBrokers paga, todas usam, ninguém conecta
        company    a conta da corretora — serve a todos os Auxiliares dela
        user       a conta da pessoa — três usuários, três contas

O caso que parece exceção e não é: o **portal da seguradora**. O mapa é nosso;
o login e a senha são da corretora. Ele é `company`, porque o scope diz quem
segura a credencial, não quem escreveu o mapa.

O que este teste protege
------------------------
Que nenhum conector de plataforma volte a virar card, e que nenhum Auxiliar
volte a ser travado por uma conexão que a corretora nunca precisou fazer.
"""

from __future__ import annotations

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FALHAS: list[str] = []

# Serviços cuja conta é UMA só para todas as corretoras. Se duas corretoras
# usam a mesma conta, é plataforma — essa é a pergunta que decide.
DEVEM_SER_PLATAFORMA = {"firecrawl", "tavily", "internal_conversations", "internal_documents"}


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


def _rest(caminho: str, **params) -> list | None:
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


def teste_o_documento_existe():
    print("\n[1] A regra está escrita, e o bootstrap manda ler")
    caminho = os.path.join(RAIZ, "docs", "canon", "CAMADAS-DE-CONEXAO.md")
    checar(os.path.isfile(caminho), "docs/canon/CAMADAS-DE-CONEXAO.md existe")
    if os.path.isfile(caminho):
        doc = _ler("docs", "canon", "CAMADAS-DE-CONEXAO.md")
        for camada in ("platform", "company", "user"):
            checar(f"`{camada}`" in doc, f"define a camada {camada}")
        checar("quem segura a credencial" in doc.lower(),
               "traz a frase que decide a classificação")
    checar("CAMADAS-DE-CONEXAO.md" in _ler("CLAUDE.md"),
           "CLAUDE.md §2 aponta para o documento")


def teste_o_card_sumiu():
    print("\n[2] Conector de plataforma não vira card para a corretora")
    rota = _sem_comentario(_ler("app", "api", "vault", "templates", "route.ts"))
    checar("scope" in rota and "platform" in rota,
           "a rota de conectores filtra por camada")
    checar(".neq('scope', 'platform')" in rota or '.neq("scope", "platform")' in rota,
           "exclui explicitamente os de plataforma",
           "sem isso a corretora vê um card pedindo a chave do que já é pago")


def teste_plataforma_nunca_trava_auxiliar():
    print("\n[3] Conector de plataforma está SEMPRE pronto")
    catalogo = _sem_comentario(_ler("lib", "auxiliaries", "catalog.ts"))
    checar("SCOPE_PLATAFORMA" in catalogo,
           "o leitor conhece a camada de plataforma")
    checar("connector_templates" in catalogo and "scope" in catalogo,
           "a prontidão de plataforma vem do banco, não de lista fixa no código",
           "lista fixa envelhece: o próximo conector global ficaria de fora")

    # O destino de "conectar" não pode existir para plataforma — se existir,
    # alguém em algum momento vai mandar o corretor para lá.
    bloco = catalogo.split("ONDE_CONECTAR", 1)[-1].split("}", 1)[0]
    for slug in ("firecrawl", "tavily"):
        checar(slug not in bloco,
               f"{slug} não tem destino de 'conectar'",
               "conector de plataforma nunca fica pendente")


def teste_o_banco_concorda(conectores: list[dict]):
    print("\n[4] O banco classifica cada conector")
    por_slug = {c["slug"]: c for c in conectores}

    for slug in DEVEM_SER_PLATAFORMA:
        c = por_slug.get(slug)
        if not c:
            checar(False, f"{slug} existe no catálogo de conectores")
            continue
        checar(c.get("scope") == "platform",
               f"{slug} é da plataforma",
               f"scope={c.get('scope')}")

    # O portal da seguradora é o caso que parece exceção: mapa nosso,
    # credencial da corretora. Tem de ser `company`.
    portal = por_slug.get("insurance_portal")
    if portal:
        checar(portal.get("scope") == "company",
               "o portal da seguradora é da corretora (o login é dela)",
               f"scope={portal.get('scope')}")

    sem_scope = [c["slug"] for c in conectores if not c.get("scope")]
    checar(not sem_scope, "nenhum conector sem camada declarada", f"{sem_scope}")


def teste_nenhuma_corretora_conecta_plataforma(conexoes: list[dict]):
    print("\n[5] Nenhuma corretora tem conexão para o que é da plataforma")
    vivas = [c for c in conexoes if c.get("status") != "archived"]
    plataforma = [
        c for c in vivas
        if ((c.get("connector_templates") or {}) or {}).get("scope") == "platform"
    ]
    checar(not plataforma,
           "nenhuma conexão viva aponta para conector de plataforma",
           f"{[c.get('name') for c in plataforma]}")


def main() -> int:
    print("=" * 68)
    print("QUEM PAGA, QUEM CONECTA, QUEM USA")
    print("=" * 68)

    for teste in (teste_o_documento_existe,
                  teste_o_card_sumiu,
                  teste_plataforma_nunca_trava_auxiliar):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    conectores = _rest("connector_templates", select="slug,scope,is_active", is_active="eq.true")
    if conectores is None:
        print("\n[4-5] (sem credencial de banco — casos pulados)")
    else:
        try:
            teste_o_banco_concorda(conectores)
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"banco: {type(exc).__name__}: {exc}")
            print(f"  X   banco EXPLODIU: {type(exc).__name__}: {exc}")

        conexoes = _rest("tenant_connections",
                         select="name,status,connector_templates(scope)") or []
        try:
            teste_nenhuma_corretora_conecta_plataforma(conexoes)
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"conexoes: {type(exc).__name__}: {exc}")
            print(f"  X   conexões EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 68)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("O QUE A PLATAFORMA PAGA, A CORRETORA NÃO CONECTA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
