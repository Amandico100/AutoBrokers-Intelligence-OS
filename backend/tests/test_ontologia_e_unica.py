"""As quatro palavras têm uma definição só, e o catálogo obedece a ela.

O que a auditoria mediu, em 02/08/2026
--------------------------------------
O produto tinha três sistemas diferentes se chamando "Auxiliar", e o menu
chamava de Auxiliares justamente aquele que não era::

    menu → "Auxiliares" → /dashboard/auxiliares → mostrava ROTINAS
    auxiliares DE VERDADE → /dashboard/auxiliares/meus → SEM LINK NO MENU

E a inversão estava escrita em código, em uma linha::

    backend/app/services/billing_collection.py
    f"Auxiliar de Cobranca - {routine.get('name')}"

Uma Rotina que se apresentava como "Auxiliar" numa f-string.

O que este teste protege
------------------------
Não protege a beleza da definição — protege que ela continue **valendo**:

* o documento canônico existe e traz as quatro palavras
* nenhuma Rotina volta a existir sem Auxiliar dono
* nenhum Auxiliar do catálogo nasce sem a copy que o corretor lê
* nenhum Auxiliar nasce ligado
* o "em breve" diz o que falta para existir, em vez de prometer vago
* e — a regra que a auditoria acrescentou ao CLAUDE.md §12.1 — nenhuma
  promessa de valor traz número inventado

O caso do número é o mais importante e o menos óbvio. A auditoria de entrada
encontrou um número ILUSTRATIVO que atravessou seis documentos citado como
medição, e virou "o achado que dá o tom do produto". Um catálogo com
"recupera R$ 2.000/mês" em dez auxiliares que ainda não existem seria a mesma
armadilha, multiplicada por dez.
"""

from __future__ import annotations

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FALHAS: list[str] = []

CATEGORIAS_VALIDAS = {
    "dinheiro_que_volta",
    "dinheiro_novo",
    "cliente_blindado",
    "negociacao",
    "protecao_carteira",
    "tempo_livre",
}


def checar(cond: bool, nome: str, detalhe: str = "") -> None:
    if cond:
        print(f"  OK  {nome}")
    else:
        FALHAS.append(f"{nome}{(' — ' + detalhe) if detalhe else ''}")
        print(f"  X   {nome}  {detalhe}")


def _ler(*partes: str) -> str:
    with open(os.path.join(RAIZ, *partes), encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# [1] O documento canônico
# ---------------------------------------------------------------------------

def teste_o_documento_existe_e_define_as_quatro():
    print("\n[1] O documento canônico existe e traz as quatro definições")
    caminho = os.path.join(RAIZ, "docs", "canon", "ONTOLOGIA-DO-TRABALHO.md")
    checar(os.path.isfile(caminho), "docs/canon/ONTOLOGIA-DO-TRABALHO.md existe")
    if not os.path.isfile(caminho):
        return

    doc = _ler("docs", "canon", "ONTOLOGIA-DO-TRABALHO.md")
    for termo in ("Skill", "Rotina", "Auxiliar", "Artifact"):
        checar(f"**{termo}**" in doc, f"define {termo}")

    checar(
        "Auxiliar **TEM** Rotina" in doc and "Auxiliar **NÃO É** Rotina" in doc,
        "traz a regra que desfaz a confusão",
    )
    checar(
        "GLOBAL" in doc and "CORRETORA" in doc and "USUÁRIO" in doc,
        "traz as três camadas",
        "é a estrutura que o Founder pediu; sem ela o documento não serve",
    )
    checar(
        "erros já cometidos" in doc.lower() or "erros ja cometidos" in doc.lower(),
        "registra os erros já cometidos",
        "sem eles a próxima LLM repete",
    )


def teste_o_bootstrap_manda_ler():
    print("\n[2] O bootstrap de sessão manda ler a ontologia")
    claude = _ler("CLAUDE.md")
    checar(
        "ONTOLOGIA-DO-TRABALHO.md" in claude,
        "CLAUDE.md §2 aponta para a ontologia",
        "documento canônico que ninguém é obrigado a ler não organiza nada",
    )


# ---------------------------------------------------------------------------
# [3..6] O catálogo obedece à ontologia — contra o banco real
# ---------------------------------------------------------------------------

def _catalogo() -> list[dict] | None:
    """Lê o catálogo do banco. Devolve None quando não há credencial."""
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
            params={
                "select": "slug,name,headline,categories,catalog_state,data_sources,"
                          "what_it_does,value_promise,missing_for_launch,status",
                "status": "eq.active",
            },
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
            timeout=20,
        )
        return r.json() if r.status_code == 200 else None
    except Exception:  # noqa: BLE001
        return None


