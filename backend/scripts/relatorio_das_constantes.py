# -*- coding: utf-8 -*-
"""🔴 O RELATÓRIO DAS CONSTANTES — SPEC-084.1 FASE 1 §3.3

> ## Navegar e decidir têm a MESMA FORMA no código, e resultados opostos na
> ## vida do segurado.

`Continuar`, `Voltar`, `Sair` movem o fluxo. `Até 10 anos`, `Condomínio`,
`Problemas no motor` **afirmam um fato sobre o cliente** — e a tecla errada não
trava: abre o chamado errado, que só aparece quando o prestador chega.

📊 Os oito defeitos que a CLAUDE.md §9.5 registra são todos desta classe.

## O que este relatório responde, e por que ele não é a varredura

⚠️ `conferir_respostas.py --todas` já devolve **ZERO** — mas ele só consegue
julgar a constante cuja tela **está no corpus**. Uma constante que decide numa
tela que o corpus não viu é invisível para ele.

**O relatório mede as três populações separadas:**

```
NAVEGA          a tecla escolhida é Continuar/Voltar/Sair/...    → não decide
DECIDE, VISTA   a tela está no corpus, e a regra B a julgou      → coberta
DECIDE, CEGA    🔴 a tela NÃO está no corpus                     → ninguém julgou
```

🔴 **A terceira é o buraco.** Ela não aparece em medição nenhuma, e é a mesma
forma dos oito: *"apareciam verdes em toda medição"*.
"""

from __future__ import annotations

import collections
import os
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import regua_motor as M            # noqa: E402
import replay as RP                # noqa: E402
import conferir_respostas as CR    # noqa: E402


def _telas_do_corredor(ref: str) -> List[str]:
    """As telas do corpus que ESTE corredor pode ver."""
    for r in M.rotas():
        if r.ref == ref:
            return [l["text"] for l in RP.carregar_corpus(r.seguradora, r.ramo)]
    return []


class Constante:
    __slots__ = ("ref", "passo", "reply", "classe", "porque", "justificada")

    def __init__(self, ref, passo, reply, classe, porque, justificada):
        self.ref, self.passo, self.reply = ref, passo, reply
        self.classe, self.porque, self.justificada = classe, porque, justificada


def levantar() -> List[Constante]:
    fora: List[Constante] = []
    cache: Dict[str, List[str]] = {}
    for ref, pb in M.CP._PLAYBOOKS.items():
        telas = cache.setdefault(ref, _telas_do_corredor(ref))
        for p in pb.get("ura_steps") or []:
            if p.get("noop"):
                continue
            reply = str(p.get("reply") or "")
            if not reply or "{" in reply:
                continue          # noop e slot não são constante
            passo = str(p.get("step") or "?")
            just = bool(p.get("constante_justificada"))

            # 🔴 A tela desta constante, e o casamento tem de ser POR PASSO e
            #    por QUALQUER subserviço: um passo com `only_subservices` só casa
            #    dentro do ofício dele, e perguntar por um só subserviço daria
            #    "cega" a um passo que a varredura ENXERGA.
            vistas = []
            for t in telas:
                for sv in (pb.get("subservices") or {}):
                    m = M.match_ura_step(pb, t, subservice=sv)
                    if m and m.get("step") == passo:
                        vistas.append(t)
                        break

            if not vistas:
                fora.append(Constante(
                    ref, passo, reply, "CEGA",
                    "a tela desta constante NAO esta no corpus — a varredura "
                    "nao tem como julga-la", just))
                continue

            # 🔴 A PERGUNTA E A DA VARREDURA, chamada -- nao reescrita.
            #    📊 Este bloco JA foi uma copia da regra B, e a copia dizia
            #    "61 decidem, ZERO sem justificativa" enquanto a varredura
            #    acusava 15. Era o C3 de novo: a regua reimplementando o motor.
            decide = False
            porque = "navega (a opcao escolhida move o fluxo)"
            for t in vistas:
                motivo = CR.decide_pelo_cliente(t, reply)
                if motivo:
                    decide, porque = True, motivo
                    break
            fora.append(Constante(ref, passo, reply,
                                  "DECIDE" if decide else "NAVEGA", porque, just))
    return fora


def relatorio() -> Tuple[str, int]:
    cs = levantar()
    L: List[str] = []
    L.append("# O relatório das constantes — SPEC-084.1 FASE 1\n")
    L.append("> **Navegar e decidir têm a mesma forma no código.** Este relatório")
    L.append("> separa as duas, e nomeia a terceira população: a que ninguém julga.\n")

    por = collections.Counter(c.classe for c in cs)
    L.append("```")
    L.append(f"  {len(cs):4d}  constantes no produto")
    L.append(f"  {por['NAVEGA']:4d}  NAVEGAM        Continuar / Voltar / Sim / Não ...")
    L.append(f"  {por['DECIDE']:4d}  DECIDEM        escolhem entre alternativas de CONTEÚDO")
    L.append(f"  {por['CEGA']:4d}  🔴 CEGAS       a tela NÃO está no corpus")
    L.append("```\n")

    decidem = [c for c in cs if c.classe == "DECIDE"]
    sem_just = [c for c in decidem if not c.justificada]
    L.append("## 1 · As que DECIDEM — cobertas pela varredura\n")
    L.append(f"📊 **{len(decidem)} constantes decidem**, e "
             f"**{len(decidem) - len(sem_just)} têm `constante_justificada`**.\n")
    if sem_just:
        L.append("🔴 **E estas decidem SEM justificativa — a varredura devia tê-las")
        L.append("pego, e o relatório existe para conferir que ela pegou:**\n")
        for c in sem_just:
            L.append(f"- `{c.ref}` · **{c.passo}** → `{c.reply}` — {c.porque}")
        L.append("")
    else:
        L.append("✅ **Nenhuma decide sem justificativa.** A varredura e o")
        L.append("relatório concordam — e é isso que se esperava, porque")
        L.append("`conferir_respostas.py` já devolve zero.\n")

    cegas = [c for c in cs if c.classe == "CEGA"]
    L.append("## 2 · 🔴 As CEGAS — o buraco que nenhuma medição mostra\n")
    L.append(f"📊 **{len(cegas)} constantes respondem uma tela que o corpus NÃO TEM.**")
    L.append("A varredura não as julga; a régua não as vê; o comparador não as conta.")
    L.append("**São exatamente a forma dos oito defeitos da §9.5:** *apareciam")
    L.append("verdes em toda medição*.\n")
    L.append("⚠️ Isto **não** quer dizer que estejam erradas — quer dizer que")
    L.append("**ninguém sabe**. Cada uma precisa da tela para ser julgada, e a")
    L.append("tela vem de coleta ou de uma sessão nova.\n")
    jc = sum(1 for c in cegas if c.justificada)
    L.append(f"📊 Destas, **{jc} têm `constante_justificada`** escrita mesmo sem a")
    L.append(f"tela, e **{len(cegas) - jc} não têm**.\n")

    por_ref = collections.Counter(c.ref for c in cegas if not c.justificada)
    L.append("**Onde elas se concentram:**\n")
    L.append("| corredor | constantes cegas sem justificativa |")
    L.append("|---|---:|")
    for ref, n in por_ref.most_common(14):
        L.append(f"| `{ref}` | {n} |")
    L.append("")
    return "\n".join(L), len(sem_just)


if __name__ == "__main__":
    texto, pendentes = relatorio()
    print(texto)
    with open("../docs/canon/reports/RELATORIO-DAS-CONSTANTES.md", "w",
              encoding="utf-8") as f:
        f.write(texto + chr(10))
    sys.exit(1 if pendentes else 0)
