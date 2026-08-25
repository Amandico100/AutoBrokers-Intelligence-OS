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


# ---------------------------------------------------------------------------
# O DIARIO DA BATERIA — 🔴 o passo 2º do `PROTOCOLO-AUTOBROKERS-AAA.md` §10
# ---------------------------------------------------------------------------
# O protocolo manda consertar a bateria em três passos, nesta ordem:
#
#     1º  a trava      (o processo solto que muta a árvore compartilhada)
#     2º  🔴 MEDIR QUANTAS VEZES ela roda de fato numa SPEC
#     3º  só então os gates por nível
#
# ⚠️ **E o 2º nunca foi feito.** 📊 O custo POR RODADA está medido com três
# pontos (19m01 · 16m26 · 14m46 → 16m44 ±13%). O **número de rodadas** não:
# `9–14` é 💭 estimativa, e "13 commits × 16m44 = 3h37" é aritmética sobre um
# chute — 🔴 **commit não é rodada.** Um commit pode não rodar a bateria, e uma
# rodada pode não virar commit.
#
# É a `CLAUDE.md` §12.1 exatamente onde dói: um número 💭 ilustrativo citado
# como 📊 medido — e desta vez por quem escreveu a regra.
#
# Este arquivo faz UMA coisa: **toda rodada de pytest deixa uma linha.** Na
# próxima SPEC o 2º passo deixa de ser opinião, e o 3º passa a ser decidível.
#
# ⚠️ **Ele NUNCA pode quebrar a suíte.** Um diário que derruba a bateria que ele
# mede é pior que diário nenhum — por isso todo o corpo vive num `except`
# largo, e a falha dele é silenciosa de propósito.

_DIARIO = Path(__file__).resolve().parent.parent / ".diario-da-bateria.jsonl"
_COMECO: dict = {}


def pytest_sessionstart(session):  # noqa: D401
    """Guarda o instante e o alvo. Silencioso em qualquer erro."""
    try:
        import time

        _COMECO["t"] = time.time()
        # 🔴 O ALVO distingue bateria INTEIRA de rodada de um arquivo só — é
        # exatamente essa diferença que o 3º passo precisa para decidir.
        alvo = [a for a in getattr(session.config, "args", []) or []]
        _COMECO["alvo"] = " ".join(alvo) if alvo else "(tudo)"
    except Exception:
        pass


def pytest_sessionfinish(session, exitstatus):  # noqa: D401
    """Uma linha por rodada: quando, quanto, sobre o quê, e em que commit."""
    try:
        import json
        import os
        import subprocess
        import time
        from datetime import datetime, timezone

        if "t" not in _COMECO:
            return

        # 🔴 UMA COLETA NAO E UMA RODADA. Medido em 25/08: um
        # `pytest tests/ --collect-only` entrou no diario como rodada de 4,4s
        # com 595 "coletados" — e uma linha dessas na media destroi exatamente
        # o numero que este arquivo existe para produzir. `CLAUDE.md` §12.1: o
        # defeito nao e o numero errado, e o numero errado com marca de medido.
        if getattr(session.config.option, "collectonly", False):
            return

        segundos = round(time.time() - _COMECO["t"], 1)

        try:
            commit = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=5,
                cwd=str(Path(__file__).resolve().parent.parent),
            ).stdout.strip() or "?"
        except Exception:
            commit = "?"

        linha = {
            "quando": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "segundos": segundos,
            "alvo": _COMECO.get("alvo", "?"),
            "commit": commit,
            "saida": int(exitstatus),
            "coletados": getattr(session, "testscollected", None),
            "falhas": getattr(session, "testsfailed", None),
            # ⚠️ CI e máquina do executor têm relógios diferentes; sem isto as
            # duas populações somam e a média não descreve nenhuma das duas.
            "onde": "ci" if os.environ.get("CI") else "local",
        }
        with open(_DIARIO, "a", encoding="utf-8") as f:
            f.write(json.dumps(linha, ensure_ascii=False) + "\n")
    except Exception:
        # 🔴 De propósito. Ver o cabeçalho.
        pass
