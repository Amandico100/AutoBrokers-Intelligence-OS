# -*- coding: utf-8 -*-
r"""🔴 M-A4 · A BASE DE PLANOS NÃO TEM DONO — canônico, CLAUDE.md §7.

SPEC-EXTRA-001.5 · BLOCO A · D-PILOTO-01. O que a apólice da HDI cobre é o
mesmo para a Resulta e para a AutoFleet. Um `company_id` nestas duas tabelas
criaria a possibilidade de **duas corretoras lerem respostas diferentes sobre a
mesma apólice** — e de alguém "corrigir" a cobertura para uma delas só.

⚠️ Isto é o **contrário** do teste de isolamento de costume. Lá se prova que o
dado de X não chega a Y. Aqui se prova que **não há dado de X**: a base é uma
só, de todas, e a prova é que o contrato **nem aceita** a pergunta "de quem".

```
[1] information_schema   zero company_id · user_id · owner_user_id
[2] assinatura           NENHUMA função do módulo aceita company_id
[3] dois tenants REAIS   a mesma chamada, de duas corretoras, MESMO resultado
[4] PII                  o varredor da casa (`redaction_service`) sobre as
                         colunas de texto: ZERO
```

⛔ Somente leitura em `[1]`, `[3]` e `[4]`. O bloco `[4]` escreve dentro de
`BEGIN … ROLLBACK` e confere as contagens no fim.
⛔ Nenhum nome, telefone, CPF ou apólice aparece: o guarda lê `companies.id` e
contagens.
"""
from __future__ import annotations

import inspect
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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


DSN = _dsn()
if not DSN:
    print("\n\U0001F7E1 PULADO: `SUPABASE_DB_URL` ausente do ambiente e de backend/.env.")
    print("   Este guarda mede o SCHEMA e dois tenants REAIS; sem banco não há o quê.")
    sys.exit(0)
try:
    import psycopg
except ImportError:
    print("\n\U0001F7E1 PULADO: `psycopg` (v3) não instalado.")
    sys.exit(0)

from app.services.knowledge import assistance_plans_base as B  # noqa: E402

TABELAS = ("insurer_assistance_plans", "insurer_assistance_services")
DONOS = ("company_id", "user_id", "owner_user_id", "tenant_id", "broker_id")

# -------------------------------------------------------------------------
print("\n[1] o SCHEMA não tem coluna de dono")
with psycopg.connect(DSN, autocommit=True, prepare_threshold=None) as c, c.cursor() as cur:
    cur.execute(
        "select table_name, column_name from information_schema.columns "
        "where table_schema='public' and table_name = any(%s) and column_name = any(%s)",
        (list(TABELAS), list(DONOS)),
    )
    achadas = cur.fetchall()
    checar(not achadas, "🔴 ZERO colunas de dono nas duas tabelas", repr(achadas))

    # 🔴 CONTROLE: a MESMA consulta acha essas colunas onde elas existem.
    cur.execute(
        "select count(*) from information_schema.columns where table_schema='public' "
        "and table_name='tool_invocations' and column_name = any(%s)",
        (list(DONOS),),
    )
    n = cur.fetchone()[0]
    checar(n > 0,
           "🔴 CONTROLE: a mesma consulta acha colunas de dono em `tool_invocations`",
           f"achou {n} — se desse 0, a linha acima passaria por vácuo")

    cur.execute("select id from companies order by id limit 2")
    empresas = [str(r[0]) for r in cur.fetchall()]
    cur.execute("select count(*) from companies")
    quantas = cur.fetchone()[0]
    cur.execute(
        "select id from normative_documents where product_line in ('auto','residencial') "
        "order by id limit 1"
    )
    doc = str(cur.fetchone()[0])

# -------------------------------------------------------------------------
print("\n[2] o CONTRATO nem aceita a pergunta 'de quem'")
funcoes = [
    (nome, obj) for nome, obj in vars(B).items()
    if inspect.isfunction(obj) and obj.__module__ == B.__name__ and not nome.startswith("_")
]
checar(len(funcoes) >= 10, f"o módulo expõe {len(funcoes)} funções públicas")
com_dono = []
for nome, obj in funcoes:
    for p in inspect.signature(obj).parameters:
        if p in DONOS:
            com_dono.append(f"{nome}({p})")
