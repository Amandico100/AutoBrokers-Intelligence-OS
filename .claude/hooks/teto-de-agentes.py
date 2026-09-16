#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PROTOCOLO AAA v12 §10 — o teto de agentes por sessão, aplicado pelo harness.

Hook PreToolUse[Agent] do Claude Code. Conta as chamadas da ferramenta Agent na sessão
e BLOQUEIA a partir da (TETO+1)-ésima. O executor do AAA FAST tem direito a: 1 juiz +
1 lente do dado (gatilho) + 1 confirmação (gatilho) + 1 investigador read-only = 4.
O 5º pedido é o sintoma de "estourou, vou chamar mais gente" — e é isso que o v12 proíbe.

Ajuste por variável de ambiente: AAA_FAST_TETO_DE_AGENTES (padrão 4).
Este script nunca pode derrubar a sessão: qualquer erro interno → exit 0 (deixa passar).
"""
import json
import os
import sys
import tempfile


def main():
    try:
        dados = json.load(sys.stdin)
    except Exception:
        return 0
    if dados.get("tool_name") != "Agent":
        return 0
    try:
        teto = int(os.environ.get("AAA_FAST_TETO_DE_AGENTES", "4"))
        sessao = str(dados.get("session_id") or "sem-id").replace("/", "_")
        arquivo = os.path.join(tempfile.gettempdir(), "aaa-fast-agentes-%s.txt" % sessao)
        n = 0
        if os.path.exists(arquivo):
            with open(arquivo, encoding="utf-8") as f:
                n = int((f.read() or "0").strip() or 0)
        n += 1
        with open(arquivo, "w", encoding="utf-8") as f:
            f.write(str(n))
        if n > teto:
            sys.stderr.write(
                "⛔ PROTOCOLO AAA v12 §10: teto de %d agentes por sessão atingido — este é o %dº pedido e foi "
                "BLOQUEADO. A resposta a 'estourou' nunca é mais um agente: entregue a fatia verde, registre o que "
                "resta no relatório (handoff) e siga. Se um gatilho da §8 exige mais um agente, o Founder sobe "
                "AAA_FAST_TETO_DE_AGENTES na sessão.\n" % (teto, n))
            return 2
        if n == teto:
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": "⚠️ AAA v12 §10: este é o %dº e ÚLTIMO agente permitido nesta sessão." % n,
                }
            }))
        return 0
    except Exception:
        return 0


if __name__ == "__main__":
    sys.exit(main())
