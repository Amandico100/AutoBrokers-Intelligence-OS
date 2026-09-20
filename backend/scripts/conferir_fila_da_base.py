# -*- coding: utf-8 -*-
"""Roda o CONFERENTE sobre a fila de curadoria. **`--ensaio` é o padrão.**

SPEC-EXTRA-001.5.2 · unidade F, e a preparação da G.

```
python scripts/conferir_fila_da_base.py                 # ensaio: não escreve nada
python scripts/conferir_fila_da_base.py --gravar        # escreve o veredito na linha
python scripts/conferir_fila_da_base.py --gabarito      # mede a concordância com o
                                                        # leitor humano de 19/09 (GATE F)
```

🔴 POR QUE O ENSAIO É O PADRÃO
==============================
Este script toca **73 linhas da base de produção** de uma vez. Um `--gravar`
que fosse o comportamento sem bandeira transformaria *"deixa eu ver o que
daria"* em escrita — e o jeito de descobrir seria pela tela do Founder.

⛔ O QUE ELE NUNCA FAZ
======================
Não publica, não recusa, não muda `curadoria`, não manda mensagem, não liga
agente. Ele **anota**. Quem promove a `publicado` continua sendo gente, por
`assistance_plans_base.publicar_servico`, com revisor.

⛔ E NÃO ESCREVE POR FORA DO CONTRATO (CLAUDE.md §5)
===================================================
A escrita nas duas tabelas tem **um caminho só**: `assistance_plans_base`. Este
script chama `BASE.anotar_conferencia(...)`. Enquanto essa função não existir, o
`--gravar` **recusa e diz o que falta** — em vez de abrir um segundo escritor
com `.table(...).update(...)`, que é exatamente o motor paralelo que a §5 proíbe.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, List

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
REPO = os.path.dirname(RAIZ)
sys.path.insert(0, RAIZ)

from app.services.knowledge import assistance_plans_base as BASE  # noqa: E402
from app.services.knowledge import assistance_plans_conferente as CONF  # noqa: E402

GABARITO = os.path.join(
    REPO, "docs", "canon", "reports", "SPEC-EXTRA-001.5-LINHAS-CONFERIDAS.json")

#: 📊 19/09: 73 linhas em `proposto`. O teto é folgado de propósito — um teto
#: apertado faria o "0 linhas sem veredito" da unidade G ser verdade só sobre a
#: primeira página da fila, que é a mentira que a 001.5.1 consertou (D3).
TETO_DA_FILA = 500


def _paginas_por_documento(linhas: List[Dict[str, Any]], minio=None, db=None
                           ) -> Dict[str, Dict[int, str]]:
    """Lê cada documento UMA vez. 📊 24 documentos para 73 linhas.

    ⛔ Nenhum segundo leitor de PDF: é `BASE.texto_das_paginas` (o `fitz` de
    `insurance_corpus`), e o documento inteiro, para o conferente poder dizer
    *"o trecho existe, mas na página 31"*.
    """
    fora: Dict[str, Dict[int, str]] = {}
    documentos = sorted({str(l.get("documento_id")) for l in linhas
                         if l.get("documento_id")})
    for i, documento in enumerate(documentos, 1):
        lidas = BASE.texto_das_paginas(documento, None, db=db, minio=minio)
        fora[documento] = {int(k): v for k, v in (lidas.paginas or {}).items()}
        print("  [%d/%d] %s  %s  %d paginas"
              % (i, len(documentos), documento[:8],
                 "ok" if lidas.ok else lidas.motivo, lidas.total), flush=True)
    return fora


def _conferir(linhas, paginas_por_documento) -> List[Dict[str, Any]]:
    pareceres = []
    for linha in linhas:
        paginas = paginas_por_documento.get(str(linha.get("documento_id")), {})
        pareceres.append({"linha": linha,
                          "parecer": CONF.conferir_linha(linha, paginas)})
    return pareceres


def _resumo(pareceres) -> None:
    contagem = Counter(p["parecer"].veredito for p in pareceres)
    print("\n  VEREDITOS")
    for v in (CONF.CONFERE, CONF.DIVERGE, CONF.NAO_CONSEGUI):
        print("    %-12s %3d" % (v, contagem.get(v, 0)))
    por_campo = defaultdict(Counter)
    for p in pareceres:
        for campo, estado in p["parecer"].campos.items():
            por_campo[campo][estado] += 1
    print("\n  POR CAMPO   ok / diverge / nao_avaliado")
    for campo in CONF.CAMPOS:
        c = por_campo[campo]
        print("    %-9s %3d / %3d / %3d"
              % (campo, c[CONF.OK], c[CONF.DIVERGE_CAMPO], c[CONF.NAO_AVALIADO]))


def _gate_g(linhas, pareceres, gravou: bool) -> int:
    """Quantas linhas `proposto` ficariam SEM veredito. O GATE G exige 0.

    🔴 SEM VEREDITO ≠ `NAO_CONSEGUI`. `NAO_CONSEGUI` **é** um veredito: está
    gravado, o CHECK do banco o aceita, e a fila o mostra ("não consegui
    conferir: trecho"). Contá-lo como ausência faria o GATE G reprovar uma
    linha que foi conferida e cujo resultado honesto é "não deu" — e empurraria
    para o próximo a tentação de selar o que não se conferiu.
    """
    propostas = [l for l in linhas if str(l.get("curadoria")) == "proposto"]
    com_parecer = {str(p["linha"].get("id")) for p in pareceres}
    sem = [l for l in propostas if str(l.get("id")) not in com_parecer]
    abstidas = [p for p in pareceres if p["parecer"].veredito == CONF.NAO_CONSEGUI]
    print("\n  GATE G (preparação)")
    print("    linhas em `proposto` .................... %d" % len(propostas))
    print("    sem veredito depois desta passada ...... %d%s"
          % (len(sem), "" if gravou else "   (ensaio: nada foi gravado)"))
    print("    dessas, com veredito `NAO_CONSEGUI` .... %d   (é veredito, não "
          "ausência)" % len(abstidas))
    for l in sem[:10]:
        print("      - %s  %s" % (str(l.get("id"))[:8], l.get("servico")))
    return len(sem)


def _gravar(pareceres, db=None) -> int:
    """🔴 A escrita passa pelo contrato, ou não acontece."""
    anotar = getattr(BASE, "anotar_conferencia", None)
    if anotar is None:
        print("\n  \U0001F534 RECUSADO: `assistance_plans_base.anotar_conferencia` "
              "nao existe ainda.")
        print("     O conferente nao abre um segundo escritor para as tabelas "
              "(CLAUDE.md §5).")
        print("     Falta: (1) aplicar "
              "`supabase/migrations/20260920_01_extra00152_veredito_do_conferente.sql`")
        print("            (2) `anotar_conferencia(servico_id, veredito, campos, "
              "motivos, pagina, *, db=None)` em assistance_plans_base.py")
        return -1
    n = 0
    for p in pareceres:
        parecer = p["parecer"]
        anotar(str(p["linha"].get("id")), parecer.veredito, parecer.campos,
               parecer.motivos, parecer.pagina, db=db)
        n += 1
    print("\n  gravados %d pareceres" % n)
    return n


def _medir_contra_o_gabarito(db=None, minio=None) -> int:
    """GATE F — a concordância com o leitor humano de 19/09, contra a PÁGINA.

    🔴 A DEFINIÇÃO, ESCRITA ANTES DE MEDIR (ela mora em `CONF.EQUIVALENCIA`):
    `PUBLICAR` ≙ `CONFERE`; `CORRIGIR` e `RECUSAR` ≙ `DIVERGE`. A régua do GATE
    é a de LINHA (81 comparações). A de CAMPO é reportada junto, e é mais dura.
    """
    gabarito = json.load(open(GABARITO, encoding="utf-8"))["linhas"]
    cliente = BASE._db(db)
    linhas, faltaram = [], []
    for g in gabarito:
        r = (cliente.table(BASE.TABELA_SERVICOS).select("*")
             .eq("id", g["servico_id"]).limit(1).execute()).data or []
        if not r:
            faltaram.append(g["servico_id"])
            continue
        linha = dict(r[0])
        plano = (cliente.table(BASE.TABELA_PLANOS).select("*")
                 .eq("id", str(linha.get("plano_id"))).limit(1).execute()).data or []
        linha["produto"] = (plano[0] if plano else {}).get("produto")
        linha["plano"] = (plano[0] if plano else {}).get("plano")
        # ⚠️ A base NÃO guarda o trecho (só o `trecho_hash`). O trecho que entra
        # aqui é o que o leitor humano copiou da página em 19/09 — é a única
        # fonte de trecho que existe para estas 81 linhas.
        linha["trecho"] = g.get("trecho")
        linha["_gabarito"] = g
        linhas.append(linha)
    print("  linhas do gabarito encontradas na base: %d  (faltaram %d)"
          % (len(linhas), len(faltaram)))

    paginas = _paginas_por_documento(linhas, minio=minio, db=cliente)

    def _rodada():
        pares = [(l["_gabarito"], CONF.conferir_linha(l, paginas.get(
            str(l.get("documento_id")), {}))) for l in linhas]
        return pares, CONF.medir(pares)

    # 🔴 OS TRÊS NÚMEROS LADO A LADO (juiz B3, 20/09/2026)
    # ===================================================
    # 📊 60 das 81 linhas dizem `Plano único`, e detectar esse PLACEHOLDER
    # respondia por 21 pontos percentuais do gate. Mas o extrator v2 **nunca
    # emite "Plano único"** — o número com a regra media um defeito do extrator
    # velho, não o conferente. O GATE deste script é o número SEM a regra.
    pares_com, com = _rodada()
    anterior = CONF.REGRA_DO_PLACEHOLDER
    try:
        CONF.REGRA_DO_PLACEHOLDER = False
        pares_sem, sem = _rodada()
    finally:
        CONF.REGRA_DO_PLACEHOLDER = anterior

    placeholder = sum(1 for l in linhas
                      if CONF._para_leitura(l.get("plano")) ==
                      CONF._para_leitura(CONF._PLANO_PADRAO))
    print("\n  GATE F — concordancia com o leitor humano de 19/09")
    print("    %-34s %s" % ("", "LINHA            CAMPO"))
    for rotulo, m in (("COM a regra do placeholder", com),
                      ("SEM a regra  <- O GATE", sem)):
        print("    %-30s %3d/%-3d = %5.1f%%   %3d/%-3d = %5.1f%%"
              % (rotulo, m["linhas_concordantes"], m["linhas"],
                 100 * m["concordancia_de_linha"], m["campos_concordantes"],
                 m["campos_comparaveis"], 100 * m["concordancia_de_campo"]))
    print("    📊 %d das %d linhas dizem %r — e o extrator v2 nunca o emite."
          % (placeholder, len(linhas), CONF._PLANO_PADRAO))
    print("       O numero da direita e o que vale para LINHA NOVA.")

    # 🔴 A PRECISAO DO `CONFERE` — a metrica do produto.
    # "Publicar sem abrir o PDF" so e seguro se o que recebe selo estiver certo.
    # Errar para MENOS (nao selar o que estava certo) custa uma leitura; errar
    # para MAIS (selar o que estava errado) publica erro com carimbo de gente.
    for rotulo, pares in (("COM a regra", pares_com), ("SEM a regra", pares_sem)):
        selados = [(g, p) for g, p in pares if p.veredito == CONF.CONFERE]
        certas = [1 for g, _ in selados if g.get("veredito") == "PUBLICAR"]
        print("    precisao do CONFERE (%s): %d de %d selados estavam certos%s"
              % (rotulo, len(certas), len(selados),
                 " = %.0f%%" % (100 * len(certas) / len(selados)) if selados else ""))

    print("\n  AS %d DISCORDANCIAS DO NUMERO QUE VALE (SEM a regra) — "
          "listadas, nao escondidas (SPEC §3.F)" % len(sem["discordancias"]))
    for d in sem["discordancias"]:
        print("    %-9s %-14s p%-4s leitor=%-9s campo=%-9s conferente=%s"
              % (d["insurer_key"], d["servico"], d["pagina"], d["leitor"],
                 d["campo_do_leitor"] or "-", d["conferente"]))
        for motivo in d["motivos"][:2]:
            print("        · %s" % motivo[:110])
    return 0 if sem["concordancia_de_linha"] >= 0.80 else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gravar", action="store_true",
                   help="escreve o veredito na linha (sem isto, e ENSAIO)")
    p.add_argument("--gabarito", action="store_true",
                   help="mede o GATE F contra as 81 linhas conferidas em 19/09")
    p.add_argument("--limite", type=int, default=TETO_DA_FILA)
    p.add_argument("--curadorias", default="proposto",
                   help="estados a conferir, separados por virgula")
    a = p.parse_args(argv)

    print("=" * 74)
    print("  CONFERENTE DA FILA — SPEC-EXTRA-001.5.2 · unidade F")
    print("  modo: %s" % ("GRAVAR" if a.gravar else "ENSAIO (nada e escrito)"))
    print("=" * 74)

    if a.gabarito:
        return _medir_contra_o_gabarito()

    estados = tuple(s.strip() for s in a.curadorias.split(",") if s.strip())
    linhas = BASE.fila_de_curadoria(limite=a.limite, curadorias=estados)
    print("  linhas na fila (%s): %d" % (",".join(estados), len(linhas)))
    if not linhas:
        return 0
    # ⚠️ `fila_de_curadoria` NAO devolve o trecho (a base guarda so o hash).
    # Sem trecho, o campo `trecho` sai `nao_avaliado` — declarado, nunca `ok`.
    sem_trecho = sum(1 for l in linhas if not l.get("trecho"))
    if sem_trecho:
        print("  ⚠ %d linhas sem trecho gravado: o campo `trecho` sai "
              "`nao_avaliado` (a base guarda so o `trecho_hash`)" % sem_trecho)

    paginas = _paginas_por_documento(linhas)
    pareceres = _conferir(linhas, paginas)
    _resumo(pareceres)

    gravou = False
    if a.gravar:
        gravou = _gravar(pareceres) >= 0
    sem_veredito = _gate_g(linhas, pareceres, gravou)
    return 0 if (not a.gravar or sem_veredito == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
