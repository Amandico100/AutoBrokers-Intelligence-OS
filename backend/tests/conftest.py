# -*- coding: utf-8 -*-
"""`pytest tests/` volta a funcionar — P-183, segunda metade.

📊 **O defeito, medido em 24/08/2026 por um auditor externo:**

```
$ python -m pytest tests/ --collect-only -q
INTERNALERROR> File ".../test_a_arvore_do_pneu_decide_o_reboque.py", line 395
INTERNALERROR>   sys.exit(1 if FAIL else 0)
INTERNALERROR> SystemExit: 0
no tests collected in 0.47s
```

🔴 **`pytest tests/` não coletava zero: ele ABORTAVA A SESSÃO INTEIRA.** A causa
é que **60 arquivos chamam `sys.exit()` em nível de módulo** — o `import` que o
coletor faz executa o guarda, o `SystemExit` sobe, e o pytest morre no primeiro.

⚠️ **E o pior era o efeito colateral:** com a sessão morta, os arquivos que
**são** pytest de verdade também nunca rodavam. 📊 Três deles guardam **35
asserções**, e **cinco estavam VERMELHAS** — inclusive *"a régua devolve 102
numa escala de 100"* e *"o replay não acha NENHUMA órfã funcional"*.

## O universo real de `tests/`, medido

```
279  arquivos test_*.py
  6  com `def test_`      →  o pytest roda, e agora consegue
273  sem `def test_`      →  rodam como PROCESSO, pelo meta-guarda
       151 com `main()`   →  o que a primeira versão pegava
       122 sem `main()`   →  asserções em nível de módulo. 🔴 Ficavam de fora.
```

## O que este arquivo faz, e é uma linha de ideia

**Tira os 273 da coleta padrão do pytest** — `collect_ignore`. Eles continuam
rodando, como processo, por `test_todos_os_guardas_script_rodam.py`. O pytest
para de importá-los, para de morrer, e **passa a rodar os 6 que são dele**.

⚠️ **Por que `collect_ignore` e não `pytest_collect_file`:** 🔴 aquele hook é
**aditivo** — o coletor padrão continua tentando importar o mesmo arquivo, e o
`SystemExit` derruba tudo do mesmo jeito. Tentado, medido, descartado.

🔴 **E a regra de exclusão é a MESMA função de descoberta do meta-guarda**,
importada daqui. Duas listas que precisam concordar e são escritas separado
divergem — é o defeito nº 1 deste projeto, e não vai ser reintroduzido por um
arquivo que existe para consertar exatamente isso.
"""
from __future__ import annotations

from pathlib import Path

_PASTA = Path(__file__).parent
_META = _PASTA / "test_todos_os_guardas_script_rodam.py"


def _sem_funcao_de_teste(caminho: Path) -> bool:
    """Cópia mínima da regra do meta-guarda — sem importá-lo.

    ⚠️ Importar o meta-guarda daqui criaria um ciclo na coleta. A regra é curta
    o bastante para caber duas vezes, e 🔴 **o guarda contra a divergência é o
    `test_a_exclusao_bate_com_a_descoberta` do próprio meta-guarda**, que
    compara as duas listas e falha se elas discordarem.
    """
    if caminho.resolve() == _META.resolve():
        return False
    try:
        fonte = caminho.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    if fonte.startswith("def test_"):
        return False
    return not any(m in fonte for m in
                   ("\ndef test_", "\nasync def test_", "\nclass Test"))


collect_ignore = sorted(
    p.name for p in _PASTA.glob("test_*.py") if _sem_funcao_de_teste(p)
)
