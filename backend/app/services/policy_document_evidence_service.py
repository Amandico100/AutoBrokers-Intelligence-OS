"""Official policy document evidence orchestration.

R1C.1: this module does not create a parallel RAG/parser/storage. It
coordinates the existing DocumentService/MinIO extraction path and the existing
ingestion path for InfoCap official policy PDFs, then builds short page-based
evidence snippets for the Smith runtime.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import tempfile
import unicodedata
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)


POLICY_DOCUMENT_STATES = {
    "source_available",
    "fetching",
    "fetched",
    "direct_extracting",
    "docling_pending",
    "parsed",
    "evidence_ready",
    "source_unavailable",
    "source_fetch_failed",
    "document_not_policy_evidence",
    "low_confidence",
    "conflict_requires_human",
}

OFFICIAL_POLICY_DOCUMENT_TYPE = "official_policy_document"
OFFICIAL_POLICY_DOCUMENT_SOURCE = "official_policy_document"
OFFICIAL_POLICY_PROVIDER = "infocap"
MAX_EVIDENCE_TEXT_CHARS = 700
# 🔴 O corretor pediu "leia o PDF inteiro". Os trechos por regex respondem o que
# o regex previu; o TEXTO da apólice responde o que ele perguntar. O limite é de
# contexto, não de política: uma apólice residencial tem ~4 páginas.
MAX_DOCUMENT_TEXT_CHARS = 60_000
#: 🔴 O teto de itens de evidência. Era **40** até 14/09/2026, escolhido quando
#: o extrator lia 10 linhas por apólice. 📊 SPEC-EXTRA-001.1 BLOCO D: a Allianz
#: condomínio real produz **22** itens estruturados e a HDI **20** — e os
#: fragmentos de cláusula/exclusão vinham DEPOIS, no mesmo teto. Com 40, uma
#: apólice de 21 coberturas perdia trecho de cláusula em silêncio.
MAX_EVIDENCE_ITEMS = 60

_INTENT_TERMS = (
    "cobertura",
    "coberturas",
    "cobre",
    "coberto",
    "garantia",
    "garantias",
    "assistencia",
    "assistencia residencial",
    "eletricista",
    "encanador",
    "chaveiro",
    "franquia",
    "lmi",
    "limite",
    "importancia segurada",
    "clausula",
    "clausulas",
    "exclusao",
    "exclusoes",
    "condicao",
    "condicoes",
    "riscos cobertos",
    "danos eletricos",
    # SPEC-016.1 D9: pedido de detalhe completo também dispara o documento.
    "detalhe",
    "detalhar",
    "detalhada",
    "todas as informacoes",
    "informacoes completas",
    "informacoes dessa apolice",
    "informacoes da apolice",
    "baixe a apolice",
    "baixar a apolice",
    "tudo sobre a apolice",
)

_EVIDENCE_PATTERNS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("coverage", ("cobertura", "coberturas", "garantia", "garantias", "riscos cobertos", "danos eletricos")),
    ("assistance", ("assistencia", "servicos emergenciais", "eletricista", "chaveiro", "encanador")),
    ("deductible", ("franquia", "dedutivel")),
    ("premium", ("premio", "premios", "custo do seguro")),
    ("installment", ("parcela", "parcelas", "vencimento", "quitacao")),
    ("lmi", ("lmi", "limite maximo", "importancia segurada", "limite de indenizacao")),
    ("clause", ("clausula", "clausulas", "condicoes particulares", "condicoes gerais")),
    ("exclusion", ("exclusao", "exclusoes", "nao coberto", "riscos excluidos")),
    ("insured_object", ("objeto segurado", "bem segurado", "imovel segurado", "endereco do risco")),
)

_FORBIDDEN_OUTPUT_TERMS = (
    "authorization",
    "bearer ",
    "cookie",
    "set-cookie",
    "token",
    "%pdf",
    "http://",
    "https://",
)


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def _short_hash(value: str, length: int = 24) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:length]


def policy_locator_hash(policy_locator: Dict[str, Any]) -> str:
    provider = str(policy_locator.get("provider") or OFFICIAL_POLICY_PROVIDER).strip().lower()
    codfil = str(policy_locator.get("codfil") or "").strip()
    nosnum = str(policy_locator.get("nosnum") or "").strip()
    if not codfil or not nosnum:
        raise ValueError("PolicyLocator requires codfil and nosnum")
    return _short_hash(f"{provider}:{codfil}:{nosnum}", 24)


def policy_document_cache_key(
    company_id: str,
    policy_locator: Dict[str, Any],
    content_hash: str,
    connection_id: str = "",
) -> str:
    """A chave do documento oficial: `company + connection + locator + conteudo`.

    🔴 O `connection_id` entrou na SPEC-EXTRA-001.1 §3.3. O `company_id` ja
    estava aqui — chave sem ele seria blocker de isolamento. O que faltava era
    a CONEXAO: 📊 a corretora piloto tem **4** conexoes InfoCap (3 `archived`,
    uma delas com `invalid_credentials`, e 1 `connected`), e trocar a conexao
    ativa nao invalidava nada. E defeito de FRESCOR dentro do mesmo tenant —
    ESSENCIAL, nao blocker — e M-A4 mede as duas partes da chave.

    ⚠️ `connection_id` vazio mantem a chave da forma antiga, de proposito: as
    entradas ja escritas continuam encontraveis, e quem ainda nao passa a
    conexao nao perde o cache de uma vez (expand-first, CLAUDE.md §8).
    """
    company_hash = _short_hash(company_id, 16)
    locator_hash = policy_locator_hash(policy_locator)
    conexao = f"{_short_hash(connection_id, 12)}:" if str(connection_id or "").strip() else ""
    return f"policydoc:{company_hash}:{conexao}infocap:{locator_hash}:{str(content_hash or '')[:24]}"


def policy_document_evidence_requested(question: Optional[str], explicit: bool = False) -> bool:
    if explicit:
        return True
    normalized = _strip_accents(question or "")
    return any(term in normalized for term in _INTENT_TERMS)


def _redact_short_text(value: str) -> str:
    text = str(value or "")
    text = re.sub(r"https?://\S+", "[url-redigida]", text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", "[documento-redigido]", text)
    text = re.sub(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b", "[documento-redigido]", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_EVIDENCE_TEXT_CHARS]


def _redact_long_text(value: str) -> str:
    """Mesma redacao de URL/CPF/CNPJ dos trechos, sem o corte de 700 chars.

    Sem isto o texto integral seria descartado inteiro por
    `_sanitize_pipeline_output` no primeiro `https://` do rodape da apolice.
    """
    text = str(value or "")
    text = re.sub(r"https?://\S+", "[url-redigida]", text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", "[documento-redigido]", text)
    text = re.sub(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b", "[documento-redigido]", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def build_document_plain_text(pages: Iterable[Dict[str, Any]]) -> str:
    """Texto integral da apolice oficial, pagina a pagina, para a LLM ler de verdade."""
    blocks: List[str] = []
    total = 0
    for page in pages or []:
        content = _redact_long_text(str(page.get("content") or page.get("text") or ""))
        if not content:
            continue
        try:
            page_number = int(page.get("page_number") or 0) or len(blocks) + 1
        except (TypeError, ValueError):
            page_number = len(blocks) + 1
        block = "[pagina {}]\n{}".format(page_number, content)
        if total + len(block) > MAX_DOCUMENT_TEXT_CHARS:
            blocks.append(block[: max(0, MAX_DOCUMENT_TEXT_CHARS - total)])
            break
        blocks.append(block)
        total += len(block)
    return "\n\n".join(blocks)


def _split_page_fragments(text: str) -> List[str]:
    raw = str(text or "").replace("\r", "\n")
    fragments: List[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if len(line) <= MAX_EVIDENCE_TEXT_CHARS:
            fragments.append(line)
            continue
        parts = re.split(r"(?<=[.;:])\s+", line)
        fragments.extend(part.strip() for part in parts if part.strip())
    return fragments


# ---------------------------------------------------------------------------
# SPEC-016.1 D2/D3/D4 — extrator v2: tabela de coberturas + anti-boilerplate
# ---------------------------------------------------------------------------

# Frases institucionais/glossário/navegação NUNCA são evidência de apólice.
_BOILERPLATE_RE = re.compile(
    r"consulte|acesse|para saber|para conhecer|a tabela indica|clique aqui|"
    r"www\.|\.com|\.br\b|obrigado por escolher|conte conosco|bem-vindo|"
    r"entende-se|indeniza apenas|valor ou percentual|conjunto de|documento emitido|"
    r"intervalo cont[ií]nuo|susep|ouvidoria|sac 24|linha direta|gloss[áa]rio",
    re.IGNORECASE,
)

# Valor monetário (centavos opcionais: "R$ 10.000" também é valor real em PDFs).
_AMOUNT_RE = re.compile(r"R\$\s*\d[\d.]*(?:,\d{2})?")

# Linha da tabela de coberturas: "<nome> R$ <LMI> [R$ <prêmio>] [<participação>]"
_COVERAGE_ROW_RE = re.compile(
    r"^(?P<label>[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9 ./+()\-]{3,70}?)\s*"
    r"R\$\s*(?P<lmi>[\d.]+,\d{2})"
    r"(?:\s*R\$\s*(?P<premium>[\d.]+,\d{2}))?"
    r"\s*(?P<part>\d{1,3}%.*)?$"
)

# Limite máximo de garantia da apólice (LMGA).
_POLICY_LIMIT_RE = re.compile(
    r"limite\s+m[aá]ximo\s+de\s+garantia\s+da\s+ap[oó]lice\s*:?\s*R\$\s*([\d.]+,\d{2})",
    re.IGNORECASE,
)

# Cabeçalho do bloco de serviços de assistência ("ASSISTÊNCIA 24H PLANO ...").
_ASSISTANCE_HEADER_RE = re.compile(r"assist[êe]ncia\s*24\s*h", re.IGNORECASE)
_SERVICE_TERM_RE = re.compile(
    r"chaveiro|eletricista|encanador|hidr[áa]ulic|vidraceiro|guincho|el[ée]trica|"
    r"telhado|resist[êe]ncia|limpeza|hospedagem|vigil[âa]ncia|eletrodom[eé]stico|check-?up",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# SPEC-EXTRA-001.1 BLOCO D — AS DUAS TABELAS REAIS (divergência D4 do BLOCO 0,
# decisão D-E0011-02)
# ---------------------------------------------------------------------------
#
# 📊 Medido em 14/09/2026 sobre `tests/fixtures/pdf_tabelas_reais_extra0011.json`
# (as linhas CRUAS dos dois PDFs reais, como o extrator `direct_text` as
# entrega): o parser anterior — `_COVERAGE_ROW_RE`, que EXIGE `R$` — produzia
# **0** `coverage_row` no PDF da HDI e **1** no da Allianz. E a única da Allianz
# era *"Prêmio Líquido"*: uma linha de PRÊMIO DA APÓLICE lida como cobertura.
#
# ```
# HDI      Incendio 133.000,00   45,64                 <- sem `R$`, 2+ espaços
# Allianz  Alagamento R$ 150.000,00 R$ 1.482,43 20 4.000,00
# Allianz  Despesas Fixas R$ 50.000,00 R$ 8,58 - 168 Hrs      <- CARÊNCIA
# Allianz  Assistência 24h R$ 23,88 - Sem Franquia            <- UMA coluna
# ```
#
# 🔴 A regra que separa cobertura de plano é o NÚMERO DE COLUNAS DE DINHEIRO,
# não a palavra "assistência" no rótulo: a HDI tem
# `Coberturas de Assistencias Essenciais 0,00   125,94` — duas colunas, LMI e
# prêmio — e ela É uma cobertura (é a linha de R$ 125,94 que paga o
# eletricista que o atendente promete ao segurado). A Allianz tem
# `Assistência 24h R$ 23,88` — uma coluna, o preço do PLANO.
_VALOR_BR = r"\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}"

#: Allianz: `<rótulo> R$ <LMI> R$ <prêmio> [<franquia>]`.
_LINHA_COM_RS_RE = re.compile(
    r"^(?P<label>.*?[A-Za-zÀ-ÿ].*?)\s+R\$\s*(?P<lmi>" + _VALOR_BR + r")"
    r"\s+R\$\s*(?P<premium>" + _VALOR_BR + r")\s*(?P<deductible>.*)$"
)

#: Allianz: `<rótulo> R$ <valor> [<franquia>]` — UMA coluna de dinheiro.
_LINHA_UM_VALOR_RE = re.compile(
    r"^(?P<label>.*?[A-Za-zÀ-ÿ].*?)\s*:?\s*R\$\s*(?P<premium>" + _VALOR_BR + r")"
    r"\s*(?P<deductible>.*)$"
)

#: HDI: `<rótulo> <LMI>   <prêmio>` — sem `R$`, separados por 2+ espaços.
#: ⚠️ Os 2+ espaços são a COLUNA: sem eles, "Parcela: 82,30 Forma de Pagamento"
#: viraria cobertura. O layout está declarado na fixture, não deduzido.
_LINHA_SEM_RS_RE = re.compile(
    r"^(?P<label>.*?[A-Za-zÀ-ÿ].*?)\s+(?P<lmi>" + _VALOR_BR + r")"
    r"\s{2,}(?P<premium>" + _VALOR_BR + r")\s*$"
)

#: HDI: `01 14/05/2026 R$ 82,31 Em trânsito   Cartão de Crédito`.
#: 🔴 É daqui que sai a FORMA DE PAGAMENTO verdadeira (§8.3): o `forma_pag` do
#: cabeçalho da HDI diz "Boleto Bancário" e as 4 parcelas dizem "Cartão".
_PARCELA_RE = re.compile(
    r"^(?P<numero>\d{1,3})\s+(?P<vencimento>\d{2}/\d{2}/\d{4})\s+R\$\s*"
    r"(?P<valor>" + _VALOR_BR + r")\s*(?P<resto>.*)$"
)

#: HDI: `10% Sobre os Prejuizos Indenizaveis, com o Minimo de R$ 600,00`.
#: A tabela da HDI não tem coluna de franquia — ela vem em PROSA, em linhas
#: separadas. Sem isto, `itens[].observacoes` e esta prosa são as duas únicas
#: fontes de franquia da apólice, e nenhuma das duas chegava ao corretor.
_FRANQUIA_EM_PROSA_RE = re.compile(
    r"^(?P<pct>\d{1,3}(?:[.,]\d{1,2})?)\s*%\s+.*?m[íi]nimo\s+de\s+R\$\s*"
    r"(?P<minimo>" + _VALOR_BR + r")",
    re.IGNORECASE,
)

#: 🔴 OS RÓTULOS QUE NUNCA SÃO COBERTURA — lista DECLARADA, com o motivo ao
#: lado de cada um (CLAUDE.md §9.5: uma constante que escolhe entre
#: alternativas de conteúdo precisa dizer POR QUE está certa). ⛔ Não é regex
#: escondido: é para ser lido e contestado.
_ROTULOS_QUE_NAO_SAO_COBERTURA: Tuple[Tuple[str, str], ...] = (
    ("premio liquido", "é a SOMA dos prêmios das coberturas, não uma cobertura"),
    ("premio total", "é o líquido + IOF + custos"),
    ("total a pagar", "é o financeiro da apólice"),
    ("custo da apolice", "é taxa de emissão (grafia Allianz)"),
    ("custo de apolice", "é taxa de emissão (grafia HDI)"),
    ("limite maximo de garantia", "é o teto da APÓLICE (LMG), não de uma cobertura"),
    ("i o f", "é imposto — a pontuação da HDI vira espaço na normalização"),
    ("iof", "é imposto"),
    ("adicional de parcelamento", "é juro de fracionamento"),
    ("cotacao", "é documento anterior à apólice"),
    ("taxa mensal juros", "é financeiro"),
    ("valor juros", "é financeiro"),
)


def _rotulo_limpo(bruto: Any) -> str:
    return re.sub(r"\s+", " ", str(bruto or "")).strip(" -:·*•")


def _rotulo_chave(rotulo: Any) -> str:
    texto = _strip_accents(rotulo or "")
    texto = re.sub(r"[^0-9a-z]+", " ", texto)
    return " ".join(texto.split())


def rotulo_nao_e_cobertura(rotulo: Any) -> Optional[str]:
    """O MOTIVO pelo qual este rótulo nunca é cobertura — ou `None`.

    📊 É o que impede *"Prêmio Líquido R$ 24.960,60"* de virar a única
    "cobertura" da Allianz, como acontecia até 14/09/2026.
    """
    chave = _rotulo_chave(rotulo)
    if not chave:
        return "linha sem rótulo legível"
    cercado = " %s " % chave
    for termo, motivo in _ROTULOS_QUE_NAO_SAO_COBERTURA:
        if chave == termo or (" %s " % termo) in cercado:
            return motivo
    return None


def _linha_de_tabela(line: str) -> Optional[Dict[str, Any]]:
    """Uma linha da tabela de coberturas, nos DOIS layouts reais. `None` se não for."""
    texto = str(line or "")
    com_rs = _LINHA_COM_RS_RE.match(texto)
    if com_rs:
        return {
            "label": _rotulo_limpo(com_rs.group("label")),
            "lmi": "R$ " + com_rs.group("lmi"),
            "premium": "R$ " + com_rs.group("premium"),
            "deductible": re.sub(r"\s+", " ", com_rs.group("deductible") or "").strip(),
            "layout": "rs_lmi_premio",
        }
    if "R$" not in texto:
        sem_rs = _LINHA_SEM_RS_RE.match(texto)
        if not sem_rs:
            return None
        return {
            "label": _rotulo_limpo(sem_rs.group("label")),
            "lmi": "R$ " + sem_rs.group("lmi"),
            "premium": "R$ " + sem_rs.group("premium"),
            "deductible": "",
            "layout": "lmi_premio_sem_rs",
        }
    um_valor = _LINHA_UM_VALOR_RE.match(texto)
    if not um_valor:
        return None
    return {
        "label": _rotulo_limpo(um_valor.group("label")),
        "lmi": None,
        "premium": "R$ " + um_valor.group("premium"),
        "deductible": re.sub(r"\s+", " ", um_valor.group("deductible") or "").strip(),
        "layout": "so_premio",
    }


def is_boilerplate_fragment(fragment: str) -> bool:
    """Frase institucional/glossário/cabeçalho: nunca evidência (SPEC-016.1 D2)."""
    text = str(fragment or "").strip()
    if not text:
        return True
    if _BOILERPLATE_RE.search(text):
        return True
    # Cabeçalho de tabela colado/solto (ex.: "CoberturasLimite") — sem valor, curto.
    normalized = _strip_accents(text).replace(" ", "")
    if not _AMOUNT_RE.search(text) and len(text) <= 46:
        header_tokens = (
            "coberturaslimite", "coberturaparticipacao", "maximode",
            "precopor", "limitemaximode",
        )
        if any(tok in normalized for tok in header_tokens):
            return True
        if normalized in ("servicos", "coberturas", "clausulas", "indenizacao"):
            return True
    return False


def _parse_structured_page_items(page_number: int, content: str) -> List[Dict[str, Any]]:
    """Itens ESTRUTURADOS de uma página: linhas da tabela, plano/serviços, LMGA."""
    lines = [ln.strip() for ln in str(content or "").replace("\r", "\n").splitlines() if ln.strip()]
    items: List[Dict[str, Any]] = []
    in_assistance_block = False
    for line in lines:
        limit_match = _POLICY_LIMIT_RE.search(line)
        if limit_match:
            items.append({
                "page_number": page_number,
                "evidence_type": "lmi",
                "evidence_text": _redact_short_text(line),
                "structured": {"kind": "policy_limit", "amount": f"R$ {limit_match.group(1)}"},
            })
            continue

        if (
            _ASSISTANCE_HEADER_RE.search(line)
            and not _AMOUNT_RE.search(line)
            and not is_boilerplate_fragment(line)
        ):
            in_assistance_block = True
            plan_text = re.sub(r"\s+", " ", line).strip()
            items.append({
                "page_number": page_number,
                "evidence_type": "assistance",
                "evidence_text": _redact_short_text(plan_text),
                "structured": {"kind": "assistance_plan", "plan": plan_text},
            })
            continue

        if in_assistance_block:
            if is_boilerplate_fragment(line):
                # Terminador do bloco ("Para conhecer... acesse...") encerra;
                # cabeçalhos soltos ("Serviços") são apenas pulados.
                if re.search(r"para conhecer|acesse|www\.|\.br\b|condi[çc][õo]es", line, re.IGNORECASE):
                    in_assistance_block = False
                continue
            if _SERVICE_TERM_RE.search(line) and not _AMOUNT_RE.search(line):
                items.append({
                    "page_number": page_number,
                    "evidence_type": "assistance",
                    "evidence_text": _redact_short_text(line),
                    "structured": {"kind": "assistance_services", "services": [re.sub(r"\s+", " ", line).strip()]},
                })
                continue

        # --- SPEC-EXTRA-001.1 BLOCO D: as parcelas do PDF -------------------
        parcela = _PARCELA_RE.match(line)
        if parcela:
            resto = re.split(r"\s{2,}", (parcela.group("resto") or "").strip())
            situacao = (resto[0] if resto else "").strip()
            forma = (resto[1] if len(resto) > 1 else "").strip()
            items.append({
                "page_number": page_number,
                "evidence_type": "installment",
                "evidence_text": _redact_short_text(line),
                "structured": {
                    "kind": "installment_row",
                    "number": int(parcela.group("numero")),
                    "due_date": parcela.group("vencimento"),
                    "amount": "R$ " + parcela.group("valor"),
                    "status": situacao or None,
                    "payment_method": forma or None,
                },
            })
            continue

        # --- as franquias em PROSA (a HDI não tem coluna de franquia) -------
        prosa = _FRANQUIA_EM_PROSA_RE.match(line)
        if prosa and not is_boilerplate_fragment(line):
            items.append({
                "page_number": page_number,
                "evidence_type": "deductible",
                "evidence_text": _redact_short_text(line),
                "structured": {
                    "kind": "deductible_prose",
                    "text": re.sub(r"\s+", " ", line).strip(),
                    "percent": prosa.group("pct"),
                    "minimum": "R$ " + prosa.group("minimo"),
                },
            })
            continue

        # --- a tabela de coberturas, nos DOIS layouts reais -----------------
        tabela = _linha_de_tabela(line)
        if tabela and not is_boilerplate_fragment(line):
            rotulo = tabela["label"]
            if rotulo_nao_e_cobertura(rotulo):
                continue
            if len(rotulo) >= 4 and any(ch.isalpha() for ch in rotulo):
                if tabela["lmi"] is not None:
                    # DUAS colunas de dinheiro → é cobertura, mesmo que o
                    # rótulo diga "assistência" (HDI: R$ 125,94).
                    items.append({
                        "page_number": page_number,
                        "evidence_type": "coverage",
                        "evidence_text": _redact_short_text(line),
                        "structured": {
                            "kind": "coverage_row",
                            "label": rotulo,
                            "lmi": tabela["lmi"],
                            "premium": tabela["premium"],
                            "participation": tabela["deductible"] or None,
                            "layout": tabela["layout"],
                        },
                    })
                    continue
                if "assistencia" in _strip_accents(rotulo):
                    # UMA coluna + rótulo de assistência → é o PLANO, e o valor
                    # é o PREÇO dele (Allianz: R$ 23,88).
                    items.append({
                        "page_number": page_number,
                        "evidence_type": "assistance",
                        "evidence_text": _redact_short_text(line),
                        "structured": {
                            "kind": "assistance_plan",
                            "plan": rotulo,
                            "premium": tabela["premium"],
                            "participation": tabela["deductible"] or None,
                        },
                    })
                    continue

        row = _COVERAGE_ROW_RE.match(line)
        if row and not is_boilerplate_fragment(line):
            label = re.sub(r"\s+", " ", row.group("label")).strip(" -:·*")
            if len(label) < 4 or not any(ch.isalpha() for ch in label):
                continue
            if rotulo_nao_e_cobertura(label):
                continue
            if "assistencia" in _strip_accents(label):
                # Linha da tabela "Assistência 24h <plano> R$ <preço do plano>"
                items.append({
                    "page_number": page_number,
                    "evidence_type": "assistance",
                    "evidence_text": _redact_short_text(line),
                    "structured": {"kind": "assistance_plan", "plan": label, "premium": f"R$ {row.group('lmi')}"},
                })
            else:
                items.append({
                    "page_number": page_number,
                    "evidence_type": "coverage",
                    "evidence_text": _redact_short_text(line),
                    "structured": {
                        "kind": "coverage_row",
                        "label": label,
                        "lmi": f"R$ {row.group('lmi')}",
                        "premium": f"R$ {row.group('premium')}" if row.group("premium") else None,
                        "participation": (row.group("part") or "").strip() or None,
                    },
                })
    return items


def _classify_fragment(fragment: str) -> List[str]:
    normalized = _strip_accents(fragment)
    if re.search(r"\b(sem|nao|não)\s+(cobertura|coberturas|garantia|garantias|assistencia|franquia)\b", normalized):
        return []
    # SPEC-016.1 D2: boilerplate nunca classifica.
    if is_boilerplate_fragment(fragment):
        return []
    found: List[str] = []
    for evidence_type, terms in _EVIDENCE_PATTERNS:
        if any(term in normalized for term in terms):
            found.append(evidence_type)
    if not found:
        return []
    # D2: keyword genérica só vira evidência com VALOR monetário no trecho,
    # exceto cláusula/exclusão (texto normativo) e assistência com termo de
    # serviço/plano real.
    has_amount = bool(_AMOUNT_RE.search(fragment))
    kept: List[str] = []
    for evidence_type in found:
        if evidence_type in ("clause", "exclusion"):
            kept.append(evidence_type)
        elif evidence_type == "assistance":
            if has_amount or _SERVICE_TERM_RE.search(fragment) or _ASSISTANCE_HEADER_RE.search(fragment):
                kept.append(evidence_type)
        elif has_amount:
            kept.append(evidence_type)
    return kept


def _confidence_for_evidence(items: List[Dict[str, Any]]) -> str:
    types_found = {item.get("evidence_type") for item in items}
    if {"coverage", "assistance", "deductible", "lmi"} & types_found:
        return "high"
    if items:
        return "medium"
    return "low"


def extract_policy_document_evidence(
    pages: Iterable[Dict[str, Any]],
    *,
    question: str,
    document_id: str,
    company_id: str,
    policy_locator: Dict[str, Any],
    content_hash: str,
    extraction_method: str = "direct_text",
) -> List[Dict[str, Any]]:
    locator_hash = policy_locator_hash(policy_locator)
    evidence: List[Dict[str, Any]] = []
    seen: set[Tuple[int, str, str]] = set()

    def _base_item(page_number: int, evidence_type: str, snippet: str) -> Dict[str, Any]:
        return {
            "document_id": document_id,
            "company_id": company_id,
            "policy_locator_hash": locator_hash,
            "page_number": page_number,
            "chunk_id": f"{document_id}:p{page_number}:{len(evidence) + 1}",
            "evidence_type": evidence_type,
            "evidence_text": snippet,
            "source_document": OFFICIAL_POLICY_DOCUMENT_SOURCE,
            "extraction_method": extraction_method,
            "confidence": "high" if evidence_type in {"coverage", "assistance", "deductible", "lmi"} else "medium",
            "content_hash": content_hash,
            "conflict_status": "none",
        }

    paginas: List[Tuple[int, str]] = []
    for page in pages or []:
        try:
            page_number = int(page.get("page_number") or 0) or 1
        except (TypeError, ValueError):
            page_number = 1
        paginas.append((page_number, page.get("content") or page.get("text") or ""))

    # 🔴 SPEC-EXTRA-001.1 BLOCO D: os ESTRUTURADOS de TODAS as páginas antes de
    # qualquer fragmento. 📊 A tabela de coberturas da Allianz mora na página 2;
    # com a ordem anterior (estruturados e fragmentos página a página), 12
    # fragmentos de cláusula da página 1 podiam consumir o teto ANTES de a
    # tabela ser lida — e o corretor receberia a apólice sem coberturas, em
    # silêncio. O teto subiu de 40 para `MAX_EVIDENCE_ITEMS` porque a apólice
    # real da Allianz já produz 22 itens estruturados (20 coberturas + plano +
    # LMG) e a da HDI, 20 (10 + 6 franquias em prosa + 4 parcelas).
    for page_number, content in paginas:
        # SPEC-016.1 D3: itens estruturados PRIMEIRO (tabela/plano/serviços/LMGA).
        for structured_item in _parse_structured_page_items(page_number, content):
            snippet = structured_item["evidence_text"]
            evidence_type = structured_item["evidence_type"]
            structured = structured_item.get("structured") or {}
            if structured.get("kind") == "assistance_plan":
                # Dedupe entre páginas: "Assistência 24h Completo" (tabela) e
                # "ASSISTÊNCIA 24H PLANO COMPLETO" (cabeçalho) são o mesmo plano.
                plan_key = _strip_accents(str(structured.get("plan") or ""))
                for noise in ("assistencia", "plano", "24h", "24 h", " "):
                    plan_key = plan_key.replace(noise, "")
                dedupe_key = (0, "assistance_plan", plan_key or snippet)
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
            key = (page_number, evidence_type, snippet)
            if key in seen:
                continue
            seen.add(key)
            item = _base_item(page_number, evidence_type, snippet)
            item["structured"] = structured_item.get("structured") or {}
            evidence.append(item)
            if len(evidence) >= MAX_EVIDENCE_ITEMS:
                return evidence

    for page_number, content in paginas:
        for fragment in _split_page_fragments(content):
            types_found = _classify_fragment(fragment)
            if not types_found:
                continue
            snippet = _redact_short_text(fragment)
            for evidence_type in types_found:
                key = (page_number, evidence_type, snippet)
                if key in seen:
                    continue
                seen.add(key)
                evidence.append(_base_item(page_number, evidence_type, snippet))
            if len(evidence) >= MAX_EVIDENCE_ITEMS:
                return evidence
    return evidence


def policy_document_filename_prefix(locator_hash: str, connection_id: str = "") -> str:
    """O PREFIXO do nome do arquivo guardado — a chave que DECIDE o hit.

    🔴 Ele existe porque `policy_document_cache_key` (acima) **não decidia
    nada**: a chave com `connection_id` era só um campo do resultado, enquanto
    o hit era resolvido por `find_official_policy_document(company, locator)`,
    sem conexão. 📊 Medido em 14/09/2026: `document_service.py:159` procura por
    `like("file_name", "infocap-policy-<locator>-%")` — o nome do arquivo é o
    único discriminador DURÁVEL que existe hoje (o `insert` de
    `store_official_policy_document` não grava `metadata`, e não há coluna
    `connection_id` na tabela `documents`). Sem DDL, é aqui que a conexão entra.

    ```
    sem conexão   infocap-policy-<locator>-<conteudo16>.pdf          (forma antiga)
    com conexão   infocap-policy-<locator>-c<conexao12>-<conteudo16>.pdf
    ```

    ⚠️ Expand-first (CLAUDE.md §8): a forma antiga continua válida e continua
    sendo encontrada por quem não declara conexão. E as duas se distinguem sem
    ambiguidade — o resto do nome, depois do prefixo base, tem um `-` a mais
    **só** na forma com conexão.

    🔴 A regra mora AQUI e em lugar nenhum mais: `document_service` a importa
    para montar o `like`. Duas cópias da mesma composição de nome seriam um
    segundo motor (CLAUDE.md §5) — e a que envelhecesse produziria miss
    permanente, em silêncio.
    """
    base = f"infocap-policy-{locator_hash}-"
    conexao = str(connection_id or "").strip()
    if not conexao:
        return base
    return f"{base}c{_short_hash(conexao, 12)}-"


def _safe_filename(policy_locator: Dict[str, Any], content_hash: str, connection_id: str = "") -> str:
    prefixo = policy_document_filename_prefix(policy_locator_hash(policy_locator), connection_id)
    return f"{prefixo}{str(content_hash or '')[:16]}.pdf"


def _sanitize_pipeline_output(value: Any) -> Any:
    if isinstance(value, list):
        return [_sanitize_pipeline_output(item) for item in value]
    if isinstance(value, dict):
        clean: Dict[str, Any] = {}
        for key, child in value.items():
            key_norm = _strip_accents(str(key))
            if key_norm in {"url", "source_url", "final_url", "authorization", "cookie", "token", "body", "raw", "payload", "codfil", "nosnum", "policy_locator"}:
                continue
            cleaned = _sanitize_pipeline_output(child)
            if cleaned is not None:
                clean[key] = cleaned
        return clean
    if isinstance(value, bytes):
        return None
    if isinstance(value, str):
        lowered = value.lower()
        if any(term in lowered for term in _FORBIDDEN_OUTPUT_TERMS):
            return None
    return value


def _empty_result(
    *,
    status: str,
    cache_status: str,
    blockers: Optional[List[str]] = None,
    policy_locator: Optional[Dict[str, Any]] = None,
    company_id: Optional[str] = None,
) -> Dict[str, Any]:
    locator_hash = policy_locator_hash(policy_locator) if policy_locator else None
    return {
        "ok": False,
        "provider": OFFICIAL_POLICY_PROVIDER,
        "document_type": OFFICIAL_POLICY_DOCUMENT_TYPE,
        "document_status": status,
        "cache_status": cache_status,
        "policy_locator_hash": locator_hash,
        "company_id": company_id,
        "evidence_items": [],
        "evidence_count": 0,
        "source_fetch_blocker": blockers or [],
        "source_transport": "unavailable",
        "source_document": OFFICIAL_POLICY_DOCUMENT_SOURCE,
    }


class PolicyDocumentEvidenceService:
    """Coordinates official policy document retrieval, cache and snippets."""

    def __init__(
        self,
        *,
        document_service: Any = None,
        ingestion_service: Any = None,
        docling_parser: Optional[Callable[..., List[Dict[str, Any]]]] = None,
    ) -> None:
        self.document_service = document_service
        self.ingestion_service = ingestion_service
        self.docling_parser = docling_parser

    @staticmethod
    def _docling_fallback_parser(*, file_bytes: bytes, policy_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Use the existing Sanitization/Docling service when configured; never a parallel parser."""
        try:
            from app.core.config import settings

            if not getattr(settings, "DOCLING_SERVICE_URL", None):
                return []
            from app.services.sanitization_service import SanitizationService
        except Exception:  # noqa: BLE001
            return []

        tmp_path = ""
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
            service = SanitizationService()
            markdown, metadata = service._docling_parse(tmp_path, extract_images=False)
            cleaned = service.post_process_markdown(markdown or "")
            if not cleaned:
                return []
            page_count = metadata.get("pages_count") if isinstance(metadata, dict) else None
            return [
                {
                    "page_number": 1,
                    "content": cleaned,
                    "parser_metadata": {
                        "parser": "docling",
                        "pages_count": page_count,
                        "policy_locator_hash": (policy_metadata or {}).get("policy_locator_hash"),
                    },
                }
            ]
        except Exception as exc:  # noqa: BLE001
            logger.warning("[PolicyDocumentEvidence] existing Docling fallback unavailable: %s", type(exc).__name__)
            return []
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def _document_service(self) -> Any:
        if self.document_service is not None:
            return self.document_service
        from .document_service import get_document_service

        self.document_service = get_document_service()
        return self.document_service

    def _ingestion_service(self) -> Any:
        if self.ingestion_service is not None:
            return self.ingestion_service
        from .ingestion_service import get_ingestion_service

        self.ingestion_service = get_ingestion_service()
        return self.ingestion_service

    @staticmethod
    def _buscar_documento_guardado(
        doc_service: Any,
        company_id: str,
        locator_hash: str,
        connection_id: str,
    ) -> Optional[Dict[str, Any]]:
        """O documento já guardado **desta corretora E desta conexão**.

        ⚠️ Leitor antigo (dublê de teste ou serviço ainda não atualizado) não
        conhece `connection_id`. Quando há conexão declarada, um hit dele
        poderia ser de OUTRA conexão — então ele vira MISS, e o PDF é buscado
        de novo. O erro custa uma leitura; o acerto silencioso custaria o
        documento errado na mão do corretor.
        """
        try:
            return doc_service.find_official_policy_document(
                company_id, locator_hash, connection_id=connection_id)
        except TypeError:
            if str(connection_id or "").strip():
                logger.warning(
                    "[PolicyDocumentEvidence] leitor de documento sem `connection_id`: "
                    "cache ignorado para nao devolver o documento de outra conexao")
                return None
            return doc_service.find_official_policy_document(company_id, locator_hash)

    async def ensure_official_policy_evidence(
        self,
        *,
        company_id: str,
        policy_locator: Dict[str, Any],
        official_document_candidate: Optional[Dict[str, Any]],
        question: str,
        fetcher: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]],
        agent_id: Optional[str] = None,
        force_refresh: bool = False,
        case_id: Optional[str] = None,
        connection_id: str = "",
    ) -> Dict[str, Any]:
        if not policy_locator:
            return _empty_result(status="source_unavailable", cache_status="unavailable", blockers=["policy_locator_required"], company_id=company_id)

        locator_hash = policy_locator_hash(policy_locator)
        doc_service = self._document_service()

        if not force_refresh and hasattr(doc_service, "find_official_policy_document"):
            # 🔴 A CONEXÃO DECIDE O HIT, não só a chave escrita no resultado.
            # Até 14/09/2026 esta linha era `find_official_policy_document(
            # company_id, locator_hash)` — e a conexão B da MESMA corretora
            # recebia o PDF que a conexão A tinha baixado. `policy_document_
            # cache_key` já carregava a conexão, mas ela não chegava aqui:
            # dois lugares, uma regra só de fachada (protocolo §0.3, o elo).
            cached = self._buscar_documento_guardado(
                doc_service, company_id, locator_hash, connection_id)
            if cached:
                pages = doc_service.load_raw_pages(cached.get("id"), company_id) if hasattr(doc_service, "load_raw_pages") else []
                content_hash = cached.get("content_hash") or (cached.get("metadata") or {}).get("content_hash") or ""
                evidence = extract_policy_document_evidence(
                    pages,
                    question=question,
                    document_id=str(cached.get("id")),
                    company_id=company_id,
                    policy_locator=policy_locator,
                    content_hash=content_hash,
                )
                return self._result(
                    company_id=company_id,
                    policy_locator=policy_locator,
                    document_id=str(cached.get("id")),
                    content_hash=content_hash,
                    cache_status="hit",
                    document_status="evidence_ready" if evidence else "low_confidence",
                    source_transport=(cached.get("metadata") or {}).get("source_transport") or "cache",
                    evidence=evidence,
                    parser_used=(cached.get("metadata") or {}).get("parser_used") or "direct_text",
                    page_count=len(pages) or (cached.get("metadata") or {}).get("page_count"),
                    pages=pages,
                    qdrant_ingested=True,
                    case_id=case_id,
                    connection_id=connection_id,
                )

        if not official_document_candidate or not official_document_candidate.get("url"):
            return _empty_result(
                status="source_unavailable",
                cache_status="unavailable",
                blockers=["official_document_url_absent"],
                policy_locator=policy_locator,
                company_id=company_id,
            )

        fetched = await fetcher(official_document_candidate)
        if not fetched or not fetched.get("ok"):
            return _empty_result(
                status="source_fetch_failed",
                cache_status="miss",
                blockers=list(fetched.get("blockers") or fetched.get("source_fetch_blocker") or ["source_fetch_failed"]) if isinstance(fetched, dict) else ["source_fetch_failed"],
                policy_locator=policy_locator,
                company_id=company_id,
            )

        body = fetched.get("body")
        if not isinstance(body, (bytes, bytearray)) or not body:
            return _empty_result(
                status="source_fetch_failed",
                cache_status="miss",
                blockers=["empty_document_body"],
                policy_locator=policy_locator,
                company_id=company_id,
            )
        body_bytes = bytes(body)
        content_hash = hashlib.sha256(body_bytes).hexdigest()
        # 🔴 O nome carrega a CONEXÃO: é por ele que o hit da leitura seguinte
        # vai distinguir a conexão A da B dentro da mesma corretora.
        filename = _safe_filename(policy_locator, content_hash, connection_id)
        metadata = {
            "provider": OFFICIAL_POLICY_PROVIDER,
            "document_type": OFFICIAL_POLICY_DOCUMENT_TYPE,
            "source_document": OFFICIAL_POLICY_DOCUMENT_SOURCE,
            "source_kind": fetched.get("source_kind") or official_document_candidate.get("source_kind") or "policy_pdf",
            "source_transport": fetched.get("source_transport") or fetched.get("recommended_r1c_transport") or "signed_url_fetch",
            "content_hash": content_hash,
            "policy_locator_hash": locator_hash,
            "sensitivity": "high",
            "scope": "connector",
            "case_id": case_id,
            "parser_used": "direct_text",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        document_id, pages = doc_service.store_official_policy_document(
            file_data=body_bytes,
            filename=filename,
            company_id=company_id,
            file_size=len(body_bytes),
            content_type=fetched.get("content_type") or "application/pdf",
            policy_metadata=metadata,
            agent_id=agent_id,
        )
        evidence = extract_policy_document_evidence(
            pages,
            question=question,
            document_id=str(document_id),
            company_id=company_id,
            policy_locator=policy_locator,
            content_hash=content_hash,
        )
        parser_used = "direct_text"
        document_status = "evidence_ready" if evidence else "low_confidence"

        docling_pages: List[Dict[str, Any]] = []
        fallback_parser = self.docling_parser or self._docling_fallback_parser
        if not evidence and fallback_parser:
            document_status = "docling_pending"
            try:
                docling_pages = fallback_parser(file_bytes=body_bytes, policy_metadata=metadata) or []
                evidence = extract_policy_document_evidence(
                    docling_pages,
                    question=question,
                    document_id=str(document_id),
                    company_id=company_id,
                    policy_locator=policy_locator,
                    content_hash=content_hash,
                    extraction_method="docling",
                )
                parser_used = "docling"
                document_status = "evidence_ready" if evidence else "document_not_policy_evidence"
            except Exception as exc:  # noqa: BLE001
                logger.warning("[PolicyDocumentEvidence] Docling fallback failed: %s", type(exc).__name__)
                document_status = "low_confidence"

        qdrant_ingested = False
        try:
            ingestion = self._ingestion_service()
            qdrant_ingested = bool(
                ingestion.process_document(
                    document_id=str(document_id),
                    company_id=company_id,
                    strategy="page",
                    agent_id=agent_id,
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[PolicyDocumentEvidence] ingestion failed: %s", type(exc).__name__)

        cache_status = "refreshed" if force_refresh else "miss"
        return self._result(
            company_id=company_id,
            policy_locator=policy_locator,
            document_id=str(document_id),
            content_hash=content_hash,
            cache_status=cache_status,
            document_status=document_status,
            source_transport=metadata["source_transport"],
            evidence=evidence,
            parser_used=parser_used,
            page_count=len(pages),
            pages=(docling_pages or pages),
            qdrant_ingested=qdrant_ingested,
            case_id=case_id,
            connection_id=connection_id,
        )

    def _result(
        self,
        *,
        company_id: str,
        policy_locator: Dict[str, Any],
        document_id: str,
        content_hash: str,
        cache_status: str,
        document_status: str,
        source_transport: str,
        evidence: List[Dict[str, Any]],
        parser_used: str,
        page_count: Any,
        qdrant_ingested: bool,
        case_id: Optional[str],
        pages: Optional[List[Dict[str, Any]]] = None,
        connection_id: str = "",
    ) -> Dict[str, Any]:
        confidence = _confidence_for_evidence(evidence)
        result = {
            "ok": document_status == "evidence_ready",
            "provider": OFFICIAL_POLICY_PROVIDER,
            "document_type": OFFICIAL_POLICY_DOCUMENT_TYPE,
            "document_status": document_status,
            "cache_status": cache_status,
            "cache_key": policy_document_cache_key(company_id, policy_locator, content_hash, connection_id),
            "company_id": company_id,
            "policy_locator_hash": policy_locator_hash(policy_locator),
            "document_id": document_id,
            "source_document": OFFICIAL_POLICY_DOCUMENT_SOURCE,
            "source_transport": source_transport,
            "content_hash": content_hash,
            "content_hash_present": bool(content_hash),
            "page_count": page_count,
            "parser_used": parser_used,
            "extraction_confidence": confidence,
            # 🔴 O corte da ENTREGA e o MESMO da extracao. Ate 14/09/2026 aqui
            # estava `evidence[:20]` enquanto o extrator lia ate
            # `MAX_EVIDENCE_ITEMS` (60) — e `evidence_count` anunciava o total.
            # 📊 Medido em 14/09/2026 sobre `pdf_tabelas_reais_extra0011.json`
            # (`extract_policy_document_evidence` sobre as linhas reais): HDI
            # **26** itens, Allianz **25**. Pelo caminho da producao a Allianz
            # perdia os itens de indice 20 e 21 — `coverage_row "Gastos com
            # Defesa"` e `assistance_plan "Assistencia 24h"` — e a apolice
            # chegava ao corretor com **20** coberturas em vez de 21, em
            # silencio. Dois tetos diferentes para a mesma lista e um corte que
            # ninguem le: o teto e UM, e ele esta declarado em `MAX_EVIDENCE_ITEMS`.
            #
            # ⚠️ A ORDEM e o que torna o teto seguro, e ela ja e a de producao
            # (`extract_policy_document_evidence`, BLOCO D): TODOS os
            # estruturados (`coverage_row`, `assistance_plan`, `deductible_prose`,
            # `installment_row`, `policy_limit`) de TODAS as paginas antes de
            # qualquer fragmento de clausula. 📊 Medido no mesmo dia: o primeiro
            # fragmento aparece no indice **20** (HDI) e **22** (Allianz) — isto
            # e, nenhum estruturado vem depois de um fragmento.
            "evidence_items": evidence[:MAX_EVIDENCE_ITEMS],
            "evidence_count": len(evidence),
            # 🔴 O TEXTO da apolice, nao so os trechos que o regex previu: e o
            # que responde "cobertura X esta contratada?" quando a pergunta nao
            # cabe em nenhum padrao.
            "document_text": build_document_plain_text(pages or []),
            "qdrant_ingested": qdrant_ingested,
            "case_id": case_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return _sanitize_pipeline_output(result)


def policy_document_evidence_role_view(
    evidence_result: Dict[str, Any],
    *,
    role: str,
    case_id: Optional[str] = None,
    capability_allowed: bool = True,
) -> Dict[str, Any]:
    """Return the allowed DTO for Core, Even or future auxiliaries."""
    if not isinstance(evidence_result, dict):
        return {}
    role_norm = str(role or "").strip().lower()
    if role_norm == "core":
        return dict(evidence_result)
    if role_norm == "even":
        if not case_id:
            return {
                "provider": evidence_result.get("provider"),
                "document_status": evidence_result.get("document_status"),
                "evidence_items": [],
                "reason": "case_id_required",
            }
        items = [
            {
                "page_number": item.get("page_number"),
                "evidence_type": item.get("evidence_type"),
                "evidence_text": item.get("evidence_text"),
                "confidence": item.get("confidence"),
                "source_document": item.get("source_document"),
            }
            for item in evidence_result.get("evidence_items") or []
        ]
        return {
            "provider": evidence_result.get("provider"),
            "document_status": evidence_result.get("document_status"),
            "evidence_items": items,
            "evidence_count": len(items),
            "case_id": case_id,
        }
    if not capability_allowed:
        return {
            "provider": evidence_result.get("provider"),
            "document_status": evidence_result.get("document_status"),
            "evidence_items": [],
            "reason": "capability_required",
        }
    return dict(evidence_result)


_policy_document_evidence_service: Optional[PolicyDocumentEvidenceService] = None


def get_policy_document_evidence_service() -> PolicyDocumentEvidenceService:
    global _policy_document_evidence_service
    if _policy_document_evidence_service is None:
        _policy_document_evidence_service = PolicyDocumentEvidenceService()
    return _policy_document_evidence_service
