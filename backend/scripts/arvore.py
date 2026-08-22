"""A ÁRVORE — SPEC-084 §2.4 e §3.3. `medir_rota.py --exportar-arvore`.

> ## A URA é uma ÁRVORE. A unidade de trabalho é o NÓ, não a rota.
>
> ```
>                   [ tronco ]  ← vista por TODOS os serviços
>          Olá · Termo · CPF · Qual seguro
>                        │
>            ┌───────────┴───────────┐
>       [ galho AUTO ]        [ galho RESIDENCIAL ]   ← vista por um ramo
>            │                        │
>     ┌──────┴──────┐         ┌───────┴────────┐
>  guincho      chaveiro   eletricista   eletrodoméstico   ← FOLHA: um serviço
> ```

E daí saem três consequências:

**(a) Consertar um nó de tronco paga por TODAS as rotas daquela seguradora.**
**(b) A validade é por NÓ, não por rota** — uma tela vista hoje numa sessão de
     guincho está atualizada para o chaveiro também.
**(c) Consertar uma folha paga por uma rota só.** Por isso folha vem depois.

🔴 **É gerada em PYTHON, reusando o `_norm` real** — nunca em SQL. A SPEC-084 §3.3
prova por que: `_norm` é função Python, `unaccent` não existe neste banco, e
reimplementá-lo em SQL seria o segundo normalizador que o CLAUDE.md §5 veda.

🔴 **E `outros` NUNCA conta em `count(distinct servico)`.** É balde de
não-classificado: contá-lo faz a regra `serviços ≥ 3 → TRONCO` disparar com dois
serviços reais mais ruído.
"""

from __future__ import annotations

import collections
import json
import os
import sys
from typing import Any, Dict, List, NamedTuple, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import regua_motor as M   # noqa: E402
import zonas_do_acervo as Z  # noqa: E402
import replay as RP       # noqa: E402

TRONCO, GALHO, FOLHA = "TRONCO", "GALHO", "FOLHA"

# 🔴 A FRONTEIRA NAO E NO — e a SPEC-084 §2.2 e explicita sobre isso.
#
# 📊 Pela formula de retorno, a tela `"Vou transferir seu caso para um
#    especialista"` da allianz-residencial e a **PRIMEIRA da fila inteira**:
#    retorno 279, maior que qualquer no de tronco real.
#
# > ## Escrita como esta, a regra manda o executor transformar em passo, ANTES DE TUDO, a tela que ENTREGA o atendimento ao humano.
#
# Ela e catalogada como `FRONTEIRA`, vira gatilho de `pausar_e_chamar`, e **sai da
# fila de telas a mapear**. Nao e trabalho a fazer: e trabalho ja feito, do outro
# lado.
FRONTEIRA = "FRONTEIRA"


class No(NamedTuple):
    seguradora: str
    ramo: str
    texto: str
    servicos: Set[str]
    sessoes: Set[str]
    visto_por_ultimo: str
    classe: str
    rotas_que_passam: List[str]
    responde: Optional[str]      # o passo que casa, ou None

    @property
    def retorno(self) -> int:
        """`retorno(nó) = (nº de rotas que PASSAM por ele) × (nº de sessões)`.

        📊 Exemplo da SPEC-084 §4.3: a tela do CPF da Allianz (5 serviços × 78
        sessões = 390) vem antes da tela do número da residência (4 × 72 = 288).

        ⚠️ **"Rotas que passam" são os SERVIÇOS das sessões em que a tela apareceu**
        — não os passos que a respondem. A primeira versão usava `rotas_que_passam`
        (= os serviços cujo passo casa) e o retorno de **toda tela órfã dava ZERO**,
        porque órfã é justamente a que nenhum passo responde.

        🔴 O efeito era o pior possível: **a fila de trabalho ordenava por retorno,
        e todo o trabalho a fazer ficava empatado em zero.** O número existe para
        dizer o que consertar primeiro; zerado, ele não dizia nada.
        """
        return max(1, len(self.servicos)) * len(self.sessoes)


