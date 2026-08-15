# -*- coding: utf-8 -*-
"""As 23 cartas que o teto de 400 matou, de volta ao acervo.

O QUE ACONTECEU
===============
📊 Medido em 15/08/2026 sobre a leva 5 (72 lotes, 1.527 fatos destilados): 23
fatos foram descartados por passar de 400 caracteres — e nenhum por ficar
abaixo de 15. O corte era mudo, então eles sumiram sem log, sem contagem e sem
rastro; o acervo ficou parecendo completo.

E o padrão é perverso: **quanto mais completa a carta, maior a chance de
morrer.** Os 23 são relações de documentos, conjuntos fechados de exigências,
listas de itens — longos PORQUE são completos.

📊 Três eram INÉDITOS no acervo (Jaccard < 0,22 contra as 18.400 cartas):
a sequência do atendimento automático da prestadora de vidros; quais
seguradoras cobrem calibração de ADAS; caminhão em nome da locadora fora da
apólice de frota.

O QUE ESTE SCRIPT NÃO FAZ, E POR QUÊ
====================================
**Não reescreve regra nenhuma.** Hash, mascaramento, assunto e seguradora vêm
de `aplicar._cartas_de` — a mesma função do fluxo normal. Recopiá-las aqui
criaria a quinta porta de entrada com regras próprias, que é exatamente o
defeito que esta leva está consertando (CLAUDE.md §5).

**Não toca em `attendance_sessions.summary->'distilled'`.** As sessões já foram
marcadas como destiladas na leva original, e a marca é o "não volte mais". O
que faltou foi a CARTA, não a destilação — então só a carta é gravada.
Por isso não chamo `_planejar`/`_gravar`, que fariam as duas coisas.

A ESCRITA VAI EM LOTE DE 200
============================
⚠️ Uma requisição por carta mata a conexão HTTP/2 no stream ~19.999
(`RemoteProtocolError <ConnectionTerminated last_stream_id:19999>`). Já derrubou
o `backfill_temas` e o espelho. O lote de 200 e o retry são obrigatórios.

USO
===
    python regravar_longas.py            # ensaio seco, não grava
    python regravar_longas.py --aplicar
"""

from __future__ import annotations

import collections
import glob
import json
import os
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from aplicar import _cartas_de  # noqa: E402
from exportar import _credenciais  # noqa: E402
from mascarar import _carregar_servico  # noqa: E402

MIN_CARACTERES = _carregar_servico("curadoria_cartas").MIN_CARACTERES
MARCA = "destilacao_max_15_08_2026_longas"
CORTE_ANTIGO = 400


def com_retry(fn, tentativas: int = 5):
    """Uma queda de conexão não pode matar a rodada. Ver `backfill_temas`."""
    import httpx

    for i in range(tentativas):
        try:
            return fn()
        except (httpx.RemoteProtocolError, httpx.ReadError, httpx.ConnectError,
                httpx.ReadTimeout, httpx.WriteError):
            if i == tentativas - 1:
                raise
            time.sleep(1.5 * (i + 1))


def _so_os_longos(d: dict) -> dict:
    """A MESMA linha do destilador, com só os fatos que o teto matou.

    Filtrar aqui — e não dentro de `_cartas_de` — é o que mantém a regra de
    gravação intocada: `_cartas_de` continua sendo a função do fluxo normal,
    recebendo um destilado normal. O recorte é do chamador.

    `temas_por_fato` é recortado NO MESMO índice dos fatos. Se as duas listas
    saíssem de sincronia, cada carta receberia o tema da carta vizinha — e um
    tema errado é pior que nenhum, porque o filtro do RAG confia nele.
    """
    fatos = (d.get("fatos_reutilizaveis") or [])[:8]
    temas = d.get("temas_por_fato") or []
    escolhidos, escolhidos_temas = [], []
    for i, fato in enumerate(fatos):
        texto = " ".join(str(fato or "").split())
        if len(texto) > CORTE_ANTIGO and len(texto) >= MIN_CARACTERES:
            escolhidos.append(fato)
            escolhidos_temas.append(temas[i] if i < len(temas) else (d.get("temas") or []))
    return {**d, "fatos_reutilizaveis": escolhidos, "temas_por_fato": escolhidos_temas}


def main() -> int:
    aplicar = "--aplicar" in sys.argv

    cartas: dict = {}
    lidos = 0
    for caminho in sorted(glob.glob(os.path.join(AQUI, "lotes_v2", "*.destilado.jsonl"))):
        with open(caminho, encoding="utf-8") as fh:
            for linha in fh:
                linha = linha.strip()
                if not linha:
                    continue
                try:
                    d = json.loads(linha)
                except json.JSONDecodeError:
                    continue
                recorte = _so_os_longos(d)
                if not recorte["fatos_reutilizaveis"]:
                    continue
                lidos += len(recorte["fatos_reutilizaveis"])
                sid = str(d.get("id") or "")
                for c in _cartas_de(recorte, sid, marca=MARCA):
                    cartas.setdefault(c["card_hash"], c)

    print(f"  {lidos} fatos acima de {CORTE_ANTIGO} caracteres nos lotes_v2")
    print(f"  {len(cartas)} cartas distintas a gravar (marca {MARCA})")
    por_status = collections.Counter(c["status"] for c in cartas.values())
    for s, n in por_status.most_common():
        print(f"    {s:20s} {n}")
    sem_tema = sum(1 for c in cartas.values() if not c.get("temas"))
    print(f"    {sem_tema} sem tema · {len(cartas) - sem_tema} com tema")

    if not aplicar:
        print("\n  (ensaio seco — nada gravado. Rode com --aplicar)")
        for c in list(cartas.values())[:3]:
            print(f"    [{len(c['card_text'])}ch {c['status']} temas={c.get('temas')}] "
                  f"{c['card_text'][:80]}...")
        return 0

    url, key = _credenciais()
    from supabase import create_client

    db = create_client(url, key)
    linhas = list(cartas.values())
    # ⚠️ Lote de 200, sempre. Ver o cabeçalho: uma requisição por carta derruba
    # a conexão HTTP/2 no stream 19.999.
    for i in range(0, len(linhas), 200):
        pedaco = linhas[i:i + 200]
        com_retry(lambda p=pedaco: db.table("knowledge_cards").upsert(
            p, on_conflict="card_hash", ignore_duplicates=True).execute())
        print(f"  gravadas {min(i + 200, len(linhas))}/{len(linhas)}")

    # 🔴 A CONFERÊNCIA É NO BANCO, NÃO NO CONTADOR DESTE SCRIPT.
    #
    # O `upsert` com `ignore_duplicates` devolve sucesso tanto para a carta que
    # entrou quanto para a que já existia. Contar o que eu MANDEI e chamar de
    # "gravadas" é o print que mente — e ele já enganou uma vez hoje.
    achadas = 0
    hashes = list(cartas)
    for i in range(0, len(hashes), 200):
        r = com_retry(lambda p=hashes[i:i + 200]: (
            db.table("knowledge_cards").select("card_hash")
            .in_("card_hash", p).execute().data)) or []
        achadas += len(r)
    print(f"\n  VERIFY no banco: {achadas}/{len(cartas)} hashes presentes em knowledge_cards")
    return 0 if achadas == len(cartas) else 1


if __name__ == "__main__":
    sys.exit(main())
