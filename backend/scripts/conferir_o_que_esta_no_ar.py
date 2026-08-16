# -*- coding: utf-8 -*-
"""Responde, em uma linha, a pergunta que a P-189 deixou sem resposta:
**o processo no ar tem o código que está no meu repositório?**

    python backend/scripts/conferir_o_que_esta_no_ar.py

📊 Por que isto foi preciso: em 16/08/2026 disparei três deploys, os três
responderam HTTP 200 `Deploying...`, e não havia como saber o que tinha subido —
`build_sha` chega `"unknown"` porque o EasyPanel exporta a árvore sem o `.git`.
O único marcador era `build_time`, que diz QUANDO a imagem foi construída, não
O QUE tem dentro dela.

Este script compara a digital do `backend/portal_worker` do repositório com a que
o `/health` devolve. Não pede credencial, não escreve nada e não toca em portal
de seguradora.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "backend"))

from portal_worker.impressao import impressao_do_diretorio  # noqa: E402

HEALTH = ("https://autobrokers-intelligence-os-portal-worker"
          ".golhpm.easypanel.host/health")


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else HEALTH

    local, quantos = impressao_do_diretorio(RAIZ / "backend" / "portal_worker")
    print(f"repositorio : {local}  ({quantos} arquivos .py)")

    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            saude = json.loads(r.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"no ar       : NAO RESPONDEU ({type(e).__name__}: {e})")
        return 2

    remoto = str(saude.get("code_fingerprint") or "ausente")
    print(f"no ar       : {remoto}  ({saude.get('code_files')} arquivos .py)"
          f"  build_time={saude.get('build_time')}")

    if remoto == "ausente":
        print()
        print("VEREDITO: o /health no ar ainda NAO expoe code_fingerprint.")
        print("          Ou seja: a versao no ar e ANTERIOR a P-189. Isso ja e")
        print("          uma resposta -- o deploy que a inclui nao subiu.")
        return 1

    print()
    if remoto == local:
        print("VEREDITO: BATE. O codigo no ar e o do repositorio.")
        return 0
    print("VEREDITO: DIVERGE. O deploy nao trocou o codigo, por mais verde que o")
    print("          painel esteja -- ou ha trabalho nao commitado no repositorio.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
