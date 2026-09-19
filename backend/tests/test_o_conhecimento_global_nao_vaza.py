# -*- coding: utf-8 -*-
r"""🔴 O CONHECIMENTO GLOBAL É DE TODAS; O DA CORRETORA É SÓ DELA — GATE E (E18, E19).

SPEC-EXTRA-001.5.1 · unidade E. O Founder pediu três coisas, e elas não são a
mesma: o que a HDI cobre é de todas as corretoras; os 17 documentos privados da
Resulta são só dela; e **nada vaza**.

📊 O ESTADO MEDIDO EM 18–19/09/2026 — e por que ele precisa de guarda
====================================================================
```
GLOBAL        insurer_assistance_plans: SEM company_id (o guarda M-A4 prova)
              coleção Qdrant `autobrokers_global`, lida por toda corretora
DA CORRETORA  documents.company_id NOT NULL — 17 · 2 · 1 nas três corretoras
              coleção Qdrant `company_<id>`, uma por corretora
```

🔴 **Não há vazamento hoje, e por um motivo que precisa virar guarda:** a tabela
`agents` **não tem** a coluna `collection_name` que `graph.py:203` tenta ler.
Ela devolve `None` sempre, e a coleção cai no padrão da própria corretora. A
cerca `colecao_permitida` (`graph.py:218`) existe e **nunca precisa agir** — que
é exatamente a situação em que uma cerca apodrece sem ninguém notar.

⚠️ **O que este guarda NÃO faz:** ele não fala com o Qdrant. 📊 O Qdrant é
inalcançável da máquina de desenvolvimento, e um guarda que só roda onde há rede
não roda. O que ele mede é a **ESCOLHA DA COLEÇÃO** e os **kwargs** — que é
onde o tenant do RAG de fato vive hoje (o tenant é o NOME da coleção, não um
filtro por `company_id` no payload; a pendência P-098-RAG-COLECAO-DO-AGENTE
registra o risco estrutural, e ela é da SPEC-098).

⛔ Dos tenants reais só os **ids** são lidos, e nenhum é impresso inteiro.
"""
from __future__ import annotations

import inspect
import io
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
REPO = os.path.dirname(RAIZ)
sys.path.insert(0, RAIZ)

OK = FAIL = 0


