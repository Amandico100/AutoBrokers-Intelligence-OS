# -*- coding: utf-8 -*-
"""Gera `app/data/nomes_por_sexo_ibge.json` — SPEC-133-A.1 F2 (D-133A1-02: o sexo pelo primeiro nome).

FONTE (pública e citável): IBGE, Censo Demográfico 2010, "Nomes no Brasil" — API de serviços de dados
    https://servicodados.ibge.gov.br/api/v2/censos/nomes/ranking?sexo=M|F[&decada=…][&localidade=<UF>]
    https://servicodados.ibge.gov.br/api/v2/censos/nomes/<nome1>|<nome2>|…?sexo=M|F
O ranking só devolve os 20 primeiros de cada recorte; por isso a lista de CANDIDATOS junta:
    ① o ranking nacional, ② o ranking de cada década (1930…2000) e ③ o de cada UF, nos dois sexos;
    ④ os prenomes de `app/data/prenomes_brasileiros.txt` (a lista do anonimizador, mesma fonte);
    ⑤ `EXTRAS` — nomes unissex conhecidos, para a tabela SABER que são ambíguos (sem eles caem em "fora da tabela",
       que dá o mesmo resultado — pergunta — mas a tabela não documentaria o porquê).
Para cada candidato, a frequência em CADA sexo vem da consulta por nome (soma das décadas). O IBGE só publica nomes
com 20+ ocorrências; um nome que a consulta de um sexo não devolve conta 0 naquele sexo.

Nada aqui é dado pessoal: são contagens agregadas do Censo. O arquivo é versionado; o canal só LÊ (offline).

    cd backend && .venv/Scripts/python.exe scripts/gerar_nomes_por_sexo.py
"""
from __future__ import annotations

import json
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://servicodados.ibge.gov.br/api/v2/censos/nomes"
RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "app" / "data" / "nomes_por_sexo_ibge.json"
PRENOMES = RAIZ / "app" / "data" / "prenomes_brasileiros.txt"
DECADAS = (1930, 1940, 1950, 1960, 1970, 1980, 1990, 2000)
#: códigos IBGE das 27 UFs
UFS = (11, 12, 13, 14, 15, 16, 17, 21, 22, 23, 24, 25, 26, 27, 28, 29, 31, 32, 33, 35, 41, 42, 43, 50, 51, 52, 53)
#: unissex conhecidos (a tabela os mede; a proporção é do IBGE, não desta lista)
EXTRAS = ("juraci", "jurandir", "darci", "darcy", "valdeci", "aldenir", "francis", "ariel", "noa", "eli", "elis",
          "dorival", "clemente", "jaci", "araci", "iraci", "dalvani", "adair", "ivani", "ivanir", "laci", "zeni",
          "deni", "cleni", "gerci", "nilsa", "nilson", "edir", "eneas", "alcione", "irani", "uiara", "joelma",
          "rosario", "cruz", "dores", "guadalupe", "jordan", "kim", "sasha", "yuri", "andrea", "dominique", "darlan",
          "vani", "valdir", "valdenir", "aldeci", "aldair", "luan", "lua", "ires", "jucelia", "juscelino", "ozeas",
          "renan", "cristian", "christian", "wellington", "pessoa", "mariana", "renata", "joana", "silvia", "jose",
          "carlos", "pedro")
LOTE = 40
PAUSA_S = 0.25


def normalizar(nome: str) -> str:
    t = unicodedata.normalize("NFKD", str(nome or ""))
    return "".join(c for c in t if not unicodedata.combining(c)).lower().strip()


def _get(url: str):
    for tentativa in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:     # noqa: S310 — URL fixa do IBGE
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            if tentativa == 3:
                raise
            print(f"  ...tentando de novo ({type(exc).__name__})", file=sys.stderr)
            time.sleep(2 * (tentativa + 1))
    return None


def _ranking(**params) -> list:
    dados = _get(f"{BASE}/ranking?{urllib.parse.urlencode(params)}") or []
    time.sleep(PAUSA_S)
    return [normalizar(x["nome"]) for bloco in dados for x in bloco.get("res", [])]


def candidatos() -> list:
    nomes = set()
    for sexo in ("M", "F"):
        nomes.update(_ranking(sexo=sexo))
        for d in DECADAS:
            nomes.update(_ranking(sexo=sexo, decada=d))
        for uf in UFS:
            nomes.update(_ranking(sexo=sexo, localidade=uf))
    for linha in PRENOMES.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#"):
            nomes.add(normalizar(linha))
    nomes.update(normalizar(n) for n in EXTRAS)
    return sorted(n for n in nomes if n.isalpha())


def frequencias(nomes: list, sexo: str) -> dict:
    total = {}
    for i in range(0, len(nomes), LOTE):
        lote = nomes[i:i + LOTE]
        url = f"{BASE}/{urllib.parse.quote('|'.join(lote), safe='|')}?sexo={sexo}"
        for item in _get(url) or []:
            total[normalizar(item["nome"])] = sum(int(r.get("frequencia") or 0) for r in item.get("res", []))
        time.sleep(PAUSA_S)
    return total


def main() -> int:
    nomes = candidatos()
    print(f"candidatos: {len(nomes)}")
    m, f = frequencias(nomes, "M"), frequencias(nomes, "F")
    tabela = {n: [m.get(n, 0), f.get(n, 0)] for n in nomes if m.get(n, 0) + f.get(n, 0) > 0}
    saida = {
        "fonte": "IBGE, Censo Demográfico 2010 — Nomes no Brasil (API servicodados.ibge.gov.br/api/v2/censos/nomes)",
        "coletado_em": datetime.now(timezone.utc).date().isoformat(),
        "comando": "cd backend && .venv/Scripts/python.exe scripts/gerar_nomes_por_sexo.py",
        "formato": "nome (sem acento, minúsculo) → [pessoas do sexo masculino, pessoas do sexo feminino]",
        "candidatos": len(nomes),
        "pessoas_cobertas": sum(a + b for a, b in tabela.values()),
        "nomes": dict(sorted(tabela.items())),
    }
    SAIDA.write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":"), indent=None) + "\n",
                     encoding="utf-8")
    print(f"nomes na tabela: {len(tabela)} - pessoas cobertas: {saida['pessoas_cobertas']} - {SAIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
