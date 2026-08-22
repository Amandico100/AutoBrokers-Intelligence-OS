# -*- coding: utf-8 -*-
"""\U0001f534 A LINHA DE BASE DO E13 — SPEC-084.1 FASE 1 §3.3, entrega 3

> ## Um `noop` sobre uma tela que PEDE algo e o corredor calado na hora do
> ## pedido. A URA espera; o segurado espera; a medicao nao ve nada.

O `noop` legitimo existe: tela de aviso, saudacao, rodape. O `noop` sobre
**pergunta** e outra coisa — e por isso a E13 exige `noop_justificado`.

\u26a0\ufe0f **Tela sem onda e entrada invalida.** Uma tela que nenhuma onda paga nunca
sera consertada, e a lista viraria um inventario morto.
"""
from __future__ import annotations
import collections
import os
import sys
from typing import Dict, List, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import regua_motor as M            # noqa: E402
import replay as RP                # noqa: E402
import conferir_respostas as CR    # noqa: E402

# As ondas, como a SPEC \u00a76 as define. A ordem importa: A-E primeiro.
ONDAS: List[Tuple[str, str, str]] = [
    ("A", "allianz", "residencial"), ("B", "allianz", "auto"),
    ("C", "hdi", "auto"), ("D", "yelum", "auto"), ("E", "porto", "auto"),
]


def onda_da_rota(r) -> str:
    for nome, seg, ramo in ONDAS:
        if r.seguradora == seg and r.ramo == ramo:
            return nome
    return "F"          # \U0001f534 as que pontuam fora de A-E; G nao tem corpus


def pede_algo(t: str) -> bool:
    """A tela PEDE? -- tem pergunta, ou oferece opcoes para escolher."""
    if "?" in t:
        return True
    if CR.opcoes_da_tela(t) or CR.opcoes_em_lista(t):
        return True
    # 🔴 SO O IMPERATIVO QUE PEDE ACAO NAQUELA TELA.
    #
    # 📊 A primeira versao aceitava tambem "por favor", "qual", "quando" --
    #    e trouxe 61 telas, das quais a maioria eram AVISOS:
    #       "Por favor, aguarde enquanto solicito o seu servico."
    #       "Verifique se o disjuntor esta na posicao 'ligado'."
    #       "E necessario que um responsavel maior de 18 anos esteja no local."
    #    ⚠️ Em aviso o `noop` e CERTO, e conta-lo como furo inflaria a E13
    #    com trabalho que nao existe -- o oposto do que a estacao serve.
    n = M._norm(t)
    return any(p in n for p in (
        "informe", "digite", "envie", "escolha", "selecione", "nos diga",
        "me diga", "responda"))


def levantar():
    """{tela: {"rotas": {..}, "ocorrencias": n, "passos": {..}, "just": bool}}"""
    fora: Dict[str, dict] = {}
    corpus: Dict[Tuple[str, str], List[str]] = {}
    for r in M.rotas():
        pb = M.get_playbook(r.ref)
        if not pb:
            continue
        chave = (r.seguradora, r.ramo)
        if chave not in corpus:
            corpus[chave] = [l["text"] for l in
                             RP.carregar_corpus(r.seguradora, r.ramo)]
        for t in corpus[chave]:
            p = M.match_ura_step(pb, t, subservice=r.servico)
            if not p or not p.get("noop"):
                continue
            if not pede_algo(t):
                continue        # noop sobre aviso/rodape e legitimo e nao e E13
            e = fora.setdefault(" ".join(t.split()), {
                "rotas": set(), "corpus": set(), "passos": set(),
                "just": True})
            e["rotas"].add((r.seguradora, r.ramo, r.servico))
            # ⚠️ A UNIDADE E A LINHA DE CORPUS, nao rota x tela. Contar por
            #    rota multiplicava a mesma tela pelas 9 rotas do mesmo corredor
            #    e dava 2.030 -- um numero que nao mede nada.
            e["corpus"].add((r.seguradora, r.ramo, t))
            e["passos"].add(str(p.get("step") or "?"))
            if not p.get("noop_justificado"):
                e["just"] = False
    return fora


def main() -> int:
    base = levantar()
    por_onda: Dict[str, List[str]] = collections.defaultdict(list)
    for tela, e in base.items():
        ondas = {onda_da_rota(type("R", (), {
            "seguradora": s, "ramo": ra, "servico": sv})())
            for s, ra, sv in e["rotas"]}
        # \U0001f534 a onda que PAGA e a mais cedo: quem chega primeiro conserta
        e["onda"] = sorted(ondas)[0] if ondas else "?"
        por_onda[e["onda"]].append(tela)

    ocor = sum(len(e["corpus"]) for e in base.values())
    rotas = {r for e in base.values() for r in e["rotas"]}
    sem_just = [t for t, e in base.items() if not e["just"]]
    orfas = [t for t, e in base.items() if e["onda"] == "?"]

    L = ["# A linha de base do E13 — SPEC-084.1 FASE 1\n",
         "> **`noop` sobre uma tela que PEDE algo é o corredor calado na hora do",
         "> pedido.** A URA espera, o segurado espera, e a medição não vê nada.\n",
         "```",
         f"  {len(base):4d}  telas distintas",
         f"  {ocor:4d}  ocorrências",
         f"  {len(rotas):4d}  rotas afetadas",
         f"  {len(sem_just):4d}  🔴 sem `noop_justificado`",
         "```\n", "## Por onda — quem paga cada uma\n",
         "| onda | telas | o que ela cobre |", "|---|---:|---|"]
    QUEM = {"A": "allianz × residencial", "B": "allianz × auto",
            "C": "hdi × auto", "D": "yelum × auto", "E": "porto × auto",
            "F": "as que pontuam fora de A–E", "?": "🔴 NENHUMA — entrada inválida"}
    for o in sorted(por_onda):
        L.append(f"| **{o}** | {len(por_onda[o])} | {QUEM.get(o, '?')} |")
    ae = sum(len(por_onda[o]) for o in "ABCDE")
    L.append(f"\n📊 **{ae} em A–E · {len(por_onda.get('F', []))} na ONDA F**\n")

    L.append("## As telas, por onda\n")
    for o in sorted(por_onda):
        L.append(f"### ONDA {o} — {QUEM.get(o, '?')} · {len(por_onda[o])} telas\n")
        for t in sorted(por_onda[o],
                        key=lambda x: -len(base[x]["corpus"]))[:400]:
            e = base[t]
            marca = "" if e["just"] else "🔴 "
            L.append(f"- {marca}`{'/'.join(sorted(e['passos']))}` · "
                     f"{len(e['corpus'])}x · {len(e['rotas'])} rota(s) — "
                     f"*{t[:120]}*")
        L.append("")

    texto = "\n".join(L)
    print(texto)
    with open("../docs/canon/reports/BASE-DO-E13.md", "w",
              encoding="utf-8") as f:
        f.write(texto + "\n")
    # \U0001f534 tela sem onda e entrada invalida -- o arquivo nao pode nascer com uma
    return 1 if orfas else 0


if __name__ == "__main__":
    sys.exit(main())
