"""Roda a suíte inteira e devolve um veredito. Um comando, uma resposta.

    python backend/tests/run_all.py

Por que este arquivo existe
---------------------------
A suíte é feita de scripts independentes — cada `test_*.py` roda sozinho e
devolve 0 ou 1. É um bom desenho: dá para investigar um caso isolado sem
carregar o resto. Mas não havia comando único para perguntar "está tudo
verde?", e cada pessoa inventava o seu laço de shell.

E havia uma armadilha, medida em 02/08/2026 nesta máquina:

    sem PYTHONIOENCODING=utf-8  →  96 verdes, 8 vermelhos
    com PYTHONIOENCODING=utf-8  →  104 verdes, 0 vermelhos

Os 8 não falhavam por asserção nenhuma. Falhavam no `print`::

    UnicodeEncodeError: 'charmap' codec can't encode character '\\u2192'

O console do Windows abre em cp1252, e oito testes escrevem `→` na saída.
A asserção passava; a impressão do "OK" derrubava o processo.

Isso é pior do que um teste quebrado, porque mente na direção errada: quem
rodar a suíte depois de uma mudança inocente vê oito vermelhos e vai procurar
o que quebrou no código. Este runner força UTF-8 e o problema deixa de existir.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
TIMEOUT_POR_TESTE = 180


def main() -> int:
    env = dict(os.environ)
    # A correção que sustenta este arquivo. Sem ela, oito testes morrem no print.
    env["PYTHONIOENCODING"] = "utf-8"
    env.setdefault("PYTHONUTF8", "1")

    arquivos = sorted(AQUI.glob("test_*.py"))
    if not arquivos:
        print("nenhum teste encontrado em", AQUI)
        return 1

    verdes: list[str] = []
    vermelhos: list[tuple[str, str]] = []
    inicio = time.monotonic()

    print("=" * 68)
    print(f"SUÍTE AUTOBROKERS — {len(arquivos)} arquivos")
    print("=" * 68)

    for arq in arquivos:
        nome = arq.name
        try:
            r = subprocess.run(
                [sys.executable, str(arq)],
                cwd=str(AQUI.parent),          # backend/ — como os testes esperam
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=TIMEOUT_POR_TESTE,
            )
            if r.returncode == 0:
                verdes.append(nome)
                print(f"  .  {nome}")
            else:
                # A última linha útil costuma ser o motivo.
                saida = (r.stdout or "") + (r.stderr or "")
                linhas = [l for l in saida.strip().split("\n") if l.strip()]
                motivo = linhas[-1][:150] if linhas else f"exit={r.returncode}"
                vermelhos.append((nome, motivo))
                print(f"  X  {nome}")
        except subprocess.TimeoutExpired:
            vermelhos.append((nome, f"estourou {TIMEOUT_POR_TESTE}s"))
            print(f"  T  {nome}  (timeout)")

    duracao = time.monotonic() - inicio
    print("\n" + "=" * 68)
    print(f"verdes: {len(verdes)}   vermelhos: {len(vermelhos)}   "
          f"tempo: {duracao:.0f}s")

    if vermelhos:
        print("\nVERMELHOS:")
        for nome, motivo in vermelhos:
            print(f"  {nome}")
            print(f"      {motivo}")
        return 1

    print("SUÍTE VERDE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
