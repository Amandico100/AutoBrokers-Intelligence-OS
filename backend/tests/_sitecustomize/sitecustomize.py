# -*- coding: utf-8 -*-
"""SPEC-123 F5a — a trava do banco real nos processos FILHOS do pytest.

O `tests/conftest.py` põe esta pasta no `PYTHONPATH` e liga `AUTOBROKERS_TRAVA_DO_BANCO=1` durante a
sessão de testes; o Python de cada guarda-script que o meta-guarda roda importa este arquivo ao subir
(mecanismo padrão do `site`). Fora do pytest a variável não existe e este arquivo não faz nada.
⛔ Nunca derruba o processo: a falha da trava é silenciosa (ela só ACRESCENTA uma recusa)."""
import os
import sys

if os.environ.get("AUTOBROKERS_TRAVA_DO_BANCO") == "1":
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import trava_do_banco_real as _t

        _t.instalar()
        sys.path.pop(0)
    except Exception:  # noqa: BLE001
        pass
