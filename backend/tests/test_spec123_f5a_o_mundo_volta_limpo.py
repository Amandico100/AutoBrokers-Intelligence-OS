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
