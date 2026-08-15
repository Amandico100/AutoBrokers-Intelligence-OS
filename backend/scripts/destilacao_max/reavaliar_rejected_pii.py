# -*- coding: utf-8 -*-
"""Reavalia `rejected_pii` no eixo certo: dado pessoal, não vocabulário.

O QUE ACONTECEU
===============
A regra era `rejected_pii` quando `templatize(texto) != texto` — ou seja,
**qualquer coisa que o mascarador encostasse** derrubava a carta.

📊 Medido em 15/08/2026 sobre as 320 cartas em `rejected_pii`: ZERO têm CPF,
CNPJ, telefone, placa, e-mail ou nome de pessoa. E contra o `templatize` de
hoje, com `rotulo_de_campo=False`, **315 das 320 não são tocadas por regra
nenhuma** — as regras que as derrubaram já foram consertadas desde então, e a
rejeição continuou de pé sozinha porque foi gravada uma vez e nunca reavaliada.

📊 As 5 que ainda são tocadas são o retrato do defeito:

    "celular com DDD confirmado por botão"      → "celular com {NOME}"
    "ou do WhatsApp que pediu a assistência"    → "ou do {NOME} que pediu"
    "o telefone de quem está no local ANTES do" → "no local {NOME} do"
    "o atendimento tem de ser feito pelo 0800." → "feito pelo {SEGREDO}."

`DDD`, `WhatsApp`, `ANTES` e um `0800` — vocabulário de contexto, não dado de
ninguém. O `{SEGREDO}` é a regra que marca qualquer número de 4+ dígitos numa
linha que fale "código de acesso": ela comeu o telefone 0800 da central, que é
justamente o conhecimento da carta.

⚠️ POR QUE ESTE SCRIPT NÃO REESCREVE O TEXTO
=============================================
`veredito_de_pii` devolve o texto MASCARADO, e a INGESTÃO grava o mascarado —
lá é obrigatório, porque no momento da escrita ninguém sabe se aquele `{NOME}`
era uma pessoa ou a palavra "WhatsApp".

Aqui é diferente: estas 320 já foram medidas uma a uma e **nenhuma tem PII**.
Gravar o mascarado nas 5 trocaria `DDD` por `{NOME}` e `0800` por `{SEGREDO}` —
destruiria conhecimento medido para proteger contra um risco medido como
inexistente. O texto fica; o que muda é o veredito.

📊 A conta que decide: 5 cartas danificadas contra 0 dados pessoais evitados.

Se alguma carta trouxesse identificador de verdade, ela CONTINUARIA
`rejected_pii` — o script não tem caminho para promovê-la, e o relatório
mostra a contagem separada.

A ESCRITA VAI EM LOTE DE 200
============================
⚠️ Uma requisição por carta mata a conexão HTTP/2 no stream ~19.999.

USO
===
    python reavaliar_rejected_pii.py            # ensaio seco
    python reavaliar_rejected_pii.py --aplicar
"""

from __future__ import annotations

import collections
import datetime
import os
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from exportar import _credenciais  # noqa: E402
from mascarar import _carregar_servico  # noqa: E402

_CURADORIA = _carregar_servico("curadoria_cartas")
veredito_de_pii = _CURADORIA.veredito_de_pii
MARCA = "reavaliacao_pii_15_08_2026"


def com_retry(fn, tentativas: int = 5):
    import httpx

    for i in range(tentativas):
        try:
            return fn()
        except (httpx.RemoteProtocolError, httpx.ReadError, httpx.ConnectError,
                httpx.ReadTimeout, httpx.WriteError):
            if i == tentativas - 1:
                raise
            time.sleep(1.5 * (i + 1))


