# -*- coding: utf-8 -*-
"""SPEC-123 F5a — A TRAVA DO BANCO REAL durante os testes (um lugar só).

📊 30/09: `diario_de_decisoes._cliente` usa `dispatch_router._db()` — o cliente REAL, com as chaves de
PRODUÇÃO que moram no `.env` desta máquina. `test_o_caso_se_explica_sozinho` (um guarda-script que o
pytest roda como SUBPROCESSO) e um ensaio da bancada TENTARAM gravar no diário real; só não gravaram
porque o banco recusou o tenant inventado (`[DIARIO] decisão NÃO registrada (APIError)`). Sorte.

A trava fica na BORDA dos dois clientes (PostgREST/supabase-py e psycopg 3): uma escrita
(POST/PATCH/PUT/DELETE, inclusive RPC; INSERT/UPDATE/DELETE/DDL no psycopg) levanta
`EscritaNoBancoRealBloqueada` ANTES de sair da máquina. Leitura passa. Dublê não é PostgREST.

Quem instala:
  · `tests/conftest.py` — no processo do pytest (`pytest_configure`);
  · `tests/_sitecustomize/sitecustomize.py` — em TODO processo Python FILHO do pytest (os guardas-
    script que o meta-guarda roda), porque o conftest põe essa pasta no `PYTHONPATH` e liga
    `AUTOBROKERS_TRAVA_DO_BANCO=1` enquanto a sessão de testes dura.
Quem libera: `@pytest.mark.banco_real` (no processo) — e, para o filho dele, `AUTOBROKERS_TRAVA_DO_BANCO=0`.

A TRANSAÇÃO DESFEITA (`transacao_desfeita(conn)`) — a ÚNICA abertura dentro de um guarda-script.
📊 01/10 (bateria em `0fe9080`): 3 guardas que provam CHECK/UNIQUE/varredor de PII no schema real
(`test_a_base_de_planos_nao_tem_dono`, `test_a_linha_sem_fonte_nao_entra`, `test_a_pagina_existe_e_o_trecho_bate`)
fazem INSERT em `insurer_assistance_*` DENTRO de `BEGIN … ROLLBACK` — e a trava os recusava. Liberar o PROCESSO
inteiro (variável por nome no meta-guarda) abriria também o PostgREST e as conexões em autocommit deles.
A abertura é por CONEXÃO psycopg e por bloco `with`, e só vale enquanto:
  · a conexão está com autocommit DESLIGADO (cada execute confere — escrita em autocommit continua recusada);
  · nenhum COMMIT/END/PREPARE TRANSACTION passa por ela (`conn.commit()` e o SQL são recusados);
  · e a saída do bloco SEMPRE faz `rollback()` — com sucesso ou com exceção.
Fora do pytest (a trava não instalada) o bloco só garante o rollback.
"""
from __future__ import annotations

import contextlib
import os
import re
import threading
import weakref

TRAVA = threading.local()
ENV = "AUTOBROKERS_TRAVA_DO_BANCO"
# As conexões psycopg dentro de um `transacao_desfeita` ativo. Fraco: a conexão morta sai sozinha.
_DESFEITAS: "weakref.WeakSet" = weakref.WeakSet()
_RX_FECHA_TRANSACAO = re.compile(
    r"^\s*(?:(?:--[^\n]*\n|/\*.*?\*/)\s*)*(?:commit|end|prepare\s+transaction|commit\s+prepared)\b", re.I | re.S)

_RX_ESCRITA_SQL = re.compile(
    r"^\s*(?:(?:--[^\n]*\n|/\*.*?\*/)\s*)*(?:insert|update|delete|merge|upsert|create|alter|drop|"
    r"truncate|grant|revoke|comment|copy|call|do|vacuum|reindex|refresh|lock)\b", re.I | re.S)
_RX_CTE_QUE_ESCREVE = re.compile(r"\binsert\s+into\b|\bupdate\s+\S+\s+set\b|\bdelete\s+from\b", re.I)


class EscritaNoBancoRealBloqueada(RuntimeError):
    """Um teste tentou ESCREVER no banco real. Use um dublê, ou marque `@pytest.mark.banco_real`."""


def liberado() -> bool:
    return bool(getattr(TRAVA, "liberado", False)) or os.environ.get(ENV) == "0"


def recusar(onde: str) -> None:
    raise EscritaNoBancoRealBloqueada(
        f"teste: escrita no banco REAL bloqueada ({onde}). As chaves locais são as de PRODUÇÃO. "
        "Use um dublê (dubles.SupabaseDuble / monkeypatch do cliente) ou marque o teste com "
        "@pytest.mark.banco_real.")


def sql_escreve(query) -> bool:
    texto = query if isinstance(query, (str, bytes)) else (getattr(query, "_obj", None) or str(query))
    if isinstance(texto, bytes):
        texto = texto.decode("utf-8", "replace")
    texto = str(texto)
    if _RX_ESCRITA_SQL.search(texto):
        return True
    return texto.lstrip().lower().startswith("with") and bool(_RX_CTE_QUE_ESCREVE.search(texto))


