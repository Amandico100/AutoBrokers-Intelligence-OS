# -*- coding: utf-8 -*-
"""🔴 A LISTA DE COLETA — SPEC-084 BLOCO 5.

> ## `SEM_CORPUS`, não `NAO_RESPONDE`.

📊 A SPEC-083 nomeou o erro: **13 rotas mandadas para coleta com o material já
no banco.** E esta execução o cometeu de novo, de outra forma — `?tecnico`
tinha 109 linhas escondidas atrás do balde de não-classificado, e duas rotas
apareciam `SEM_CORPUS` com o acervo cheio (P-084-19).

Por isso este arquivo **mede antes de pedir**. Uma rota só entra na lista se:

```
1. o corpus dela está vazio                      (a régua diz SEM_CORPUS)
2. E o ACERVO da seguradora também não a tem      <- a pergunta que faltava
```

Se o acervo tem e o corpus não, o problema é do CLASSIFICADOR, não da coleta —
e a linha sai com esse diagnóstico em vez de virar pedido.

## O roteiro, no formato que funcionou com a Yelum

```
1. o número da assistência da seguradora
2. o caminho de telas até o ponto desconhecido
3. 🔴 a LINHA DE CONTROLE — uma segunda rodada com um serviço cujo desfecho já
      conhecemos, para provar que a URA não mudou entre as duas
4. o que se espera aprender
```

🔴 **A linha de controle é o que dá direito à conclusão.** Sem ela, uma tela
nova pode ser "a URA mudou" ou "esse serviço é diferente", e não há como saber
qual — é a mesma regra do §9.2 do CLAUDE.md.
"""

from __future__ import annotations

import collections
import os
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import regua_motor as M     # noqa: E402
import replay as RP         # noqa: E402
import rubrica as RB        # noqa: E402
import padroes_de_servico as PS   # noqa: E402

# 📊 A demanda MEDIDA, lida da fonte -- {servico: escolhido}. E ela ordena a
#    lista: coletar guincho (72 escolhas) antes de vidros (2) e o obvio, e o
#    obvio precisa estar escrito para nao se perder na pressa.
_DEMANDA = {sv: esc for sv, esc, _card in PS.DEMANDA_MEDIDA}


def _servicos_no_acervo(seguradora: str) -> Set[str]:
    """O que o ACERVO da seguradora tem, olhando o corpus regerado.

    ⚠️ O corpus é o espelho do acervo depois do classificador. Se um serviço
    aparece aqui, ele **existe** — e pedir coleta dele seria o erro da §7.2.
    """
    fora: Set[str] = set()
    for ramo in ("auto", "residencial"):
        for l in RP.carregar_corpus(seguradora, ramo):
            sv = (l.get("servico") or "").lstrip("?").strip()
            if sv:
                fora.add(sv)
    return fora


def _caminho_ate_o_menu(pb: Dict[str, Any]) -> List[str]:
    """Os passos que o corredor percorre ANTES de escolher o serviço.

    📊 Lido do próprio playbook, na ordem em que o motor os avalia — é o
    caminho que a corretora vai repetir no acionamento de coleta.
    """
    marcos = ("abertura", "termo", "saudacao", "pedir_cpf", "identificacao",
              "informar_nome", "perfil", "menu_tipo_seguro", "menu_qual_seguro",
              "confirmar_veiculo", "continuar_com_placa", "menu_raiz",
              "menu_inicial", "menu_como_ajudar", "menu_servico", "menu_atendimento")
    fora = []
    for p in pb.get("ura_steps") or []:
        nome = str(p.get("step") or "")
        if any(nome.startswith(m) for m in marcos):
            fora.append(nome)
    # ordem estável e sem repetição
    vistos, ordenado = set(), []
    for n in fora:
        if n not in vistos:
            vistos.add(n)
            ordenado.append(n)
    return ordenado[:8]


def _linha_de_controle(seguradora: str, servico_pedido: str,
                       notas: List[Any]) -> Optional[Tuple[str, int]]:
    """🔴 O serviço da MESMA seguradora cuja rota já pontua — e a nota dele.

    É com ele que a segunda rodada é feita. Se ele der o mesmo desfecho de
    antes, o que a primeira rodada mostrou é do SERVIÇO; se der diferente, a
    URA mudou e nenhuma das duas conclusões vale.
    """
    candidatos = [
        (n.rota.servico, n.pontos)
        for n in notas
        if n.rota.seguradora == seguradora
        and n.rota.servico != servico_pedido
        and n.patamar not in ("SEM_CORPUS", "NAO_RESPONDE")
    ]
    if not candidatos:
        return None
    return max(candidatos, key=lambda kv: kv[1])


