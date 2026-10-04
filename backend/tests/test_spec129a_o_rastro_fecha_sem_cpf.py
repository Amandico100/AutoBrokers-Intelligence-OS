# -*- coding: utf-8 -*-
r"""SPEC-129-A · F4 — PRESOS E RASTRO: as migrations `_01`, `_02`, `_03` provadas no BANCO REAL.

⚠️ Este guarda não pergunta ao Python. Quem decide aqui é o Postgres: CHECK, gatilho, UPDATE filtrado.
Por isso o alvo é o banco de produção, por `psycopg`, dentro de `transacao_desfeita` (tests/trava_do_banco_real.py):
a escrita só passa NESTA conexão, em transação, COMMIT é recusado, e a saída SEMPRE faz ROLLBACK.
🔴 Sem marcador `banco_real` DE PROPÓSITO: o marcador abriria o processo inteiro (inclusive COMMIT);
   `transacao_desfeita` abre só a conexão do teste.

O que se aplica é o TEXTO DOS ARQUIVOS (APPLY = o corpo; VERIFY e ROLLBACK = os blocos do cabeçalho), nunca uma
cópia — mudou o arquivo, mudou a prova.

```
_01  medido pela DIFERENÇA (📊 a _01 FOI APLICADA em 04/10: VERIFY 21·21·6·0; hoje 0 presos): re-APPLY no
     banco já aplicado = os presos de AGORA (📊 0 linhas) · os 3 do teste expiram com a marca, e SÓ eles ·
     os "sem fila" intocados · jovem e com lease intocados · re-APPLY → 0 linhas · o ROLLBACK volta tudo
     menos o que o RUNTIME expirou · CONTROLE + MUTAÇÃO: sem o filtro de lease o run com dono expira
_02  2 colunas · índice · 2 CHECKs · smith dormindo sem relógio → recusado · acionamento com relógio →
     recusado · CONTROLE smith com relógio → aceito · idempotente · ROLLBACK re-enfileira com outbox
_03  0 cru · os 17 = gêmeo · passo `ura` cru de run vivo → mascarado · `monitoring` de run vivo → cru ·
     run fecha → mascarado · checkpoint em run fechado → mascarado · smith intocado · duas corretoras ·
     varredura das > 24 h · anon não executa · CONTROLE: sem o gatilho de fechamento fica cru (G7)
CAS  o 2º UPDATE filtrado devolve 0 linhas · a sombra `running` sem lease não é pega pelo filtro `smith`
```
Ao fim de cada teste, uma conexão NOVA, só leitura, confere que produção não mudou (impressão antes = depois).
⚠️ A impressão olha o que ESTE guarda pode deixar para trás (os runs marcados do teste, a marca da _01, o
retrato do acionamento, a estrutura) — nunca contagens globais: 📊 04/10 o worker de produção roda
`detect_signals` ao vivo (+4 `work_events` durante um teste) e a contagem global ficava vermelha sem culpa.
🔴 Sem banco o teste FALHA com a causa (nunca "pulado = verde").
"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import pytest

psycopg = pytest.importorskip("psycopg")
from psycopg import errors as pgerr  # noqa: E402

from trava_do_banco_real import transacao_desfeita  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]
MIGR = BACKEND / "supabase" / "migrations"
M01 = MIGR / "20261004_01_spec129a_presos_expiram.sql"
M02 = MIGR / "20261004_02_spec129a_espera_duravel.sql"
M03 = MIGR / "20261004_03_spec129a_retrato_mascarado.sql"

RX_CRU = r'"(titular_cpf|telefone_contato|client_phone)"\s*:\s*"[0-9]'
MARCADOR = {"_retrato": "mascarado (SPEC-129-A)"}
# 💭 dado SINTÉTICO de teste: CPF e telefone inventados, nunca de segurado
CRU = {"fase": "x", "titular_cpf": "12345678909", "telefone_contato": "11999990000"}
GEMEO = {"fase": "x", "titular_cpf": "...8909", "telefone_contato": "...0000"}


# =============================================================================
# a borda: DSN, arquivos, impressão de produção
# =============================================================================
def _dsn() -> str:
    dsn = os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        try:
            from dotenv import dotenv_values

            dsn = dotenv_values(BACKEND / ".env").get("SUPABASE_DB_URL")
        except Exception:  # noqa: BLE001
            dsn = None
    if not dsn:
        pytest.fail("SUPABASE_DB_URL ausente (ambiente e backend/.env): este guarda mede o BANCO; "
                    "sem ele não há prova — e pular não conta como verde.")
    return dsn


def _apply(caminho: Path) -> str:
    """O corpo executável do arquivo (o APPLY)."""
    return caminho.read_text(encoding="utf-8")


def _bloco(caminho: Path, cabecalho: str) -> str:
    """Um bloco do cabeçalho (VERIFY / ROLLBACK): as linhas depois de `-- <cabecalho>` até a linha `--`,
    sem o `--` da frente. Dentro do bloco toda linha é SQL ou comentário SQL (o arquivo garante)."""
    linhas = caminho.read_text(encoding="utf-8").splitlines()
    ini = next(i for i, l in enumerate(linhas) if l.startswith("-- " + cabecalho))
    corpo = []
    for l in linhas[ini + 1:]:
        if l.strip() == "--" or l.startswith("-- ="):
            break
        assert l.startswith("--"), (caminho.name, cabecalho, l)
        corpo.append(l[2:])
    sql = "\n".join(corpo).strip()
    assert sql, (caminho.name, cabecalho)
    return sql


def _um(cur, sql, params=None):
    cur.execute(sql, params)
    return cur.fetchone()


def _todas(cur, sql, params=None) -> list:
    cur.execute(sql, params)
    return cur.fetchall()


#: o que ESTE arquivo pode deixar em produção se o ROLLBACK falhar — e nada que o tráfego vivo mexa
IMPRESSAO = (
    "select (select count(*) from public.work_runs where outcome_title = 'guarda F4 SPEC-129-A'),"
    " (select count(*) from public.work_steps where idempotency_key like 'f4-%'),"
    " (select md5(coalesce(string_agg(id::text||status::text||coalesce(error_code,''),',' order by id),''))"
    "    from public.work_runs where error_code = 'expirado_sem_rodar_129a'),"
    " (select count(*) from public.work_events where payload_redacted->>'spec' = '129-A'"
    "    and payload_redacted->>'migration' = '_01'),"
    " (select md5(coalesce(string_agg(id::text||md5(output_summary::text),',' order by id),''))"
    "    from public.work_steps where step_type='dispatch_phase'),"
    " (select count(*) from information_schema.columns where table_schema='public'"
    "    and table_name='work_runs' and column_name in ('wake_at','wait_for')),"
    " (select count(*) from pg_trigger where tgname in ('trg_work_steps_retrato','trg_acionamento_fechado_mascara')),"
    " (select count(*) from pg_constraint where conname in ('ck_work_runs_wake_so_da_fila','ck_work_runs_espera_tem_relogio'))")


def _impressao(dsn: str) -> tuple:
    """Produção, só leitura, numa conexão NOVA: o que nenhum teste pode deixar mudado."""
    with psycopg.connect(dsn, prepare_threshold=None) as c, c.cursor() as cur:
        cur.execute("set transaction read only")
        cur.execute(IMPRESSAO)
        r = cur.fetchone()
        c.rollback()
        return r


@pytest.fixture
def banco():
    """(cursor, conexão) em transação DESFEITA + a prova de que produção não mudou."""
    dsn = _dsn()
    antes = _impressao(dsn)
    with psycopg.connect(dsn, prepare_threshold=None) as conn, transacao_desfeita(conn), conn.cursor() as cur:
        assert conn.autocommit is False
        yield cur, conn
    assert _impressao(dsn) == antes, "PRODUÇÃO MUDOU depois de uma transação que devia ser desfeita"


def _duas_corretoras(cur) -> tuple[str, str]:
    """Dois company_id REAIS, pelo banco (§13.9: nenhum nome, nenhuma constante)."""
    cur.execute("select id::text from public.companies order by created_at limit 2")
    ids = [r[0] for r in cur.fetchall()]
    assert len(ids) == 2, "o banco precisa de duas corretoras para a prova de isolamento"
    return ids[0], ids[1]


def _run(cur, company, *, runtime="smith", status="queued", idade_h=0.0, lease=False, wake=None,
         workflow="intelligence.detect_signals") -> str:
    rid = str(uuid.uuid4())
    cur.execute(
        "insert into public.work_runs (id, company_id, source_type, outcome_type, outcome_title, status,"
        " runtime_kind, workflow_key, thread_id, input_fingerprint, idempotency_key, requested_at, queued_at,"
        " lease_owner, lease_token, lease_expires_at" + (", wake_at" if wake else "") + ")"
        " values (%s, %s, 'system', 'teste', 'guarda F4 SPEC-129-A', %s::work_run_status, %s, %s,"
        " 'work:' || %s || ':' || %s, 'f4', %s, now() - make_interval(secs => %s), now() - make_interval(secs => %s),"
        " %s, %s, case when %s then now() + interval '2 minutes' end"
        + (", now() + interval '5 minutes'" if wake else "") + ")",
        (rid, company, status, runtime, workflow, company, rid, "f4-" + rid, idade_h * 3600, idade_h * 3600,
         "guarda-f4" if lease else None, str(uuid.uuid4()) if lease else None, lease))
    return rid


def _passo(cur, run, company, key, *, saida=None, gemeo=None, tipo="dispatch_phase", fim_ha_h=None) -> str:
    sid = str(uuid.uuid4())
    cur.execute(
        "insert into public.work_steps (id, work_run_id, company_id, step_key, ordinal, name, step_type,"
        " output_summary, output_redacted, idempotency_key, finished_at)"
        " values (%s, %s, %s, %s, 1, %s, %s, %s::jsonb, %s::jsonb, %s,"
        " case when %s::float is null then null else now() - make_interval(secs => %s::float) end)",
        (sid, run, company, key, key, tipo, json.dumps(saida if saida is not None else CRU),
         None if gemeo is None else json.dumps(gemeo), "f4-" + sid,
         None if fim_ha_h is None else fim_ha_h * 3600, None if fim_ha_h is None else fim_ha_h * 3600))
    return sid


def _saida(cur, sid):
    return _um(cur, "select output_summary from public.work_steps where id=%s", (sid,))[0]


# =============================================================================
# _01 — os presos expiram sem rodar (medido pela DIFERENÇA: a _01 já está aplicada em produção)
# =============================================================================
ALVO_01 = ("select id::text from public.work_runs where runtime_kind='smith' and status in ('queued','retry_scheduled')"
           " and lease_owner is null and requested_at < now() - interval '2 hours' order by id")
MARCADOS_01 = "select id::text from public.work_runs where error_code='expirado_sem_rodar_129a' order by id"
EVENTOS_01 = ("select count(*) from public.work_events where event_type='run.expired'"
              " and payload_redacted->>'spec'='129-A' and payload_redacted->>'migration'='_01'")
RUNS_HASH = ("select md5(string_agg(id::text||'|'||status::text||'|'||coalesce(error_code,'')||'|'||"
             "coalesce(error_message,'')||'|'||coalesce(finished_at::text,'')||'|'||coalesce(lease_owner,''),',' order by id))"
             " from public.work_runs where id::text = any(%s)")
SEM_FILA_HASH = ("select md5(string_agg(id::text||status::text||coalesce(error_code,''), ',' order by id))"
                 " from public.work_runs where runtime_kind <> 'smith'")
#: a linha do WHERE do APPLY que a MUTAÇÃO tira (o filtro de lease: "sem dono")
FILTRO_DE_LEASE = "and lease_owner is null"


def _apply_sem_o_filtro_de_lease() -> str:
    """A MUTAÇÃO: o APPLY da _01 sem `lease_owner is null` — só no CORPO (o cabeçalho é comentário)."""
    linhas = _apply(M01).splitlines(keepends=True)
    alvo = [i for i, l in enumerate(linhas) if not l.startswith("--") and l.strip() == FILTRO_DE_LEASE]
    assert len(alvo) == 1, "o APPLY mudou: a mutação não acha o filtro de lease"
    del linhas[alvo[0]]
    return "".join(linhas)


def _cenario_01(cur) -> dict:
    """Os runs do teste: 3 que EXPIRAM (2 corretoras · retry_scheduled · queued_at regravado) e 3 que FICAM."""
    a, b = _duas_corretoras(cur)
    ids = {
        "velho_a": _run(cur, a, idade_h=3),                                       # expira
        # retry_scheduled smith exige relógio (`ck_work_runs_espera_tem_relogio`: a _02 está aplicada)
        "velho_b": _run(cur, b, idade_h=3, status="retry_scheduled", wake=True),  # expira (outra corretora)
        "jovem": _run(cur, a, idade_h=1),                                         # fica: < 2 h
        "com_lease": _run(cur, a, idade_h=3, lease=True),                         # fica: tem dono
        "sombra": _run(cur, b, runtime="sombra", idade_h=3, workflow="claims.shadow"),  # "sem fila": nunca
        # a idade é por requested_at, NUNCA queued_at: um velho com queued_at regravado AGORA expira igual
        "regravado": _run(cur, a, idade_h=3),
    }
    cur.execute("update public.work_runs set queued_at = now() where id = %s", (ids["regravado"],))
    return ids


EXPIRAM = ("velho_a", "velho_b", "regravado")


def test_01_os_presos_expiram_e_o_rollback_nao_ressuscita_o_runtime(banco):
    cur, _ = banco
    _a, b = _duas_corretoras(cur)

    # 1) RE-APPLY no banco JÁ APLICADO: toca exatamente os presos que existem AGORA (📊 04/10: 0)
    presos_agora = [r[0] for r in _todas(cur, ALVO_01)]
    cur.execute(_apply(M01))
    reapply = cur.rowcount
    print(f"\n  _01 re-APPLY no banco já aplicado: {reapply} linha(s) (presos de agora: {len(presos_agora)})")
    assert reapply == len(presos_agora), (reapply, presos_agora)
    assert _todas(cur, ALVO_01) == [], "depois do APPLY não sobra preso"

    # 2) a DIFERENÇA: o que a _01 já marcou (produção) + os runs do teste
    ja = [r[0] for r in _todas(cur, MARCADOS_01)]
    eventos_ja = _um(cur, EVENTOS_01)[0]
    ids = _cenario_01(cur)
    # uma expiração de RUNTIME (o despertador da F1): OUTRO código, evento SEM a marca da _01
    runtime = _run(cur, b, idade_h=5)
    cur.execute("update public.work_runs set status='expired', finished_at=now(), error_code='expirado_pela_idade',"
                " error_message='expirou pela idade' where id=%s", (runtime,))
    cur.execute("insert into public.work_events (company_id, work_run_id, event_type, actor_type, severity,"
                " message_human, payload_redacted) values (%s, %s, 'run.expired', 'worker', 'warning',"
                " 'expirou pela idade', '{\"spec\":\"129-A\",\"origem\":\"despertador\"}'::jsonb)", (b, runtime))
    # a impressão de produção CONSEGUE ver o que o teste escreve (senão o fixture não guardaria nada)
    assert _um(cur, IMPRESSAO)[0] >= 7, "a impressão não enxerga os runs marcados do teste"

    alvo = {r[0] for r in _todas(cur, ALVO_01)}
    assert alvo == {ids[k] for k in EXPIRAM}, ("o alvo devia ser SÓ os 3 do teste", alvo)
    do_teste = list(ids.values()) + [runtime]
    sem_fila_antes = _um(cur, SEM_FILA_HASH)[0]
    hash_antes = _um(cur, RUNS_HASH, (do_teste,))[0]
    vivos_sem_fila = _um(cur, "select count(*) from public.work_runs where runtime_kind<>'smith'"
                              " and status::text not in ('completed','failed','cancelled','expired')")[0]

    cur.execute(_apply(M01))
    escritos = cur.rowcount                                    # um run.expired por run expirado (UM comando)
    v1 = _um(cur, _bloco(M01, "VERIFY"))
    print(f"  _01 APPLY: {escritos} linha(s) · VERIFY (já marcados={len(ja)}, eventos={eventos_ja}): {v1}")
    assert escritos == len(EXPIRAM), ("a _01 tocou além dos 3 do teste", escritos)
    assert v1 == (len(ja) + 3, eventos_ja + 3, vivos_sem_fila, 0), v1
    assert _um(cur, SEM_FILA_HASH)[0] == sem_fila_antes, "tocou um 'sem fila'"
    estados = dict(_todas(cur, "select id::text, status::text from public.work_runs where id::text = any(%s)",
                          (list(ids.values()),)))
    assert estados == {ids["velho_a"]: "expired", ids["velho_b"]: "expired", ids["regravado"]: "expired",
                       ids["jovem"]: "queued", ids["com_lease"]: "queued", ids["sombra"]: "queued"}, estados
    ev = _um(cur, "select count(*), min(severity), min(company_id::text) = %s, min(payload_redacted->>'status_antes')"
                  " from public.work_events where work_run_id = %s and event_type = 'run.expired'", (b, ids["velho_b"]))
    assert ev == (1, "warning", True, "retry_scheduled"), ev

    # idempotência: o re-APPLY escreve 0 linhas e o VERIFY não muda
    cur.execute(_apply(M01))
    assert cur.rowcount == 0, cur.rowcount
    assert _um(cur, _bloco(M01, "VERIFY")) == v1

    # ROLLBACK do arquivo: os da _01 voltam; o expirado pelo RUNTIME (e o evento dele) NÃO
    cur.execute(_bloco(M01, "ROLLBACK"))
    assert _um(cur, "select status::text, error_code from public.work_runs where id=%s",
               (runtime,)) == ("expired", "expirado_pela_idade")
    assert _um(cur, "select count(*) from public.work_events where work_run_id=%s", (runtime,))[0] == 1
    # e os runs do teste voltam EXATAMENTE ao de antes (menos updated_at, que o gatilho regrava)
    assert _um(cur, RUNS_HASH, (do_teste,))[0] == hash_antes
    assert _um(cur, EVENTOS_01)[0] == 0
    # os de produção também voltam ao status de antes (dentro da transação desfeita)
    assert _um(cur, "select count(*) from public.work_runs where id::text = any(%s) and status='expired'",
               (ja,))[0] == 0


def test_01_CONTROLE_e_MUTACAO_sem_o_filtro_de_lease_o_dono_perde_o_run(banco):
    """§9.3 / G7: o guarda CONSEGUE ficar vermelho. A linha de CONTROLE repete o APPLY de verdade (o run com
    dono fica); a MUTAÇÃO tira só `lease_owner is null` — e o run com dono expira por baixo do worker."""
    cur, _ = banco
    cur.execute(_apply(M01))                                   # zera os presos de agora (re-APPLY)
    ids = _cenario_01(cur)
    cur.execute(_apply(M01))                                   # CONTROLE: o APPLY de verdade
    assert cur.rowcount == len(EXPIRAM), cur.rowcount
    assert _um(cur, "select status::text from public.work_runs where id=%s", (ids["com_lease"],))[0] == "queued"
    cur.execute(_apply_sem_o_filtro_de_lease())                # a MUTAÇÃO
    print(f"\n  _01 MUTAÇÃO (sem o filtro de lease): {cur.rowcount} linha(s)")
    assert cur.rowcount == 1, cur.rowcount
    estado = _um(cur, "select status::text, error_code from public.work_runs where id=%s", (ids["com_lease"],))
    assert estado == ("expired", "expirado_sem_rodar_129a"), (
        "sem o filtro de lease o run com dono devia expirar (senão o guarda não guarda)", estado)
    # o "sem fila" nem a mutação toca: o filtro dele é outro (`runtime_kind='smith'`)
    assert _um(cur, "select status::text from public.work_runs where id=%s", (ids["sombra"],))[0] == "queued"


# =============================================================================
# _02 — a estrutura da espera
# =============================================================================
def test_02_a_espera_tem_relogio_e_so_na_fila(banco):
    cur, conn = banco
    a, b = _duas_corretoras(cur)
    cur.execute(_apply(M02))
    v = _um(cur, _bloco(M02, "VERIFY ("))
    print(f"\n  _02 VERIFY: {v}")
    assert v == (2, 1, 2), v
    cur.execute(_apply(M02))                                           # idempotente
    assert _um(cur, _bloco(M02, "VERIFY (")) == (2, 1, 2)
    cur.execute(_bloco(M02, "VERIFY comportamental"))                  # o DO do arquivo levanta se falhar

    # as mesmas travas, com runs do teste nas DUAS corretoras
    s = _run(cur, a, status="running")
    acion = _run(cur, b, runtime="acionamento", status="waiting_input", workflow="acionamento.seguradora")
    with pytest.raises(pgerr.CheckViolation, match="ck_work_runs_espera_tem_relogio"):
        with conn.transaction():
            cur.execute("update public.work_runs set status='waiting_input' where id=%s", (s,))
    with pytest.raises(pgerr.CheckViolation, match="ck_work_runs_espera_tem_relogio"):
        with conn.transaction():
            cur.execute("update public.work_runs set status='retry_scheduled' where id=%s", (s,))
    with pytest.raises(pgerr.CheckViolation, match="ck_work_runs_wake_so_da_fila"):
        with conn.transaction():
            cur.execute("update public.work_runs set wake_at=now() where id=%s", (acion,))
    # CONTROLE: com relógio, o smith dorme (sem ele, as recusas acima podiam ser de qualquer coisa)
    cur.execute("update public.work_runs set status='waiting_input', wake_at=now()+interval '5 minutes',"
                " wait_for='{\"tipo\":\"portal_job\",\"ref\":\"x\"}'::jsonb where id=%s returning id", (s,))
    assert cur.fetchone()
    # o "sem fila" continua podendo esperar SEM relógio (acionamento waiting_input é o normal dele)
    assert _um(cur, "select status::text, wake_at from public.work_runs where id=%s", (acion,)) == ("waiting_input", None)
    # o despertador usa o índice parcial
    plano = "\n".join(r[0] for r in _todas(
        cur, "explain select id from public.work_runs where runtime_kind='smith' and status in "
             "('waiting_input','retry_scheduled') and wake_at <= now()"))
    print("  plano do despertador:", plano.splitlines()[0])

    # ROLLBACK do arquivo: o dormindo volta à fila COM outbox; travas e índice saem; colunas ficam
    cur.execute(_bloco(M02, "ROLLBACK"))
    assert _um(cur, "select status::text, wake_at, wait_for, lease_owner from public.work_runs where id=%s",
               (s,)) == ("queued", None, None, None)
    assert _um(cur, "select count(*), min(event_kind) from public.work_queue_outbox where work_run_id=%s",
               (s,)) == (1, "run.recovered")
    assert _um(cur, "select status::text from public.work_runs where id=%s", (acion,))[0] == "waiting_input"
    assert _um(cur, _bloco(M02, "VERIFY (")) == (2, 0, 0)


# =============================================================================
# _03 — o retrato fecha sem CPF
# =============================================================================
VERIFY03_ESPERADO_DISPATCH = (
    "select count(*) filter (where output_redacted is not null"
    "   and not (step_key='monitoring' and coalesce(finished_at, updated_at) >= now() - interval '24 hours'"
    "            and exists (select 1 from public.work_runs r where r.id=s.work_run_id and r.company_id=s.company_id"
    "                        and r.status::text not in ('completed','failed','cancelled','expired'))))"
    " from public.work_steps s where step_type='dispatch_phase'")


def test_03_o_retrato_de_producao_fecha_sem_cpf(banco):
    cur, _ = banco
    cru_antes = _um(cur, "select count(*) from public.work_steps where output_summary::text ~ %s", (RX_CRU,))[0]
    esperado = _um(cur, VERIFY03_ESPERADO_DISPATCH)[0]
    gemeos = dict(_todas(cur, "select id::text, output_redacted from public.work_steps where step_type='dispatch_phase'"
                              " and output_redacted is not null"))
    cur.execute(_apply(M03))
    v = _um(cur, _bloco(M03, "VERIFY ("))
    print(f"\n  _03 VERIFY (cru antes={cru_antes}, dispatch_phase com gêmeo={len(gemeos)}): {v}")
    assert v == (0, esperado, 2, 1), v
    # sem exceção: CADA linha mascarada é o gêmeo dela (nunca o marcador, quando o gêmeo existe)
    depois = dict(_todas(cur, "select id::text, output_summary from public.work_steps where id::text = any(%s)",
                         (list(gemeos),)))
    assert sum(depois[k] == gemeos[k] for k in gemeos) == esperado
    cur.execute(_apply(M03))                                           # idempotente
    assert _um(cur, _bloco(M03, "VERIFY (")) == v
    # ROLLBACK: a estrutura sai; o dado continua mascarado (por desenho)
    cur.execute(_bloco(M03, "ROLLBACK"))
    assert _um(cur, _bloco(M03, "VERIFY (")) == (0, esperado, 0, 0)


def test_03_a_regra_do_retrato_no_motor_do_banco(banco):
    cur, conn = banco
    a, b = _duas_corretoras(cur)
    cur.execute(_apply(M03))

    vivo = _run(cur, a, runtime="acionamento", status="waiting_input", workflow="acionamento.seguradora")
    ura = _passo(cur, vivo, a, "ura", gemeo=GEMEO)
    sem_gemeo = _passo(cur, vivo, a, "human_phase")
    mon = _passo(cur, vivo, a, "monitoring", gemeo=GEMEO, fim_ha_h=0.1)
    assert _saida(cur, ura) == GEMEO, "passo `ura` cru de run vivo devia sair mascarado"
    assert _saida(cur, sem_gemeo) == MARCADOR, "sem gêmeo, o marcador"
    assert _saida(cur, mon) == CRU, "`monitoring` de run vivo é o único que fica cru (é restaurável)"

    # a OUTRA corretora: um monitoring vivo dela, e a regra perguntada com a corretora errada
    vivo_b = _run(cur, b, runtime="acionamento", status="waiting_input", workflow="acionamento.seguradora")
    mon_b = _passo(cur, vivo_b, b, "monitoring", gemeo=GEMEO, fim_ha_h=0.1)
    assert _um(cur, "select public.retrato_pode_ficar_cru(%s, %s, 'monitoring')", (vivo_b, a))[0] is False

    # o run FECHA → o retrato dele vira o gêmeo; o da outra corretora não é tocado
    cur.execute("update public.work_runs set status='completed', finished_at=now() where id=%s", (vivo,))
    assert _saida(cur, mon) == GEMEO
    assert _saida(cur, mon_b) == CRU, "fechar um run de A tocou o passo de B"
    # checkpoint DEPOIS do fechamento (B6: o router grava o passo antes do status) → mascarado
    cur.execute("update public.work_steps set output_summary=%s::jsonb where id=%s", (json.dumps(CRU), mon))
    assert _saida(cur, mon) == GEMEO
    reaberto = _passo(cur, vivo, a, "test_aborted", gemeo=GEMEO)
    assert _saida(cur, reaberto) == GEMEO

    # o smith é intocado: outro step_type, mesmo com chave de CPF; e fechar o run não o mexe
    s = _run(cur, b, status="running")
    sp = _passo(cur, s, b, "analise", tipo="analysis", gemeo=GEMEO)
    cur.execute("update public.work_runs set status='completed' where id=%s", (s,))
    assert _saida(cur, sp) == CRU

    # a varredura: monitoring de run VIVO com mais de 24 h deixa de ser restaurável → mascarado
    vivo_c = _run(cur, b, runtime="acionamento", status="waiting_input", workflow="acionamento.seguradora")
    mon_velho = _passo(cur, vivo_c, b, "monitoring", gemeo=GEMEO, fim_ha_h=25)
    assert _saida(cur, mon_velho) == CRU
    n = _um(cur, "select public.work_steps_mascarar_vencidos(24)")[0]
    assert n >= 1 and _saida(cur, mon_velho) == GEMEO and _saida(cur, mon_b) == CRU, n

    # quem pode chamar: service_role sim (e o gatilho dispara para ela); anon e authenticated não
    with conn.transaction():
        cur.execute("set local role service_role")
        assert _um(cur, "select public.work_steps_mascarar_vencidos(24)")[0] == 0
        p = _passo(cur, vivo_b, b, "ura", gemeo=GEMEO)
        assert _saida(cur, p) == GEMEO
        cur.execute("reset role")
    for papel in ("anon", "authenticated"):
        with pytest.raises(pgerr.InsufficientPrivilege, match="function work_steps_mascarar_vencidos"):
            with conn.transaction():
                cur.execute(f"set local role {papel}")
                cur.execute("select public.work_steps_mascarar_vencidos(24)")


def test_03_CONTROLE_sem_o_gatilho_de_fechamento_o_retrato_fica_cru(banco):
    """§9.3 / G7: o guarda consegue ficar VERMELHO — a mutação da SPEC reintroduz o defeito."""
    cur, _ = banco
    a, _b = _duas_corretoras(cur)
    cur.execute(_apply(M03))
    cur.execute("drop trigger trg_acionamento_fechado_mascara on public.work_runs")      # a MUTAÇÃO
    vivo = _run(cur, a, runtime="acionamento", status="waiting_input", workflow="acionamento.seguradora")
    mon = _passo(cur, vivo, a, "monitoring", gemeo=GEMEO)
    cur.execute("update public.work_runs set status='completed' where id=%s", (vivo,))
    assert _saida(cur, mon) == CRU, "sem o gatilho de fechamento o retrato devia continuar cru (o guarda não guarda)"


# =============================================================================
# CAS — o UPDATE filtrado do PostgREST é a linha ou nada (D-129A-3)
# =============================================================================
CAS_LEASE = ("update public.work_runs set status='running', lease_owner=%s, lease_token=%s,"
             " lease_expires_at=now()+interval '120 seconds', started_at=now()"
             " where id=%s and runtime_kind='smith' and status in ('queued')"
             " and (lease_expires_at is null or lease_expires_at < now()) returning lease_token::text")


def test_cas_o_segundo_update_filtrado_devolve_zero_linhas(banco):
    cur, _ = banco
    a, b = _duas_corretoras(cur)
    r = _run(cur, a)
    t1, t2 = str(uuid.uuid4()), str(uuid.uuid4())
    cur.execute(CAS_LEASE, ("w1", t1, r))
    assert [x[0] for x in cur.fetchall()] == [t1]
    cur.execute(CAS_LEASE, ("w2", t2, r))
    assert cur.fetchall() == [], "a 2ª lease ganhou: dois processos no mesmo run"
    assert _um(cur, "select lease_token::text from public.work_runs where id=%s", (r,))[0] == t1
    # concluir só com o MEU token
    fim = ("update public.work_runs set status='completed', lease_owner=null, lease_token=null, lease_expires_at=null"
           " where id=%s and runtime_kind='smith' and status='running' and lease_token=%s returning id")
    cur.execute(fim, (r, t2))
    assert cur.fetchall() == []
    cur.execute(fim, (r, t1))
    assert len(cur.fetchall()) == 1
    # a sombra `running` SEM lease não casa o filtro `smith` (📊 3 em produção)
    sombra = _run(cur, b, runtime="sombra", status="running", workflow="claims.shadow")
    cur.execute(CAS_LEASE.replace("status in ('queued')", "status in ('queued','running')"), ("w3", t2, sombra))
    assert cur.fetchall() == []