@contextlib.contextmanager
def transacao_desfeita(conn):
    """Libera a escrita SÓ nesta conexão psycopg, SÓ em transação, e DESFAZ no fim — sempre.
    Uso: `with psycopg.connect(DSN) as conn, transacao_desfeita(conn), conn.cursor() as cur:`."""
    if getattr(conn, "autocommit", True):
        raise EscritaNoBancoRealBloqueada(
            "transacao_desfeita exige a conexão com autocommit DESLIGADO (senão cada INSERT já é definitivo).")
    _DESFEITAS.add(conn)
    try:
        yield conn
    finally:
        _DESFEITAS.discard(conn)
        conn.rollback()


def _na_transacao_desfeita(cursor, query) -> bool:
    """A escrita deste cursor está DENTRO de uma transação que vai ser desfeita?"""
    conn = getattr(cursor, "connection", None)
    try:
        dentro = conn is not None and conn in _DESFEITAS
    except TypeError:
        return False
    if not dentro:
        return False
    if getattr(conn, "autocommit", True):
        recusar("psycopg em transacao_desfeita com autocommit LIGADO")
    return True


def _fecha_transacao(query) -> bool:
    texto = query if isinstance(query, (str, bytes)) else (getattr(query, "_obj", None) or str(query))
    if isinstance(texto, bytes):
        texto = texto.decode("utf-8", "replace")
    return bool(_RX_FECHA_TRANSACAO.search(str(texto)))


def _metodo_que_escreve(builder) -> bool:
    return str(getattr(builder, "http_method", "")).upper() in ("POST", "PATCH", "PUT", "DELETE")


def instalar() -> list:
    """Embrulha o `execute` dos construtores do PostgREST e dos cursores do psycopg (idempotente).
    Devolve [(classe, nome, original-próprio-ou-None)] para desfazer."""
    trocas = []

    def _postgrest(cls, assincrono):
        original = cls.__dict__["execute"]
        if getattr(original, "_trava_do_banco", False):
            return
        if assincrono:
            async def execute(self, *a, **k):
                if not liberado() and _metodo_que_escreve(self):
                    recusar(f"PostgREST {self.http_method} {getattr(self, 'path', '?')}")
                return await original(self, *a, **k)
        else:
            def execute(self, *a, **k):
                if not liberado() and _metodo_que_escreve(self):
                    recusar(f"PostgREST {self.http_method} {getattr(self, 'path', '?')}")
                return original(self, *a, **k)
        execute.__wrapped__ = original
        execute._trava_do_banco = True
        setattr(cls, "execute", execute)
        trocas.append((cls, "execute", original))

    try:
        import inspect

        from postgrest._async import request_builder as _pa
        from postgrest._sync import request_builder as _ps

        for mod, assincrono in ((_ps, False), (_pa, True)):
            for _n, cls in inspect.getmembers(mod, inspect.isclass):
                if cls.__module__ == mod.__name__ and "execute" in cls.__dict__:
                    _postgrest(cls, assincrono)
    except Exception:  # noqa: BLE001 — sem postgrest instalado não há o que travar
        pass

    def _psycopg(cls, nome, assincrono):
        proprio = cls.__dict__.get(nome)
        original = proprio or getattr(cls, nome)
        if getattr(original, "_trava_do_banco", False):
            return
        def _conferir(self, query):
            if liberado():
                return
            desfeita = _na_transacao_desfeita(self, query)
            if desfeita and _fecha_transacao(query):
                recusar(f"psycopg {nome}: COMMIT dentro de transacao_desfeita")
            if sql_escreve(query) and not desfeita:
                recusar(f"psycopg {nome}")

        if assincrono:
            async def f(self, query, *a, **k):
                _conferir(self, query)
                return await original(self, query, *a, **k)
        else:
            def f(self, query, *a, **k):
                _conferir(self, query)
                return original(self, query, *a, **k)
        f.__wrapped__ = original
        f._trava_do_banco = True
        setattr(cls, nome, f)
        trocas.append((cls, nome, proprio))

    def _commit(cls, assincrono):
        proprio = cls.__dict__.get("commit")
        original = proprio or getattr(cls, "commit")
        if getattr(original, "_trava_do_banco", False):
            return
        if assincrono:
            async def commit(self, *a, **k):
                if not liberado() and self in _DESFEITAS:
                    recusar("psycopg commit() dentro de transacao_desfeita")
                return await original(self, *a, **k)
        else:
            def commit(self, *a, **k):
                if not liberado() and self in _DESFEITAS:
                    recusar("psycopg commit() dentro de transacao_desfeita")
                return original(self, *a, **k)
        commit.__wrapped__ = original
        commit._trava_do_banco = True
        setattr(cls, "commit", commit)
        trocas.append((cls, "commit", proprio))

    try:
        import psycopg as _pg

        for cls, assincrono in ((_pg.Cursor, False), (_pg.AsyncCursor, True)):
            for nome in ("execute", "executemany"):
                _psycopg(cls, nome, assincrono)
        _commit(_pg.Connection, False)
        _commit(_pg.AsyncConnection, True)
    except Exception:  # noqa: BLE001
        pass
    return trocas


def desinstalar(trocas: list) -> None:
    for cls, nome, original in reversed(trocas):
        try:
            if original is None:
                delattr(cls, nome)
            else:
                setattr(cls, nome, original)
        except Exception:  # noqa: BLE001
            pass
