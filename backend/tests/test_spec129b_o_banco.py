# -*- coding: utf-8 -*-
r"""SPEC-129-B · F1 · G7 — a migration `20261005_01_spec129b_motor.sql` provada no BANCO REAL, em transação DESFEITA.

⚠️ Quem decide aqui é o Postgres: CHECK, FK composta, unique, gatilho, REVOKE. O alvo é o banco de produção, por
`psycopg`, dentro de `transacao_desfeita` (tests/trava_do_banco_real.py): a escrita só passa NESTA conexão, em
transação, COMMIT é recusado e a saída SEMPRE faz ROLLBACK. Sem marcador `banco_real` DE PROPÓSITO.

O que se aplica é o TEXTO DO ARQUIVO (APPLY = o corpo; VERIFY e ROLLBACK = os blocos do cabeçalho), nunca uma cópia.

```
APPLY      o arquivo inteiro, na transação (lock_timeout 5 s: nunca fila atrás de produção)
VERIFY     o read-only → 1·1·1·6·5·1·1·0·0·≥5·2 · o comportamental (DO com 14 casos + CONTROLES) → NOTICE "OK"
IDEMPOT.   APPLY 2× → 1 canal, 1 agger, o CHECK igual, 0 erro
ROLLBACK   sem dado → o CHECK volta ao texto EXATO de hoje, 0 tabela multicalculo, 0 canal, 0 agger
           com dado → RECUSA (a 1ª instrução levanta) — e a prova roda num SAVEPOINT
GRANT      service_role lê; anon/authenticated não (tabelas, view, sequência)
```
Ao fim, uma conexão NOVA, só leitura, confere que produção não mudou (impressão antes = depois).
🔴 Sem banco o teste FALHA com a causa (nunca "pulado = verde").
"""
from __future__ import annotations

import os
import time
import uuid
from pathlib import Path

import pytest

psycopg = pytest.importorskip("psycopg")
from psycopg import errors as pgerr  # noqa: E402

from trava_do_banco_real import transacao_desfeita  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]
MIGRACAO = BACKEND / "supabase" / "migrations" / "20261005_01_spec129b_motor.sql"

#: 📊 05/10/2026 `select pg_get_constraintdef(oid) from pg_constraint where conname='companies_company_kind_check'`
CHECK_DE_HOJE = ("CHECK ((company_kind = ANY (ARRAY['client'::text, 'platform_knowledge'::text, "
                 "'platform_blueprint_studio'::text])))")
TABELAS = ("multicalculo_adesoes", "multicalculo_pedidos", "multicalculo_calculos", "multicalculo_ofertas",
           "multicalculo_eventos")


def _dsn() -> str:
    dsn = os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        try:
            from dotenv import dotenv_values

            dsn = dotenv_values(BACKEND / ".env").get("SUPABASE_DB_URL")
        except Exception:  # noqa: BLE001
            dsn = None
    if not dsn:
        pytest.fail("SUPABASE_DB_URL ausente (ambiente e backend/.env): este guarda mede o BANCO; sem ele não há prova.")
    return dsn


def _bloco(cabecalho: str) -> str:
    """Um bloco do cabeçalho: as linhas depois de `-- <cabecalho>` até a linha `--` sozinha, sem o `--` da frente."""
    linhas = MIGRACAO.read_text(encoding="utf-8").splitlines()
    ini = next(i for i, l in enumerate(linhas) if l.startswith("-- " + cabecalho))
    corpo = []
    for l in linhas[ini + 1:]:
        if l.strip() == "--" or l.startswith("-- ="):
            break
        assert l.startswith("--"), (cabecalho, l)
        corpo.append(l[2:])
    sql = "\n".join(corpo).strip()
    assert sql, cabecalho
    return sql


IMPRESSAO = (
    "select (select pg_get_constraintdef(oid) from pg_constraint where conname='companies_company_kind_check'),"
    " (select count(*) from public.companies),"
    " (select count(*) from public.companies where company_kind='platform_canal'),"
    " (select count(*) from public.portals where key='agger'),"
    " (select count(*) from public.portal_accounts),"
    " (select count(*) from information_schema.columns where table_schema='public' and table_name='portal_accounts'"
    "    and column_name like 'robo%'),"
    " (select count(*) from pg_class where relnamespace='public'::regnamespace and relname like 'multicalculo%'),"
    " (select count(*) from pg_trigger where tgname='trg_portal_accounts_robo_pausa')")


