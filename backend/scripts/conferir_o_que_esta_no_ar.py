# -*- coding: utf-8 -*-
"""Responde, em duas linhas, a pergunta que a P-189 deixou sem resposta:
**o processo no ar tem o código que está no meu repositório?**

    python backend/scripts/conferir_o_que_esta_no_ar.py

📊 Por que isto foi preciso: em 16/08/2026 disparei três deploys, os três
responderam HTTP 200 `Deploying...`, e não havia como saber o que tinha subido —
`build_sha` chega `"unknown"` e `git_commit` chega `"nao-injetado"`, porque o
EasyPanel exporta a árvore sem o `.git`. O único marcador restante era
`build_time`, que diz QUANDO a imagem foi construída, não O QUE tem dentro dela.

Compara a digital do código no repositório com a que cada `/health` devolve.
Não pede credencial, não escreve nada e não toca em portal de seguradora.

Saída: `0` só quando TODOS os serviços conferidos batem.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "backend"))

from portal_worker.impressao import impressao_do_diretorio  # noqa: E402

BASE = "https://autobrokers-intelligence-os"
SERVICOS = (
    # (nome, url do /health, pasta que a imagem carrega, onde a digital aparece)
    ("portal-worker", f"{BASE}-portal-worker.golhpm.easypanel.host/health",
     "backend/portal_worker", ()),
    ("smith-api", f"{BASE}-autobrokers-smith-api.golhpm.easypanel.host/health",
     "backend/app", ("codigo",)),
)


def _cavar(d: dict, caminho: tuple) -> dict:
    for parte in caminho:
        d = (d or {}).get(parte) or {}
    return d or {}


def conferir(nome: str, url: str, pasta: str, caminho: tuple) -> bool:
    local, quantos = impressao_do_diretorio(RAIZ / pasta)
    print(f"\n{nome}")
    print(f"  repositorio : {local}  ({quantos} arquivos .py em {pasta})")

    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            saude = json.loads(r.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"  no ar       : NAO RESPONDEU ({type(e).__name__})")
        return False

    bloco = _cavar(saude, caminho) if caminho else saude
    remoto = str(bloco.get("code_fingerprint") or "ausente")
    extra = saude.get("build_time") or saude.get("timestamp") or ""
    print(f"  no ar       : {remoto}  ({bloco.get('code_files')} arquivos)  {extra}")

    if remoto == "ausente":
        print("  VEREDITO    : o /health no ar ainda NAO expoe a digital -- ou")
        print("                seja, a versao no ar e ANTERIOR a P-189.")
        return False
    if remoto == local:
        print("  VEREDITO    : BATE.")
        return True
    print("  VEREDITO    : DIVERGE. O deploy nao trocou o codigo, por mais verde")
    print("                que o painel esteja -- ou ha trabalho nao commitado.")
    return False


def main() -> int:
    alvo = sys.argv[1] if len(sys.argv) > 1 else ""
    servicos = [s for s in SERVICOS if not alvo or s[0] == alvo]
    if not servicos:
        print(f"servico desconhecido: {alvo}")
        return 2
    todos = [conferir(*s) for s in servicos]
    print()
    print("=" * 60)
    print("TODOS BATEM" if all(todos) else "HA DIVERGENCIA")
    print("=" * 60)
    return 0 if all(todos) else 1


if __name__ == "__main__":
    raise SystemExit(main())
