# -*- coding: utf-8 -*-
"""🔴 Nenhum módulo pode usar um nome que ele não importou.

📊 02/09/2026 — a API de produção ficou **sete dias no chão** por uma linha:

```
File "/app/app/api/webhook.py", line 1571, in <module>
    mensagem: str) -> Dict[str, Any]:
NameError: name 'Dict' is not defined
```

O módulo importava só `Optional`. A anotação de retorno usava `Dict[str, Any]`.

```
main.py:36  →  from app.api.webhook import router
webhook.py  →  NameError
uvicorn     →  morre
EasyPanel   →  reinicia, e de novo, e de novo
```

## ⚠️ E TUDO estava verde

`py_compile` passa. `ast.parse` passa. `tsc` passa. `next build` passa. **A
bateria de 965 testes passa.** Porque `NameError` no import é erro de
**RUNTIME**, e nenhum gate deste projeto liga o servidor.

> É o `CLAUDE.md` §9.1 na forma mais pura — *"build verde não é prova de que a
> aplicação sobe"* — e desta vez custou uma semana de Espelho parado, com o
> `smith-web` respondendo 200 e escondendo a queda.

## 🔴 A sutileza que o guarda PRECISA saber

📊 `channel_state.py` **também** usa `Dict` sem importar — e **não quebra**.

A diferença é uma linha:

```
from __future__ import annotations
```

Com ela (PEP 563), **toda anotação vira texto** e não é avaliada no import.
Sem ela, a anotação é **código executado na hora**.

⛔ **Um guarda que ignorasse isso acusaria `channel_state.py` de um defeito que
ele não tem** — e guarda que acusa inocente ensina a ignorá-lo.

## O que este arquivo NÃO faz

⛔ Ele não importa os módulos de verdade. Importar `webhook.py` exige Supabase,
Redis e as env de produção — e um guarda que precisa da produção para rodar não
roda. **Ele resolve os nomes estaticamente, que é o que o Python faz no import.**
"""
from __future__ import annotations

import ast
import io
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(RAIZ, "app")

# 🔴 Os nomes de `typing` que aparecem em anotação e explodem se não importados.
NOMES_DE_TYPING = frozenset({
    "Dict", "List", "Optional", "Any", "Tuple", "Set", "Union", "Callable",
    "Iterable", "Sequence", "Mapping", "Type", "Literal", "TypedDict",
    "Awaitable", "AsyncIterator", "Iterator", "Coroutine", "NamedTuple",
})

OK = FAIL = 0


def certo(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  ok    %s" % rotulo)
    else:
        FAIL += 1
        print("  FALHA %s" % rotulo + ("\n        %s" % detalhe if detalhe else ""))


def _tem_future_annotations(arv: ast.Module) -> bool:
    """PEP 563: com isto, anotação vira texto e NÃO é avaliada no import."""
    for n in arv.body:
        if isinstance(n, ast.ImportFrom) and n.module == "__future__":
            if any(a.name == "annotations" for a in n.names):
                return True
    return False


def _nomes_definidos(arv: ast.Module) -> set:
    """Tudo que o módulo importa, define ou atribui — em qualquer nível."""
    definidos = set(dir(__builtins__)) if isinstance(__builtins__, type(sys)) else set()
    definidos |= set(vars(__builtins__)) if not isinstance(__builtins__, type(sys)) else set()
    for n in ast.walk(arv):
        if isinstance(n, ast.ImportFrom):
            for a in n.names:
                definidos.add(a.asname or a.name)
        elif isinstance(n, ast.Import):
            for a in n.names:
                definidos.add((a.asname or a.name).split(".")[0])
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            definidos.add(n.name)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            definidos.add(n.id)
        elif isinstance(n, ast.alias):
            definidos.add(a.asname or a.name if False else n.asname or n.name)
    return definidos


def _anotacoes_avaliadas(arv: ast.Module) -> set:
    """Os nomes de typing que o Python REALMENTE avalia no import.

    🔴 Só anotação conta. Um `Dict` dentro do corpo de uma função só explode
    quando a função é chamada — e aí não é o import que quebra.
    """
    usados = set()

    def colher(no):
        if no is None:
            return
        for x in ast.walk(no):
            if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load):
                if x.id in NOMES_DE_TYPING:
                    usados.add(x.id)

    for n in ast.walk(arv):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            colher(n.returns)
            for a in list(n.args.args) + list(n.args.kwonlyargs) + list(n.args.posonlyargs):
                colher(a.annotation)
            colher(n.args.vararg.annotation if n.args.vararg else None)
            colher(n.args.kwarg.annotation if n.args.kwarg else None)
        elif isinstance(n, ast.AnnAssign):
            colher(n.annotation)
    return usados


