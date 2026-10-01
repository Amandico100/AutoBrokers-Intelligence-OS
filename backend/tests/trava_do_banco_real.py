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
"""
from __future__ import annotations

import os
import re
import threading

TRAVA = threading.local()
ENV = "AUTOBROKERS_TRAVA_DO_BANCO"

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
        if assincrono:
            async def f(self, query, *a, **k):
                if not liberado() and sql_escreve(query):
                    recusar(f"psycopg {nome}")
                return await original(self, query, *a, **k)
        else:
            def f(self, query, *a, **k):
                if not liberado() and sql_escreve(query):
                    recusar(f"psycopg {nome}")
                return original(self, query, *a, **k)
        f.__wrapped__ = original
        f._trava_do_banco = True
        setattr(cls, nome, f)
        trocas.append((cls, nome, proprio))

    try:
        import psycopg as _pg

        for cls, assincrono in ((_pg.Cursor, False), (_pg.AsyncCursor, True)):
            for nome in ("execute", "executemany"):
                _psycopg(cls, nome, assincrono)
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
