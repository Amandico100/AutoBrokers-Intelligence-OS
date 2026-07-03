"""Divisor de balões (SPEC-017 P2 / S17-9) — PURO.

Humanização: resposta longa vira 2–3 balões curtos, como humano digita.
Regras:
- alvo ~300 chars por balão (limite duro 500);
- NUNCA quebrar no meio de lista/checklist: bloco com linhas iniciadas por
  -, *, •, dígito+'.' ou '|' (tabela) fica inteiro num balão próprio;
- quebra preferencial em parágrafo (linha em branco), depois em fim de frase;
- máximo de 4 balões (acima disso, mantém o restante junto no último).
"""

from __future__ import annotations

import re
from typing import List

TARGET_LEN = 300
HARD_LEN = 500
MAX_BALLOONS = 4

_LIST_LINE_RE = re.compile(r"^\s*([-*•]|\d{1,2}[.)]|\|)")
_SENTENCE_END_RE = re.compile(r"(?<=[.!?…])\s+")


def _is_list_block(block: str) -> bool:
    lines = [ln for ln in block.splitlines() if ln.strip()]
    if not lines:
        return False
    listish = sum(1 for ln in lines if _LIST_LINE_RE.match(ln))
    return listish >= max(1, len(lines) // 2)


def _split_long_text(text: str) -> List[str]:
    """Divide texto corrido por fim de frase respeitando TARGET_LEN."""
    sentences = _SENTENCE_END_RE.split(text.strip())
    parts: List[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence.strip()
        if len(candidate) <= TARGET_LEN or not current:
            current = candidate
        else:
            parts.append(current)
            current = sentence.strip()
    if current:
        parts.append(current)
    return parts


def split_whatsapp_balloons(text: str) -> List[str]:
    raw = str(text or "").strip()
    if not raw:
        return []
    if len(raw) <= TARGET_LEN:
        return [raw]

    blocks = [b.strip() for b in re.split(r"\n\s*\n", raw) if b.strip()]
    balloons: List[str] = []
    current = ""

    def _flush():
        nonlocal current
        if current.strip():
            balloons.append(current.strip())
        current = ""

    for block in blocks:
        if _is_list_block(block):
            # Lista/checklist/tabela: balão próprio, nunca fatiada.
            _flush()
            balloons.append(block)
            continue
        candidate = f"{current}\n\n{block}".strip() if current else block
        if len(candidate) <= TARGET_LEN:
            current = candidate
            continue
        _flush()
        if len(block) <= HARD_LEN:
            balloons.append(block)
        else:
            balloons.extend(_split_long_text(block))
    _flush()

    if len(balloons) > MAX_BALLOONS:
        head = balloons[: MAX_BALLOONS - 1]
        tail = "\n\n".join(balloons[MAX_BALLOONS - 1:])
        balloons = head + [tail]
    return balloons
