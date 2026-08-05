"""Confere o que o destilador escreveu, ANTES de qualquer coisa tocar o banco.

Por que este script existe
--------------------------
O subagente é bom e ainda assim é um modelo escrevendo JSON à mão, 70 linhas
seguidas. Um `id` trocado grava conhecimento na conversa errada; um campo com
nome de pessoa atravessa o portão de PII que o `aplicar.py` só checa por
regex determinística; um arquivo com 68 linhas em vez de 70 perde duas
conversas em silêncio — e elas voltam à fila para sempre, porque `distilled`
nunca é escrito.

Nenhum desses erros aparece no `aplicar.py`: ele grava o que recebe.

O QUE ESTE SCRIPT NÃO FAZ
-------------------------
Não conserta. Ele reprova e diz por quê. Consertar automaticamente esconderia
a causa — e a causa é o prompt, não a linha.

Uso
---
    python validar.py pacotes/pacote_002.destilado.jsonl [outro ...]

Sai 0 se TODOS passarem. Sai 1 na primeira reprovação, com o motivo.
"""

from __future__ import annotations

import json
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")

TIPOS = {"assistencia", "sinistro", "apolice", "renovacao", "cobranca", "outro"}
RAMOS = {"auto", "residencial", "vida", "outro"}

# PII que o templatize do sistema NÃO pega, porque não tem forma fixa.
# Nome de pessoa é o caso perigoso e é procurado pelo varrer_nomes.py; aqui
# pegamos o que tem forma: número solto longo, CPF/CNPJ escrito, placa, e-mail,
# e valor em reais — todos proibidos pelo briefing em QUALQUER campo.
SUSPEITOS = [
    (re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), "CPF"),
    (re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"), "CNPJ"),
    (re.compile(r"\b[A-Z]{3}-?\d[A-Z0-9]\d{2}\b"), "placa"),
    (re.compile(r"\b\d{4,5}-?\d{4}\b"), "telefone"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "e-mail"),
    (re.compile(r"R\$\s?\d"), "valor em reais"),
    (re.compile(r"\b\d{9,}\b"), "número longo (apólice/protocolo?)"),
]

LISTAS = ("resumo_conduta", "perguntas_na_ordem", "fatos_reutilizaveis", "flags")


def _ids_da_entrada(destilado: str) -> list:
    entrada = destilado.replace(".destilado.jsonl", ".jsonl")
    if not os.path.isfile(entrada):
        return []
    ids = []
    with open(entrada, encoding="utf-8") as fh:
        for linha in fh:
            linha = linha.strip()
            if linha:
                try:
                    ids.append(str(json.loads(linha).get("id") or ""))
                except json.JSONDecodeError:
                    pass
    return ids


def validar(caminho: str) -> list:
    """Devolve a lista de problemas. Lista vazia = passou."""
    problemas = []
    if not os.path.isfile(caminho):
        return [f"arquivo não existe: {caminho}"]

    esperados = _ids_da_entrada(caminho)
    vistos = []
    fatos = 0

    with open(caminho, encoding="utf-8") as fh:
        for n, linha in enumerate(fh, 1):
            linha = linha.strip()
            if not linha:
                continue
            if linha.startswith("```") or linha.startswith("["):
                problemas.append(f"linha {n}: não é JSONL puro (cerca de código ou array)")
                continue
            try:
                d = json.loads(linha)
            except json.JSONDecodeError as e:
                problemas.append(f"linha {n}: JSON inválido — {e}")
                continue

            sid = str(d.get("id") or "")
            if not UUID.match(sid):
                problemas.append(f"linha {n}: id não é uuid ({sid[:20]!r})")
                continue
            vistos.append(sid)

            if d.get("tipo") not in TIPOS:
                problemas.append(f"linha {n}: tipo inválido {d.get('tipo')!r}")
            if d.get("ramo") not in RAMOS:
                problemas.append(f"linha {n}: ramo inválido {d.get('ramo')!r}")

            score = d.get("score")
            if not isinstance(score, int) or not 0 <= score <= 100:
                problemas.append(f"linha {n}: score inválido {score!r}")

            for campo in LISTAS:
                v = d.get(campo, [])
                if not isinstance(v, list):
                    problemas.append(f"linha {n}: {campo} não é lista")
                    continue
                for item in v:
                    if not isinstance(item, str):
                        problemas.append(f"linha {n}: {campo} tem item não-texto")
                        continue
                    for rx, nome in SUSPEITOS:
                        if rx.search(item):
                            problemas.append(
                                f"linha {n}: {campo} parece conter {nome} — "
                                f"{item[:60]!r}")
                            break

            fatos += len(d.get("fatos_reutilizaveis") or [])

    # Cobertura: toda conversa da entrada tem de ter saída, e nenhuma a mais.
    if esperados:
        faltando = [i for i in esperados if i not in set(vistos)]
        sobrando = [i for i in vistos if i not in set(esperados)]
        if faltando:
            problemas.append(f"{len(faltando)} conversas SEM saída (ex.: {faltando[0]})")
        if sobrando:
            problemas.append(f"{len(sobrando)} ids que não estão na entrada (ex.: {sobrando[0]})")
    else:
        problemas.append("não achei o arquivo de entrada para conferir cobertura")

    dup = len(vistos) - len(set(vistos))
    if dup:
        problemas.append(f"{dup} ids repetidos na saída")

    if not problemas:
        print(f"[validar] OK  {os.path.basename(caminho)}: "
              f"{len(vistos)} conversas · {fatos} fatos", file=sys.stderr)
    return problemas


def main() -> int:
    if len(sys.argv) < 2:
        print("uso: validar.py <destilado.jsonl> [...]", file=sys.stderr)
        return 2
    ruim = 0
    for caminho in sys.argv[1:]:
        problemas = validar(caminho)
        if problemas:
            ruim += 1
            print(f"[validar] REPROVADO  {os.path.basename(caminho)}", file=sys.stderr)
            for p in problemas[:20]:
                print(f"          · {p}", file=sys.stderr)
            if len(problemas) > 20:
                print(f"          · (+{len(problemas)-20} outros)", file=sys.stderr)
    return 1 if ruim else 0


if __name__ == "__main__":
    sys.exit(main())
