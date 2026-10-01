# -*- coding: utf-8 -*-
"""SPEC-123 F5a — os dois guardas do `tests/conftest.py`.

① A TRAVA DO BANCO REAL: um teste sem `@pytest.mark.banco_real` não escreve no banco real (as
  chaves locais são as de PRODUÇÃO). Prova pelo CLIENTE REAL do PostgREST apontado para um
  endereço morto: a escrita é recusada ANTES da rede; a leitura passa pela trava (e só cai na rede).
  CONTROLE: o MESMO pedido com o marcador chega à rede (erro de conexão, não a trava).

② P-121-28: o que um ARQUIVO troca, ele devolve. Este arquivo é o "teste que dependia da ordem":
  rodado DEPOIS de `test_a_janela_esta_ligada_nos_portoes.py` e `test_spec116_f3a_quem_escreve_pede_papel.py`
  (que trocam `attendance_agent_active` e `get_supabase_client` e não devolvem — o segundo já na
  COLETA), ele encontrava o mundo deles. 📊 Comando (no relatório da F5a, com o conftest de HEAD e
  o novo):
      pytest tests/test_a_janela_esta_ligada_nos_portoes.py \
             tests/test_spec116_f3a_quem_escreve_pede_papel.py tests/test_spec123_f5a_o_mundo_volta_limpo.py
"""
from __future__ import annotations

import importlib
import sys

import pytest


# =============================================================================
# ① a trava do banco real
# =============================================================================
def _cliente_morto():
    from postgrest import SyncPostgrestClient

    return SyncPostgrestClient("http://127.0.0.1:9", headers={"apikey": "x"}, timeout=2)


def test_escrita_pelo_cliente_real_e_recusada_antes_da_rede():
    conftest = sys.modules[[n for n in sys.modules if n.endswith("conftest") and
                            hasattr(sys.modules[n], "EscritaNoBancoRealBloqueada")][0]]
    db = _cliente_morto()
    for pedido in (db.from_("diario_de_decisoes").insert({"x": 1}),
                   db.from_("diario_de_decisoes").update({"x": 2}).eq("id", "1"),
                   db.from_("diario_de_decisoes").delete().eq("id", "1"),
                   db.from_("diario_de_decisoes").upsert({"x": 1}),
                   db.rpc("qualquer_funcao", {})):
        with pytest.raises(conftest.EscritaNoBancoRealBloqueada):
            pedido.execute()


def test_leitura_passa_pela_trava():
    conftest = sys.modules[[n for n in sys.modules if n.endswith("conftest") and
                            hasattr(sys.modules[n], "EscritaNoBancoRealBloqueada")][0]]
    with pytest.raises(Exception) as e:
        _cliente_morto().from_("diario_de_decisoes").select("id").execute()
    assert not isinstance(e.value, conftest.EscritaNoBancoRealBloqueada)


@pytest.mark.banco_real
def test_CONTROLE_com_o_marcador_a_escrita_chega_a_rede():
    conftest = sys.modules[[n for n in sys.modules if n.endswith("conftest") and
                            hasattr(sys.modules[n], "EscritaNoBancoRealBloqueada")][0]]
    with pytest.raises(Exception) as e:
        _cliente_morto().from_("diario_de_decisoes").insert({"x": 1}).execute()
    assert not isinstance(e.value, conftest.EscritaNoBancoRealBloqueada), "o marcador não liberou"


def test_o_psycopg_tambem_esta_travado():
    psycopg = pytest.importorskip("psycopg")
    conftest = sys.modules[[n for n in sys.modules if n.endswith("conftest") and
                            hasattr(sys.modules[n], "_sql_escreve")][0]]
    assert hasattr(psycopg.Cursor.execute, "__wrapped__") and hasattr(psycopg.AsyncCursor.execute, "__wrapped__")
    for sql in ("insert into t values (1)", "  UPDATE t set a=1", "-- x\ndelete from t", "create table t()",
                "with x as (delete from t returning 1) select * from x", "alter table t add c int"):
        assert conftest._sql_escreve(sql), sql
    for sql in ("select 1", "with x as (select 1) select * from x", "SET TRANSACTION READ ONLY"):
        assert not conftest._sql_escreve(sql), sql


# =============================================================================
# ② o mundo que os outros arquivos deixaram
# =============================================================================
def test_o_cliente_do_banco_e_o_do_produto():
    db = importlib.import_module("app.core.database")
    assert getattr(db, "__file__", None), "app.core.database é um módulo de mentira"
    assert db.get_supabase_client.__module__ == "app.core.database", db.get_supabase_client


def test_o_agente_ligado_e_a_funcao_do_produto():
    cap = importlib.import_module("app.services.atlas.attendance_capture")
    f = cap.attendance_agent_active
    assert f.__module__ == "app.services.atlas.attendance_capture", (f.__module__, f.__qualname__)


def test_o_pacote_app_e_o_de_verdade():
    app = importlib.import_module("app")
    assert getattr(app, "__file__", None) and app.__spec__ is not None


# =============================================================================
# ①b a trava vale também nos processos FILHOS (os guardas-script do meta-guarda)
# =============================================================================
_FILHO = (
    "from postgrest import SyncPostgrestClient\n"
    "db = SyncPostgrestClient('http://127.0.0.1:9', headers={'apikey': 'x'}, timeout=2)\n"
    "try:\n"
    "    db.from_('diario_de_decisoes').insert({'x': 1}).execute()\n"
    "except Exception as e:\n"
    "    print('ERRO=' + type(e).__name__)\n"
)


