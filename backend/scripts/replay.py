"""O REPLAY — SPEC-083 §3.3, Bloco B. A única medida que reproduziu.

Cada tela do corpus roda pelo **MOTOR** (`match_ura_step`) e cai numa classe:

```
RESPONDIDA      casou um passo que devolve resposta          ✅
NOOP            casou um passo `noop`                        ✅
ORFA_INOCUA     não casou, e `_tela_pede_alguma_coisa` = False   ⚪ tolerável
ORFA_FUNCIONAL  não casou, e `_tela_pede_alguma_coisa` = True    🔴 é o defeito
```

🔴 **O eixo B vale 35 dos 100 pontos porque esta é a única medida que reproduziu.**
O juiz reconstruiu o replay da régua à mão e chegou às mesmas 20 respondidas da
auditoria. É o que separa a régua (20 respondidas) de `mapfre-auto` (0 de 29).

🔴 **E o discriminador é o do PRODUTO, nunca um novo.**
`_tela_pede_alguma_coisa(playbook, texto) -> bool` mora em
`insurer_dispatch_service.py:1974` e lê os `finalize_anchors` do próprio corredor.
*"Um segundo discriminador divergiria em silêncio"* (SPEC-083 §3.3).
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import regua_motor as M   # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(RAIZ, "tests", "corpus", "telas_reais")

RESPONDIDA = "RESPONDIDA"
NOOP = "NOOP"
ORFA_INOCUA = "ORFA_INOCUA"
ORFA_FUNCIONAL = "ORFA_FUNCIONAL"


class Tela(NamedTuple):
    session_id: str
    wa_timestamp: str
    texto: str
    classe: str
    passo: Optional[str]


class Replay(NamedTuple):
    rota: Any
    telas: List[Tela]
    amostra: str                 # 📊 "AMOSTRA: 5 de 137 sessoes"
    sessoes_no_corpus: int
    sessoes_no_acervo: Optional[int]

    @property
    def respondidas(self) -> int:
        return sum(1 for t in self.telas if t.classe == RESPONDIDA)

    @property
    def noops(self) -> int:
        return sum(1 for t in self.telas if t.classe == NOOP)

    @property
    def orfas_funcionais(self) -> List[Tela]:
        return [t for t in self.telas if t.classe == ORFA_FUNCIONAL]

    @property
    def orfas_inocuas(self) -> int:
        return sum(1 for t in self.telas if t.classe == ORFA_INOCUA)

    @property
    def pedem_algo(self) -> int:
        """Telas que PEDEM alguma coisa — o denominador do determinismo."""
        return self.respondidas + len(self.orfas_funcionais)

    @property
    def determinismo(self) -> Optional[float]:
        """`respondidas ÷ (telas que pedem algo)`. `None` quando não há denominador."""
        if not self.pedem_algo:
            return None
        return self.respondidas / self.pedem_algo


def carregar_corpus(seguradora: str, ramo: str) -> List[Dict[str, Any]]:
    caminho = os.path.join(CORPUS, f"{seguradora}-{ramo}.jsonl")
    if not os.path.exists(caminho):
        return []
    linhas = []
    with open(caminho, encoding="utf-8") as fh:
        for l in fh:
            if l.strip():
                linhas.append(json.loads(l))
    return linhas


def replay(rota, *, sessoes_no_acervo: Optional[int] = None) -> Replay:
    """Roda o corpus de `(seguradora, ramo)` pelo motor, filtrando por serviço."""
    pb = M.get_playbook(rota.ref)
    todas = carregar_corpus(rota.seguradora, rota.ramo)

    # 🔴 SO AS SESSOES QUE PASSARAM POR ESTA ROTA.
    #
    # A SPEC-084 §5.1① e literal: *"Ache as sessoes do corpus que passam por ESTA
    # ROTA"*. Sem o filtro, o replay roda o corpus inteiro de (seguradora, ramo)
    # contra uma rota so -- e as telas de OUTRO servico viram orfas funcionais
    # dela. 📊 Medido: 20 orfas para `maquina_de_lavar` onde a SPEC-083 §4.1
    # espera **1**, porque `allianz-residencial` tem SEIS servicos num corpus.
    #
    # ⚠️ E a sessao SEM servico determinado FICA: ela e tronco (Termo, CPF,
    # endereco) e vale para todas as rotas daquele ramo. Descarta-la perderia
    # justamente as telas que a §2.4 da 084 chama de "as que pagam por todas".
    linhas = [l for l in todas
              if l.get("servico") in (None, rota.servico)]
    telas: List[Tela] = []
    for l in linhas:
        texto = l["text"]
        # 🔴 O MOTOR, com o `subservice` da rota — é ele que aplica
        #    `only_subservices`. Um replay sem o filtro mede outro corredor.
        passo = M.match_ura_step(pb, texto, subservice=rota.servico)
        if passo is not None:
            classe = NOOP if passo.get("noop") else RESPONDIDA
            nome = passo.get("step")
        else:
            pede = M.tela_pede_alguma_coisa(pb, texto)
            classe = ORFA_FUNCIONAL if pede else ORFA_INOCUA
            nome = None
        telas.append(Tela(l["session_id"], l.get("wa_timestamp") or "",
                          texto, classe, nome))

    sessoes = len({l["session_id"] for l in linhas})
    # ⚠️ *"Todo ponto que depende do corpus carrega a amostra"* (§3.3). Sem isto,
    #    ruído de amostragem lê-se como defeito de rota.
    amostra = (f"AMOSTRA: {sessoes} de {sessoes_no_acervo} sessoes"
               if sessoes_no_acervo else f"AMOSTRA: {sessoes} sessoes")
    return Replay(rota, telas, amostra, sessoes, sessoes_no_acervo)


def imprimir_detalhado(r: Replay, limite: int = 12) -> str:
    L = [f"{r.rota}",
         f"  {r.amostra}",
         f"  telas no corpus ......... {len(r.telas)}",
         f"  RESPONDIDA .............. {r.respondidas}",
         f"  NOOP .................... {r.noops}",
         f"  ORFA_INOCUA ............. {r.orfas_inocuas}",
         f"  ORFA_FUNCIONAL .......... {len(r.orfas_funcionais)}   <-- o defeito"]
    d = r.determinismo
    L.append(f"  determinismo ............ "
             + ("sem denominador (nenhuma tela pede algo)" if d is None
                else f"{100*d:.0f}%  ({r.respondidas} de {r.pedem_algo})"))
    if r.orfas_funcionais:
        L.append("\n  as orfas funcionais:")
        for t in r.orfas_funcionais[:limite]:
            L.append(f"    [{t.session_id}] {' '.join(t.texto.split())[:96]}")
        if len(r.orfas_funcionais) > limite:
            L.append(f"    ... e mais {len(r.orfas_funcionais)-limite}")
    return "\n".join(L)
