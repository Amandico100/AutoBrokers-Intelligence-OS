# -*- coding: utf-8 -*-
"""A impressão digital do código que ESTE processo tem em disco.

## Por que isto existe (P-189)

📊 Medido em 16/08/2026: `/health` do portal-worker reportava
`build_sha: "unknown"` e o do smith-api, `git_commit: "nao-injetado"`. A SPEC-073
pediu "build/git SHA real e verificável" e o que existia **não era verificável**.

A causa é o estágio `gitinfo` do Dockerfile: ele lê `.git/HEAD` do contexto de
build. O EasyPanel exporta a árvore de arquivos, **sem o diretório `.git`** —
então a leitura falha e o SHA cai no literal `"unknown"`. Não é bug do
Dockerfile; é uma suposição sobre o contexto que o construtor não cumpre.

## Por que a saída não é "injetar o SHA no build"

Seria a resposta óbvia, e ela depende de configurar build-arg no painel do
EasyPanel — fora do repositório, invisível ao revisor e fácil de perder num
redeploy. Uma prova de versão que mora fora do código não é prova.

Esta função responde a pergunta operacional de verdade, que nunca foi "qual
commit?" e sim **"o processo no ar tem o código que eu escrevi?"**. Ela hasheia
os `.py` que o processo tem em disco AGORA. Não precisa de git, não precisa de
build-arg, e é reproduzível: dá para rodar a mesma função sobre o repositório e
comparar com o que `/health` devolve.

## A armadilha que precisa ser tratada

O repositório é editado no Windows (CRLF) e roda em contêiner Linux (LF). Hashear
bytes crus daria digitais diferentes para o **mesmo** código, e a comparação
acusaria divergência todo santo dia — um alarme que sempre toca é um alarme que
ninguém escuta. Por isso o `\\r` sai antes do hash.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, Optional, Tuple

# Calcular a cada `/health` seria desperdício, e o disco não muda sob o processo.
_CACHE: Optional[Tuple[str, int]] = None

IGNORAR_DIRETORIOS = {"__pycache__", ".pytest_cache", ".mypy_cache"}


def _hash_do_arquivo(caminho: Path) -> str:
    """SHA-256 do conteúdo, com fim de linha normalizado para LF."""
    dados = caminho.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(dados).hexdigest()


def impressao_do_diretorio(raiz: Path) -> Tuple[str, int]:
    """`(digital, quantos_arquivos)` para todos os `.py` sob `raiz`.

    Entram no hash o **caminho relativo** e o conteúdo de cada arquivo. O caminho
    importa: renomear um módulo muda o que o processo consegue importar, então
    tem de mudar a digital — mesmo que nenhum byte de conteúdo mude.
    """
    raiz = Path(raiz).resolve()
    arquivos = []
    for p in sorted(raiz.rglob("*.py")):
        if any(parte in IGNORAR_DIRETORIOS for parte in p.parts):
            continue
        if not p.is_file():
            continue
        arquivos.append(p)

    somador = hashlib.sha256()
    for p in arquivos:
        rel = p.relative_to(raiz).as_posix()
        somador.update(rel.encode("utf-8"))
        somador.update(b"\0")
        somador.update(_hash_do_arquivo(p).encode("ascii"))
        somador.update(b"\n")
    return somador.hexdigest()[:16], len(arquivos)


_CACHE_POR_RAIZ: Dict[str, Tuple[str, int]] = {}


def impressao_cacheada(raiz: Path) -> Tuple[str, int]:
    """`impressao_do_diretorio` memoizada por caminho.

    O `/health` do smith-api cobre 319 arquivos. Hashear tudo a cada chamada
    seria pagar, em toda checagem de saúde, por uma resposta que não muda
    enquanto o processo vive — e `/health` é justamente o endpoint que precisa
    responder rápido quando alguém está apurando uma queda.

    Nunca levanta: disco ilegível vira `("indisponivel", 0)`.
    """
    chave = str(Path(raiz).resolve())
    if chave not in _CACHE_POR_RAIZ:
        try:
            _CACHE_POR_RAIZ[chave] = impressao_do_diretorio(Path(raiz))
        except Exception:  # noqa: BLE001
            _CACHE_POR_RAIZ[chave] = ("indisponivel", 0)
    return _CACHE_POR_RAIZ[chave]


def impressao_do_processo() -> Tuple[str, int]:
    """A digital do pacote `portal_worker` deste processo. Cacheada.

    Nunca levanta: se o disco não puder ser lido, devolve `("indisponivel", 0)`.
    Um `/health` que quebra por causa do próprio marcador de versão seria pior do
    que não ter marcador.
    """
    global _CACHE
    if _CACHE is None:
        try:
            _CACHE = impressao_do_diretorio(Path(__file__).resolve().parent)
        except Exception:  # noqa: BLE001
            _CACHE = ("indisponivel", 0)
    return _CACHE
