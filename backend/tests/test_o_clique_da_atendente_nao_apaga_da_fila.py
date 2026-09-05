# -*- coding: utf-8 -*-
"""🔴 O clique da atendente NÃO pode apagar o caso da Fila.

===============================================================================
🔄 MIGRADO EM 05/09/2026 PELA SPEC-097 (emenda E13) — o que mudou e por quê
===============================================================================

⚠️ **Este guarda era regex sobre `app/api/dashboard/atendimentos/route.ts`.** Ele
provava que o filtro não era `.eq('unblock_state','travado')` — e não provava
NADA sobre a Fila. É exatamente o defeito que o CLAUDE.md §9.4 nomeia: *"teste
que chama o regex guarda o regex"*. 📊 A SPEC-096 pagou por isso com 72
asserções verdes sobre um agendamento que nunca chegava ao cliente.

**O que a lição virou (§9.3 — a lição MIGRA, não morre):**

```
ANTES  re.search(r"\\.in\\(['\"]unblock_state['\"], \\[.*travado", fonte_da_rota)
DEPOIS EXECUTAR o read model sobre um dublê e perguntar:
       o caso que a atendente DESTRAVOU continua na Fila?
```

O read model é executado por `scripts/a-operacao-tem-uma-casa.test.mjs
--fila-json` — o MESMO arnês do guarda da tela, não uma segunda cópia em python
(CLAUDE.md §5: consolidar antes de duplicar). Quando a SPEC-097 escrever
`lib/atendimento/casos.ts::projetarCasos`, este guarda passa a medir a projeção
sozinho; até lá ele mede a rota, que é o read model de hoje. **A pergunta é a
mesma nos dois casos.**

⛔ **O que NÃO migrou para cá, de propósito:** a regra nova da 097 — *"só
desfecho ESCRITO tira da Fila; o PARADO fica"* (R1). Ela nasce VERMELHA e mora
em `scripts/a-operacao-tem-uma-casa.test.mjs` [2], que é o guarda do gate zero.
Um guarda que já existia e estava verde não é o lugar de uma regra que ainda não
foi construída — misturar as duas coisas apagaria a fronteira entre "isto
regrediu" e "isto ainda não foi feito".

A checagem de FORMA da declaração continua aqui, ao lado da de comportamento,
porque as duas pegam coisas diferentes: a de forma nomeia o defeito histórico
(`.eq` no lugar de `.in`) mesmo quando o dublê não tem uma linha que o exponha.

===============================================================================
📊 O DEFEITO ORIGINAL, achado em 26/08/2026 por auditoria da SPEC-093
===============================================================================

    app/api/dashboard/atendimentos/route.ts:160
        .eq('unblock_state', 'travado')        <-- igualdade EXATA

O BLOCO C da SPEC-093 passou a gravar `assumido_por_humano` quando alguém
destrava pelo WhatsApp. Com a igualdade exata, **bastava a atendente mandar
"só um minuto" para o caso travado sumir da única Fila que existe** — assim
que o Redis expirasse (TTL de 6h, `dispatch_router.py:77`).

🔴 E não voltava nunca: `_fechar_travamento` (`dispatch_router.py:1126-1128`)
filtra `['travado','retomado_pelo_robo']` **de propósito**, para não pisar em
`assumido_por_humano`. Estado terminal e invisível.

⚠️ **E é a mesma classe de defeito que `e527705` consertou na véspera** — o
commit chama-se literalmente *"o desfecho parava de apagar da Fila quem ainda
espera gente"*. Consertado em 25/08, reintroduzido por outra porta em 26/08.

## O motivo de produto, que é o que decide

O Founder desenhou assim, com estas palavras: *"não é para ela assumir o
atendimento. É para ele apenas destravar e monitorar."*

> **A atendente DESTRAVA. Ela não assume.** O caso continua sendo do robô,
> continua em voo, e continua precisando de olho. Tirá-lo da Fila é dizer que
> alguém tomou conta — e ninguém tomou.

E o docstring de `_fechar_travamento:1114` já dizia: *"um travamento que o
acionamento não resolveu **continua na Fila**, que é o produto inteiro desta
SPEC"*.
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # backend/
PROJETO = os.path.dirname(RAIZ)
ROTA = os.path.join(PROJETO, "app", "api", "dashboard", "atendimentos", "route.ts")
PROJECAO = os.path.join(PROJETO, "lib", "atendimento", "casos.ts")
ARNES = os.path.join(PROJETO, "scripts", "a-operacao-tem-uma-casa.test.mjs")

OK = FAIL = 0


def certo(cond, rotulo, detalhe=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  ok    %s" % rotulo)
    else:
        FAIL += 1
        print("  FALHA %s" % rotulo + ("\n        %s" % detalhe if detalhe else ""))
    return bool(cond)


def par(cond_reprovou, rotulo, detalhe=""):
    """A linha de controle: `cond_reprovou` é True quando o guarda ACUSOU."""
    global OK, FAIL
    if cond_reprovou:
        OK += 1
        print("  ok    PAR %s — o guarda acusou" % rotulo)
    else:
        FAIL += 1
        print("  FALHA PAR %s — o guarda NÃO acusou; ele não guarda nada" % rotulo
              + ("\n        %s" % detalhe if detalhe else ""))
    return bool(cond_reprovou)


def _sem_comentario(fonte: str) -> str:
    """O TypeScript sem `//` e sem `/* */`.

    ⚠️ O texto acima do filtro EXPLICA o defeito e cita o padrão proibido —
    lê-lo seria aprovar a prosa (SPEC-086 pagou isso sete vezes)."""
    sem_bloco = re.sub(r"/\*.*?\*/", " ", fonte, flags=re.S)
    return "\n".join(l.split("//", 1)[0] for l in sem_bloco.splitlines())


def _fonte_do_read_model():
    """A projeção da 097 quando ela existir; a rota de hoje enquanto não.

    🔴 Devolve `(caminho, texto)`. Sem isto, o guarda ficaria VERDE POR VACUIDADE
    no dia em que a consulta mudasse de arquivo (E14 — foi o que ia acontecer com
    três asserções da SPEC-086)."""
    for caminho in (PROJECAO, ROTA):
        if os.path.exists(caminho):
            texto = _sem_comentario(io.open(caminho, encoding="utf-8").read())
            if "unblock_state" in texto:
                return caminho, texto
    return None, None


def _rodar_o_read_model():
    """EXECUTA o read model sobre o dublê e devolve o JSON.

    🔴 É o mesmo arnês de `scripts/a-operacao-tem-uma-casa.test.mjs` — um motor
    de leitura, dois guardas (CLAUDE.md §5)."""
    if not os.path.exists(ARNES):
        return None, "o arnês %s não existe" % ARNES
    try:
        r = subprocess.run(["node", ARNES, "--fila-json"], cwd=PROJETO,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=300)
    except FileNotFoundError as exc:
        return None, "AMBIENTE: `node` não está no PATH desta máquina (%s)" % exc
    except subprocess.TimeoutExpired:
        return None, "o arnês não terminou em 300s"
    if r.returncode != 0:
        return None, "o arnês saiu com %d: %s" % (r.returncode, (r.stderr or "")[-600:])
    try:
        return json.loads(r.stdout), None
    except ValueError as exc:
        return None, "o arnês não devolveu JSON (%s): %s" % (exc, r.stdout[:400])


def _fila_medida(dados):
    """A lente que este guarda usa: a projeção da 097 se ela já existir, senão a
    rota. Devolve `(nome_da_lente, items)`."""
    proj = dados.get("projecao") or {}
    if "items" in proj:
        return "projetarCasos", proj["items"]
    return "atendimentos/route.ts", (dados.get("rota") or {}).get("items", [])


def _os_destravados_estao_na_fila(items, runs):
    """A régua. Devolve a lista de problemas — e é ela que o PAR reprova.

    ⚠️ "Estar na Fila" é o que a tela mostra: `stage !== 'concluido'`
    (`AttendanceQueueClient.tsx:98`). Um caso que chega como 'concluido' está
    fora do quadro, mesmo constando do payload."""
    problemas = []
    destravados = [r for r in runs if r.get("unblock_state") == "assumido_por_humano"]
    if not destravados:
        problemas.append("o dublê não tem NENHUM run com `assumido_por_humano` — "
                         "sem essa linha, esta régua não mede nada")
        return problemas
    for run in destravados:
        achados = [i for i in items
                   if str(i.get("key", "")).endswith(run["id"])
                   or (i.get("case_id") and i["case_id"] == run.get("case_id"))
                   or i.get("work_run_id") == run["id"]]
        if not achados:
            problemas.append(
                "o caso destravado pela atendente (run %s, `assumido_por_humano`) NÃO está "
                "na Fila — é o defeito de 26/08/2026, reintroduzido: ela mandou 'só um "
                "minuto' e o caso sumiu do único quadro que existe" % run["id"])
            continue
        fora = [a for a in achados if a.get("stage") == "concluido"]
        if fora:
            problemas.append(
                "o caso destravado (run %s) está na Fila como 'concluido' — a tela filtra "
                "`stage !== 'concluido'` (AttendanceQueueClient.tsx:98), então ele está "
                "FORA do quadro. A atendente DESTRAVA; ela não assume." % run["id"])
    return problemas


def main() -> int:
    print("\n[1] O DESTRAVADO CONTINUA NA FILA — medido EXECUTANDO o read model")

    dados, erro = _rodar_o_read_model()
    if dados is None:
        certo(False, "o read model executa sobre o dublê", erro)
    else:
        lente, items = _fila_medida(dados)
        runs = (dados.get("mundo") or {}).get("work_runs", [])
        print("        lente: %s · %d itens · %d runs no dublê"
              % (lente, len(items), len(runs)))
        certo(bool(items), "o read model devolveu itens (senão nada foi medido)")
        problemas = _os_destravados_estao_na_fila(items, runs)
        certo(not problemas,
              "o caso com `unblock_state='assumido_por_humano'` CONTINUA na Fila",
              "\n        ".join(problemas))

        # ---- PAR: uma Fila-controle de onde ele sumiu -------------------
        par(bool(_os_destravados_estao_na_fila([], runs)),
            "fila-controle VAZIA (o destravado sumiu)")
        par(bool(_os_destravados_estao_na_fila(
                [{"key": "travado-wr-2", "stage": "concluido"}],
                [{"id": "wr-2", "unblock_state": "assumido_por_humano"}])),
            "fila-controle que devolve o destravado como 'concluido' (fora do quadro)")
        par(bool(_os_destravados_estao_na_fila(
                [{"key": "travado-wr-2", "stage": "precisa_de_voce"}], [])),
            "mundo-controle SEM run destravado (a régua acusa que não mediu nada)")

    # ------------------------------------------------------------------
    print("\n[2] A FORMA DA DECLARAÇÃO — o filtro não é igualdade exata")
    # 🔴 §9.4, a exceção escrita: aqui o alvo é a FORMA da consulta declarada,
    #    não o comportamento (que o [1] mede). As duas pegam coisas diferentes:
    #    o [1] só vê o defeito se o dublê tiver a linha que o expõe.
    caminho, fonte = _fonte_do_read_model()
    if fonte is None:
        certo(False, "o read model que consulta `unblock_state` foi encontrado",
              "nem `%s` nem `%s` consultam `unblock_state` — a consulta mudou de lugar e "
              "este guarda ficaria VERDE POR VACUIDADE (E14)"
              % (os.path.relpath(PROJECAO, PROJETO), os.path.relpath(ROTA, PROJETO)))
    else:
        print("        lendo: %s" % os.path.relpath(caminho, PROJETO))
        igualdade_exata = re.search(
            r"\.eq\(\s*['\"]unblock_state['\"]\s*,\s*['\"]travado['\"]\s*\)", fonte)
        certo(igualdade_exata is None,
              "o filtro NÃO é `.eq('unblock_state','travado')`",
              "igualdade exata apaga da Fila o caso que a atendente destravou, "
              "assim que o Redis expira. Use `.in(...)`.")
        usa_in = re.search(
            r"\.in\(\s*['\"]unblock_state['\"]\s*,\s*\[[^\]]*['\"]travado['\"]", fonte)
        certo(usa_in is not None,
              "o filtro usa `.in('unblock_state', [...])` incluindo 'travado'")
        certo("assumido_por_humano" in fonte,
              "`assumido_por_humano` está entre os estados que a Fila mostra",
              "é o estado que o BLOCO C da SPEC-093 grava quando um humano "
              "destrava pelo WhatsApp")

    # ------------------------------------------------------------------
    print("\n[3] LINHA DE CONTROLE — o guarda CONSEGUE ficar vermelho?")
    falso = "  .eq('unblock_state', 'travado')\n"
    par(re.search(r"\.eq\(\s*['\"]unblock_state['\"]\s*,\s*['\"]travado['\"]\s*\)",
                  falso) is not None,
        "o padrão proibido É detectável quando está presente",
        "se este controle falhar, os testes de cima passam por vacuidade e "
        "não guardam nada (CLAUDE.md §9.3)")
    par(re.search(r"\.in\(\s*['\"]unblock_state['\"]\s*,\s*\[[^\]]*['\"]travado['\"]",
                  falso) is None,
        "o padrão BOM não é detectado num texto que não o tem",
        "um casador que casa com tudo aprova qualquer coisa")
    # 🔴 e o cortador CORTA: sem isto, o [2] leria o comentário que explica o defeito.
    bruto = "// .eq('unblock_state', 'travado')  <- o defeito de 26/08\nconst x = 1;\n"
    par(re.search(r"\.eq\(\s*['\"]unblock_state['\"]", _sem_comentario(bruto)) is None,
        "o cortador de comentário CORTA (o padrão só no `//` não conta)")

    print("\n  %d ok, %d falhas" % (OK, FAIL))
    return 1 if FAIL else 0


def test_o_clique_da_atendente_nao_apaga_da_fila():
    """Roda a si mesmo num subprocesso: ele chama `node`, e o processo do pytest
    não precisa herdar nada disso."""
    r = subprocess.run([sys.executable, os.path.abspath(__file__)], cwd=RAIZ,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    assert r.returncode == 0, (r.stdout[-4000:] + r.stderr[-1500:])


if __name__ == "__main__":
    sys.exit(main())