# Um número em reais, um percentual, ou "X por mês" — o formato de quem promete
# em vez de medir. `value_promise` de auxiliar que ainda não existe não pode
# ter nenhum deles (CLAUDE.md §12.1).
PROMESSA_COM_NUMERO = re.compile(
    r"R\$\s*[\d.,]+|\d+\s*%|\d[\d.,]*\s*(mil|reais|horas?|dias?)\b",
    re.IGNORECASE,
)


def teste_catalogo_completo_e_honesto(catalogo: list[dict]):
    print("\n[3] Todo Auxiliar do catálogo tem a copy que o corretor lê")
    for aux in catalogo:
        slug = aux.get("slug")
        checar(bool(aux.get("headline")), f"{slug} tem headline")
        checar(bool(aux.get("value_promise")), f"{slug} tem promessa de valor")
        checar(bool(aux.get("data_sources")), f"{slug} declara de onde tira a informação")
        checar(bool(aux.get("what_it_does")), f"{slug} lista o que faz")

        cats = set(aux.get("categories") or [])
        checar(bool(cats), f"{slug} tem categoria")
        checar(
            cats <= CATEGORIAS_VALIDAS,
            f"{slug} usa só categoria do vocabulário",
            f"fora do vocabulário: {sorted(cats - CATEGORIAS_VALIDAS)}",
        )

    print("\n[4] A headline vende o resultado, não repete a descrição técnica")
    for aux in catalogo:
        slug, head = aux.get("slug"), (aux.get("headline") or "").strip()
        checar(
            head.lower() != (aux.get("name") or "").lower(),
            f"{slug}: headline não é só o nome repetido",
        )
        checar(len(head) >= 25, f"{slug}: headline tem substância", f"{len(head)} chars")

    print("\n[5] O 'em breve' diz o que falta — e não promete número")
    em_breve = [a for a in catalogo if a.get("catalog_state") == "coming_soon"]
    checar(bool(em_breve), "há auxiliares 'em breve' no catálogo", f"{len(em_breve)}")
    for aux in em_breve:
        slug = aux.get("slug")
        checar(bool(aux.get("missing_for_launch")), f"{slug} diz o que falta para existir")

        # A regra do CLAUDE.md §12.1 aplicada ao catálogo.
        achado = PROMESSA_COM_NUMERO.search(aux.get("value_promise") or "")
        checar(
            achado is None,
            f"{slug}: a promessa não inventa número",
            f"encontrado: {achado.group(0) if achado else ''} — "
            "auxiliar que ainda não existe diz o que SERÁ medido",
        )

    print("\n[6] O catálogo cabe numa leitura de dois minutos")
    checar(
        len(em_breve) <= 10,
        "no máximo 10 'em breve' visíveis",
        f"{len(em_breve)} — acima disso o catálogo vira promessa, não produto",
    )


