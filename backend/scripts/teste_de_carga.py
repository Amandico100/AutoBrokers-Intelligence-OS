"""SPEC-062 §29 — teste de carga honesto.

O que ele mede, e o que NÃO mede
--------------------------------
Mede o que dá para medir **sem inventar tráfego de segurado**: quanto as
superfícies de leitura aguentam de concorrência, e onde elas começam a doer.

Não mede — e é deliberado — o caminho de atendimento. Disparar mil mensagens
falsas no WhatsApp da corretora para "testar carga" contamina o Atlas com rotas
que não existem, gasta token de verdade e, se algo escapar do modo observação,
manda mensagem para gente real. O caminho de atendimento se mede com o tráfego
real da Resulta, a partir de amanhã, pelos SLIs (§18).

Por que um teste de carga contra produção, e não contra um clone
----------------------------------------------------------------
Porque não existe clone, e fingir que existe seria pior. Todas as chamadas aqui
são **somente leitura** e usam endpoints públicos de saúde. Nenhuma escreve,
nenhuma autentica, nenhuma toca dado de corretora.

Uso
---
    python scripts/teste_de_carga.py                 # perfil leve
    python scripts/teste_de_carga.py --usuarios 20 --segundos 60
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
import time
from typing import Optional

API = ("https://autobrokers-intelligence-os-autobrokers-smith-api"
       ".golhpm.easypanel.host")
WEB = ("https://autobrokers-intelligence-os-autobrokers-smith-web"
       ".golhpm.easypanel.host")

# Só leitura, só endpoint que não expõe dado. `/health` bate em banco, Redis,
# Qdrant e MinIO — é o alvo mais honesto que existe sem autenticar.
ALVOS = [
    ("saude da API", f"{API}/health"),
    ("porta do painel", f"{WEB}/admin/login"),
]

# §29.4 — os limites que fazem o teste ter veredito em vez de tabela.
# Vêm do bom senso do produto, não de benchmark: acima de 3s o corretor
# acha que travou; acima de 1% de erro, alguém já viu tela quebrada.
TETO_P95_MS = 3000.0
TETO_ERRO_PCT = 1.0


async def _uma(cliente, url: str) -> tuple[float, bool]:
    inicio = time.perf_counter()
    try:
        r = await cliente.get(url, timeout=15.0)
        ok = r.status_code < 500
    except Exception:  # noqa: BLE001
        ok = False
    return (time.perf_counter() - inicio) * 1000, ok


async def _usuario(cliente, url: str, ate: float, amostras: list, erros: list):
    while time.perf_counter() < ate:
        ms, ok = await _uma(cliente, url)
        amostras.append(ms)
        if not ok:
            erros.append(1)
        await asyncio.sleep(0.05)  # não é DDoS no próprio produto


async def medir(nome: str, url: str, usuarios: int, segundos: int) -> dict:
    try:
        import httpx
    except ImportError:
        return {"alvo": nome, "erro": "httpx não instalado (pip install httpx)"}

    amostras: list[float] = []
    erros: list[int] = []
    ate = time.perf_counter() + segundos

    async with httpx.AsyncClient() as cliente:
        await asyncio.gather(*[
            _usuario(cliente, url, ate, amostras, erros)
            for _ in range(usuarios)
        ])

    if not amostras:
        return {"alvo": nome, "erro": "nenhuma amostra"}

    ordenado = sorted(amostras)
    p = lambda q: ordenado[min(len(ordenado) - 1, int(q * (len(ordenado) - 1)))]  # noqa: E731
    erro_pct = 100.0 * len(erros) / len(amostras)

    return {
        "alvo": nome,
        "requisicoes": len(amostras),
        "req_por_segundo": round(len(amostras) / segundos, 1),
        "p50_ms": round(p(0.50), 1),
        "p95_ms": round(p(0.95), 1),
        "p99_ms": round(p(0.99), 1),
        "erro_pct": round(erro_pct, 2),
        "passou": p(0.95) <= TETO_P95_MS and erro_pct <= TETO_ERRO_PCT,
    }


async def principal(usuarios: int, segundos: int) -> int:
    print("=" * 66)
    print(f"TESTE DE CARGA — {usuarios} usuários simultâneos por {segundos}s")
    print("=" * 66)
    print(f"tetos: p95 <= {TETO_P95_MS:.0f}ms · erro <= {TETO_ERRO_PCT}%\n")

    reprovou = False
    for nome, url in ALVOS:
        r = await medir(nome, url, usuarios, segundos)
        if r.get("erro"):
            print(f"  ??  {nome}: {r['erro']}")
            continue
        marca = "OK " if r["passou"] else "X  "
        print(f"  {marca} {nome}")
        print(f"      {r['requisicoes']} req ({r['req_por_segundo']}/s) · "
              f"p50 {r['p50_ms']}ms · p95 {r['p95_ms']}ms · "
              f"p99 {r['p99_ms']}ms · erro {r['erro_pct']}%")
        if not r["passou"]:
            reprovou = True

    print("\n" + "=" * 66)
    if reprovou:
        print("ALGUM ALVO PASSOU DO TETO — ver acima")
        return 1
    print("DENTRO DOS TETOS")
    print("\nObservação honesta: isto mede a superfície de LEITURA. O caminho")
    print("de atendimento se mede com o tráfego real, pelos SLIs (§18) —")
    print("simular conversa de segurado contaminaria o Atlas com rota falsa.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--usuarios", type=int, default=5)
    ap.add_argument("--segundos", type=int, default=20)
    a = ap.parse_args()
    sys.exit(asyncio.run(principal(max(1, a.usuarios), max(5, a.segundos))))
