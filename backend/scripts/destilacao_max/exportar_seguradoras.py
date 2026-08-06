"""Puxa as conversas com as SEGURADORAS e escreve lotes MASCARADOS em disco.

Por que este script existe, e não o `exportar.py`
-------------------------------------------------
O `exportar.py` lê `attendance_sessions` — a corretora falando com o SEGURADO.
Aquele acervo ensina o que a corretora faz. Este lê `observed_sessions`: a
corretora falando com a URA da SEGURADORA. Ele ensina o que a **seguradora**
faz, que é outra coisa e não está em contrato nenhum.

📊 Medido em 06/08/2026 (`select count(*) from observed_sessions` e
`observed_events`): 551 sessões, 19.421 eventos, 10 seguradoras, **zero**
destiladas. É o material mais valioso e nunca lido do projeto.

E há uma diferença que muda o valor de tudo: **aqui o rótulo de seguradora é
confiável por construção.** No acervo de atendimento a seguradora da SESSÃO era
carimbada em todo fato, e só 32% das cartas etiquetadas citavam a própria
seguradora — por isso `aplicar.py` trata `seguradora` como candidata e
re-decide fato a fato em `curadoria_cartas.seguradora_do_fato`. Aqui a conversa
**é** com aquela seguradora: `insurer_key` vem da sessão e vai para o lote.

O que este script NÃO faz
-------------------------
Não escreve nada em banco nenhum. Ele lê, mascara e larga arquivo em disco.
A marca `summary.distilled` é **lida** (para não refazer trabalho) e quem a
escreve continua sendo o aplicador, depois da validação.

Nada é cortado em silêncio
--------------------------
Toda sessão que fica de fora aparece no `INDICE.md` com o motivo e a contagem
por seguradora, e todo transcript que bate no teto é listado com o tamanho
original. Cap silencioso é defeito (CLAUDE.md §11).

Credenciais
-----------
As mesmas do `exportar.py` — `_credenciais()` é importado, não recopiado.

Uso
---
    python exportar_seguradoras.py                       # tudo o que é substancial
    python exportar_seguradoras.py --lotes 1 --por-lote 12 --saida lotes_prova
    python exportar_seguradoras.py --seguradora porto
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from exportar import _credenciais  # noqa: E402  — a mesma porta de credencial
from mascarar import (  # noqa: E402  — o mesmo portão de PII
    transcript_seguradora, vocabulario_de_menu)

# Quantos eventos fazem uma sessão "substancial".
#
# 📊 Medido em 06/08/2026: 319 sessões têm 10+ eventos, 47 têm de 4 a 9, e 185
# têm 3 ou menos. Uma conversa com URA gasta os primeiros eventos em saudação,
# confirmação de identidade e CPF — abaixo de 10 quase nunca se chega ao menu,
# que é onde o conhecimento começa. As magras não são apagadas: ficam de fora
# deste lote e continuam no banco, contadas no INDICE.
MIN_EVENTOS = 10

# Teto do transcript, em caracteres. Não é o `TETO = 7000` de produção: aquele
# existe para caber num prompt de runtime. 📊 Medido em 06/08/2026: com 7.000,
# 82 das 320 sessões substanciais (26%) seriam cortadas; com 14.000, 12 (3,8%).
# O fim de uma conversa com URA é onde mora o desfecho — para onde ela mandou,
# o que ela recusou — então cortar cedo custa exatamente a parte que interessa.
TETO = 14000

# Quantas sessões por lote. O acervo de atendimento usa 100; aqui a conversa é
# 📊 ~6.000 caracteres em média (contra algumas centenas numa troca de
# WhatsApp), e 100 delas não cabem na leitura de um destilador só.
POR_LOTE = 12

PAGINA = 1000


def _pendentes(db, seguradora: str) -> tuple:
    """(sessões elegíveis, motivos de descarte). Uma ida ao banco por página."""
    descartes: dict = collections.defaultdict(collections.Counter)
    sessoes: list = []
    de = 0
    while True:
        q = db.table("observed_sessions").select(
            "id, insurer_key, summary, started_at, status")
        if seguradora:
            q = q.eq("insurer_key", seguradora)
        pagina = (q.order("insurer_key", desc=False)
                  .order("started_at", desc=False)
                  .range(de, de + PAGINA - 1).execute().data) or []
        if not pagina:
            break
        for r in pagina:
            chave = str(r.get("insurer_key") or "(sem seguradora)")
            resumo = r.get("summary") or {}
            # A MESMA marca do `exportar.py`: destilada não volta para a fila, e
            # três falhas seguidas também não. Sem isto, a segunda rodada refaz
            # a primeira inteira e paga de novo por conhecimento que já existe.
            if resumo.get("distilled"):
                descartes["já destilada"][chave] += 1
                continue
            if int(resumo.get("distill_falhas") or 0) >= 3:
                descartes["3+ falhas de destilação"][chave] += 1
                continue
            sessoes.append(r)
        if len(pagina) < PAGINA:
            break
        de += PAGINA
    return sessoes, descartes


def _eventos_por_sessao(db, ids: list) -> dict:
    """Os eventos das sessões pedidas, em ordem, agrupados por sessão.

    Uma consulta por lote, não uma por sessão — é a lição do `exportar.py`: o
    gargalo nunca foi ler nem escrever, foi ir ao banco N vezes.

    `interactive` vem junto porque 📊 937 dos 1.861 `button_reply` têm texto
    vazio e o rótulo do clique mora lá. `media_meta` NÃO vem: nome de arquivo
    e legenda de foto são PII de origem e nenhum deles ensina o que a
    seguradora faz.
    """
    por_sessao: dict = collections.defaultdict(list)
    for i in range(0, len(ids), 40):
        fatia = ids[i:i + 40]
        de = 0
        while True:
            eventos = (db.table("observed_events")
                       .select("session_id, direction, msg_type, text, "
                               "interactive, wa_timestamp")
                       .in_("session_id", fatia)
                       .order("wa_timestamp", desc=False)
                       .range(de, de + PAGINA - 1).execute().data) or []
            for e in eventos:
                por_sessao[str(e.get("session_id"))].append(e)
            if len(eventos) < PAGINA:
                break
            de += PAGINA
    return por_sessao


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--lotes", type=int, default=0, help="0 = todos")
    p.add_argument("--por-lote", type=int, default=POR_LOTE)
    p.add_argument("--saida", default=os.path.join(AQUI, "lotes_seguradoras"))
    p.add_argument("--seguradora", default="", help="insurer_key; vazio = todas")
    p.add_argument("--min-eventos", type=int, default=MIN_EVENTOS)
    p.add_argument("--teto", type=int, default=TETO)
    args = p.parse_args()

    url, key = _credenciais()
    from supabase import create_client

    db = create_client(url, key)
    saida = args.saida if os.path.isabs(args.saida) else os.path.join(AQUI, args.saida)
    os.makedirs(saida, exist_ok=True)

    sessoes, descartes = _pendentes(db, args.seguradora)
    print(f"[exportar-seg] {len(sessoes)} sessões pendentes no banco", file=sys.stderr)

    # Os eventos de TODAS as pendentes: é a leitura que decide quem é
    # substancial. Contar por SQL seria uma segunda régua do que é uma sessão.
    eventos = _eventos_por_sessao(db, [str(s["id"]) for s in sessoes])

    # O vocabulário de menu é do ACERVO, não da sessão: é ele que responde se
    # "Roubo," no começo de uma mensagem é opção de menu ou nome de gente. Uma
    # sessão sozinha não contém o vocabulário dela mesma (medido em 06/08/2026).
    todos = [e for lista in eventos.values() for e in lista]
    menu = vocabulario_de_menu(todos)
    print(f"[exportar-seg] vocabulário de menu do acervo: {len(menu)} palavras",
          file=sys.stderr)

    prontas: list = []
    truncadas: list = []
    for s in sessoes:
        sid = str(s["id"])
        chave = str(s.get("insurer_key") or "(sem seguradora)")
        brutos = eventos.get(sid) or []
        if len(brutos) < args.min_eventos:
            faixa = "magra (<4 eventos)" if len(brutos) < 4 else \
                    f"média (4-{args.min_eventos - 1} eventos)"
            descartes[faixa][chave] += 1
            continue
        texto = transcript_seguradora(brutos, menu)
        if len(texto) < 80:
            # Acontece: 10 eventos de mídia sem legenda nenhuma.
            descartes["transcript curto demais (<80 car.)"][chave] += 1
            continue
        if len(texto) > args.teto:
            truncadas.append((sid, chave, len(texto)))
            texto = texto[:args.teto]
        prontas.append({"id": sid, "seguradora": chave,
                        "eventos": len(brutos), "conversa": texto})

    # O CAP É O ÚLTIMO A AGIR, e ele se declara. Quem cai aqui não caiu por
    # qualidade — caiu porque o Founder pediu N lotes.
    alvo = args.lotes * args.por_lote if args.lotes else len(prontas)
    if len(prontas) > alvo:
        for r in prontas[alvo:]:
            descartes[f"fora do cap de --lotes {args.lotes}"][r["seguradora"]] += 1
        prontas = prontas[:alvo]

    indice = [f"# Lotes de conversas com SEGURADORAS — destilação pelo plano Max",
              "",
              f"Fonte: `observed_sessions` + `observed_events`. "
              f"Corte de substancial: {args.min_eventos}+ eventos. "
              f"Teto do transcript: {args.teto} caracteres.", ""]

    numero = 0
    for i in range(0, len(prontas), args.por_lote):
        fatia = prontas[i:i + args.por_lote]
        numero += 1
        caminho = os.path.join(saida, f"lote_{numero:03d}.jsonl")
        with open(caminho, "w", encoding="utf-8") as fh:
            for r in fatia:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        composicao = collections.Counter(r["seguradora"] for r in fatia)
        resumo = " · ".join(f"{k} {v}" for k, v in composicao.most_common())
        indice.append(f"- `lote_{numero:03d}.jsonl` — {len(fatia)} conversas · {resumo}")
        print(f"[exportar-seg] lote_{numero:03d}.jsonl · {len(fatia)} conversas · {resumo}",
              file=sys.stderr)

    indice += ["", "## O que ficou de fora, e por quê", ""]
    total_fora = 0
    for motivo in sorted(descartes):
        cont = descartes[motivo]
        total_fora += sum(cont.values())
        detalhe = " · ".join(f"{k} {v}" for k, v in cont.most_common())
        indice.append(f"- **{sum(cont.values())}** — {motivo}  \n  {detalhe}")
    indice += ["", f"Total fora dos lotes: **{total_fora}** sessões.", ""]

    if truncadas:
        indice += ["## Transcripts truncados no teto", "",
                   f"{len(truncadas)} conversas passaram de {args.teto} caracteres "
                   f"e foram cortadas no fim. O id fica aqui para que ninguém "
                   f"conclua que o desfecho delas não existia.", ""]
        for sid, chave, tam in sorted(truncadas, key=lambda t: -t[2]):
            indice.append(f"- `{sid}` · {chave} · {tam} caracteres")
        indice.append("")

    with open(os.path.join(saida, "INDICE.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(indice) + "\n")

    print(f"[exportar-seg] pronto: {numero} lotes · {len(prontas)} conversas mascaradas "
          f"· {total_fora} fora · {len(truncadas)} truncadas", file=sys.stderr)
    print(f"[exportar-seg] o motivo de cada uma que ficou de fora está em "
          f"{os.path.join(saida, 'INDICE.md')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
