"""Mede o que uma republicacao faz com o lastro das cartas de acervo.

    python backend/scripts/destilacao_max/medir_o_lastro.py

SOMENTE LEITURA. Nao escreve no banco, nao escreve no Qdrant, nao gasta OpenAI.

POR QUE ISTO EXISTE
===================
📊 O conserto do BLOCO 0 da SPEC-072 foi justificado com cinco numeros — 5.394
cartas de acervo, 5.337 reescritas sem lastro, 57 recusadas, todas da HDI, todas
por `{CNPJ}`. Eles sairam de um script que morava so no `%TEMP%` de uma sessao.

O `pedacos/README.md` ja tinha escrito a licao, e ela vale aqui:

> **Numero medido sem base de prova preservada vira folclore no lote seguinte.**

E a CLAUDE.md §12.1 exige que 📊 traga "data, fonte e a query/comando que
produziu o numero". Um numero em comentario de codigo, sem o comando ao lado,
nao e citavel — nem quando esta certo. Este arquivo E o comando.

O QUE ELE MEDE
==============
Roda a rede de PII REAL (`curadoria_cartas.veredito_de_pii`, nao uma
reimplementacao) sobre as cartas de acervo publicadas, nos DOIS modos:

    documento_publico=False   o que rodava antes do conserto, porque o `select`
                              de `_ler_publicadas` nao pedia `source_unit_id`
    documento_publico=True    o que roda agora

A diferenca entre os dois e a regressao silenciosa que o conserto fechou.

⚠️ LINHA DE CONTROLE (CLAUDE.md §9.2): as duas medicoes rodam sobre O MESMO
conjunto de cartas, mudando UM fator. Sem isso, uma diferenca poderia vir de
qualquer outra coisa.
"""

from __future__ import annotations

import collections
import importlib.util
import json
import os
import sys
import types
import urllib.parse
import urllib.request
from pathlib import Path

AQUI = Path(__file__).resolve()
BACKEND = AQUI.parents[2]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _veredito_de_pii():
    """A regua real, carregada sem arrastar `openai` pelo `app/__init__.py`.

    Mesmo mecanismo dos testes da casa (`test_a_regua_da_carta_e_uma_so.py`):
    pacotes de fachada + `importlib`. Reimplementar a rede de PII aqui daria um
    numero que nao e o do produto — que e exatamente o erro que este arquivo
    existe para nao repetir.
    """
    for nome, partes in (("app", ("app",)),
                         ("app.services", ("app", "services")),
                         ("app.services.atlas", ("app", "services", "atlas"))):
        if nome not in sys.modules:
            mod = types.ModuleType(nome)
            mod.__path__ = [str(BACKEND.joinpath(*partes))]
            mod.__package__ = nome
            sys.modules[nome] = mod

    def carregar(nome, *partes):
        spec = importlib.util.spec_from_file_location(
            nome, str(BACKEND.joinpath(*partes)))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[nome] = mod
        spec.loader.exec_module(mod)
        return mod

    carregar("app.services.atlas.templater", "app", "services", "atlas", "templater.py")
    return carregar("app.services.curadoria_cartas",
                    "app", "services", "curadoria_cartas.py").veredito_de_pii


def _rest(url: str, key: str, caminho: str, *, contar: bool = False):
    req = urllib.request.Request(f"{url}/rest/v1/{caminho}", method="GET")
    req.add_header("apikey", key)
    req.add_header("Authorization", f"Bearer {key}")
    if contar:
        req.add_header("Prefer", "count=exact")
        req.add_header("Range", "0-0")
    with urllib.request.urlopen(req, timeout=180) as r:
        corpo = r.read().decode("utf-8", "replace")
        faixa = r.headers.get("Content-Range") or ""
    total = faixa.split("/")[-1]
    return corpo, (int(total) if total.isdigit() else None)


