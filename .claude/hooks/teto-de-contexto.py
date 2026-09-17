#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""PROTOCOLO AAA v12 §5.2/§10 — o teto de CONTEXTO do executor, lembrado pelo harness.

Hook PreToolUse[Edit|Write|MultiEdit|NotebookEdit]. Lê o fim do transcrito da própria sessão
(~/.claude/projects/<projeto>/<session_id>.jsonl), pega o contexto do último turno
(input + cache_write + cache_read) e, acima do teto, injeta um aviso no contexto do modelo
a CADA edição: "feche a fatia, commite, handoff, sessão nova". Não bloqueia; avisa: da fatia seguinte em diante,
quem escreve é um builder subagente fresco (v12.1 §5.2). 📊 Na EXTRA-001.3 a regra escrita não bastou:
o executor seguiu até 649 k na mesma sessão e a segunda fatia custou ≈ o dobro.

Ajuste: AAA_FAST_TETO_DE_CONTEXTO (padrão 300000). Qualquer erro interno → exit 0.
"""
import json
import os
import sys


def contexto_atual(caminho):
    tam = os.path.getsize(caminho)
    with open(caminho, "rb") as f:
        f.seek(max(0, tam - 400_000))
        cauda = f.read().decode("utf-8", errors="replace")
    ultimo = 0
    for linha in cauda.splitlines():
        if '"usage"' not in linha or '"assistant"' not in linha:
            continue
        try:
            o = json.loads(linha)
        except ValueError:
            continue
        u = (o.get("message") or {}).get("usage") or {}
        if u:
            ultimo = u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0) + u.get("cache_read_input_tokens", 0)
    return ultimo


def main():
    try:
        dados = json.load(sys.stdin)
        if dados.get("tool_name") not in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
            return 0
        teto = int(os.environ.get("AAA_FAST_TETO_DE_CONTEXTO", "300000"))
        sessao = str(dados.get("session_id") or "")
        caminho = dados.get("transcript_path") or ""
        if not caminho or not os.path.exists(caminho):
            raiz = os.path.join(os.path.expanduser("~"), ".claude", "projects")
            for pasta in os.listdir(raiz) if os.path.isdir(raiz) else []:
                c = os.path.join(raiz, pasta, sessao + ".jsonl")
                if os.path.exists(c):
                    caminho = c
                    break
        if not caminho or not os.path.exists(caminho):
            return 0
        ctx = contexto_atual(caminho)
        if ctx > teto:
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": (
                    "🔴 PROTOCOLO AAA v12 §5.2/§10: o contexto desta sessão está em %dk (teto %dk). "
                    "Feche a FATIA verde (commit + handoff ≤ 20 linhas no §12 do relatório) e DELEGUE a próxima fatia "
                    "a UM builder subagente fresco (Opus 5 xhigh) com o pacote: card, unidades, arquivos, handoff, "
                    "gates. Você continua nesta sessão como gerente: provas, juiz, conserto. Nunca sessão nova." % (ctx // 1000, teto // 1000)),
            }}))
        return 0
    except Exception:
        return 0


if __name__ == "__main__":
    sys.exit(main())
