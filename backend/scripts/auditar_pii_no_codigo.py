# -*- coding: utf-8 -*-
"""🔴 PII escrita À MÃO no CÓDIGO — que é onde o mascarador não chega.

O corpus é mascarado, e há guarda para isso (`test_o_corpus_nao_vaza_pii`,
📊 20 asserções verdes). **Comentário e fixture não passam pelo mascarador.**
Quando alguém transcreve uma tela real para explicar um passo, o dado do
segurado entra no repositório por uma porta que nenhum guarda vigiava.

📊 Medido em 23/08/2026, varrendo `git ls-files`. A conta se moveu duas vezes
naquele dia, e as duas merecem estar escritas:

```
166  a primeira varredura, sem filtro estrutural
 85  com o filtro -- e ele engolia placa REAL (ver `_e_sintetico`)
101  com o filtro corrigido: a medida honesta
 89  depois da limpeza desta SPEC -- 12 identificadores saíram
```

⚠️ Dos 89 que restam, boa parte NÃO é dado de pessoa: número PUBLICADO de
seguradora (`0800`, central de atendimento) tem forma de telefone e é endereço
comercial. **A varredura completa depende de autorização** e está no
`CHANGE-ADDENDA` como ESSENCIAL: ela cruza dez SPECs e mexe em fixture que
outros guardas comparam entre si.

⚠️ **Este script NUNCA imprime o valor inteiro.** Ele imprime a forma e o local:
presença/ausência, como manda o CLAUDE.md §13.3. Auditar vazamento imprimindo o
vazamento é repetir o vazamento com mais leitores.
"""
from __future__ import annotations

import argparse
import collections
import io
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(RAIZ)

TELEFONE = re.compile(r"\+?55[\s\-]*\(?\d{2}\)?[\s\-]*9?\d{4}[-\s]?\d{4}")
CPF = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
PLACA = re.compile(r"\b[A-Z]{3}[-\s]?\d[A-Z0-9]\d{2}\b")

# ⚠️ Prefixos que a regex de placa casa por acidente — `URA 2026`, `CPF 1234`.
_FALSO_POSITIVO = re.compile(r"^(URA|CPF|CNPJ|SPEC|LGPD|API|ADR|RFC)\b")


def _e_sintetico(valor: str) -> bool:
    """Valor cuja FORMA já anuncia que é inventado.

    🔴 O critério é estrutural, não uma lista de exceções que cresce: dígito ou
    letra repetida em bloco (`AAA1111`, `5547999999999`, `111.111.111-11`) e as
    sequências canônicas de exemplo. Uma lista de exceções seria uma porta para
    carimbar como sintético um valor real que incomoda.
    """
    if _FALSO_POSITIVO.match(valor):
        return True
    # 🔴 O separador sai ANTES de comparar. `ABC-1D23` e `ABC 1D23` sao o mesmo
    #    exemplo canonico que `ABC1D23`, e a primeira redacao so reconhecia a
    #    forma colada -- acusava de PII o proprio exemplo que o repo usa para
    #    NAO usar PII.
    _limpo = valor.upper().replace("-", "").replace(" ", "")
    if _limpo in {"ABC1D23", "ABC1234", "AAA1111", "BBB2222", "CCC3333",
                  "ZZZ9999", "QQQ1111", "XXX0000", "AAA1231", "BBB1244"}:
        return True
    # ⚠️ Codigo de regra de linter (`# noqa: PLC0415`) tem a forma de placa.
    if re.match(r"^(PLC|PLR|PLW|ARG|ANN|ERA|TRY|SIM|RUF)\d", valor.upper()):
        return True
    so_digitos = re.sub(r"\D", "", valor)
    if so_digitos:
        # 📊 corrida de 4+ dígitos iguais: `5547999999999`, `111.111.111-11`
        if re.search(r"(\d)\1{3,}", so_digitos):
            return True
        # ⚠️ "poucos dígitos distintos" só vale para valor LONGO (telefone, CPF).
        #    🔴 A primeira redação aplicava a regra a tudo e engolia uma placa
        #    REAL de forma `LLLDLDD` cujos dígitos eram `9`, `5` e `9`: dois
        #    distintos. Placa tem 4 dígitos; repetir um é comum. O filtro
        #    carimbava de sintético exatamente o tipo de dado que este script
        #    existe para achar — e a correção subiu a contagem de 85 para 101.
        if len(so_digitos) >= 11 and len(set(so_digitos)) <= 3:
            return True
    if re.match(r"^([A-Z])\1{2}", valor.upper()):   # AAA…, ZZZ…
        return True
    return False


def _forma(valor: str) -> str:
    """A FORMA do valor — nunca o valor. `AAA9A59` → `LLLDLDD`."""
    return "".join("D" if c.isdigit() else "L" if c.isalpha() else "."
                   for c in valor)


def _sombra(valor: str) -> str:
    """Sombra estável e curta para contar sem revelar."""
    import hashlib
    return hashlib.sha256(valor.encode()).hexdigest()[:8]


def varrer(prefixos=()):
    arquivos = subprocess.run(["git", "ls-files"], cwd=REPO,
                              capture_output=True, text=True).stdout.split()
    achados = collections.defaultdict(set)     # sombra -> {arquivo}
    formas = {}
    for f in arquivos:
        if not f.endswith((".py", ".md", ".ts", ".tsx")):
            continue
        if prefixos and not any(f.startswith(p) for p in prefixos):
            continue
        p = os.path.join(REPO, f)
        if not os.path.isfile(p):
            continue
        txt = io.open(p, encoding="utf-8", errors="replace").read()
        for rx, tipo in ((TELEFONE, "telefone"), (CPF, "cpf"), (PLACA, "placa")):
            for m in rx.finditer(txt):
                v = m.group(0)
                if _e_sintetico(v):
                    continue
                s = f"{tipo}:{_sombra(v)}"
                achados[s].add(f)
                formas[s] = _forma(v)
    return achados, formas


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--em", action="append", default=[],
                    help="limita a varredura a prefixos de caminho")
    a = ap.parse_args()
    achados, formas = varrer(tuple(a.em))
    print("=" * 74)
    print("PII ESCRITA A MAO NO CODIGO")
    print("=" * 74)
    if a.em:
        print("  escopo:", ", ".join(a.em))
    print(f"  identificadores distintos com forma real: {len(achados)}")
    print(f"  arquivos atingidos: {len({f for s in achados.values() for f in s})}")
    print()
    for s, onde in sorted(achados.items(), key=lambda kv: -len(kv[1]))[:25]:
        print(f"  {s}  forma={formas[s]}  x{len(onde)} arquivo(s)")
        print(f"      {sorted(onde)[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