def main() -> int:
    aplicar = "--aplicar" in sys.argv
    url, key = _credenciais()
    from supabase import create_client

    db = create_client(url, key)

    ini, cartas = 0, []
    while True:
        # 🔴 `select("*")` E NÃO SÓ AS COLUNAS QUE EU LEIO — 15/08/2026.
        #
        # O upsert do PostgREST monta um INSERT e só depois resolve o conflito,
        # e o Postgres valida NOT NULL na linha PROPOSTA. Com um payload de
        # `{id, status, pii_check}` a escrita morre em
        # `null value in column "card_hash" violates not-null constraint` —
        # mesmo com `on_conflict=id` e a linha existindo.
        #
        # A alternativa seria um UPDATE por carta: 320 requisições numa conexão
        # HTTP/2 que morre no stream 19.999. Reler a linha inteira e devolvê-la
        # inteira cabe em 2 requisições e não depende de eu adivinhar quais
        # colunas são obrigatórias hoje.
        lote = com_retry(lambda i=ini: (
            db.table("knowledge_cards").select("*")
            .eq("status", "rejected_pii").order("id")
            .range(i, i + 499).execute().data)) or []
        if not lote:
            break
        cartas.extend(lote)
        ini += 500

    print(f"  {len(cartas)} cartas em rejected_pii lidas do BANCO")

    promover, ficam = [], []
    por_placeholder = collections.Counter()
    for c in cartas:
        mascarado, achados = veredito_de_pii(c["card_text"] or "")
        if mascarado != (c["card_text"] or ""):
            import re
            for p in set(re.findall(r"\{[A-Z_]+\}", mascarado)):
                if mascarado.count(p) > (c["card_text"] or "").count(p):
                    por_placeholder[p] += 1
        (ficam if achados else promover).append((c, achados))

    print(f"  {len(promover)} SEM identificador → pending_review")
    print(f"  {len(ficam)} COM identificador → continuam rejected_pii")
    print("\n  o que o mascarador ainda encostaria (e que deixou de rejeitar):")
    for p, n in por_placeholder.most_common():
        print(f"    {p:22s} {n}")
    for c, achados in ficam[:20]:
        print(f"    FICA {achados}: {c['card_text'][:80]}...")

    if not aplicar:
        print("\n  (ensaio seco — nada gravado. Rode com --aplicar)")
        return 0

    agora = datetime.datetime.now(datetime.timezone.utc).isoformat()
    linhas = []
    for c, _ in promover:
        marcas = dict(c.get("pii_check") or {})
        # O motivo da MUDANÇA fica gravado. Sem isto, a próxima pessoa a olhar
        # esta carta vê `pending_review` e não tem como saber que ela já foi
        # rejeitada, nem por quê — que é exatamente como as 320 ficaram de pé.
        marcas["deterministic"] = True
        marcas["reavaliado_por"] = MARCA
        marcas["reavaliado_em"] = agora
        marcas["motivo_da_rejeicao_anterior"] = "templatize(t) != t (eixo errado)"
        # A linha INTEIRA volta, com `status` e `pii_check` trocados e o resto
        # idêntico ao que veio do banco. Ver o comentário do `select("*")`.
        linhas.append({**c, "status": "pending_review", "pii_check": marcas})

    # ⚠️ Lote de 200. Ver o cabeçalho.
    for i in range(0, len(linhas), 200):
        pedaco = linhas[i:i + 200]
        com_retry(lambda p=pedaco: db.table("knowledge_cards").upsert(
            p, on_conflict="id").execute())
        print(f"  atualizadas {min(i + 200, len(linhas))}/{len(linhas)}")

    # 🔴 VERIFY NO BANCO. O contador deste script não é prova de nada.
    restam = com_retry(lambda: (
        db.table("knowledge_cards").select("id", count="exact")
        .eq("status", "rejected_pii").limit(1).execute().count))
    voltaram = com_retry(lambda: (
        db.table("knowledge_cards").select("id", count="exact")
        .eq("pii_check->>reavaliado_por", MARCA).limit(1).execute().count))
    print(f"\n  VERIFY no banco: rejected_pii agora = {restam} "
          f"(esperado {len(ficam)})")
    print(f"  VERIFY no banco: marcadas {MARCA} = {voltaram} "
          f"(esperado {len(promover)})")
    return 0 if (restam == len(ficam) and voltaram == len(promover)) else 1


if __name__ == "__main__":
    sys.exit(main())