def main() -> int:
    print("\n[1] NENHUM MODULO USA NOME DE TYPING QUE NAO IMPORTOU")

    arquivos = []
    for raiz, _, arqs in os.walk(APP):
        for a in arqs:
            if a.endswith(".py"):
                arquivos.append(os.path.join(raiz, a))

    certo(len(arquivos) > 100,
          "achei %d arquivos .py em backend/app" % len(arquivos),
          "se o numero cair muito, a varredura quebrou e tudo abaixo passa "
          "por vacuidade")

    quebrados = []
    protegidos_por_future = 0
    for p in arquivos:
        try:
            arv = ast.parse(io.open(p, encoding="utf-8").read())
        except SyntaxError:
            continue
        faltando = _anotacoes_avaliadas(arv) - _nomes_definidos(arv)
        if not faltando:
            continue
        if _tem_future_annotations(arv):
            # ⚠️ PEP 563: a anotação virou texto. Não quebra o import.
            protegidos_por_future += 1
            continue
        quebrados.append((os.path.relpath(p, RAIZ), sorted(faltando)))

    certo(not quebrados,
          "nenhum modulo quebra no import por nome nao importado",
          "\n        ".join("%s  falta: %s" % (p, " · ".join(f))
                            for p, f in quebrados))

    print("\n  (📊 %d modulo(s) usam typing sem importar mas tem "
          "`from __future__ import annotations` — e por isso nao quebram)"
          % protegidos_por_future)

    # ------------------------------------------------------------------
    print("\n[2] LINHA DE CONTROLE -- o guarda CONSEGUE ficar vermelho?")
    # 🔴 Sem isto, um erro no colhedor faria [1] passar para sempre — que e
    #    exatamente a doenca de 02/09: tudo verde, produto no chao.

    doente = ast.parse("def f(x: str) -> Dict[str, Any]: return {}\n")
    faltam = _anotacoes_avaliadas(doente) - _nomes_definidos(doente)
    certo(faltam == {"Dict", "Any"},
          "o colhedor ACHA `Dict` e `Any` num modulo que nao os importa",
          "achou: %s" % (sorted(faltam) or "nada"))

    curado = ast.parse("from typing import Any, Dict\n"
                       "def f(x: str) -> Dict[str, Any]: return {}\n")
    certo(not (_anotacoes_avaliadas(curado) - _nomes_definidos(curado)),
          "e NAO acha nada quando o import esta la",
          "um casador que casa com tudo aprova qualquer coisa")

    com_future = ast.parse("from __future__ import annotations\n"
                           "def f(x: str) -> Dict[str, Any]: return {}\n")
    certo(_tem_future_annotations(com_future),
          "o guarda RECONHECE o `from __future__ import annotations`",
          "sem isto ele acusaria channel_state.py de um defeito que ele nao tem")

    sem_future = ast.parse("def f() -> None: pass\n")
    certo(not _tem_future_annotations(sem_future),
          "e nao o inventa onde nao existe")

    # 🔴 e o corpo da funcao NAO conta: `Dict` usado dentro do corpo so explode
    #    quando alguem chama, e ai nao e o import que cai.
    so_no_corpo = ast.parse("def f():\n    d = Dict\n    return d\n")
    certo(not _anotacoes_avaliadas(so_no_corpo),
          "uso dentro do CORPO nao e contado — so anotacao quebra o import")

    print("\n  %d ok, %d falhas" % (OK, FAIL))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