def main() -> int:
    sys.path.insert(0, str(AQUI.parent))
    from exportar import _credenciais  # noqa: E402 — vizinho, nao pacote

    url, key = _credenciais()
    veredito_de_pii = _veredito_de_pii()

    print("=" * 74)
    print("O LASTRO DAS CARTAS DE ACERVO — medicao somente leitura")
    print("=" * 74)

    # ── o universo, com o status DECLARADO ──────────────────────────────────
    # `superseded` NAO esta no indice. Conta-lo como RAG ja inflou tres
    # medicoes desta SPEC — por isso o filtro aparece em toda linha.
    print("\nGET /rest/v1/knowledge_cards?select=id&status=eq.published"
          "&source_unit_id=not.is.null   Prefer: count=exact")
    _, n_acervo = _rest(url, key,
                        "knowledge_cards?select=id&status=eq.published"
                        "&source_unit_id=not.is.null", contar=True)
    print(f"  cartas de ACERVO publicadas ......... {n_acervo:>6,d}")

    # ── a populacao, paginada ate o fim ─────────────────────────────────────
    # ⚠️ `limit=1000` sem laco devolve o COMECO da tabela, nao uma amostra.
    print("\nGET ...&select=id,card_text,insurer_key,source_unit_id"
          "&order=id.asc&limit=1000&offset=N   (ate o fim)")
    cartas, inicio = [], 0
    while True:
        corpo, _ = _rest(url, key,
                         "knowledge_cards?select=id,card_text,insurer_key,"
                         "source_unit_id&status=eq.published"
                         f"&source_unit_id=not.is.null&order=id.asc"
                         f"&limit=1000&offset={inicio}")
        lote = json.loads(corpo)
        cartas.extend(lote)
        if len(lote) < 1000:
            break
        inicio += 1000
    print(f"  lidas ............................... {len(cartas):>6,d}")
    if len(cartas) != n_acervo:
        print(f"  ⚠️ POPULACAO INCOMPLETA: {len(cartas)} != {n_acervo}. Nao cite estes numeros.")
        return 1
    print("  ✅ populacao completa conferida")

    # ── os dois modos, mesmo conjunto, UM fator ─────────────────────────────
    apertado, correto = [], []
    for c in cartas:
        texto = c.get("card_text") or ""
        if veredito_de_pii(texto, documento_publico=False)[1]:
            apertado.append(c)
        if veredito_de_pii(texto, documento_publico=True)[1]:
            correto.append(c)

    print("\n" + "=" * 74)
    print("A REGRESSAO QUE O SELECT INCOMPLETO CAUSAVA")
    print("=" * 74)
    print("  publish_card_sync:571 -> documento_publico=bool(card['source_unit_id'])")
    print("  e o select de _ler_publicadas nao pedia a coluna => sempre False.\n")
    print(f"  RECUSADAS com documento_publico=False (antes) .. {len(apertado):>5,d}")
    print(f"  RECUSADAS com documento_publico=True  (agora) .. {len(correto):>5,d}")
    print(f"  >>> regressao silenciosa ....................... {len(apertado) - len(correto):>5,d}")
    print(f"  >>> reescritas sem unit_id e sem faceta ........ {len(cartas) - len(apertado):>5,d}")

    if apertado:
        seg = collections.Counter((c.get("insurer_key") or "<sem>") for c in apertado)
        marcas = collections.Counter(
            m for c in apertado
            for m in veredito_de_pii(c.get("card_text") or "",
                                     documento_publico=False)[1])
        print(f"\n  por seguradora ....... {dict(seg.most_common())}")
        print(f"  marcas que reprovam .. {dict(marcas.most_common())}")
        exemplo = apertado[0]
        print("\n  --- uma delas, para ver a causa ---")
        print(f"    unit_id: {exemplo.get('source_unit_id')}")
        print(f"    texto:   {(exemplo.get('card_text') or '')[:160]}")
        print("\n  ⚠️ Se as marcas forem `{CNPJ}` e o texto trouxer um numero de")
        print("     PROCESSO SUSEP, e este o caso: o processo so parece CNPJ para")
        print("     quem nao sabe que o documento e publico.")

    print("\n" + "=" * 74)
    print("Nada foi escrito. Nenhum segredo impresso.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
