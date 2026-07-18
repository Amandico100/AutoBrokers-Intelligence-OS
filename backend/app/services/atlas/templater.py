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
from typing import Dict, List, Optional, Tuple

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
    r"(?im)^(\s*[\*\-•]*\s*\*?(?:nome|modelo|placa|ve[íi]culo|cor|endere[çc]o|"
    r"cliente|segurado|cpf|cnpj|telefone|celular|marca|ano|cidade|estado|bairro|rua|"
    r"n[úu]mero|complemento|refer[êe]ncia|logradouro)\*?\s*:?\*?\s*)(.+)$"
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
    node = {
        "hash": node_hash(template),
        "text": template[:400],
        "kind": kind,
        "options": [{"label": o, "reply": o, "leads_to": None} for o in options],
    }
    if kind == "pergunta":
        hint = answer_hint(template)
        if hint:
            node["answer_hint"] = hint
    return node


# O que o AGENTE deve responder numa pergunta aberta (founder: "respostas com
# exemplos, o atendente já sabe o que precisa"). Determinístico, sem PII.
_ANSWER_HINTS: List[Tuple[re.Pattern, str, str]] = [
    (re.compile(r"cpf|cnpj", re.IGNORECASE), "{CPF}", "CPF/CNPJ do titular da apólice (só números)"),
    (re.compile(r"placa", re.IGNORECASE), "{PLACA}", "Placa do veículo (ex.: ABC1D23) — vem da InfoCap"),
    (re.compile(r"telefone|celular|n[úu]mero (?:de|para) contato", re.IGNORECASE), "{TELEFONE}", "Telefone do cliente com DDD"),
    (re.compile(r"\bcep\b", re.IGNORECASE), "{CEP}", "CEP do local (8 dígitos)"),
    (re.compile(r"complemento", re.IGNORECASE), "{COMPLEMENTO}", "Apto/bloco/casa — ou 'não tem'"),
    (re.compile(r"refer[êe]ncia", re.IGNORECASE), "{REFERENCIA}", "Ponto de referência próximo (mercado, posto...)"),
    (re.compile(r"endere[çc]o|localiza[çc][ãa]o|onde (?:o ve[íi]culo|o carro|voc[êe]) est[áa]", re.IGNORECASE),
     "{ENDERECO}", "Endereço completo: rua, número, bairro, cidade - UF"),
    (re.compile(r"nome", re.IGNORECASE), "{NOME}", "Nome completo de quem acompanha no local"),
    (re.compile(r"\bdata\b|\bdia\b", re.IGNORECASE), "{DATA}", "Data (dd/mm/aaaa)"),
    (re.compile(r"motivo|conte o que|descreva", re.IGNORECASE), "{DESCRICAO}", "Descrição curta do ocorrido"),
]


def answer_hint(question_text: str) -> Optional[Dict[str, str]]:
    """Para telas-pergunta (sem botões): o placeholder e a instrução do que o
    agente/atendente deve responder. None quando não reconhecido."""
    for rx, ph, instr in _ANSWER_HINTS:
        if rx.search(str(question_text or "")):
            return {"placeholder": ph, "instrucao": instr}
    return None


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