def _rodar_filho():
    import subprocess

    r = subprocess.run([sys.executable, "-c", _FILHO], capture_output=True, text=True, timeout=120)
    return (r.stdout or "").strip()


def test_o_processo_filho_sobe_com_a_trava():
    """📊 30/09: `test_o_caso_se_explica_sozinho` roda como SUBPROCESSO e chegava ao banco real
    (`[DIARIO] decisão NÃO registrada (APIError)` — a recusa veio do BANCO, não do teste)."""
    assert _rodar_filho() == "ERRO=EscritaNoBancoRealBloqueada"


@pytest.mark.banco_real
def test_CONTROLE_o_filho_de_um_teste_marcado_chega_a_rede():
    assert _rodar_filho() not in ("", "ERRO=EscritaNoBancoRealBloqueada")


# =============================================================================
# ①c a TRANSAÇÃO DESFEITA — a única abertura de um guarda-script (bateria 01/10: 3 guardas de CHECK/UNIQUE)
#     Sem banco: um cursor de mentira chama o `execute` EMBRULHADO do psycopg. Chegar ao driver = AttributeError
#     do cursor falso (não a trava); a trava = EscritaNoBancoRealBloqueada antes de qualquer rede.
# =============================================================================
class _ConexaoFalsa:
    def __init__(self, autocommit=False):
        self.autocommit = autocommit
        self.rollbacks = 0

    def rollback(self):
        self.rollbacks += 1


class _CursorFalso:
    def __init__(self, conn):
        self.connection = conn


def _trava():
    return sys.modules["trava_do_banco_real"]


def _executar(cur, sql):
    psycopg = pytest.importorskip("psycopg")
    try:
        psycopg.Cursor.execute(cur, sql)
    except _trava().EscritaNoBancoRealBloqueada:
        return "TRAVA"
    except Exception:  # noqa: BLE001 — passou pela trava e caiu no driver (cursor falso)
        return "DRIVER"
    return "DRIVER"


def test_CONTROLE_sem_transacao_desfeita_a_escrita_do_psycopg_e_recusada():
    cur = _CursorFalso(_ConexaoFalsa())
    assert _executar(cur, "insert into insurer_assistance_plans (x) values (1)") == "TRAVA"
    assert _executar(cur, "select 1") == "DRIVER"


def test_dentro_da_transacao_desfeita_a_escrita_chega_ao_driver_e_sai_desfeita():
    conn = _ConexaoFalsa()
    cur = _CursorFalso(conn)
    with _trava().transacao_desfeita(conn):
        assert _executar(cur, "insert into insurer_assistance_plans (x) values (1)") == "DRIVER"
        assert _executar(cur, "savepoint sp") == "DRIVER"
    assert conn.rollbacks == 1, "a saída do bloco não desfez a transação"
    # fora do bloco, a MESMA conexão volta a ser recusada
    assert _executar(cur, "insert into insurer_assistance_plans (x) values (1)") == "TRAVA"


def test_a_transacao_desfeita_desfaz_tambem_quando_o_guarda_estoura():
    conn = _ConexaoFalsa()
    with pytest.raises(ZeroDivisionError):
        with _trava().transacao_desfeita(conn):
            1 / 0
    assert conn.rollbacks == 1


def test_a_transacao_desfeita_nao_abre_o_que_nao_e_desfeito():
    t = _trava()
    # autocommit LIGADO: cada INSERT seria definitivo — recusa já na entrada
    with pytest.raises(t.EscritaNoBancoRealBloqueada):
        with t.transacao_desfeita(_ConexaoFalsa(autocommit=True)):
            pass
    conn = _ConexaoFalsa()
    cur = _CursorFalso(conn)
    with t.transacao_desfeita(conn):
        # COMMIT por SQL, ou autocommit ligado no meio: recusados
        assert _executar(cur, "commit") == "TRAVA"
        assert _executar(cur, "  END") == "TRAVA"
        conn.autocommit = True
        assert _executar(cur, "insert into t values (1)") == "TRAVA"
        conn.autocommit = False
        # OUTRA conexão, no mesmo processo e no mesmo bloco: continua travada
        assert _executar(_CursorFalso(_ConexaoFalsa()), "insert into t values (1)") == "TRAVA"
        # e o PostgREST também (a abertura é da conexão, não do processo)
        with pytest.raises(t.EscritaNoBancoRealBloqueada):
            _cliente_morto().from_("diario_de_decisoes").insert({"x": 1}).execute()


def test_conn_commit_dentro_da_transacao_desfeita_e_recusado():
    psycopg = pytest.importorskip("psycopg")
    t = _trava()
    conn = _ConexaoFalsa()
    with t.transacao_desfeita(conn):
        with pytest.raises(t.EscritaNoBancoRealBloqueada):
            psycopg.Connection.commit(conn)
    # CONTROLE: fora do bloco o commit passa pela trava (e cai no driver: a conexão é falsa)
    with pytest.raises(Exception) as e:
        psycopg.Connection.commit(conn)
    assert not isinstance(e.value, t.EscritaNoBancoRealBloqueada)