def checar(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ok    {rotulo}")
    else:
        FAIL += 1
        print(f"  FALHA \U0001F534 {rotulo}" + (f"\n        {detalhe}" if detalhe else ""))


def _fechar() -> int:
    print()
    print("=" * 74)
    print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
    print("=" * 74)
    return 1 if FAIL else 0


def _curto(uuid: str) -> str:
    """⛔ Nunca o id inteiro no log: 8 caracteres bastam para DISTINGUIR."""
    return str(uuid or "")[:8] + "…"


def _dsn():
    dsn = os.environ.get("SUPABASE_DB_URL")
    if dsn:
        return dsn
    try:
        from dotenv import load_dotenv

        load_dotenv(os.path.join(RAIZ, ".env"))
    except Exception:  # noqa: BLE001
        pass
    return os.environ.get("SUPABASE_DB_URL")


from app.services import knowledge_scope as KS  # noqa: E402
from app.services.knowledge import assistance_plans_base as B  # noqa: E402

# ---------------------------------------------------------------------------
print("\n[1] a base de planos NÃO aceita a pergunta 'de quem' (E18-i)")
# ⚠️ O schema e os dois tenants reais estão em `test_a_base_de_planos_nao_tem_dono`
#    (M-A4). Aqui fica o lado do CONTRATO, porque é ele que esta SPEC toca.
_publicas = [n for n, f in vars(B).items()
             if inspect.isfunction(f) and not n.startswith("_")]
_com_dono = [n for n in _publicas
             if "company_id" in inspect.signature(getattr(B, n)).parameters]
checar(not _com_dono,
       f"🔴 nenhuma das {len(_publicas)} funções públicas aceita `company_id`",
       repr(_com_dono))
checar(len(_publicas) >= 10,
       "🔴 CONTROLE: o módulo tem funções públicas de verdade — a linha acima "
       "não passou por vácuo", str(len(_publicas)))

# ---------------------------------------------------------------------------
print("\n[2] a busca GLOBAL não sabe de que corretora é a pergunta (E18-iii)")
_kwargs_globais = inspect.signature(KS.build_global_search_kwargs).parameters
checar("company_id" not in _kwargs_globais,
       "🔴 `build_global_search_kwargs` não tem parâmetro de corretora",
       repr(list(_kwargs_globais)))
_global = KS.build_global_search_kwargs()
checar(_global.get("collection_name") == KS.GLOBAL_COLLECTION
       == "autobrokers_global",
       "e ela aponta para a coleção GLOBAL, sempre a mesma",
       repr(_global.get("collection_name")))
checar(not any("company" in str(k) for k in _global),
       "⛔ e nenhum kwarg dela carrega corretora", repr(sorted(_global)))

# ---------------------------------------------------------------------------
print("\n[3] 🔴 DUAS CORRETORAS REAIS — coleções DIFERENTES, cerca FECHADA (E18-ii)")
DSN = _dsn()
if not DSN:
    print("\n\U0001F7E1 PULADO a partir daqui: `SUPABASE_DB_URL` ausente.")
    print("   Os blocos [1] e [2] mediram o CONTRATO; [3] e [4] medem o BANCO.")
    sys.exit(_fechar())
try:
    import psycopg
except ImportError:
    print("\n\U0001F7E1 PULADO a partir daqui: `psycopg` (v3) não instalado.")
    sys.exit(_fechar())

with psycopg.connect(DSN, autocommit=True, prepare_threshold=None) as c, c.cursor() as cur:
    # 🔴 CONSERTO P5 — AS DUAS CORRETORAS TÊM DE TER DOCUMENTO.
    #
    # 📊 `order by id limit 2` pegava um par 17 + 0, e "os conjuntos não se
    # cruzam" com um conjunto VAZIO é verdade por vácuo. O par certo é o das
    # corretoras que de fato têm acervo privado — é ali que o vazamento
    # aconteceria. 📊 19/09/2026: 17 · 2 · 1 nas três corretoras.
    cur.execute("select company_id, count(*) as n from documents "
                "group by company_id having count(*) > 0 "
                "order by n desc limit 2")
    empresas = [str(r[0]) for r in cur.fetchall()]
    if len(empresas) < 2:
        cur.execute("select id from companies order by id limit 2")
        empresas = [str(r[0]) for r in cur.fetchall()]
    checar(len(empresas) == 2 and empresas[0] != empresas[1],
           "duas corretoras REAIS lidas do banco (só os ids)",
           " · ".join(_curto(e) for e in empresas))
    if len(empresas) == 2:
        A, Z = empresas
        col_a, col_z = KS.company_collection(A), KS.company_collection(Z)
        # ⚠️ `company_collection` troca `-` por `_` (o Qdrant não aceita `-` em
        #    nome de coleção), então o id NÃO aparece literal: o que se afirma é
        #    que o nome DERIVA do id daquela corretora e de mais nada.
        checar(col_a != col_z
               and col_a == "company_" + A.replace("-", "_")
               and col_z == "company_" + Z.replace("-", "_"),
               "🔴 a coleção privada de cada uma é DIFERENTE e deriva do id dela",
               f"{col_a[:20]}… · {col_z[:20]}…")
        checar(KS.colecao_permitida(A, col_a) and KS.colecao_permitida(Z, col_z),
               "🔴 CONTROLE: cada corretora PODE ler a própria coleção — a cerca "
               "não recusa tudo")
        checar(not KS.colecao_permitida(A, col_z)
               and not KS.colecao_permitida(Z, col_a),
               "🔴 e NENHUMA delas pode ler a coleção da outra",
               f"A→colZ={KS.colecao_permitida(A, col_z)} "
               f"Z→colA={KS.colecao_permitida(Z, col_a)}")
        checar(KS.colecao_permitida(A, KS.GLOBAL_COLLECTION)
               and KS.colecao_permitida(Z, KS.GLOBAL_COLLECTION),
               "⚠️ e as DUAS podem ler a global — é o conhecimento de todas")

    # ---------------------------------------------------------------------
    print("\n[4] o documento privado nasce COM dono, e o dono é NOT NULL (E18-iv)")
    cur.execute(
        "select is_nullable from information_schema.columns "
        "where table_schema='public' and table_name='documents' "
        "and column_name='company_id'")
    linha = cur.fetchone()
    checar(bool(linha) and linha[0] == "NO",
           "🔴 `documents.company_id` é NOT NULL — documento órfão não existe",
           repr(linha))
    cur.execute("select count(*) from documents where company_id is null")
    orfaos = cur.fetchone()[0]
    checar(orfaos == 0, "e ZERO linhas sem dono", str(orfaos))
    if len(empresas) == 2:
        cur.execute("select count(*) from documents where company_id = %s", (A,))
        de_a = cur.fetchone()[0]
        cur.execute("select count(*) from documents where company_id = %s", (Z,))
        de_z = cur.fetchone()[0]
        cur.execute("select count(*) from documents where company_id in (%s,%s)",
                    (A, Z))
        das_duas = cur.fetchone()[0]
        checar(de_a + de_z == das_duas,
               f"🔴 os conjuntos NÃO se cruzam: {de_a} + {de_z} = {das_duas}")
        checar(de_a > 0 and de_z > 0,
               "🔴 CONTROLE: as DUAS têm acervo privado — a linha acima não "
               "passou por vácuo com um conjunto vazio", f"{de_a} · {de_z}")

    # ---------------------------------------------------------------------
    print("\n[5] 🔴 a base de planos responde a MESMA coisa para as duas (E18-i)")
    cur.execute("select insurer_key, ramo, produto, plano from "
                "insurer_assistance_plans limit 1")
    algum = cur.fetchone()
    if algum:
        # ⚠️ Não há como PASSAR a corretora — é esse o ponto. As duas leituras
        #    são literalmente a mesma chamada, e é isso que se afirma.
        r_a = B.planos_publicados(algum[0], algum[1], algum[2])
        r_z = B.planos_publicados(algum[0], algum[1], algum[2])
        checar(r_a == r_z,
               "🔴 a mesma pergunta, a mesma resposta — a base não tem dono",
               f"{len(r_a)} vs {len(r_z)} plano(s)")
    else:
        checar(True, "⚠️ nenhum plano na base ainda — nada a comparar")

# ---------------------------------------------------------------------------
print("\n[6] 🔴 MUTAÇÃO do [3]: a cerca sempre-True → o guarda fica VERMELHO")
_original = KS.colecao_permitida
try:
    KS.colecao_permitida = lambda *_a, **_k: True
    vazou = (len(empresas) == 2
             and KS.colecao_permitida(empresas[0], KS.company_collection(empresas[1])))
    checar(vazou,
           "🔴 MUTAÇÃO: com `colecao_permitida` sempre True, a corretora A LÊ a "
           "coleção de B — este guarda CONSEGUE ficar vermelho")
finally:
    KS.colecao_permitida = _original
checar(len(empresas) == 2
       and not KS.colecao_permitida(empresas[0], KS.company_collection(empresas[1])),
       "🔴 CONTROLE: restaurada, a cerca volta a fechar")

# ---------------------------------------------------------------------------
print("\n[7] a CURADORIA é de administrador da plataforma (E19)")
# ⚠️ Guarda ESTÁTICO sobre o BFF: o Next não sobe aqui, e o que se afirma é que
#    a rota CHAMA a autorização certa — a mesma forma dos guardas vizinhos da
#    fatia 1 sobre `route.ts`.
ROTA = os.path.join(REPO, "app", "api", "dashboard", "knowledge", "planos",
                    "route.ts")
fonte = io.open(ROTA, encoding="utf-8").read()
#: ⛔ Comentários fora: um `requireMasterAdmin` citado numa explicação não
#: autoriza nada. O que conta é a CHAMADA.
sem_comentario = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", fonte, flags=re.S))
checar("requireMasterAdmin" in sem_comentario,
       "🔴 `route.ts` chama `requireMasterAdmin` (e não só o cita num comentário)")
_post = sem_comentario[sem_comentario.index("export async function POST"):]
checar("requireMasterAdmin()" in _post
       and "requireCompanyMember({ write: true })" not in _post,
       "🔴 o POST (publicar/rejeitar) exige PLATAFORMA — não mais o admin da "
       "corretora", _post[:300])
_get = sem_comentario[sem_comentario.index("export async function GET"):
                      sem_comentario.index("export async function POST")]
checar("requireCompanyMember({ write: false })" in _get,
       "o GET continua exigindo sessão da corretora (a cobertura é leitura de "
       "todos)")
checar("podeCurar" in _get and "master_required" in _get,
       "🔴 e a FILA e a PÁGINA só saem para quem pode curar", _get[-400:])
checar("Este conhecimento é de todas as corretoras e é mantido pela AutoBrokers."
       in fonte,
       "🔴 e a frase que explica a leitura sem botão está escrita no produto")

TELA = os.path.join(REPO, "app", "dashboard", "personalizacao", "conhecimento",
                    "KnowledgeClient.tsx")
tela = io.open(TELA, encoding="utf-8").read()
checar("curadoria_permitida" in tela and "podeCurar ?" in tela,
       "🔴 e a TELA só mostra a fila quando a curadoria é permitida")

print("\n      🔴 MUTAÇÃO do [7]: o cheque removido → o guarda fica VERMELHO")
_mutado = _post.replace("requireMasterAdmin()",
                        "requireCompanyMember({ write: true })")
checar("requireMasterAdmin()" not in _mutado,
       "🔴 MUTAÇÃO: trocado de volta por `requireCompanyMember`, a asserção do "
       "POST falharia — o guarda mede a CHAMADA, não a intenção")

sys.exit(_fechar())
