"""Transcript cru -> transcript MASCARADO, com as funções de produção.

Por que este arquivo existe
---------------------------
A destilação das 6.118 conversas restantes da Resulta custaria ~US$ 80 de API
— dinheiro que o projeto não tem em 29/07/2026. A alternativa é fazer a parte
cara (ler a conversa e escrever o conhecimento) com o plano Max, por fora, e
devolver o resultado ao sistema pelo mesmo caminho de sempre.

Para isso o texto precisa sair do banco e ser lido por um subagente. E aí vale
a mesma regra de sempre: **PII nunca chega a um modelo**. Este script é o
portão. Ele não reimplementa nada — importa `sem_copias` e `templatize`, as
MESMAS funções que `_load_session_text_sync` usa em produção. Se o mascaramento
melhorar lá, melhora aqui no mesmo commit.

Reimplementar o mascaramento aqui seria criar um segundo motor de PII que
envelheceria em silêncio — exatamente o que o CLAUDE.md §5 proíbe.

Uso
---
    python mascarar.py < cru.json > mascarado.jsonl

Entrada: JSON com [{session_id, direction, msg_type, text, wa_timestamp}, ...]
Saída:   uma linha JSON por sessão: {"id": ..., "conversa": "CLIENTE: ..."}
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import types

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# O `app/__init__.py` real arrasta openai e pydantic_settings, que não existem
# na máquina do Founder. O templater e o `sem_copias` não dependem de nada —
# são carregados por caminho, sobre pacotes de fachada.
for _n, _p in (("app", ("app",)), ("app.services", ("app", "services")),
               ("app.services.atlas", ("app", "services", "atlas"))):
    if _n not in sys.modules:
        _m = types.ModuleType(_n)
        _m.__path__ = [os.path.join(RAIZ, *_p)]
        _m.__package__ = _n
        sys.modules[_n] = _m


def _carregar(nome: str):
    caminho = os.path.join(RAIZ, "app", "services", "atlas", f"{nome}.py")
    spec = importlib.util.spec_from_file_location(f"app.services.atlas.{nome}", caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"app.services.atlas.{nome}"] = mod
    spec.loader.exec_module(mod)
    return mod


templatize = _carregar("templater").templatize
sem_copias = _carregar("mensagem").sem_copias

# O mesmo teto de produção: acima disto a conversa é cortada, e o corte tem de
# ser idêntico ao que o destilador faria — senão o conhecimento extraído aqui
# seria diferente do extraído lá, sem ninguém saber qual dos dois está certo.
TETO = 7000


def transcript(eventos: list) -> str:
    linhas = []
    for e in sem_copias(eventos):
        quem = "ATENDENTE" if e.get("direction") == "out" else "CLIENTE"
        txt = str(e.get("text") or "").strip() or f"[{e.get('msg_type') or 'midia'}]"
        linhas.append(f"{quem}: {templatize(txt)}")
    return "\n".join(linhas)[:TETO]


def main() -> int:
    linhas = json.load(sys.stdin)
    por_sessao: dict = {}
    for e in linhas:
        por_sessao.setdefault(str(e.get("session_id")), []).append(e)

    escritas = curtas = 0
    for sid, eventos in por_sessao.items():
        texto = transcript(eventos)
        if len(texto) < 80:          # mesma regra do destilador: sessão sem conteúdo
            curtas += 1
            continue
        sys.stdout.write(json.dumps({"id": sid, "conversa": texto}, ensure_ascii=False) + "\n")
        escritas += 1
    print(f"[mascarar] {escritas} conversas · {curtas} curtas demais (puladas)",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
