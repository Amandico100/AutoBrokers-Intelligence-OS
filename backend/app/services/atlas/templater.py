"""SPEC-038 ATLAS — Templater (Bloco B).

Transforma a tela crua observada em TEMPLATE reutilizável: troca a PII do
cliente por placeholders ({CPF}/{PLACA}/{NOME}/{ENDERECO}/{PROTOCOLO}/{DATA}/
{NUM}), preservando a ESTRUTURA (a inteligência que é nossa e global). É o que
garante a política do conhecimento global: o mapa NUNCA guarda dado de cliente.

Reusa os helpers canônicos: node_hash/normalize_screen_text (ura_map_service),
parse_options/classify_screen (cartographer).
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

# Ordem importa: específico → genérico.
_PII_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), "{CPF}"),
    (re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"), "{CNPJ}"),
    (re.compile(r"\b[A-Z]{3}[-\s]?\d[A-Z0-9]\d{2}\b"), "{PLACA}"),   # Mercosul e antiga
    (re.compile(r"\b\d{5}-?\d{3}\b"), "{CEP}"),
    (re.compile(r"(?<!\d)(?:\+?55\s?)?\(?\d{2}\)?\s?9?\d{4}[-\s]?\d{4}(?!\d)"), "{TELEFONE}"),
    (re.compile(r"\b\d{2}/\d{2}/\d{2,4}\b"), "{DATA}"),
    (re.compile(r"\bprotocolo[:\s]*\#?\s*[\w\-]{4,}", re.IGNORECASE), "protocolo {PROTOCOLO}"),
    (re.compile(r"\bchassi[:\s]*\w{6,}", re.IGNORECASE), "chassi {CHASSI}"),
]

# Rótulos de campo que costumam preceder um VALOR de cliente numa linha
# "Rótulo: valor" (Placa: QJQ0A91 / Modelo: Gol / Nome: ...).
_LABELED_VALUE = re.compile(
    r"(?im)^(\s*[\*\-•]?\s*(?:nome|modelo|placa|ve[íi]culo|cor|endere[çc]o|"
    r"cliente|segurado|cpf|cnpj|telefone|celular|marca|ano|cidade|bairro|rua)\s*:?\s*)(.+)$"
)


def templatize(text: str) -> str:
    """Devolve a tela com a PII trocada por placeholders. Determinístico."""
    s = str(text or "")
    for rx, repl in _PII_PATTERNS:
        s = rx.sub(repl, s)
    # "Placa: QJQ0A91" → "Placa: {VALOR}" (o valor após o rótulo é dado do cliente)
    def _mask_labeled(m: re.Match) -> str:
        val = m.group(2).strip()
        # não mascara se o "valor" já é placeholder ou é curtíssimo/opção
        if val.startswith("{") or len(val) <= 1:
            return m.group(0)
        return f"{m.group(1)}{{VALOR}}"
    s = _LABELED_VALUE.sub(_mask_labeled, s)
    return s


# Linhas que NÃO são escolha de menu (eco de dados do cliente): "Placa: {X}",
# "Modelo: Gol", "Telefone {X}" — viram ruído de opção. Filtradas.
_DATA_ECHO = re.compile(
    r"^(?:placa|modelo|ve[íi]culo|telefone|celular|nome|cor|marca|ano|cidade|"
    r"bairro|rua|endere[çc]o|cpf|cnpj|cliente|segurado|chassi|protocolo)\b[:\s]",
    re.IGNORECASE)


def _real_options(labels: List[str]) -> List[str]:
    """Descarta 'opções' que na verdade são linhas de dados (Placa:/Modelo:/...)
    ou que contêm placeholder de valor — não são cliques de menu."""
    out = []
    for lab in labels:
        if _DATA_ECHO.match(lab.strip()):
            continue
        if "{VALOR}" in lab or "{PLACA}" in lab or "{CPF}" in lab or "{TELEFONE}" in lab:
            continue
        out.append(lab)
    return out


def screen_node(text: str) -> Dict:
    """Constrói o nó canônico da tela (template + hash + kind + opções)."""
    from app.services.cartographer import classify_screen, parse_options
    from app.services.ura_map_service import node_hash

    template = templatize(text)
    options = _real_options(parse_options(template))
    kind = classify_screen(template, options)
    # marca app nativo/humano quando reconhecível (mesma semântica do cartógrafo)
    up = template.upper()
    if "FORMULARIO NATIVO" in up:
        kind = "app_form"
    return {
        "hash": node_hash(template),
        "text": template[:400],
        "kind": kind,
        "options": [{"label": o, "reply": o, "leads_to": None} for o in options],
    }


def infer_ramo_servico(labels: List[str], full_text: str) -> Tuple[str, str]:
    """Infere ramo/serviço PELA ROTA (labels), não pelo número (uma seguradora
    atende vários ramos no mesmo WhatsApp)."""
    blob = (" ".join(labels) + " " + str(full_text or "")).lower()
    servico = ""
    for key, terms in (
        ("guincho", ("guincho", "reboque", "remocao", "remoção")),
        ("chaveiro", ("chaveiro", "chave", "trancad")),
        ("bateria", ("bateria", "carga")),
        ("pane_seca", ("pane seca", "combustivel", "combustível")),
        ("pneu", ("pneu", "troca de pneu", "estepe")),
        ("vidros", ("vidro", "para-brisa", "parabrisa")),
        ("residencial", ("encanador", "eletricista", "chaveiro residencial", "residencia", "residência")),
    ):
        if any(t in blob for t in terms):
            servico = key
            break
    ramo = "residencial" if servico == "residencial" or "residenc" in blob else "auto"
    if any(t in blob for t in ("sinistro", "colisao", "colisão", "acidente")):
        servico = servico or "sinistro"
    return ramo, servico