def gerar() -> str:
    notas = [RB.medir(r) for r in M.rotas()]
    L: List[str] = []
    L.append("# A lista de coleta — SPEC-084 BLOCO 5\n")
    L.append(f"> Gerado do corpus e do corredor · commit `{_commit()}`\n")
    L.append("🔴 **Uma rota só entra aqui se o CORPUS está vazio E o ACERVO da")
    L.append("seguradora também não a tem.** Se o acervo tem e o corpus não, o")
    L.append("problema é do classificador — e a linha sai com esse diagnóstico,")
    L.append("não como pedido de coleta. 📊 Foi assim que `tecnico` (109 linhas)")
    L.append("quase virou pedido de coleta com o material já no banco.\n")

    sem_corpus = [n for n in notas if n.patamar == "SEM_CORPUS"]
    por_seg: Dict[str, List[Any]] = collections.defaultdict(list)
    for n in sem_corpus:
        por_seg[n.rota.seguradora].append(n)

    falsos: List[str] = []
    pedidos = 0

    for seg in sorted(por_seg):
        no_acervo = _servicos_no_acervo(seg)
        rotas = sorted(por_seg[seg], key=lambda n: (n.rota.ramo, n.rota.servico))
        # separa o que é coleta de verdade do que é defeito do classificador
        reais = sorted([n for n in rotas if n.rota.servico not in no_acervo],
                       key=lambda n: -_DEMANDA.get(n.rota.servico, 0))
        artefato = [n for n in rotas if n.rota.servico in no_acervo]
        for n in artefato:
            falsos.append(f"{seg}/{n.rota.ramo}/{n.rota.servico}")
        if not reais:
            continue

        pb = M.get_playbook(reais[0].rota.ref)
        L.append(f"\n## {seg.upper()}\n")
        L.append(f"**1 · O número:** `insurer_contact_ref = "
                 f"{pb.get('insurer_contact_ref')!r}` — ⚠️ o número real vem da "
                 f"configuração da corretora, não do código.\n")
        caminho = _caminho_ate_o_menu(pb)
        L.append("**2 · O caminho até o ponto desconhecido:**\n")
        L.append("```")
        L.append("  " + "\n  -> ".join(caminho) if caminho else "  (o corredor não tem passos de entrada — ver PENDENCIAS)")
        L.append(f"  -> [ AQUI: escolher o serviço ]")
        L.append("```\n")

        ctrl = _linha_de_controle(seg, reais[0].rota.servico, notas)
        if ctrl:
            L.append(f"**3 · 🔴 A LINHA DE CONTROLE:** repetir a rodada com "
                     f"**`{ctrl[0]}`**, que hoje pontua **{ctrl[1]}/96**.\n")
            L.append(f"   Se `{ctrl[0]}` der o mesmo desfecho de hoje, o que a "
                     f"primeira rodada mostrar é do SERVIÇO. Se der diferente, a "
                     f"URA mudou — e nenhuma das duas conclusões vale.\n")
        else:
            L.append("**3 · 🔴 SEM LINHA DE CONTROLE POSSÍVEL:** nenhuma rota "
                     "desta seguradora pontua hoje. ⚠️ Isso significa que a "
                     "coleta aqui **não terá como distinguir** 'a URA mudou' de "
                     "'este serviço é diferente'. Colete o serviço mais comum "
                     "PRIMEIRO, e ele passa a ser o controle dos próximos.\n")

        L.append("**4 · O que se espera aprender, por rota:**\n")
        L.append("| ramo | serviço | demanda | o que falta ver |")
        L.append("|---|---|---:|---|")
        for n in reais:
            pedidos += 1
            tem_menu = (pb.get("subservice_menu_map") or {}).get(n.rota.servico)
            falta = ("a tela SEGUINTE ao clique no menu — é ela que separa este "
                     "serviço dos outros" if tem_menu else
                     "🔴 o RÓTULO do menu, que o corredor ainda não tem")
            L.append(f"| {n.rota.ramo} | {n.rota.servico} | "
                     f"{_DEMANDA.get(n.rota.servico, 0)} | {falta} |")

    if falsos:
        L.append("\n---\n")
        L.append("## ⚠️ NÃO SÃO COLETA — o acervo TEM, o corpus não\n")
        L.append("📊 Estas rotas aparecem `SEM_CORPUS` na régua, mas a seguradora")
        L.append("**já tem sessões desse serviço no acervo**. O problema é o")
        L.append("classificador ou a cota por rota, não a falta de material.")
        L.append("Mandá-las para coleta é o erro que a SPEC-083 nomeou.\n")
        for f in sorted(falsos):
            L.append(f"- `{f}`")

    L.append("\n---\n")
    L.append(f"📊 **{pedidos} rotas pedem coleta de verdade** · "
             f"{len(falsos)} eram artefato do medidor · "
             f"{len(sem_corpus)} apareciam SEM_CORPUS na régua.")
    return "\n".join(L)


def _commit() -> str:
    import subprocess
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True,
                              cwd=os.path.dirname(os.path.dirname(
                                  os.path.abspath(__file__)))).stdout.strip() or "?"
    except Exception:  # noqa: BLE001
        return "?"


if __name__ == "__main__":
    print(gerar())
