# -*- coding: utf-8 -*-
r"""🔴 M-A2 · A LINHA SEM FONTE NÃO ENTRA — e quem recusa é o BANCO.

SPEC-EXTRA-001.5 · BLOCO A. A base desta SPEC vai responder a segurados sobre o
que a apólice deles cobre. Uma linha sem documento e página é uma afirmação sem
lastro — e sai pelo WhatsApp igualzinho a uma com lastro.

⚠️ **Este guarda não pergunta ao Python.** O contrato
(`assistance_plans_base.propor_servico`) também recusa, e isso é redundância
deliberada — mas o código pode ser contornado por um script, um backfill ou um
`INSERT` de curadoria feito à mão. O CHECK, não. Por isso o alvo aqui é o
**banco**, por `psycopg`, em transação que termina em `ROLLBACK`.

```
servico_tem_fonte                documento_id + pagina >= 1 + trecho_hash 64 hex
servico_publicado_foi_revisado   publicado exige revisado_por E revisado_em
limite_tem_unidade               limite_valor sem unidade não entra
```

🔴 **Linha de controle (CLAUDE.md §9.3):** o bloco final insere a linha
COMPLETA e ela tem de ser **ACEITA**. Sem ela, uma tabela que recusasse tudo
(ou um `INSERT` com erro de digitação) deixaria este guarda verde.

⛔ **Nada é escrito.** Tudo roda dentro de `BEGIN … ROLLBACK`, e a última
consulta confere que produção continua com as mesmas contagens.
⛔ **Nada de PII:** o guarda só toca `normative_documents.id` e as tabelas novas.
"""
from __future__ import annotations

import os
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
    # 🔴 PULA COM MOTIVO ESCRITO — nunca em silêncio, nunca "verde".
    print("\n\U0001F7E1 PULADO: `SUPABASE_DB_URL` ausente do ambiente e de backend/.env.")
    print("   Este guarda mede o BANCO; sem ele não há o que medir, e fingir que")
    print("   passou seria pior que não rodar. Exporte a variável e rode de novo.")
    sys.exit(0)

try:
    import psycopg
except ImportError:
    print("\n\U0001F7E1 PULADO: `psycopg` (v3) não instalado neste ambiente.")
    sys.exit(0)

H64 = "a" * 64
P = "public.insurer_assistance_plans"
S = "public.insurer_assistance_services"

COLS_S = ("plano_id,servico,coberto,documento_id,pagina,trecho_hash,confianca")

