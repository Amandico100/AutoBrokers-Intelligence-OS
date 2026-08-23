# -*- coding: utf-8 -*-
"""`roteiro_de_coleta.py` — o que falta COLETAR, rota por rota (SPEC-084.1 ONDA G).

```bash
python backend/scripts/roteiro_de_coleta.py                       # tabela
python backend/scripts/roteiro_de_coleta.py --markdown > docs/canon/reports/ROTEIRO-DE-COLETA.md
```

🔴 A PERGUNTA QUE ESTE SCRIPT RESPONDE, e ela é do Founder:

> *"SEM_CORPUS é uma de duas coisas: **(a) coleta legítima** — ninguém pediu
> aquele serviço àquela seguradora no período — ou **(b) 🔴 BUG** — o serviço
> foi pedido e o produto não soube reconhecê-lo. Fundir as duas manda para
> coleta uma rota cujo acervo está cheio."*

⚠️ E a diferença não se adivinha pelo nome da rota: ela se MEDE, com linhas de
CONTROLE. Para cada rota sem corpus este script pergunta três coisas ao acervo
versionado:

```
1. o CORREDOR tem corpus?          se não, é a seguradora inteira que falta
2. a URA OFERECE este serviço?     o rótulo do menu aparece nas telas dela?
3. as OUTRAS teclas do mesmo menu decodificam?
```

🔴 **A terceira é a linha de CONTROLE**, e é ela que dá direito à conclusão. Se
as outras teclas do mesmo menu produzem rotas com corpus, então o decodificador
funciona e o silêncio desta é do mundo, não do código. Se NENHUMA tecla daquele
menu decodifica, o suspeito é o produto.

📊 O caso que obrigou este script a existir: `allianz/auto/chaveiro`. A tecla 7
foi apresentada 25 vezes e pressionada ZERO — e as teclas 1, 3, 4 e 6 do MESMO
menu produzem 47, 149 e 85 telas. Sem o controle, a rota pareceria defeito.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import regua_motor as M      # noqa: E402
import replay as RP          # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _rotulos_do_menu(pb) -> dict:
    """`{servico: rótulo que a URA usa}` — do MAPA do corredor, não de uma cópia."""
    fora = {}
    for chave in ("subservice_menu_map", "subservice_labels"):
        for sv, rot in (pb.get(chave) or {}).items():
            if rot and not str(rot).isdigit():
                fora.setdefault(sv, str(rot))
    for sv, sub in (pb.get("subservices") or {}).items():
        rot = sub.get("tipo_servico_opcao") or sub.get("menu_value")
        if rot and not str(rot).isdigit():
            fora.setdefault(sv, str(rot))
    return fora


def levantar():
    """Uma linha por rota SEM_CORPUS, com o veredito medido."""
    corpus_por_corredor = {}
    telas_por_rota = collections.Counter()
    for rota in M.rotas():
        chave = (rota.seguradora, rota.ramo)
        if chave not in corpus_por_corredor:
            corpus_por_corredor[chave] = RP.carregar_corpus(*chave)
        telas_por_rota[(rota.seguradora, rota.ramo, rota.servico)] = len(
            [l for l in corpus_por_corredor[chave]
             if str(l.get("servico") or "") == rota.servico])

    fora = []
    for rota in M.rotas():
        if telas_por_rota[(rota.seguradora, rota.ramo, rota.servico)]:
            continue
        pb = M.get_playbook(rota.ref) or {}
        chave = (rota.seguradora, rota.ramo)
        corpus = corpus_por_corredor[chave]
        rotulos = _rotulos_do_menu(pb)
        rotulo = rotulos.get(rota.servico) or rota.servico.replace("_", " ")

        # 2 · a URA OFERECE o serviço? (o rótulo aparece em alguma tela?)
        alvo = M._norm(rotulo)
        ofertas = {M._norm(l["text"]) for l in corpus if alvo and alvo in M._norm(l["text"])}

        # 3 · CONTROLE: as OUTRAS teclas do mesmo corredor decodificam?
        irmas = {sv: telas_por_rota[(rota.seguradora, rota.ramo, sv)]
                 for sv in (pb.get("subservices") or {})
                 if sv != rota.servico}
        vivas = {k: v for k, v in irmas.items() if v}

        if not corpus:
            veredito = "SEGURADORA INTEIRA SEM ACERVO"
            porque = "o corredor não tem uma tela sequer — é coleta de canal"
        elif not vivas:
            veredito = "🔴 SUSPEITO DE BUG"
            porque = ("NENHUMA rota deste corredor tem telas, e o corredor TEM "
                      "corpus: o decodificador de serviço é o suspeito")
        elif ofertas:
            veredito = "COLETA LEGÍTIMA"
            porque = (f"a URA OFERECE o serviço ({len(ofertas)} tela(s) com o "
                      f"rótulo) e ninguém o pediu; as irmãs decodificam "
                      f"({', '.join(f'{k}={v}' for k, v in sorted(vivas.items()))})")
        else:
            veredito = "⚠️ RÓTULO NÃO VISTO"
            porque = (f"o rótulo {rotulo!r} não aparece em nenhuma tela deste "
                      f"corredor; as irmãs decodificam "
                      f"({', '.join(f'{k}={v}' for k, v in sorted(vivas.items()))}) "
                      f"— ou a URA não oferece, ou o rótulo está errado")
        fora.append((rota, rotulo, veredito, porque, len(ofertas), sorted(vivas.items())))
    return fora


def _controle_de_coleta(rota, vivas) -> str:
    """A linha de CONTROLE que a coleta precisa levar junto (§9.2)."""
    if not vivas:
        return ("🔴 Sem irmã com desfecho conhecido neste corredor: a coleta "
                "precisa de DUAS tentativas, e a segunda repete a primeira.")
    irma, n = max(vivas, key=lambda kv: kv[1])
    return (f"🔴 CONTROLE da mesma rodada: peça **{irma}** nesta seguradora — "
            f"desfecho conhecido, {n} telas no acervo. Sem ele, uma coleta que "
            f"falha não distingue *'a tecla não abre'* de *'o WhatsApp não "
            f"respondeu hoje'*.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markdown", action="store_true")
    a = ap.parse_args()
    linhas = levantar()

    if not a.markdown:
        print(f"{len(linhas)} rotas SEM_CORPUS")
        for rota, rotulo, ver, porque, n_of, vivas in linhas:
            print(f"  {rota.seguradora:9}{rota.ramo:12}{rota.servico:16} {ver}")
            print(f"      {porque}")
        return 0

    agora = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    por_veredito = collections.Counter(x[2] for x in linhas)
    print("# Roteiro de coleta — as rotas que o acervo ainda não viu\n")
    print(f"> Gerado em **{agora}** · {len(linhas)} rotas sem corpus\n")
    print("🔴 `SEM_CORPUS` é uma de duas coisas — **coleta legítima** ou "
          "**bug de reconhecimento** — e a diferença se MEDE, não se adivinha. "
          "Cada linha abaixo traz o veredito e o CONTROLE que a coleta precisa "
          "levar junto.\n")
    for k, v in por_veredito.most_common():
        print(f"- **{v}** · {k}")
    print()
    ordem = {"🔴 SUSPEITO DE BUG": 0, "⚠️ RÓTULO NÃO VISTO": 1,
             "COLETA LEGÍTIMA": 2, "SEGURADORA INTEIRA SEM ACERVO": 3}
    for rota, rotulo, ver, porque, n_of, vivas in sorted(
            linhas, key=lambda x: (ordem.get(x[2], 9), x[0].seguradora, x[0].servico)):
        print(f"\n## {rota.seguradora} × {rota.ramo} × {rota.servico} — {ver}\n")
        print(f"- **rótulo da URA:** `{rotulo}`")
        print(f"- **por quê:** {porque}")
        print(f"- **como pedir:** abra o WhatsApp da assistência 24h da "
              f"{rota.seguradora} e escolha `{rotulo}` no menu de "
              f"{'veículo' if rota.ramo == 'auto' else 'residência'}.")
        print(f"- {_controle_de_coleta(rota, vivas)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
