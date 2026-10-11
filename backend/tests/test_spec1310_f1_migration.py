# -*- coding: utf-8 -*-
"""SPEC-131-0 parte A · F1 — a migration dos membros (`20261011_02_spec1310_membros.sql`), lida como TEXTO.

O que se guarda aqui é a FORMA da migration (CLAUDE.md §8 / MIGRATIONS-AUTHORITY §7): o cabeçalho com APPLY/VERIFY/
ROLLBACK escrito antes, idempotência, expand-first, os dois CHECKs `NOT VALID` + `VALIDATE`, e a VERIFY comportamental
que prova que a trava RECUSA (papel inventado, `admin`, função inventada). O COMPORTAMENTO das listas contra o código é
provado em `scripts/spec1310-membros.test.mjs` — que este arquivo também executa, para que a bateria (pytest) o rode.

📊 As expressões dos dois CHECKs foram avaliadas no Postgres real, só leitura, em 11/10/2026
(`select <array> <@ array['comercial','calculista','negociador']::text[]` e `select <papel> in (...)`):
'{}', '{comercial}', '{calculista,negociador}' → true · '{vendedor}', '{comercial,vendedor}', array[null] → false ·
owner/admin_company/member/attendant → true · admin, gerente_geral → false.
"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
RAIZ = BACKEND.parent
MIG = BACKEND / "supabase" / "migrations" / "20261011_02_spec1310_membros.sql"
TESTE_MJS = RAIZ / "scripts" / "spec1310-membros.test.mjs"

PAPEIS = ["owner", "admin_company", "member", "attendant"]
FUNCOES = ["comercial", "calculista", "negociador"]


def _texto():
    return MIG.read_text(encoding="utf-8")


def _corpo():
    """O SQL que RODA (sem as linhas de comentário do cabeçalho)."""
    return "\n".join(l for l in _texto().splitlines() if not l.lstrip().startswith("--"))


def _cabecalho():
    return "\n".join(l for l in _texto().splitlines() if l.lstrip().startswith("--"))


def test_a_migration_existe_no_diretorio_canonico():
    assert MIG.exists(), MIG


def test_cabecalho_tem_objetivo_apply_verify_rollback_e_as_classes():
    cab = _cabecalho()
    for chave in ("OBJETIVO:", "APPLY", "VERIFY", "ROLLBACK", "EXPAND-FIRST:", "DESTRUTIVA:", "IDEMPOTENTE:"):
        assert chave in cab, chave
    assert "o builder NÃO aplica" in cab
    # 📊 o ANTES medido, com o comando
    assert "📊 ANTES" in cab and "select role, count(*) from company_members" in cab


def test_cabecalho_lista_os_escritores_de_company_members():
    cab = _cabecalho()
    assert "app/api/dashboard/team/route.ts" in cab
    assert "20260721_01_spec047_rls_e_company_members.sql" in cab
    assert "git grep" in cab


def test_coluna_funcoes_idempotente_e_nao_nula():
    corpo = _corpo()
    assert re.search(
        r"alter table public\.company_members add column if not exists funcoes text\[\] not null default '\{\}'",
        corpo, re.I), "funcoes text[] NOT NULL DEFAULT '{}' com IF NOT EXISTS"


def _lista(padrao):
    m = re.search(padrao, _corpo(), re.I | re.S)
    assert m, padrao
    return re.findall(r"'([a-z_]+)'", m.group(1))


def test_check_das_funcoes_e_a_lista_fechada():
    assert _lista(r"add constraint ck_company_members_funcoes\s+check \(funcoes <@ array\[([^\]]*)\]") == FUNCOES


def test_check_do_papel_e_a_lista_fechada():
    lista = _lista(r"add constraint ck_company_members_role\s+check \(role in \(([^)]*)\)\)")
    assert lista == PAPEIS
    # ⛔ os legados que a política antiga conhece NÃO entram no banco
    assert "admin" not in lista and "master_admin" not in lista


@pytest.mark.parametrize("nome", ["ck_company_members_funcoes", "ck_company_members_role"])
def test_cada_check_nasce_not_valid_dentro_de_if_not_exists_e_depois_valida(nome):
    corpo = _corpo()
    bloco = re.search(
        r"if not exists \(select 1 from pg_constraint\s+where conrelid = 'public\.company_members'::regclass and conname = '%s'\) then"
        r"(.*?)end if;" % nome, corpo, re.I | re.S)
    assert bloco, "o ADD CONSTRAINT %s fica atrás da checagem no catálogo (idempotente)" % nome
    assert re.search(r"add constraint %s\b.*not valid;" % nome, bloco.group(1), re.I | re.S), "NOT VALID"
    assert re.search(r"alter table public\.company_members validate constraint %s;" % nome, corpo, re.I), "VALIDATE"
    # o VALIDATE vem DEPOIS do ADD
    assert corpo.lower().index("validate constraint %s" % nome) > corpo.lower().index("add constraint %s" % nome)


def test_todo_add_constraint_esta_protegido():
    corpo = _corpo().lower()
    assert corpo.count("add constraint") == corpo.count("if not exists (select 1 from pg_constraint") == 2


def test_transacao_e_nada_destrutivo_no_corpo():
    corpo = _corpo().lower()
    assert corpo.strip().startswith("begin;") and corpo.strip().endswith("commit;")
    for proibido in ("drop ", "truncate", "delete from", "update public.", "insert into public."):
        assert proibido not in corpo, proibido


def test_verify_prova_que_a_trava_recusa_sem_deixar_nada():
    cab = _cabecalho()
    assert "do $$" in cab and "on commit drop" in cab
    assert "pg_get_constraintdef" in cab, "a VERIFY copia a definição REAL do catálogo, não uma cópia escrita à mão"
    # o papel inventado, o legado `admin`, a função inventada (só e misturada) e a nula — 5 recusas esperadas
    for recusado in ("'gerente_geral'", "('admin', '{}')", "'{vendedor}'", "'{comercial,vendedor}'", "array[null]::text[]"):
        assert recusado in cab, recusado
    assert cab.count("exception when check_violation then recusas := recusas + 1") == 5
    assert "if recusas <> 5 then raise exception" in cab
    # e os válidos passam (a trava não recusa tudo)
    for papel in PAPEIS:
        assert "('%s'," % papel in cab, papel


def test_rollback_desfaz_os_dois_checks_e_a_coluna():
    cab = _cabecalho()
    rb = cab[cab.index("ROLLBACK"):]
    assert "drop constraint if exists ck_company_members_role" in rb
    assert "drop constraint if exists ck_company_members_funcoes" in rb
    assert "drop column if exists funcoes" in rb


@pytest.mark.skipif(shutil.which("node") is None, reason="node ausente")
def test_o_comportamento_contra_o_codigo_roda_no_node():
    """A rota, a política e o requireCompanyMember REAIS sobre duas corretoras (scripts/spec1310-membros.test.mjs)."""
    r = subprocess.run(["node", str(TESTE_MJS)], cwd=str(RAIZ), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=180)
    assert r.returncode == 0, (r.stdout or "")[-3000:] + (r.stderr or "")[-2000:]
    assert re.search(r"\d+ ok, 0 falha", r.stdout), r.stdout[-500:]