checar(not com_dono,
       "🔴 NENHUMA função pública do módulo tem parâmetro de dono",
       repr(com_dono))

# 🔴 CONTROLE: a varredura CONSEGUE acusar — ela acha o parâmetro numa função
#    que o tem de verdade.
def _dublê_com_dono(company_id=None):  # noqa: E301
    return company_id


checar("company_id" in inspect.signature(_dublê_com_dono).parameters,
       "🔴 CONTROLE: a varredura de assinatura acha `company_id` quando ele existe")

with open(os.path.join(RAIZ, "app", "services", "knowledge", "assistance_plans_base.py"),
          encoding="utf-8") as fh:
    fonte = fh.read()
checar('eq("company_id"' not in fonte and ".eq('company_id'" not in fonte,
       "🔴 e o módulo nunca filtra por `company_id` no `.table(...)`")

# -------------------------------------------------------------------------
print("\n[3] 🔴 DOIS TENANTS REAIS — a mesma pergunta, a mesma resposta")
checar(len(empresas) == 2 and empresas[0] != empresas[1],
       f"os dois `company_id` são REAIS e distintos (📊 {quantas} corretoras na base)",
       f"{len(empresas)} lidos de `companies`")


def como_a_corretora(company_id):
    """O wrapper que a unidade D usaria — e que IGNORA o `company_id`.

    🔴 Ele ignora porque **não há onde passá-lo**: `cobertura_por_seguradora_e_ramo`
    não tem o parâmetro (bloco [2]). O `company_id` entra aqui só para provar
    que ele não muda nada.
    """
    assert "company_id" not in inspect.signature(
        B.cobertura_por_seguradora_e_ramo).parameters
    return B.cobertura_por_seguradora_e_ramo()


if len(empresas) == 2:
    r_a = como_a_corretora(empresas[0])
    r_b = como_a_corretora(empresas[1])
    checar(r_a == r_b,
           "🔴 `cobertura_por_seguradora_e_ramo()` dá o MESMO resultado para as duas",
           f"A={len(r_a)} chaves · B={len(r_b)} chaves")
    checar(isinstance(r_a, dict) and all(isinstance(k, tuple) and len(k) == 2 for k in r_a),
           "e a régua conta SEGURADORA × RAMO (a chave é um par), nunca linhas",
           f"chaves: {list(r_a)[:3]}")

# -------------------------------------------------------------------------
print("\n[4] o varredor de PII da casa sobre as colunas de texto: ZERO")
from app.services.intelligence.redaction_service import (  # noqa: E402
    PADROES_PII,
    contem_pii,
)

# 🔴 CONTROLE do varredor, ANTES de usá-lo: ele CONSEGUE acusar.
checar(contem_pii("meu cpf e 123.456.789-09"),
       "🔴 CONTROLE: o varredor da casa acusa um CPF de exemplo (💭 fictício)")
checar(not contem_pii("guincho ate 200 km, carencia de 15 dias"),
       "🔴 CONTROLE: e não acusa um texto de cobertura normal")

COLS_TEXTO = {
    "insurer_assistance_plans": ("insurer_key", "ramo", "produto", "plano",
                                 "susep_process", "content_hash"),
    "insurer_assistance_services": ("servico", "limite_texto", "condicao", "trecho_hash"),
}

#: 🔴 ATUALIZADO EM 18/09/2026, quando a onda 1 encheu a base (CLAUDE.md §9.3).
#: Com a tabela vazia, este bloco varria só as duas linhas-molde do próprio
#: guarda. Com 36 planos e 81 serviços reais de condições gerais, o varredor da
#: casa acusou DUAS coisas — e nenhuma é PII:
#:
#:   📊 `trecho_hash` — um sha256 tem runs de 10 dígitos e cai no padrão
#:      `[TELEFONE]`. Um hash é irreversível: não há pessoa ali por construção.
#:   📊 `condicao` — *"...em decorrência de **sinistro coberto** pelas..."* cai no
#:      padrão `sinistro [NUMERO]`, que casa "sinistro" + qualquer palavra.
#:
#: A lição MIGRA em vez de morrer:
#:   ① o `trecho_hash` passa a ser conferido pela FORMA (64 hex), que é uma trava
#:      MAIS forte — ela pega o defeito real, que é alguém gravar o trecho cru no
#:      lugar do hash;
#:   ② as colunas de texto continuam varridas pelo varredor da casa, e um acerto
#:      dele só conta quando o casamento tem DÍGITO ou é e-mail — que é o que
#:      separa "CPF, telefone, cartão, CEP, placa, e-mail" de "a palavra
#:      sinistro seguida de um adjetivo".
#: O controle do CPF continua verde, então o varredor continua CONSEGUINDO acusar.
_SEM_DIGITO_NAO_E_PII = re.compile(r"\d")