with psycopg.connect(DSN, prepare_threshold=None) as conn, conn.cursor() as cur:
    cur.execute("select count(*) from " + P)
    antes_p = cur.fetchone()[0]
    cur.execute("select count(*) from " + S)
    antes_s = cur.fetchone()[0]

    cur.execute("select id from normative_documents "
                "where product_line in ('auto','residencial') order by id limit 1")
    linha = cur.fetchone()
    if not linha:
        print("\n\U0001F7E1 PULADO: nenhum documento de auto/residencial no corpus.")
        sys.exit(0)
    doc = linha[0]

    cur.execute(
        "insert into " + P + " (insurer_key,ramo,produto,plano,nivel,vigencia_inicio,"
        "documento_id,pagina,confianca,curadoria,content_hash) "
        "values ('allianz','auto','GUARDA M-A2','Essencial',1,'2026-01-01',%s,3,"
        "'media','proposto','h') returning id",
        (doc,),
    )
    plano = cur.fetchone()[0]

    print("\n[1] o BANCO recusa a linha de serviço sem lastro")
    ataques = (
        ("documento_id NULL",
         f"insert into {S} ({COLS_S}) values ('{plano}','guincho','sim',null,3,'{H64}','media')",
         "not-null"),
        ("pagina NULL",
         f"insert into {S} ({COLS_S}) values ('{plano}','guincho','sim','{doc}',null,'{H64}','media')",
         "not-null"),
        ("pagina = 0",
         f"insert into {S} ({COLS_S}) values ('{plano}','guincho','sim','{doc}',0,'{H64}','media')",
         "servico_tem_fonte"),
        ("pagina negativa",
         f"insert into {S} ({COLS_S}) values ('{plano}','guincho','sim','{doc}',-1,'{H64}','media')",
         "servico_tem_fonte"),
        ("trecho_hash de 63 chars",
         f"insert into {S} ({COLS_S}) values ('{plano}','guincho','sim','{doc}',3,'{'a' * 63}','media')",
         "servico_tem_fonte"),
        ("trecho_hash de 65 chars",
         f"insert into {S} ({COLS_S}) values ('{plano}','guincho','sim','{doc}',3,'{'a' * 65}','media')",
         "servico_tem_fonte"),
        ("trecho_hash NULL",
         f"insert into {S} ({COLS_S}) values ('{plano}','guincho','sim','{doc}',3,null,'media')",
         "not-null"),
        ("curadoria='publicado' SEM revisor",
         f"insert into {S} ({COLS_S},curadoria) "
         f"values ('{plano}','guincho','sim','{doc}',3,'{H64}','media','publicado')",
         "servico_publicado_foi_revisado"),
        ("publicado com revisor mas SEM data",
         f"insert into {S} ({COLS_S},curadoria,revisado_por) "
         f"values ('{plano}','guincho','sim','{doc}',3,'{H64}','media','publicado',gen_random_uuid())",
         "servico_publicado_foi_revisado"),
        ("limite_valor SEM limite_unidade",
         f"insert into {S} ({COLS_S},limite_valor) "
         f"values ('{plano}','guincho','sim','{doc}',3,'{H64}','media',200)",
         "limite_tem_unidade"),
        ("documento_id que não existe",
         f"insert into {S} ({COLS_S}) "
         f"values ('{plano}','guincho','sim','00000000-0000-0000-0000-000000000000',3,'{H64}','media')",
         "foreign key"),
    )
    for nome, sql, marca in ataques:
        cur.execute("savepoint sp")
        try:
            cur.execute(sql)
            checar(False, f"🔴 {nome}: o banco ACEITOU",
                   "uma afirmação sem lastro chegaria ao segurado")
        except Exception as exc:  # noqa: BLE001
            msg = str(exc).strip().splitlines()[0]
            checar(marca.replace("not-null", "not-null") in msg or marca in msg,
                   f"{nome}: RECUSADO por `{marca}`",
                   f"{type(exc).__name__}: {msg}")
        cur.execute("rollback to savepoint sp")

    print("\n[2] e o PLANO tem os mesmos irmãos")
    COLS_P = ("insurer_key,ramo,produto,plano,nivel,vigencia_inicio,documento_id,"
              "pagina,confianca,content_hash")
    ataques_p = (
        ("plano com pagina = 0",
         f"insert into {P} ({COLS_P}) values "
         f"('allianz','auto','GUARDA M-A2','Outro',9,'2026-01-01','{doc}',0,'media','h')",
         "plano_tem_fonte"),
        ("plano publicado SEM revisor",
         f"insert into {P} ({COLS_P},curadoria) values "
         f"('allianz','auto','GUARDA M-A2','Outro',9,'2026-01-01','{doc}',3,'media','h','publicado')",
         "plano_publicado_foi_revisado"),
        ("plano com nivel 0",
         f"insert into {P} ({COLS_P}) values "
         f"('allianz','auto','GUARDA M-A2','Outro',0,'2026-01-01','{doc}',3,'media','h')",
         "plano_nivel_positivo"),
        ("insurer_key com lixo ('Seguradora XYZ')",
         f"insert into {P} ({COLS_P}) values "
         f"('Seguradora XYZ','auto','GUARDA M-A2','Outro',9,'2026-01-01','{doc}',3,'media','h')",
         "plano_insurer_key_canonica"),
    )
    for nome, sql, marca in ataques_p:
        cur.execute("savepoint sp")
        try:
            cur.execute(sql)
            checar(False, f"🔴 {nome}: o banco ACEITOU")
        except Exception as exc:  # noqa: BLE001
            msg = str(exc).strip().splitlines()[0]
            checar(marca in msg, f"{nome}: RECUSADO por `{marca}`",
                   f"{type(exc).__name__}: {msg}")
        cur.execute("rollback to savepoint sp")

    print("\n[3] 🔴 AS LINHAS DE CONTROLE — a tabela não recusa TUDO")
    controles = (
        ("a linha de serviço COMPLETA",
         f"insert into {S} ({COLS_S}) values ('{plano}','guincho','sim','{doc}',3,'{H64}','media')"),
        ("publicado COM revisor E data",
         f"insert into {S} ({COLS_S},curadoria,revisado_por,revisado_em) values "
         f"('{plano}','vidros','sim','{doc}',3,'{H64}','media','publicado',gen_random_uuid(),now())"),
        ("limite COM unidade",
         f"insert into {S} ({COLS_S},limite_valor,limite_unidade) values "
         f"('{plano}','carro_reserva','sim','{doc}',3,'{H64}','media',7,'dias')"),
        ("pagina = 1 (a borda do CHECK)",
         f"insert into {S} ({COLS_S}) values ('{plano}','chaveiro','sim','{doc}',1,'{H64}','media')"),
    )
    for nome, sql in controles:
        cur.execute("savepoint sp")
        try:
            cur.execute(sql)
            checar(True, f"🔴 CONTROLE: {nome} foi ACEITA")
        except Exception as exc:  # noqa: BLE001
            checar(False, f"🔴 CONTROLE: {nome} foi RECUSADA — o guarda mede a coisa errada",
                   f"{type(exc).__name__}: {str(exc).strip().splitlines()[0]}")
        cur.execute("rollback to savepoint sp")

    print("\n[4] e o CONTRATO em Python recusa ANTES do banco")
    from app.services.knowledge import assistance_plans_base as B  # noqa: E402

    for nome, kw in (
        ("sem documento_id", dict(plano_id=str(plano), servico="guincho", coberto="sim",
                                  documento_id="", pagina=3, trecho="x")),
        ("pagina 0", dict(plano_id=str(plano), servico="guincho", coberto="sim",
                          documento_id=str(doc), pagina=0, trecho="x")),
        ("sem trecho nem hash", dict(plano_id=str(plano), servico="guincho", coberto="sim",
                                     documento_id=str(doc), pagina=3)),
        ("hash de 63", dict(plano_id=str(plano), servico="guincho", coberto="sim",
                            documento_id=str(doc), pagina=3, trecho_hash="a" * 63)),
    ):
        try:
            B.propor_servico(**kw)
            checar(False, f"🔴 contrato: {nome} passou")
        except B.FonteObrigatoria as exc:
            checar(True, f"contrato: {nome} recusado ANTES do banco", str(exc))
        except Exception as exc:  # noqa: BLE001
            checar(False, f"🔴 contrato: {nome} levantou o erro ERRADO",
                   f"{type(exc).__name__}: {exc}")

    try:
        B.publicar_servico("00000000-0000-0000-0000-000000000000", None)
        checar(False, "🔴 contrato: publicar sem revisor passou")
    except B.RevisorObrigatorio as exc:
        checar(True, "contrato: publicar sem revisor recusado ANTES do banco", str(exc))

    conn.rollback()

with psycopg.connect(DSN, autocommit=True, prepare_threshold=None) as c, c.cursor() as cur:
    cur.execute("select count(*) from " + P)
    depois_p = cur.fetchone()[0]
    cur.execute("select count(*) from " + S)
    depois_s = cur.fetchone()[0]
print("\n[5] o guarda não deixou rastro em produção")
checar((antes_p, antes_s) == (depois_p, depois_s),
       "🔴 as contagens antes e depois são IGUAIS — tudo rodou em ROLLBACK",
       f"antes=({antes_p},{antes_s}) depois=({depois_p},{depois_s})")

print()
print("=" * 74)
print(f"  {OK} assercoes verdes - {FAIL} vermelhas")
print("=" * 74)
sys.exit(1 if FAIL else 0)