def montar(seguradora: str, ramo: str) -> List[No]:
    """A árvore de `(seguradora, ramo)`, uma linha por tela distinta."""
    linhas = RP.carregar_corpus(seguradora, ramo)
    if not linhas:
        return []
    ref = M.resolve_playbook_ref(seguradora, ramo)
    pb = M.get_playbook(ref) if ref else None
    servicos_do_pb = sorted((pb or {}).get("subservices") or {})

    por_tela: Dict[str, Dict[str, Any]] = {}
    for l in linhas:
        chave = M._norm(l["text"])
        d = por_tela.setdefault(chave, {"texto": l["text"], "servicos": set(),
                                        "sessoes": set(), "ts": ""})
        s = l.get("servico")
        # 🔴 o balde de não-classificado NÃO conta como serviço
        if s and not str(s).startswith("?"):
            d["servicos"].add(s)
        d["sessoes"].add(l["session_id"])
        d["ts"] = max(d["ts"], l.get("wa_timestamp") or "")

    fora: List[No] = []
    for chave, d in por_tela.items():
        n = len(d["servicos"])
        classe = TRONCO if n >= 3 else (GALHO if n == 2 else FOLHA)

        # ⚠️ O viés declarado (§3.3): uma tela vista numa sessão só PARECE folha
        #    mesmo sendo tronco. Quem responde a MUITAS rotas é tronco por
        #    construção — e quem responde é o MOTOR, não a contagem.
        respondem = [s for s in servicos_do_pb
                     if M.match_ura_step(pb, d["texto"], subservice=s)] if pb else []
        if len(respondem) >= 3 and classe == FOLHA:
            classe = TRONCO

        # 🔴 a tela de transferencia sai da fila -- ela ja tem destino
        if Z.e_fronteira(seguradora, M._norm(d["texto"])):
            classe = FRONTEIRA

        passo = None
        if classe == FRONTEIRA:
            passo = "pausar_e_chamar (FRONTEIRA)"
        elif respondem:
            p = M.match_ura_step(pb, d["texto"], subservice=respondem[0])
            passo = (p or {}).get("step")

        fora.append(No(seguradora, ramo, d["texto"], d["servicos"], d["sessoes"],
                       d["ts"], classe, respondem, passo))
    return sorted(fora, key=lambda x: -x.retorno)


def imprimir(nos: List[No], *, so_orfas: bool = False, limite: int = 40) -> str:
    if not nos:
        return "  (sem corpus)"
    L = [f"{'classe':7s} {'srv':>3s} {'ses':>4s} {'retorno':>8s} {'passo':28s} tela"]
    L.append("─" * 132)
    mostrados = 0
    for n in nos:
        if so_orfas and n.responde:
            continue
        if mostrados >= limite:
            L.append(f"  ... e mais {sum(1 for x in nos if not (so_orfas and x.responde)) - limite}")
            break
        mostrados += 1
        L.append(f"{n.classe:7s} {len(n.servicos):3d} {len(n.sessoes):4d} {n.retorno:8d} "
                 f"{(n.responde or '🔴 ORFA'):28s} {' '.join(n.texto.split())[:62]}")
    c = collections.Counter(n.classe for n in nos)
    orfas = [n for n in nos if not n.responde]
    L.append("")
    L.append(f"  {len(nos)} telas distintas · TRONCO {c[TRONCO]} · GALHO {c[GALHO]} "
             f"· FOLHA {c[FOLHA]}")
    L.append(f"  🔴 {len(orfas)} telas SEM PASSO — somam retorno de "
             f"{sum(n.retorno for n in orfas)}")
    return "\n".join(L)


def ordem_de_trabalho() -> List[Tuple[int, str, str, str, str]]:
    """A fila da SPEC-084: por PROFUNDIDADE, e dentro dela por RETORNO.

    ```
    ONDA 1 · o TRONCO de cada seguradora     ← paga por TODAS as rotas dela
    ONDA 2 · os GALHOS (auto / residencial)  ← paga por metade
    ONDA 3 · as FOLHAS, por demanda medida   ← paga por uma
    ```

    🔴 A demanda ordena **dentro** de cada onda, nunca entre ondas. 📊 `chaveiro`
    é folha de 10 seguradoras: sem o tronco de cada uma, ela não fecha em nenhuma.
    """
    fila: List[Tuple[int, str, str, str, str]] = []
    for seg in M.seguradoras():
        for ramo in ("auto", "residencial"):
            for n in montar(seg, ramo):
                if n.responde:
                    continue
                onda = 1 if n.classe == TRONCO else (2 if n.classe == GALHO else 3)
                fila.append((onda, seg, ramo, n.classe, n.texto))
    return sorted(fila, key=lambda x: (x[0], x[1]))
