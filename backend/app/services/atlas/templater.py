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
    # O `(?=[\w-]*\d)` exige um DÍGITO no que vem depois da palavra.
    #
    # Sem ele, "protocolo aberto" virava "protocolo {PROTOCOLO}" — qualquer
    # palavra de 4+ letras era tratada como número de protocolo. E como
    # `_card_pii_clean` reprova todo texto que o templatize mudaria, uma carta
    # legítima como "o protocolo aberto na seguradora deve ser informado ao
    # segurado" era marcada como PII e nunca chegava ao RAG.
    #
    # É a mesma família do defeito do rótulo sem dois-pontos, encontrada no
    # mesmo dia (29/07/2026) por um subagente destilando o lote 002. Número de
    # protocolo e número de chassi SEMPRE têm dígito; prosa, não.
    (re.compile(r"\bprotocolo[:\s]*\#?\s*(?=[\w-]*\d)[\w\-]{4,}", re.IGNORECASE),
     "protocolo {PROTOCOLO}"),
    (re.compile(r"\bchassi[:\s]*(?=\w*\d)\w{6,}", re.IGNORECASE), "chassi {CHASSI}"),
]

# Rótulos de campo que costumam preceder um VALOR de cliente numa linha
# "Rótulo: valor" (Placa: QJQ0A91 / Modelo: Gol / Nome: ...).
#
# A segunda metade da lista veio das telas de COMPROVANTE, medidas em
# 28/07/2026. "Assistência: 8923467" (Yelum) e "Agendamento: 28/01/2026, entre
# 10h00 e 12h00" (Porto) não eram mascarados, e cada protocolo diferente virava
# uma TELA diferente: 18 nós na Yelum e 10 na Porto para o que é uma tela só.
# Mascarado o valor, o mapa volta a ter o tamanho da URA de verdade.
_LABELED_VALUE = re.compile(
    r"(?im)^(\s*[\*\-•]*\s*\*?(?:nome|modelo|placa|ve[íi]culo|cor|endere[çc]o|"
    r"cliente|segurado|cpf|cnpj|telefone|celular|marca|ano|cidade|estado|bairro|rua|"
    r"n[úu]mero|complemento|refer[êe]ncia|logradouro|"
    r"assist[êe]ncia|agendamento|protocolo|boleto|parcelas?|senha|ordem|"
    r"chamado|solicita[çc][ãa]o|atendimento|pedido|ap[óo]lice|sinistro|contrato|"
    r"data do (?:vencimento|pagamento(?: mensal)?)|"
    r"quantidade de parcelas(?: a pagar| restantes)?)\*?\s*:?\*?\s*)(.+)$"
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
        # SEM DOIS-PONTOS, o rótulo pode ser só a primeira palavra de uma frase.
        #
        # O `:` era opcional, e o `(.+)$` é guloso: "Boleto de seguro não pago
        # até a data limite leva ao cancelamento" virava "Boleto {VALOR}".
        # Como `_card_pii_clean` reprova todo texto que o templatize mudaria,
        # QUALQUER carta começando por boleto / sinistro / apólice / protocolo /
        # atendimento era marcada como PII e nunca chegava ao RAG. Medido em
        # 29/07/2026: 51 das 306 barradas — 17% — eram conhecimento legítimo
        # jogado fora, e nenhuma delas tinha dado de pessoa.
        #
        # Com dois-pontos é rótulo de formulário e o valor é do cliente. Sem
        # dois-pontos, só é valor se PARECER valor: começa com dígito
        # ("Assistência 8923467") ou é um código/nome em caixa alta
        # ("Placa QJQ0A91"). Prosa em minúscula é frase, não campo.
        if ":" not in m.group(1):
            primeira = val.split()[0]
            parece_valor = primeira[0].isdigit() or (
                len(primeira) >= 2 and primeira.upper() == primeira
                and any(c.isalnum() for c in primeira))
            if not parece_valor:
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


def _options_do_interativo(interactive: Optional[Dict]) -> List[str]:
    """Os títulos exatos de uma lista/botão do WhatsApp.

    Esta é a fonte da verdade e estava sendo ignorada. O evento guarda a
    estrutura que o WhatsApp mandou:

        {"kind": "list", "options": [
            {"title": "Abertura de sinistro",
             "description": "Batida ou acidente com envolvimento de terceiros"},
            {"title": "Carro reserva",
             "description": "Solicitar, prorrogar ou dúvidas com as locações"}]}

    O Tecelão lia o TEXTO RENDERIZADO e adivinhava quais linhas eram opção —
    e no render a lista vira título e descrição em linhas alternadas, sem
    marca. Resultado medido em 28/07/2026: a Porto ficou com 859 "opções" em
    353 telas, quase o dobro do real, porque as descrições viraram opções.

    E opção que não existe nunca é percorrida: cada descrição contada virava
    uma lacuna permanente, afundando a cobertura de todas as seguradoras que
    usam lista.
    """
    if not isinstance(interactive, dict):
        return []
    titulos: List[str] = []
    for op in interactive.get("options") or []:
        if isinstance(op, dict):
            t = str(op.get("title") or "").strip()
        else:
            t = str(op or "").strip()
        if t:
            titulos.append(t)
    return titulos


def screen_node(text: str, interactive: Optional[Dict] = None) -> Dict:
    """Constrói o nó canônico da tela (template + hash + kind + opções).

    Quando a tela veio como lista ou botão do WhatsApp, as opções saem da
    ESTRUTURA (`interactive`), não do texto. Só quando não há estrutura — URA
    de texto puro, como a da Allianz — é que o texto é interpretado.
    """
    from app.services.cartographer import classify_screen, parse_options
    from app.services.ura_map_service import node_hash

    template = templatize(text)

    estruturadas = _options_do_interativo(interactive)
    if estruturadas:
        # Os títulos também passam pelo templatize: uma lista pode trazer o
        # nome do segurado num item ("Confirmar João da Silva"), e PII não
        # entra no Atlas nem como rótulo de opção.
        options = _real_options([templatize(t) for t in estruturadas])
    else:
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
