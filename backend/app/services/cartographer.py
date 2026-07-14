"""CARTÓGRAFO v1 (SPEC-034 Onda 2) — motor de exploração de URAs de seguradoras.

Conceito validado no mercado (Botium Crawler): conversar com o bot da seguradora
clicando/digitando cada opção e montar a árvore completa do fluxo (Mapa de URA).

Este módulo é o MOTOR PURO (decisões, freios, construção do mapa) — testável
offline. A fiação com a instância Evolution GO dedicada (número exclusivo de
exploração que o founder vai prover) entra num router fino por cima deste motor.

FREIOS INEGOCIÁVEIS (hard-coded, fora do alcance de LLM):
1. NUNCA responde afirmativamente a uma tela de confirmação final — responde a
   opção de SAIR/CANCELAR e marca o nó como 'finalize'.
2. NUNCA entra em ramo de SINISTRO além do primeiro nó (registra que existe e sai).
3. Máximo de mensagens por sessão de exploração (padrão 60) — estourou, encerra.
4. Se a URA pedir um dado que não temos, aborta o ramo educadamente ('needs_data').
5. Horário permitido (madrugada por padrão) — verificado pelo runner, não aqui.

Escopo atual: ASSISTÊNCIA via WhatsApp (decisão do founder 13/07 — sinistro e
vidros-portal ficam para depois).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.services.ura_map_service import node_hash, normalize_screen_text

MAX_MESSAGES_PER_SESSION = 60

# Telas de confirmação FINAL (freio 1) — mesmos padrões dos finalize_anchors.
_FINALIZE_RE = re.compile(
    r"podemos confirmar|posso confirmar|tudo est[áa] correto|como voc[êe] quer prosseguir"
    r"|confirmar o agendamento|posso continuar o agendamento|deseja confirmar",
    re.IGNORECASE,
)
_ABORT_PREFERENCES = ["Sair e não agendar", "Sair", "Cancelar", "Não", "Voltar", "0", "9"]

# Ramos proibidos de explorar a fundo (freio 2).
_SINISTRO_RE = re.compile(r"sinistro|colis[ãa]o com terceiro|aviso de acidente", re.IGNORECASE)

# Pedidos de dados que sabemos preencher com a apólice de teste.
_DATA_REPLIES = [
    (re.compile(r"cpf ou cnpj|digite o cpf|informe o cpf", re.IGNORECASE), "cpf"),
    (re.compile(r"placa do ve[íi]culo|informe a placa", re.IGNORECASE), "placa"),
    (re.compile(r"cep\b", re.IGNORECASE), "cep"),
]


def parse_options(text: str) -> List[str]:
    """Extrai os rótulos clicáveis/numerados de uma tela renderizada.
    Cobre: 'Botão 1: X', listas 'Opção: X', menus numerados '1 - X'."""
    labels: List[str] = []
    for m in re.finditer(r"bot[ãa]o\s*\d+\s*:\s*([^\n|]+)", text, re.IGNORECASE):
        labels.append(m.group(1).strip())
    for m in re.finditer(r"(?:^|\n)\s*(\d{1,2})\s*[-–.)]\s*([^\n|]{2,60})", text):
        labels.append(m.group(2).strip())
    seen, out = set(), []
    for lab in labels:
        k = lab.lower()
        if k not in seen:
            seen.add(k)
            out.append(lab)
    return out


def classify_screen(text: str, options: List[str]) -> str:
    if _FINALIZE_RE.search(text):
        return "finalize"
    if options:
        return "menu"
    if "?" in text or re.search(r"informe|digite|qual", text, re.IGNORECASE):
        return "pergunta"
    return "informativo"


def new_exploration(*, insurer_key: str, ramo: str, test_data: Dict[str, str]) -> Dict[str, Any]:
    """test_data: {'cpf': ..., 'placa': ..., 'cep': ...} da apólice de teste."""
    return {
        "insurer_key": insurer_key, "ramo": ramo, "test_data": dict(test_data or {}),
        "state": "exploring",  # exploring | done | aborted
        "nodes": {}, "root": None,
        "frontier": [],           # [(node_id, label_ainda_nao_explorado)]
        "current_path": [],       # labels escolhidos até aqui (p/ replay do ramo)
        "visited_edges": set(),   # {(node_id, label)} — em runtime vira list p/ JSON
        "msg_count": 0, "last_node": None,
        "transcript": [], "started_at": datetime.now(timezone.utc).isoformat(),
    }


def _pick_abort_reply(options: List[str]) -> str:
    for pref in _ABORT_PREFERENCES:
        for lab in options:
            if pref.lower() in lab.lower():
                return lab
    return _ABORT_PREFERENCES[0]


def handle_insurer_message(exp: Dict[str, Any], text: str) -> Optional[str]:
    """Processa uma tela da URA e devolve a resposta do Cartógrafo (ou None p/
    silêncio). Aplica os freios e registra o nó no mapa em construção."""
    exp["msg_count"] = int(exp.get("msg_count") or 0) + 1
    exp.setdefault("transcript", []).append(
        {"direction": "in", "text": str(text)[:2000], "at": datetime.now(timezone.utc).isoformat()}
    )

    # Freio 3: orçamento de mensagens da sessão.
    if exp["msg_count"] > MAX_MESSAGES_PER_SESSION:
        exp["state"] = "aborted"
        exp["abort_reason"] = "max_messages"
        return None

    options = parse_options(text)
    kind = classify_screen(text, options)
    h = node_hash(text)
    node_id = h
    if node_id not in exp["nodes"]:
        exp["nodes"][node_id] = {
            "text": normalize_screen_text(text)[:400], "kind": kind,
            "options": [{"label": lab, "reply": lab, "leads_to": None} for lab in options],
            "hash": h,
        }
        if exp.get("root") is None:
            exp["root"] = node_id
    # Liga a aresta percorrida: o nó anterior levou até aqui.
    prev = exp.get("last_node")
    prev_reply = exp.get("last_reply")
    if prev and prev_reply and prev in exp["nodes"]:
        for opt in exp["nodes"][prev]["options"]:
            if opt["label"].lower() == str(prev_reply).lower():
                opt["leads_to"] = node_id
    exp["last_node"] = node_id

    reply = _decide_reply(exp, node_id, text, options, kind)
    if reply is not None:
        exp["last_reply"] = reply
        exp["transcript"].append(
            {"direction": "out", "text": reply, "at": datetime.now(timezone.utc).isoformat()}
        )
    return reply


def _decide_reply(exp: Dict[str, Any], node_id: str, text: str,
                  options: List[str], kind: str) -> Optional[str]:
    # Freio 1: confirmação final → SAIR, nunca confirmar. Marca e encerra o ramo.
    if kind == "finalize":
        exp["nodes"][node_id]["kind"] = "finalize"
        exp["state"] = "done" if not exp.get("frontier") else "exploring"
        return _pick_abort_reply(options)

    # Perguntas de dados: respondemos com a apólice de teste (freio 4 se faltar).
    for rx, slot in _DATA_REPLIES:
        if rx.search(text):
            value = str((exp.get("test_data") or {}).get(slot) or "").strip()
            if value:
                return value
            exp["nodes"][node_id]["kind"] = "needs_data"
            return _pick_abort_reply(options) if options else None

    if not options:
        return None  # informativo — a URA segue sozinha

    visited = exp.setdefault("visited_edges", set())
    if isinstance(visited, list):  # sessão restaurada de JSON
        visited = set(tuple(v) for v in visited)
        exp["visited_edges"] = visited

    for lab in options:
        # Freio 2: ramo de sinistro — registra que existe e NÃO entra.
        if _SINISTRO_RE.search(lab):
            visited.add((node_id, lab))
            continue
        if (node_id, lab) not in visited:
            visited.add((node_id, lab))
            exp.setdefault("current_path", []).append(lab)
            return lab

    # Nada inexplorado aqui → encerra o ramo educadamente.
    exp["state"] = "done"
    return _pick_abort_reply(options)


def has_unexplored(exp: Dict[str, Any]) -> bool:
    """Ainda existem opções seguras não percorridas? (Base do multi-pass: o
    founder exige TODAS as combinações, não só uma rota por sessão.)"""
    visited = exp.get("visited_edges") or set()
    if isinstance(visited, list):
        visited = set(tuple(v) for v in visited)
    for node_id, node in (exp.get("nodes") or {}).items():
        if node.get("kind") in ("finalize", "needs_data"):
            continue
        for opt in node.get("options") or []:
            lab = str(opt.get("label") or "")
            if _SINISTRO_RE.search(lab):
                continue
            if (node_id, lab) not in visited:
                return True
    return False


def exploration_to_map(exp: Dict[str, Any]) -> Dict[str, Any]:
    """Converte a exploração no formato canônico do ura_map_service."""
    return {"root": exp.get("root"), "nodes": exp.get("nodes") or {},
            "meta": {"insurer_key": exp.get("insurer_key"), "ramo": exp.get("ramo"),
                     "msg_count": exp.get("msg_count"),
                     "started_at": exp.get("started_at")}}