def _pii_de_verdade(valor: str) -> bool:
    if not contem_pii(valor):
        return False
    for padrao, marca in PADROES_PII:
        m = padrao.search(valor)
        if not m:
            continue
        if marca == "[EMAIL]" or _SEM_DIGITO_NAO_E_PII.search(m.group(0)):
            return True
    return False
with psycopg.connect(DSN, prepare_threshold=None) as conn, conn.cursor() as cur:
    cur.execute("select count(*) from insurer_assistance_plans")
    antes_p = cur.fetchone()[0]
    cur.execute("select count(*) from insurer_assistance_services")
    antes_s = cur.fetchone()[0]

    # a base ainda nasce vazia: o guarda insere UMA linha-molde, varre, e desfaz.
    cur.execute(
        "insert into insurer_assistance_plans (insurer_key,ramo,produto,plano,nivel,"
        "vigencia_inicio,documento_id,pagina,confianca,content_hash) values "
        "('allianz','auto','GUARDA M-A4','Essencial',1,'2026-01-01',%s,3,'media','h') "
        "returning id",
        (doc,),
    )
    plano = cur.fetchone()[0]
    cur.execute(
        "insert into insurer_assistance_services (plano_id,servico,coberto,documento_id,"
        "pagina,trecho_hash,confianca,limite_texto,condicao) values "
        "(%s,'guincho','sim',%s,3,%s,'media','ate 200 km por acionamento',"
        "'valido apos 15 dias de carencia')",
        (plano, doc, "a" * 64),
    )

    sujas, hashes_torto = [], []
    for tabela, colunas in COLS_TEXTO.items():
        cur.execute(f"select {', '.join(colunas)} from {tabela}")
        for linha in cur.fetchall():
            for col, valor in zip(colunas, linha):
                if not valor:
                    continue
                if col == "trecho_hash":
                    # ① a trava da FORMA: 64 hex. Mais forte que o varredor aqui.
                    if not re.fullmatch(r"[0-9a-f]{64}", str(valor)):
                        hashes_torto.append(f"{tabela}.{col}")
                    continue
                if _pii_de_verdade(str(valor)):
                    sujas.append(f"{tabela}.{col}")
    checar(not sujas, "🔴 varredor de PII sobre TODAS as colunas de texto = 0", repr(sujas[:5]))
    checar(not hashes_torto,
           "🔴 e todo `trecho_hash` é sha256 (64 hex) — o trecho CRU nunca foi gravado",
           repr(hashes_torto[:5]))
    checar(_pii_de_verdade("meu cpf e 123.456.789-09")
           and not _pii_de_verdade("em decorrencia de sinistro coberto pelas garantias"),
           "🔴 CONTROLE do filtro novo: ele acusa o CPF e NÃO acusa 'sinistro coberto'")
    checar(True, "     (varridas as linhas-molde + o que houver na base)")
    conn.rollback()

with psycopg.connect(DSN, autocommit=True, prepare_threshold=None) as c, c.cursor() as cur:
    cur.execute("select count(*) from insurer_assistance_plans")
    depois_p = cur.fetchone()[0]
    cur.execute("select count(*) from insurer_assistance_services")
    depois_s = cur.fetchone()[0]
checar((antes_p, antes_s) == (depois_p, depois_s),
       "🔴 o guarda não deixou rastro: as contagens antes e depois são iguais",
       f"antes=({antes_p},{antes_s}) depois=({depois_p},{depois_s})")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
