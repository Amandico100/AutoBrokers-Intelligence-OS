"""O backend COMPILA na versão de Python que roda em produção (a do `backend/Dockerfile`).

📊 14/10/2026: `proposta_html.py` tinha construções que só o Python 3.12+ aceita (barra invertida e aspas iguais
aninhadas DENTRO da expressão de uma f-string). Os testes rodavam em 3.14 nesta máquina e passavam; o servidor roda
`python:3.11-slim`, onde o arquivo nem carrega — e TODA página de proposta (`/r/…`, renovação, cotação, QCM) dava 500.
A importação é preguiçosa, então o servidor subia "saudável" e o defeito só aparecia ao abrir um link.

O guarda usa o interpretador da MESMA versão do Dockerfile (`py -3.11` no Windows, `python3.11` no Linux). Sem ele na
máquina, o teste é PULADO com o motivo — nunca passa calado. A linha de controle prova que o guarda consegue ficar
vermelho (CLAUDE.md §9.3).
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]  # backend/
PASTAS = ("app", "portal_worker", "scripts")

_CHECADOR = r"""
import ast, sys
falhas = []
for caminho in sys.stdin.read().splitlines():
    try:
        ast.parse(open(caminho, encoding="utf-8-sig").read(), caminho)
    except SyntaxError as e:
        falhas.append(f"{caminho}:{e.lineno}: {e.msg}")
print("\n".join(falhas))
"""


def _versao_da_producao() -> str:
    texto = (RAIZ / "Dockerfile").read_text(encoding="utf-8")
    m = re.search(r"^FROM\s+python:(\d+\.\d+)", texto, re.M)
    assert m, "o Dockerfile do backend não diz a versão do Python"
    return m.group(1)


def _interpretador(versao: str) -> list[str] | None:
    if sys.version.startswith(versao + "."):
        return [sys.executable]
    if shutil.which("py"):
        r = subprocess.run(["py", f"-{versao}", "-c", "import sys; print(sys.version)"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.startswith(versao + "."):
            return ["py", f"-{versao}"]
    exe = shutil.which(f"python{versao}")
    return [exe] if exe else None


def _falhas(interp: list[str], arquivos: list[Path]) -> list[str]:
    r = subprocess.run(interp + ["-c", _CHECADOR], input="\n".join(str(a) for a in arquivos),
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-2000:]
    return [linha for linha in r.stdout.splitlines() if linha.strip()]


def _arquivos() -> list[Path]:
    return sorted(p for pasta in PASTAS for p in (RAIZ / pasta).rglob("*.py") if "__pycache__" not in p.parts)


def test_o_backend_compila_no_python_da_producao(tmp_path):
    versao = _versao_da_producao()
    interp = _interpretador(versao)
    if not interp:
        pytest.skip(f"sem Python {versao} nesta máquina (instale: `py install {versao}`) — o guarda não pode medir")

    # CONTROLE: o que quebrou em 14/10 tem de ficar VERMELHO aqui
    ruim = tmp_path / "ruim.py"
    ruim.write_text('i = 1\nx = f"{\'\' if i == 0 else \' tabindex=\\"-1\\"\'}"\n', encoding="utf-8")
    if versao < "3.12":
        assert _falhas(interp, [ruim]), "o controle passou: o guarda não consegue ficar vermelho"

    falhas = _falhas(interp, _arquivos())
    assert falhas == [], f"não compilam no Python {versao} da produção:\n" + "\n".join(falhas)
