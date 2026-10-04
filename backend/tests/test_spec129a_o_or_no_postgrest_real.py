# -*- coding: utf-8 -*-
"""SPEC-129-A (conserto · a MAIOR LACUNA do juiz) — os `or_(...)` do Work OS no PostgREST REAL.

📊 Antes do conserto: o filtro da lease (`adquirir_lease`) e os dois do re-despacho
(`redespachar_parados`) só tinham sido exercidos pelo DUBLÊ (`dubles_do_work_os.Consulta.or_`).
Se a sintaxe falhasse em produção, `adquirir_lease` engolia a exceção → NENHUM run pegava lease,
e o Work OS parava em silêncio.

O que este guarda prova, com o MESMO cliente do backend (`app.core.database`, supabase-py, o
`backend/.env`) e as MESMAS strings (`runs.filtro_lease_livre`, `runs.filtros_do_redespacho` — o
código as usa por estas funções, não por cópia):

  1. o PostgREST de produção ACEITA cada `or_` — SELECT só leitura, `count="exact"`, nenhuma escrita
  2. a contagem pelo PostgREST BATE com a mesma pergunta feita em SQL pelo psycopg (caminho
     INDEPENDENTE: a sintaxe não só é aceita, ela significa o que o código acha que significa)
  3. CONTROLE: uma expressão QUEBRADA é RECUSADA pelo PostgREST real — sem isto, (1) passaria
     com um servidor que ignora o filtro

🔴 Sem banco: FALHA (não pula) — pular não conta como verde.

    cd backend && PYTHONIOENCODING=utf-8 .venv/Scripts/python -m pytest tests/test_spec129a_o_or_no_postgrest_real.py -q -s
"""
from __future__ import annotations

import os
import sys
from datetime import timedelta
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from app.services.work import runs as R  # noqa: E402

#: o Postgres compara timestamptz em microssegundos; o PostgREST recebe o mesmo instante com `Z`
_SMITH = R.RUNTIME_DA_FILA


@pytest.fixture(scope="module")
def cliente():
    try:
        from dotenv import load_dotenv

        load_dotenv(RAIZ / ".env")
    except Exception:  # noqa: BLE001
        pass
    if not (os.getenv("SUPABASE_URL") and (os.getenv("SUPABASE_SERVICE_KEY")
                                           or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
                                           or os.getenv("SUPABASE_KEY"))):
        pytest.fail("SEM BANCO: SUPABASE_URL/chave ausentes — o or_ precisa do PostgREST REAL.")
    try:
        from app.core.database import get_supabase_client

        return get_supabase_client().client
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"SEM BANCO: o cliente do backend não subiu ({type(exc).__name__}).")


@pytest.fixture(scope="module")
def sql():
    dsn = os.getenv("SUPABASE_DB_URL")
    if not dsn:
        pytest.fail("SEM BANCO: SUPABASE_DB_URL ausente — o caminho independente (SQL) é obrigatório.")
    import psycopg

    def contar(consulta: str, params: tuple) -> int:
        with psycopg.connect(dsn, prepare_threshold=None, connect_timeout=20) as c, c.cursor() as cur:
            cur.execute("begin; set transaction read only")   # 🔴 nunca SET de sessão pelo pooler
            cur.execute(consulta, params)
            n = int(cur.fetchone()[0])
            cur.execute("rollback")
            return n
    return contar


def _duas_vezes(f):
    """O banco é VIVO: uma linha pode mudar entre as duas perguntas. Uma segunda rodada decide."""
    a = f()
    return a if a[0] == a[1] else f()


def test_o_or_da_lease_no_postgrest_real(cliente, sql):
    agora = R._agora()
    filtro = R.filtro_lease_livre(agora)

    def medir():
        res = (cliente.table("work_runs").select("id", count="exact")
               .eq("runtime_kind", _SMITH)
               .in_("status", list(R.ESTADOS_QUE_PEGAM_LEASE))
               .or_(filtro).limit(1).execute())
        n_sql = sql("select count(*) from public.work_runs where runtime_kind = %s "
                    "and status::text = any(%s) "
                    "and (lease_expires_at is null or lease_expires_at < %s)",
                    (_SMITH, list(R.ESTADOS_QUE_PEGAM_LEASE), agora))
        return res.count, n_sql

    n_rest, n_sql = _duas_vezes(medir)
    print(f"\n[or_ lease] filtro={filtro!r} · PostgREST count={n_rest} · SQL count={n_sql}")
    assert isinstance(n_rest, int), "o PostgREST não devolveu contagem para o or_ da lease"
    assert n_rest == n_sql, f"o or_ da lease significa outra coisa no PostgREST: {n_rest} ≠ {n_sql} (SQL)"


@pytest.mark.parametrize("status", ["queued", "running"])
def test_os_or_do_redespacho_no_postgrest_real(cliente, sql, status):
    corte = R._agora() - timedelta(seconds=R.PARADO_SEGUNDOS)
    expressao = R.filtros_do_redespacho(corte)[status]
    em_sql = {
        "queued": "(queued_at < %(c)s or (queued_at is null and requested_at < %(c)s))",
        "running": ("(heartbeat_at < %(c)s or (heartbeat_at is null and started_at < %(c)s) or "
                    "(heartbeat_at is null and started_at is null and requested_at < %(c)s))"),
    }[status]

    def medir():
        res = (cliente.table("work_runs").select("id", count="exact")
               .eq("runtime_kind", _SMITH).eq("status", status)
               .is_("lease_owner", "null")
               .or_(expressao).limit(1).execute())
        n_sql = sql("select count(*) from public.work_runs where runtime_kind = %(k)s "
                    "and status::text = %(s)s and lease_owner is null and " + em_sql,
                    {"k": _SMITH, "s": status, "c": corte})
        return res.count, n_sql

    n_rest, n_sql = _duas_vezes(medir)
    print(f"\n[or_ re-despacho {status}] PostgREST count={n_rest} · SQL count={n_sql}")
    assert isinstance(n_rest, int), f"o PostgREST não devolveu contagem para o or_ de {status}"
    assert n_rest == n_sql, f"o or_ do re-despacho ({status}) significa outra coisa: {n_rest} ≠ {n_sql}"


@pytest.mark.parametrize("quebrada", [
    "lease_expires_at.is.nulo,lease_expires_at.lt.2026-01-01T00:00:00.000000Z",   # operando inválido
    "queued_at.lt.2026-01-01T00:00:00.000000Z,and(queued_at.is.null,requested_at.lt.2026",  # parêntese
])
def test_CONTROLE_o_postgrest_real_recusa_um_or_quebrado(cliente, quebrada):
    """Sem esta linha, os de cima passariam com um servidor que IGNORA o filtro (§9.3)."""
    with pytest.raises(Exception) as erro:
        (cliente.table("work_runs").select("id", count="exact")
         .eq("runtime_kind", _SMITH).or_(quebrada).limit(1).execute())
    print(f"\n[CONTROLE] recusado: {type(erro.value).__name__}")
