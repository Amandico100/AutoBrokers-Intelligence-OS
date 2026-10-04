# -*- coding: utf-8 -*-
"""SPEC-128 G10 — a prova do Agger só está pronta quando TODAS as perguntas têm resposta.

A ficha (PLANO-MESTRE-MULTICALCULO §4, SPEC-128) diz "pronta quando: todos os E têm resposta;
E0, E2, E3, E5, E7, E16 e E20 respondidos com número". Um documento bonito que pula uma
pergunta passaria por qualquer revisão de leitura — este guarda conta.

Regra de cada seção `### E<n>`:
  - existe (E0 a E21, todas);
  - as sete com número exigem 📊 (medido, CLAUDE.md §12.1) E um comando ou tela entre crases
    (protocolo §0.4: número sem o comando ao lado é defeito);
  - "NÃO MEDIDA" é resposta legítima só fora das sete, e tem de dizer por quê.

Linhas de CONTROLE (CLAUDE.md §9.3): um documento sem o 📊 da E16 TEM de reprovar; um mínimo
completo TEM de passar — prova que o casador consegue ficar vermelho.
"""
from __future__ import annotations

import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOC = os.path.join(REPO, "docs", "canon", "programa-multicalculo", "A-PROVA-DO-AGGER.md")

TODAS = [f"E{i}" for i in range(22)]
COM_NUMERO = ["E0", "E2", "E3", "E5", "E7", "E16", "E20"]


def secoes(texto: str) -> dict:
    """`### E5 — ...` até o próximo `### ` ou `## `."""
    partes = {}
    marcas = list(re.finditer(r"^###\s+(E\d{1,2})\b.*$", texto, re.M))
    for i, m in enumerate(marcas):
        fim = len(texto)
        prox = re.search(r"^#{2,3}\s", texto[m.end():], re.M)
        if prox:
            fim = m.end() + prox.start()
        partes[m.group(1)] = texto[m.start():fim]
    return partes


def defeitos(texto: str) -> list:
    s = secoes(texto)
    out = []
    for e in TODAS:
        if e not in s:
            out.append(f"{e} ausente")
            continue
        corpo = s[e]
        if e in COM_NUMERO:
            if "📊" not in corpo:
                out.append(f"{e} sem número medido (📊)")
            if not re.search(r"`[^`\n]{3,}`", corpo):
                out.append(f"{e} sem o comando/tela entre crases")
            if re.search(r"N[ÃA]O MEDIDA", corpo):
                out.append(f"{e} declarada NÃO MEDIDA, mas a ficha exige número")
        elif re.search(r"N[ÃA]O MEDIDA", corpo) and not re.search(r"(?i)porque|por qu[eê]|motivo|exige|falta", corpo):
            out.append(f"{e} NÃO MEDIDA sem dizer por quê")
    return out


def _minimo_completo() -> str:
    linhas = ["# A prova"]
    for e in TODAS:
        linhas.append(f"### {e} — pergunta\n📊 1 coisa medida, `comando --x` (04/10)\n")
    return "\n".join(linhas)


def test_controle_documento_completo_passa():
    assert defeitos(_minimo_completo()) == []


def test_controle_sem_o_numero_da_E16_reprova():
    ruim = _minimo_completo().replace("### E16 — pergunta\n📊 1 coisa medida", "### E16 — pergunta\nalgo")
    d = defeitos(ruim)
    assert any("E16 sem número" in x for x in d), d


def test_controle_pergunta_faltando_reprova():
    ruim = _minimo_completo().replace("### E13 — pergunta", "### X13 — pergunta")
    assert "E13 ausente" in defeitos(ruim)


def test_controle_E20_nao_medida_reprova():
    ruim = _minimo_completo().replace("### E20 — pergunta\n📊 1 coisa medida, `comando --x` (04/10)",
                                      "### E20 — pergunta\n📊 `x` NÃO MEDIDA porque não deu")
    assert any("E20 declarada NÃO MEDIDA" in x for x in defeitos(ruim))


def test_a_prova_do_agger_esta_completa():
    assert os.path.exists(DOC), f"falta {DOC}"
    texto = open(DOC, encoding="utf-8").read()
    d = defeitos(texto)
    assert d == [], "\n".join(d)