def _impressao(dsn: str) -> tuple:
    with psycopg.connect(dsn, prepare_threshold=None) as c, c.cursor() as cur:
        cur.execute("set transaction read only")
        cur.execute(IMPRESSAO)
        r = cur.fetchone()
        c.rollback()
        return r


@pytest.fixture(scope="module")
def banco():
    """UMA transação para o arquivo inteiro: o APPLY segura ACCESS EXCLUSIVE em `companies`/`portal_accounts` até o
    ROLLBACK — uma janela só, curta, em vez de uma por teste. O teste do ROLLBACK é o ÚLTIMO do arquivo."""
    dsn = _dsn()
    antes = _impressao(dsn)
    avisos: list = []
    with psycopg.connect(dsn, prepare_threshold=None) as conn, transacao_desfeita(conn), conn.cursor() as cur:
        assert conn.autocommit is False
        conn.add_notice_handler(lambda d: avisos.append(d.message_primary))
        cur.execute("set local lock_timeout = '5s'")
        cur.execute("set local statement_timeout = '60s'")
        t0 = time.monotonic()
        cur.execute(MIGRACAO.read_text(encoding="utf-8"))          # o APPLY
        yield cur, conn, avisos
        print(f"\n[janela do lock] APPLY -> ROLLBACK: {time.monotonic() - t0:.1f} s")
    assert _impressao(dsn) == antes, "PRODUÇÃO MUDOU depois de uma transação que devia ser desfeita"


def _um(cur, sql, params=None):
    cur.execute(sql, params)
    return cur.fetchone()


def test_g7_verify_estrutural_e_comportamental(banco):
    cur, _conn, avisos = banco
    r = _um(cur, _bloco("VERIFY (read-only"))
    assert tuple(r[:9]) == (1, 1, 1, 6, 5, 1, 1, 0, 0), r
    assert r[9] >= 5 and r[10] == 2, r
    cur.execute(_bloco("VERIFY comportamental"))
    assert any(str(a).startswith("VERIFY 20261005_01 OK") for a in avisos), avisos
    print("\n" + next(str(a) for a in avisos if str(a).startswith("VERIFY 20261005_01 OK")))


def test_g7_grants_service_role_le_e_o_publico_nao(banco):
    """UMA ida ao banco (a janela do lock em `companies` é o custo de cada round trip)."""
    cur, _c, _a = banco
    r = _um(cur, """
        with alvo(t) as (select unnest(%s::text[])),
             papel(p) as (values ('anon'), ('authenticated')),
             priv(v) as (values ('select'), ('insert'), ('update'), ('delete'))
        select (select bool_and(has_table_privilege('service_role', 'public.'||t, 'select')) from alvo),
               (select count(*) from alvo, papel, priv where has_table_privilege(p, 'public.'||t, v)),
               (select count(*) from papel where has_sequence_privilege(p, 'public.multicalculo_eventos_id_seq', 'usage')),
               (select count(*) from pg_policies where tablename like 'multicalculo%%'),
               (select 'security_invoker=on' = any(reloptions) from pg_class where relname='multicalculo_seguradora_dia')
    """, ([*TABELAS, "multicalculo_seguradora_dia"],))
    assert r == (True, 0, 0, 0, True), r


def test_g7_as_16_contas_de_hoje_intocadas_e_o_canal_e_tecnico(banco):
    cur, _c, _a = banco
    assert _um(cur, "select count(*) from public.portal_accounts where robo_estado is not null "
                    "or robo_dono is not null or robo_janela is not null")[0] == 0
    linha = _um(cur, "select is_technical, status, agent_enabled, allow_web_search, use_langchain, "
                     "split_part(company_name,' ',1) from public.companies where company_kind='platform_canal'")
    assert linha == (True, "active", False, False, False, "AutoBrokers"), linha
    assert _um(cur, "select is_active, category from public.portals where key='agger'") == (False, "multicalculo")


def test_g7_idempotente(banco):
    cur, _c, _a = banco
    antes = _um(cur, "select pg_get_constraintdef(oid) from pg_constraint where conname='companies_company_kind_check'")
    cur.execute(MIGRACAO.read_text(encoding="utf-8"))              # 2ª vez
    assert _um(cur, "select count(*) from public.companies where company_kind='platform_canal'")[0] == 1
    assert _um(cur, "select count(*) from public.portals where key='agger'")[0] == 1
    assert _um(cur, "select pg_get_constraintdef(oid) from pg_constraint "
                    "where conname='companies_company_kind_check'") == antes
    assert "platform_canal" in antes[0]