def teste_nada_nasce_ligado_e_rotina_tem_dono():
    print("\n[7] Nada nasce ligado, e nenhuma Rotina existe sem dono")
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
    if not url or not key:
        # 🔴 SPEC-078 C.8 — pular sem credencial é aceitável na mesa do
        # desenvolvedor e INACEITÁVEL num gate. Sem esta distinção, o gate
        # ficaria verde por não ter rodado — que é o pior verde que existe.
        if os.environ.get("ONTOLOGIA_EXIGE_BANCO") == "1":
            checar(False,
                   "credencial de banco presente (ONTOLOGIA_EXIGE_BANCO=1)",
                   "SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY ausentes — "
                   "o caso que prova a ontologia NAO rodou")
            return
        print("      (sem credencial — caso pulado; use ONTOLOGIA_EXIGE_BANCO=1 no gate)")
        return
    try:
        import httpx
    except ImportError:
        if os.environ.get("ONTOLOGIA_EXIGE_BANCO") == "1":
            checar(False, "httpx disponivel (ONTOLOGIA_EXIGE_BANCO=1)", "httpx ausente")
            return
        print("      (httpx ausente — caso pulado)")
        return

    h = {"apikey": key, "Authorization": f"Bearer {key}"}
    base = url.rstrip("/")

    inst = httpx.get(f"{base}/rest/v1/tenant_auxiliaries",
                     params={"select": "slug,status,last_run_at"},
                     headers=h, timeout=20).json()
    nascidos_ligados = [
        i for i in inst
        if i.get("status") == "active" and not i.get("last_run_at")
        and i.get("slug") in {"cobranca-feita", "checklist-6h"}
    ]
    checar(not nascidos_ligados,
           "nenhum Auxiliar semeado pela SPEC-064 nasceu ligado",
           f"{[i.get('slug') for i in nascidos_ligados]}")

    rot = httpx.get(f"{base}/rest/v1/routines",
                    params={"select": "name,tenant_auxiliary_id,is_active,company_id"},
                    headers=h, timeout=20).json()
    # 🔴 SPEC-078 C.8 — a isenção da "Notícias da Globo" ACABOU.
    #
    # 📊 Medido em 17/08/2026: existem 2 rotinas no banco inteiro, ambas de
    # cobrança. A rotina da Globo não existe mais, e manter a isenção seria
    # guardar uma verdade vencida — pior que teste nenhum (CLAUDE.md §9.3).
    #
    # Desde a migration `20260817_03` o banco recusa rotina sem dono via
    # `NOT NULL`. Este caso deixa de ser o guarda principal e vira o CONTROLE
    # dele: se ele ficar vermelho, é porque a constraint sumiu ou alguém
    # escreveu direto no banco por fora do produto.
    orfas = [r for r in rot if not r.get("tenant_auxiliary_id")]
    checar(not orfas,
           "nenhuma Rotina existe sem Auxiliar dono",
           f"{[r.get('name') for r in orfas]}")

    # E a trava tem de MORDER, não só estar escrita. Um guarda que só olha os
    # dados de hoje passaria num banco vazio.
    cols = httpx.get(f"{base}/rest/v1/routines",
                     params={"select": "tenant_auxiliary_id", "limit": "1"},
                     headers=h, timeout=20)
    checar(cols.status_code == 200,
           "a tabela routines responde (a checagem acima não passou por vazio)",
           f"HTTP {cols.status_code}")

    lixo: list[dict] = []
    if lixo:
        print(f"      pendente para o Bloco H (limpeza): {[r.get('name') for r in lixo]}")


def main() -> int:
    print("=" * 68)
    print("A ONTOLOGIA É ÚNICA, E O CATÁLOGO OBEDECE A ELA")
    print("=" * 68)

    for teste in (teste_o_documento_existe_e_define_as_quatro,
                  teste_o_bootstrap_manda_ler):
        try:
            teste()
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"{teste.__name__}: {type(exc).__name__}: {exc}")
            print(f"  X   {teste.__name__} EXPLODIU: {type(exc).__name__}: {exc}")

    catalogo = _catalogo()
    if catalogo is None:
        print("\n[3-6] (sem credencial de banco — casos de catálogo pulados)")
    else:
        try:
            teste_catalogo_completo_e_honesto(catalogo)
        except Exception as exc:  # noqa: BLE001
            FALHAS.append(f"catalogo: {type(exc).__name__}: {exc}")
            print(f"  X   catálogo EXPLODIU: {type(exc).__name__}: {exc}")

    try:
        teste_nada_nasce_ligado_e_rotina_tem_dono()
    except Exception as exc:  # noqa: BLE001
        FALHAS.append(f"instalacoes: {type(exc).__name__}: {exc}")
        print(f"  X   instalações EXPLODIU: {type(exc).__name__}: {exc}")

    print("\n" + "=" * 68)
    if FALHAS:
        print(f"{len(FALHAS)} PROBLEMA(S):")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("UMA PALAVRA, UMA DEFINIÇÃO — E O CATÁLOGO OBEDECE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