def test_g7_o_verify_tem_controle_a_fk_composta_sem_a_corretora_deixaria_passar(banco):
    """§9.3: o guarda CONSEGUE ficar vermelho. Sem a FK composta (só a do pedido), a oferta com a corretora trocada
    ENTRA — então a recusa do VERIFY é mérito da FK de 4 colunas, e de mais nada."""
    cur, conn, _a = banco
    cur.execute("select id from public.companies where company_kind='client' order by created_at limit 2")
    a, b = [r[0] for r in cur.fetchall()]
    p = str(uuid.uuid4())
    c1 = str(uuid.uuid4())
    cur.execute("insert into public.multicalculo_pedidos (id, company_id, origem, opcoes, corretoras, pedido_cifrado)"
                " values (%s, %s, 'auxiliar', array['padrao'], array[%s]::uuid[], 'x')", (p, a, a))
    cur.execute("insert into public.multicalculo_calculos (id, pedido_id, solicitante_company_id, company_id, opcao,"
                " coberturas) values (%s, %s, %s, %s, 'padrao', '{}')", (c1, p, a, a))
    troca = ("insert into public.multicalculo_ofertas (calculo_id, pedido_id, company_id, solicitante_company_id,"
             " seguradora, premio_total) values (%s, %s, %s, %s, 'X', 100)")
    with pytest.raises(pgerr.ForeignKeyViolation):
        with conn.transaction():
            cur.execute(troca, (c1, p, b, a))
    with conn.transaction():
        cur.execute("alter table public.multicalculo_ofertas drop constraint fk_mc_ofertas_calculo")
        cur.execute(troca, (c1, p, b, a))           # MUTAÇÃO: sem a FK composta, a corretora trocada ENTRA
        assert _um(cur, "select count(*) from public.multicalculo_ofertas where calculo_id=%s and company_id=%s",
                   (c1, b))[0] == 1
    # (tudo isto morre no ROLLBACK da transação desfeita; a impressão do fixture confere)


def test_g7_rollback_volta_o_check_exato_e_recusa_com_dado(banco):
    cur, conn, _a = banco
    rollback = _bloco("ROLLBACK")
    # com DADO: um pedido real-de-teste → a 1ª instrução recusa (num SAVEPOINT; a transação externa segue)
    a = _um(cur, "select id from public.companies where company_kind='client' order by created_at limit 1")[0]
    with conn.transaction():
        cur.execute("insert into public.multicalculo_pedidos (company_id, origem, opcoes, corretoras, pedido_cifrado)"
                    " values (%s, 'auxiliar', array['padrao'], array[%s]::uuid[], 'x')", (a, a))
        with pytest.raises(pgerr.RaiseException):
            with conn.transaction():
                cur.execute(rollback)
        cur.execute("delete from public.multicalculo_pedidos where company_id=%s and pedido_cifrado='x'", (a,))
    # sem dado (o estado desta transação): o ROLLBACK volta TUDO — exceto as colunas robo_* (decisão do Founder)
    tem_robo = _um(cur, "select count(*) from public.portal_accounts where portal_key='agger' "
                        "or robo_estado is not null")[0]
    if tem_robo:   # depois do APPLY real e da T-120: o certo é RECUSAR
        with pytest.raises(pgerr.RaiseException):
            with conn.transaction():
                cur.execute(rollback)
        return
    cur.execute(rollback)
    assert _um(cur, "select pg_get_constraintdef(oid) from pg_constraint "
                    "where conname='companies_company_kind_check'")[0] == CHECK_DE_HOJE
    assert _um(cur, "select count(*) from pg_class where relnamespace='public'::regnamespace "
                    "and relname like 'multicalculo%%'")[0] == 0
    assert _um(cur, "select count(*) from public.companies where company_kind='platform_canal'")[0] == 0
    assert _um(cur, "select count(*) from public.portals where key='agger'")[0] == 0
    assert _um(cur, "select count(*) from pg_trigger where tgname='trg_portal_accounts_robo_pausa'")[0] == 0
