"""Official policy document evidence orchestration.

R1C.1: this module does not create a parallel RAG/parser/storage. It
coordinates the existing DocumentService/MinIO extraction path and the existing
ingestion path for InfoCap official policy PDFs, then builds short page-based
evidence snippets for the Smith runtime.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
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
#:
#: 🔴 SPEC-130-B: DOIS tetos, um por tipo, e o total é a soma. 📊 BLOCO 0 do
#: laudo: a apólice empresarial de 105 páginas parou em 7 % do prêmio porque os
#: estruturados de todas as páginas disputavam o MESMO teto de 60 com os
#: fragmentos. Estruturados (linha de cobertura, plano, parcela, franquia em
#: prosa, LMG) têm teto próprio e GRANDE; fragmentos de cláusula, o de sempre.
#: ⚠️ O corte da ENTREGA (`_result`) é `MAX_EVIDENCE_ITEMS` — o mesmo número que
#: a extração nunca ultrapassa (300 + 60).
TETO_ESTRUTURADOS = 300
TETO_FRAGMENTOS = 60
MAX_EVIDENCE_ITEMS = TETO_ESTRUTURADOS + TETO_FRAGMENTOS

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
    # SPEC-130-B: o anexo do WhatsApp/chat não tem locator — o hash fica vazio.
    locator_hash = policy_locator_hash(policy_locator) if policy_locator else ""
    evidence: List[Dict[str, Any]] = []
    seen: set[Tuple[int, str, str]] = set()
    estruturados = 0

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
            estruturados += 1
            if estruturados >= TETO_ESTRUTURADOS:
                break
        if estruturados >= TETO_ESTRUTURADOS:
            logger.warning("[PolicyDocumentEvidence] teto de estruturados (%d) atingido", TETO_ESTRUTURADOS)
            break

    teto_total = len(evidence) + TETO_FRAGMENTOS
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
            if len(evidence) >= teto_total:
                return evidence[:teto_total]
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


# ===========================================================================
# SPEC-130-B U3 — A LEITURA EM CASCATA, COM JUIZ
# ===========================================================================
#
#   regex → JUIZ (fecha o prêmio?) → modelo barato (texto MASCARADO, trecho
#   literal obrigatório) → JUIZ → visão (só página sem texto) → JUIZ → estado
#
# 🔴 Não é um leitor novo (CLAUDE.md §5, D-130B-01): o degrau 1 é o MESMO
# `extract_policy_document_evidence` de sempre, intacto; os degraus 2 e 3
# devolvem `coverage_row` no MESMO formato, e o juiz é o MESMO cálculo do
# contador de prêmio (`fecha_o_premio`, D-130B-02), com a tolerância do
# documento (D-130B-12).

#: A versão do leitor. 🔴 A leitura guardada só é reaproveitada se for DESTA
#: versão — mudar o leitor é mudar este número, e tudo é relido uma vez.
LEITOR_VERSAO = "130B.1"

ESTADOS_DA_LEITURA = ("fechou", "nao_fechou", "sem_premio_para_conferir", "pendente", "falhou")
#: Os estados em que a leitura guardada SERVE (não se relê pelo modelo).
ESTADOS_FINAIS = ("fechou", "nao_fechou", "sem_premio_para_conferir")

PAPEL_DA_LEITURA = "leitura_de_apolice"
#: no máximo 20 páginas sem texto vão à visão (custo e latência têm teto)
MAX_PAGINAS_NA_VISAO = 20
DPI_DA_VISAO = 150
#: 📊 `llm_pricing` 11/10/2026 (migration 20261007_02, cabeçalho): gpt-6-luna
#: US$ 0,10 / 0,50 por 1 M tokens (entrada / saída). Só para ESTIMAR quando a
#: resposta não traz custo; o custo de verdade é o do ledger (`token_usage_logs`).
_PRECO_ESTIMADO_POR_MILHAO = (0.10, 0.50)


def leitor_por_modelo_ligado() -> bool:
    """`LEITOR_APOLICE_MODELO=0` desliga o modelo E a visão (padrão: ligado)."""
    return str(os.getenv("LEITOR_APOLICE_MODELO", "1")).strip().lower() not in ("0", "false", "nao", "não", "off")


def orcamento_do_modelo_s() -> float:
    """`LEITOR_APOLICE_ORCAMENTO_S` (padrão 20 s) — D-130B-08."""
    try:
        valor = float(str(os.getenv("LEITOR_APOLICE_ORCAMENTO_S", "20")).strip())
    except ValueError:
        valor = 20.0
    return valor if valor > 0 else 20.0


# ---------------------------------------------------------------------------
# A MÁSCARA DO LEITOR (D-130B-07)
# ---------------------------------------------------------------------------
# 🔴 Por que NÃO o mascarador do canal inteiro: 📊 `canal/conversa.py:332` troca
# QUALQUER sequência de 8+ dígitos (com separadores) por `[NUMERO]` — e
# `600.000,00` tem 8 dígitos. Ele apagaria o LMI e o prêmio, que são exatamente
# o que o modelo precisa ler. Daqui se REUSA dele o que não toca dinheiro:
# e-mail, placa (com uma trava a mais: placa seguida de `,dd`/`.ddd` é DINHEIRO
# — "LMI 1000,00" casaria a regra de placa) e o CEP com traço.
# Os números de documento são reconhecidos pela FORMA (pontuação de CPF/CNPJ,
# hífen de telefone) ou pela LONGURA SEM separador decimal (9+ dígitos crus).
# ⛔ Dinheiro em pt-BR sempre tem vírgula decimal — e é ela que o protege.
_MASCARA_CNPJ = re.compile(r"(?<![\d.,/])\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}(?!\d)")
_MASCARA_CPF = re.compile(r"(?<![\d.,/])\d{3}\.\d{3}\.\d{3}-\d{2}(?!\d)")
_MASCARA_CEP_PONTO = re.compile(r"(?<![\d.,])\d{2}\.\d{3}-\d{3}(?!\d)")
_MASCARA_TELEFONE = re.compile(
    r"(?:\+?55[\s-]?)?\(\d{2}\)\s*9?\d{4}[\s-]?\d{4}(?!\d)"           # (11) 98765-4321
    r"|(?<![\d.,])(?:\+?55[\s-]?)?\d{2}\s9?\d{4}-\d{4}(?!\d)"         # 11 98765-4321
    r"|(?<![\d.,-])(?!(?:19|20)\d{2}-(?:19|20)\d{2}(?!\d))9?\d{4}-\d{4}(?!\d)"  # 98765-4321 (não "2025-2026")
    r"|(?<!\d)0[38]00[\s-]?\d{3}[\s-]?\d{4}(?!\d)"                     # 0800 / 0300
)
_MASCARA_CHASSI = re.compile(
    r"(?<![A-Za-z0-9])(?=[A-HJ-NPR-Z0-9]{17}(?![A-Za-z0-9]))(?=[A-HJ-NPR-Z0-9]*\d)"
    r"(?=[A-HJ-NPR-Z0-9]*[A-HJ-NPR-Z])[A-HJ-NPR-Z0-9]{17}")
_MASCARA_DIGITOS_CRUS = re.compile(r"(?<![\d.,])\d{9,}(?!\d|[.,]\d)")
_DINHEIRO_LOGO_DEPOIS = re.compile(r"^[.,]\d")
_PALAVRA_E_ANO = re.compile(r"^[A-Za-z]{3}\s+(?:19|20)\d{2}$")
_MASCARA_PLACA_ROTULADA = re.compile(r"(?i)(\bplaca\s*:?\s*)[A-Z]{3}[\s-]?\d[A-Z0-9]\d{2}\b")


def _mascaras_do_canal() -> Dict[str, Any]:
    """E-mail, placa e CEP do mascarador do CANAL — o MESMO padrão, não uma cópia."""
    try:
        from app.services.canal.conversa import _MASCARAS

        return {marcador: padrao for padrao, marcador in _MASCARAS
                if marcador in ("[EMAIL]", "[PLACA]", "[CEP]")}
    except Exception:  # noqa: BLE001 — sem o canal, a reserva local (mesmas formas)
        return {
            "[EMAIL]": re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
            "[PLACA]": re.compile(r"(?<![A-Za-z0-9])[A-Za-z]{3}[\s-]?\d[A-Za-z0-9]\d{2}(?![A-Za-z0-9])"),
            "[CEP]": re.compile(r"(?<!\d)\d{5}-\d{3}(?!\d)"),
        }


def mascarar_texto_de_apolice(texto: str) -> str:
    """CPF, CNPJ, telefone, e-mail, CEP, placa e chassi → marcadores. **Nunca dinheiro.**

    ✅ `600.000,00` · `15.103,93` · `R$ 1500000,00` passam intactos.
    ⛔ `123.456.789-09` · `12.345.678/0001-90` · `(11) 98765-4321` · `12345678909` não.
    """
    t = str(texto or "")
    canal = _mascaras_do_canal()
    if "[EMAIL]" in canal:
        t = canal["[EMAIL]"].sub("[EMAIL]", t)
    t = _MASCARA_CNPJ.sub("[CNPJ]", t)
    t = _MASCARA_CPF.sub("[CPF]", t)
    t = _MASCARA_CEP_PONTO.sub("[CEP]", t)
    if "[CEP]" in canal:
        t = canal["[CEP]"].sub("[CEP]", t)
    t = _MASCARA_TELEFONE.sub("[TELEFONE]", t)
    t = _MASCARA_PLACA_ROTULADA.sub(lambda m: m.group(1) + "[PLACA]", t)
    if "[PLACA]" in canal:
        def _placa(m: "re.Match[str]") -> str:
            # 🔴 as travas a mais, porque um documento de seguro não é uma conversa:
            #    "LMI 1000,00" (3 letras + 4 dígitos + `,00`) é DINHEIRO, e
            #    "Vig 2025-2026" (palavra + espaço + ANO) é DATA. A placa que vem
            #    rotulada ("Placa: ABC 2019") já saiu na linha acima.
            if _DINHEIRO_LOGO_DEPOIS.match(m.string[m.end():]):
                return m.group(0)
            if _PALAVRA_E_ANO.match(m.group(0)):
                return m.group(0)
            return "[PLACA]"
        t = canal["[PLACA]"].sub(_placa, t)
    t = _MASCARA_CHASSI.sub("[CHASSI]", t)
    t = _MASCARA_DIGITOS_CRUS.sub("[NUMERO]", t)
    return t


def _espacos(texto: Any) -> str:
    return " ".join(str(texto or "").split())


# ---------------------------------------------------------------------------
# O QUE O DOCUMENTO É, O PRÊMIO IMPRESSO E O OBJETO DO RISCO — regex LOCAL
# ---------------------------------------------------------------------------
_PREMIO_LIQUIDO_IMPRESSO_RE = re.compile(
    r"pr[eê]mio\s+l[ií]quido(?:\s+total)?(?:\s*\(R\$\))?\s*:?\s*(?:R\$)?\s*:?\s*"
    r"(?P<valor>" + _VALOR_BR + r")",
    re.IGNORECASE,
)


def premio_liquido_impresso(pages: Iterable[Dict[str, Any]]) -> Optional[str]:
    """O `Prêmio Líquido … R$ X` IMPRESSO no documento (o 1º, em ordem de página)."""
    for page in pages or []:
        achado = _PREMIO_LIQUIDO_IMPRESSO_RE.search(str(page.get("content") or page.get("text") or ""))
        if achado:
            return achado.group("valor")
    return None


def tipo_de_documento(pages: Iterable[Dict[str, Any]]) -> str:
    """apólice · proposta · endosso · cotação · crlv · desconhecido — por PALAVRAS, sem modelo.

    A 1ª página decide (é onde mora o título); a ordem dá prioridade ao que é
    mais específico: o CRLV não tem a palavra apólice; o endosso e a proposta
    citam a apólice; a cotação, ainda não.
    """
    lista = list(pages or [])
    primeira = _strip_accents(str((lista[0].get("content") or lista[0].get("text") or "") if lista else ""))
    tudo = _strip_accents(" ".join(str(p.get("content") or p.get("text") or "") for p in lista[:3]))
    if not tudo.strip():
        return "desconhecido"
    if re.search(r"certificado de registro e licenciamento|\bcrlv\b", primeira):
        return "crlv"
    if re.search(r"\bendosso\s+(?:n\s*[o°º.]|de\s+(?:altera|cancel|inclus|exclus|restitui|cobran))", primeira):
        return "endosso"
    tem_numero_de_apolice = bool(re.search(r"\bapolice\s*(?:n\s*[o°º.]|numero|:)", primeira))
    if re.search(r"\bcotacao\b|\borcamento\b", primeira) and not tem_numero_de_apolice:
        return "cotacao"
    if re.search(r"\bproposta\s+de\s+seguro\b|\bproposta\s+n\s*[o°º.]", primeira) and not tem_numero_de_apolice:
        return "proposta"
    if re.search(r"\bapolice\b", tudo):
        return "apolice"
    return "desconhecido"


_OBJETO_RE: Tuple[Tuple[str, "re.Pattern[str]"], ...] = (
    ("placa", re.compile(r"\bplaca\s*:?\s*([A-Z]{3}[\s-]?\d[A-Z0-9]\d{2})\b", re.IGNORECASE)),
    ("chassi", re.compile(r"\bchassi\s*:?\s*([A-HJ-NPR-Z0-9]{17})\b", re.IGNORECASE)),
    ("ano_modelo", re.compile(r"\bano\s*/?\s*modelo\s*:?\s*((?:19|20)\d{2}(?:\s*/\s*(?:19|20)\d{2})?)", re.IGNORECASE)),
    ("cep", re.compile(r"\bCEP\s*:?\s*(\d{2}\.?\d{3}-?\d{3})\b", re.IGNORECASE)),
    ("atividade", re.compile(r"\batividade(?:\s+(?:principal|do\s+risco|exercida))?\s*:\s*([^\n]{3,80})", re.IGNORECASE)),
    ("importancia_segurada", re.compile(
        r"(?:import[aâ]ncia\s+segurada|valor\s+em\s+risco|limite\s+m[aá]ximo\s+de\s+garantia(?:\s+da\s+ap[oó]lice)?)"
        r"[^\n\d]{0,30}?(?:R\$\s*)?(" + _VALOR_BR + r")", re.IGNORECASE)),
)


def objeto_do_risco_local(pages: Iterable[Dict[str, Any]]) -> Dict[str, Optional[str]]:
    """Placa, chassi, ano/modelo, CEP, atividade, importância segurada — regex LOCAL.

    ⛔ O modelo NUNCA extrai dado pessoal: o que identifica o bem segurado sai
    daqui, do texto cru, e fica na FICHA (MinIO) — nunca no `documents.metadata`.
    """
    texto = "\n".join(str(p.get("content") or p.get("text") or "") for p in pages or [])
    saida: Dict[str, Optional[str]] = {}
    for campo, padrao in _OBJETO_RE:
        achado = padrao.search(texto)
        valor = _espacos(achado.group(1)) if achado else None
        if valor and campo == "placa":
            valor = re.sub(r"[\s-]", "", valor).upper()
        saida[campo] = valor or None
    return saida


# ---------------------------------------------------------------------------
# O JUIZ
# ---------------------------------------------------------------------------
def _decimal(valor: Any) -> Optional[Any]:
    from app.providers.policy_data_provider import Indisponivel, dinheiro

    d = dinheiro(valor)
    return None if isinstance(d, Indisponivel) else d


def _linhas_que_contam(evidence: Iterable[Dict[str, Any]]) -> List[Any]:
    """Os prêmios que `apolice_documental_do_pack` CONTARIA: `coverage_row` com
    prêmio + `assistance_plan` com prêmio (o plano com preço é linha, 📊 Allianz
    R$ 23,88). ⚠️ A mesma regra do adaptador — se ela divergir, o juiz julga
    uma lista que o corretor não recebe."""
    premios: List[Any] = []
    for item in evidence or []:
        estruturado = (item or {}).get("structured") or {}
        if estruturado.get("kind") not in ("coverage_row", "assistance_plan"):
            continue
        if estruturado.get("kind") == "coverage_row" and not str(estruturado.get("label") or "").strip():
            continue
        if estruturado.get("kind") == "assistance_plan" and not str(estruturado.get("plan") or "").strip():
            continue
        premio = _decimal(estruturado.get("premium"))
        if premio is not None:
            premios.append(premio)
    return premios


def _julgar(evidence: List[Dict[str, Any]], esperado: Any) -> Dict[str, Any]:
    from decimal import Decimal

    from app.providers.policy_data_provider import TOLERANCIA_DO_DOCUMENTO, fecha_o_premio

    premios = _linhas_que_contam(evidence)
    soma = sum(premios, Decimal("0")).quantize(Decimal("0.01"))
    if esperado is None:
        return {"linhas": len(premios), "soma": soma, "fecha": False, "diferenca": None, "pct": None}
    fecha, diferenca, pct = fecha_o_premio(soma, esperado, tolerancia=TOLERANCIA_DO_DOCUMENTO)
    return {"linhas": len(premios), "soma": soma, "fecha": bool(fecha), "diferenca": diferenca, "pct": pct}


# ---------------------------------------------------------------------------
# OS DEGRAUS 2 e 3 — modelo e visão, por PAPEL do Model Router
# ---------------------------------------------------------------------------
_INSTRUCAO_DA_LEITURA = (
    "Você lê a TABELA DE COBERTURAS de um documento de seguro brasileiro. Dados pessoais já foram "
    "trocados por marcadores como [CPF]; ignore-os. Devolva SÓ um JSON, sem texto em volta:\n"
    '{"linhas":[{"pagina":N,"rotulo":"...","limite":"600.000,00","premio":"15.103,93","franquia":"...",'
    '"trecho":"..."}],"premio_liquido_impresso":"..."}\n'
    "Regras: uma linha por cobertura ou assistência que tenha PRÊMIO; `trecho` é a linha do documento "
    "COPIADA LITERALMENTE (sem corrigir nada), e o prêmio tem de aparecer nela; `pagina` é o número do "
    "marcador [pagina N]; não invente linha; não inclua prêmio líquido, IOF, custo de apólice, total ou "
    "parcelas como linha; valores no formato do documento."
)


def _texto_da_resposta(resposta: Any) -> str:
    if resposta is None:
        return ""
    if isinstance(resposta, (dict, list)) and not hasattr(resposta, "content"):
        return json.dumps(resposta, ensure_ascii=False)
    conteudo = getattr(resposta, "content", resposta)
    if isinstance(conteudo, list):
        return "".join(
            str(b.get("text") or "") if isinstance(b, dict) else str(b) for b in conteudo)
    return str(conteudo or "")


def _json_da_resposta(resposta: Any) -> Dict[str, Any]:
    if isinstance(resposta, dict) and "linhas" in resposta:
        return resposta
    texto = _texto_da_resposta(resposta)
    achado = re.search(r"\{.*\}", texto, re.S)
    if not achado:
        return {}
    try:
        dados = json.loads(achado.group(0))
    except (ValueError, TypeError):
        return {}
    return dados if isinstance(dados, dict) else {}


def _custo_da_resposta(resposta: Any) -> Tuple[float, bool, Optional[str]]:
    """`(custo_usd, estimado, modelo)` — do `usage_metadata` quando há."""
    uso = getattr(resposta, "usage_metadata", None) or {}
    meta = getattr(resposta, "response_metadata", None) or {}
    modelo = meta.get("model_name") or meta.get("model") if isinstance(meta, dict) else None
    try:
        entrada = float(uso.get("input_tokens") or 0)
        saida = float(uso.get("output_tokens") or 0)
    except (AttributeError, TypeError, ValueError):
        entrada = saida = 0.0
    if not (entrada or saida):
        return 0.0, True, modelo
    custo = entrada / 1e6 * _PRECO_ESTIMADO_POR_MILHAO[0] + saida / 1e6 * _PRECO_ESTIMADO_POR_MILHAO[1]
    # 💭 estimado pela tabela da Luna; o ledger (`token_usage_logs`) tem o real
    return round(custo, 6), True, modelo


async def _leitor_modelo_padrao(texto_mascarado: str, *, company_id: str,
                                service_type: str = PAPEL_DA_LEITURA) -> Any:
    """O degrau 2 pelo PAPEL `leitura_de_apolice` (Model Router, com reserva).

    `service_type` só muda a LINHA DO LEDGER (a régua da bancada usa `bancada_130b`);
    o papel, o prompt e a máscara são os mesmos do produto."""
    from langchain_core.messages import HumanMessage, SystemMessage

    from app.factories.llm_factory import invocar_com_reserva

    return await invocar_com_reserva(
        PAPEL_DA_LEITURA,
        [SystemMessage(content=_INSTRUCAO_DA_LEITURA), HumanMessage(content=texto_mascarado)],
        company_id=company_id, service_type=service_type, classe_de_dado="pii",
    )


async def _leitor_visao_padrao(imagens: List[Tuple[int, str]], *, company_id: str,
                               service_type: str = PAPEL_DA_LEITURA) -> Any:
    """O degrau 3: SÓ as páginas sem texto, como imagem, pelo mesmo papel."""
    from langchain_core.messages import HumanMessage, SystemMessage

    from app.factories.llm_factory import invocar_com_reserva

    conteudo: List[Dict[str, Any]] = [{
        "type": "text",
        "text": "As imagens abaixo são páginas de um documento de seguro, na ordem: "
                + ", ".join("[pagina %d]" % n for n, _ in imagens)
                + ". Leia a tabela de coberturas. ⛔ Não transcreva nome, CPF, telefone ou endereço.",
    }]
    for _numero, b64 in imagens:
        conteudo.append({"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}})
    return await invocar_com_reserva(
        PAPEL_DA_LEITURA,
        [SystemMessage(content=_INSTRUCAO_DA_LEITURA), HumanMessage(content=conteudo)],
        company_id=company_id, service_type=service_type, classe_de_dado="pii",
    )


def _paginas_mascaradas(paginas: List[Tuple[int, str]]) -> Dict[int, str]:
    return {numero: mascarar_texto_de_apolice(conteudo) for numero, conteudo in paginas}


def _texto_marcado(mascaradas: Dict[int, str]) -> str:
    return "\n\n".join("[pagina %d]\n%s" % (n, t) for n, t in sorted(mascaradas.items()) if t.strip())


#: Um valor em dinheiro pt-BR: SEMPRE 2 decimais. Lido da esquerda para a direita, é isso que
#: separa valores COLADOS pelo extrator (📊 Tokio EMPR, PyPDF2: `17.539,151.803,19` são dois valores).
_DINHEIRO_NO_TRECHO_RE = re.compile(r"\d{1,3}(?:\.\d{3})+,\d{2}|\d+,\d{2}")


def _premio_no_trecho(premio: Any, trecho_norm: str) -> bool:
    """O prêmio aparece no trecho, como UM dos valores em dinheiro dele?

    🔴 SPEC-130-B F5 (régua): antes, a grafia era procurada com "nem dígito antes nem depois" — e o
    PyPDF2 COLA os valores das colunas da Tokio (📊 EMPR-TMAR-16: as 11 linhas do modelo somavam o
    prêmio líquido ao centavo e 10 eram descartadas por isso). Agora o trecho é FATIADO em valores
    pela forma do dinheiro pt-BR (2 decimais, da esquerda para a direita) e o prêmio tem de ser
    IGUAL a um deles. ⛔ Continua estrito: `2.345,67` não casa com `12.345,67` (o fatiamento dá
    12345,67), nem `345,67` com `2.345,67`."""
    from decimal import Decimal, InvalidOperation

    if premio is None:
        return False
    numero = Decimal(premio).quantize(Decimal("0.01"))
    texto = str(trecho_norm or "")
    fim_anterior = -1
    for achado in _DINHEIRO_NO_TRECHO_RE.finditer(texto):
        bruto, inicio = achado.group(0), achado.start()
        colado = inicio > 0 and texto[inicio - 1] in "0123456789.,"
        anterior, fim_anterior = fim_anterior, achado.end()
        # ⛔ um dígito/separador colado ANTES só vale se o valor anterior acabou EXATAMENTE aqui
        #    (a cola do extrator); senão o valor começa no meio de outro número e não conta.
        if colado and inicio != anterior:
            continue
        try:
            valor = Decimal(bruto.replace(".", "").replace(",", "."))
        except InvalidOperation:
            continue
        if valor == numero:
            return True
    return False


def _linha_para_coverage_row(
    linha: Dict[str, Any],
    *,
    pagina: int,
    trecho: str,
    premio: Any,
    metodo: str,
    confianca: str,
    base: Dict[str, Any],
    indice: int,
) -> Dict[str, Any]:
    from app.providers.policy_data_provider import reais

    limite = _decimal(linha.get("limite"))
    franquia = _espacos(linha.get("franquia")) or None
    item = {
        **base,
        "page_number": pagina,
        "chunk_id": f"{base.get('document_id') or 'anexo'}:p{pagina}:{metodo}{indice}",
        "evidence_type": "coverage",
        "evidence_text": _redact_short_text(trecho),
        "extraction_method": metodo,
        "confidence": confianca,
        "structured": {
            "kind": "coverage_row",
            "label": _rotulo_limpo(linha.get("rotulo")),
            "lmi": reais(limite) if limite is not None else None,
            "premium": reais(premio),
            "participation": franquia,
            "layout": metodo,
        },
    }
    return item


def _linhas_do_modelo(
    dados: Dict[str, Any],
    mascaradas: Dict[int, str],
    *,
    base: Dict[str, Any],
    exigir_trecho_literal: bool,
    metodo: str,
) -> Tuple[List[Dict[str, Any]], int]:
    """As linhas do modelo que SOBREVIVEM à conferência → `(coverage_rows, descartadas)`.

    🔴 D-130B-06: no degrau do texto, uma linha só entra se o `trecho` existir
    LITERALMENTE no texto mascarado daquela página E o prêmio aparecer nele.
    O modelo não tem como inventar uma linha que o documento não tem.
    """
    saida: List[Dict[str, Any]] = []
    descartadas = 0
    vistos: set = set()
    normalizadas = {n: _espacos(t) for n, t in mascaradas.items()}
    for indice, linha in enumerate(dados.get("linhas") or []):
        if not isinstance(linha, dict):
            descartadas += 1
            continue
        try:
            pagina = int(linha.get("pagina"))
        except (TypeError, ValueError):
            descartadas += 1
            continue
        rotulo = _rotulo_limpo(linha.get("rotulo"))
        premio = _decimal(linha.get("premio"))
        trecho = _espacos(linha.get("trecho"))
        if not rotulo or premio is None or rotulo_nao_e_cobertura(rotulo):
            descartadas += 1
            continue
        if exigir_trecho_literal:
            pagina_texto = normalizadas.get(pagina)
            if (not trecho or pagina_texto is None or trecho not in pagina_texto
                    or not _premio_no_trecho(premio, trecho)):
                descartadas += 1
                continue
        else:
            if pagina not in mascaradas:
                descartadas += 1
                continue
            trecho = trecho or rotulo
        chave = (pagina, trecho if exigir_trecho_literal else rotulo, str(premio))
        if chave in vistos:
            continue
        vistos.add(chave)
        saida.append(_linha_para_coverage_row(
            linha, pagina=pagina, trecho=mascarar_texto_de_apolice(trecho), premio=premio,
            metodo=metodo, confianca="high" if exigir_trecho_literal else "medium",
            base=base, indice=indice + 1))
    return saida, descartadas


def _sem_as_linhas_do_regex(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """O regex SAI da conta quando o modelo vence: sem `coverage_row`, e o
    `assistance_plan` fica — SEM o preço (senão ele seria contado duas vezes)."""
    saida: List[Dict[str, Any]] = []
    for item in evidence:
        estruturado = (item or {}).get("structured") or {}
        if estruturado.get("kind") == "coverage_row":
            continue
        if estruturado.get("kind") == "assistance_plan" and estruturado.get("premium") is not None:
            item = {**item, "structured": {k: v for k, v in estruturado.items() if k != "premium"}}
        saida.append(item)
    return saida


def _renderizar_paginas(file_bytes: bytes, numeros: List[int]) -> List[Tuple[int, str]]:
    """PNG base64 das páginas pedidas (~150 dpi), no máximo `MAX_PAGINAS_NA_VISAO`."""
    import base64

    import fitz  # PyMuPDF

    imagens: List[Tuple[int, str]] = []
    documento = fitz.open(stream=bytes(file_bytes), filetype="pdf")
    try:
        for numero in numeros[:MAX_PAGINAS_NA_VISAO]:
            if 1 <= numero <= documento.page_count:
                png = documento[numero - 1].get_pixmap(dpi=DPI_DA_VISAO).tobytes("png")
                imagens.append((numero, base64.b64encode(png).decode("ascii")))
    finally:
        documento.close()
    return imagens


def _texto_de_dinheiro(valor: Any) -> Optional[str]:
    return None if valor is None else str(valor)


async def ler_documento_de_seguro(
    pages: Iterable[Dict[str, Any]],
    *,
    company_id: str,
    premio_esperado: Any = None,
    fonte_do_esperado: Optional[str] = None,
    file_bytes: Optional[bytes] = None,
    total_paginas: Optional[int] = None,
    parser_por_pagina: Optional[Dict[str, str]] = None,
    permitir_modelo: bool = True,
    leitor_modelo: Optional[Callable[..., Awaitable[Any]]] = None,
    leitor_visao: Optional[Callable[..., Awaitable[Any]]] = None,
    document_id: str = "",
    policy_locator: Optional[Dict[str, Any]] = None,
    content_hash: str = "",
    extraction_method: str = "direct_text",
) -> Dict[str, Any]:
    """A cascata (SPEC-130-B §4). Devolve `{evidence_items, leitura, objeto_do_risco}`.

    ⛔ Nunca loga o texto. ⛔ O modelo só vê o texto MASCARADO. ⛔ A visão só vê
    página SEM texto. ⚠️ `permitir_modelo=False` (ou `LEITOR_APOLICE_MODELO=0`)
    para no regex.
    """
    from time import monotonic

    inicio = monotonic()
    lista = [p for p in (pages or []) if isinstance(p, dict)]
    parser = {str(k): str(v) for k, v in (parser_por_pagina or {}).items()}
    sem_texto = sorted(int(n) for n, p in parser.items() if p == "sem_texto" and str(n).isdigit())
    leitura: Dict[str, Any] = {
        "leitor_versao": LEITOR_VERSAO,
        "tipo_documento": "desconhecido",
        "estado": "falhou",
        "degraus": [],
        "linhas": 0,
        "soma_linhas": "0.00",
        "premio_esperado": None,
        "fonte_do_esperado": None,
        "diferenca": None,
        "paginas": int(total_paginas or 0) or len(lista),
        "paginas_sem_texto": sem_texto,
        "parser_por_pagina": parser,
        "custo_usd": 0.0,
        "custo_estimado": False,
        "modelo": None,
        "duracao_s": 0.0,
    }
    objeto: Dict[str, Any] = {}
    evidence: List[Dict[str, Any]] = []
    try:
        evidence = extract_policy_document_evidence(
            lista, question="", document_id=str(document_id or ""), company_id=company_id,
            policy_locator=policy_locator or {}, content_hash=content_hash,
            extraction_method=extraction_method,
        )
        leitura["tipo_documento"] = tipo_de_documento(lista)
        objeto = objeto_do_risco_local(lista)

        esperado = _decimal(premio_esperado) if premio_esperado is not None else None
        fonte = (fonte_do_esperado or "corp") if esperado is not None else None
        if esperado is None:
            impresso = premio_liquido_impresso(lista)
            esperado = _decimal(impresso) if impresso else None
            fonte = "impresso" if esperado is not None else None
        leitura["premio_esperado"] = _texto_de_dinheiro(esperado)
        leitura["fonte_do_esperado"] = fonte

        juizo = _julgar(evidence, esperado)
        leitura["degraus"].append({"degrau": "regex", "linhas": juizo["linhas"],
                                   "soma": str(juizo["soma"]), "fecha": juizo["fecha"]})

        modelo_ligado = bool(permitir_modelo) and leitor_por_modelo_ligado()
        base = {
            "document_id": str(document_id or ""), "company_id": company_id,
            "policy_locator_hash": policy_locator_hash(policy_locator) if policy_locator else "",
            "source_document": OFFICIAL_POLICY_DOCUMENT_SOURCE, "content_hash": content_hash,
            "conflict_status": "none",
        }

        # --- degrau 2: o modelo, sobre o texto MASCARADO -------------------------
        if esperado is not None and not juizo["fecha"] and modelo_ligado and lista:
            leitor = leitor_modelo or _leitor_modelo_padrao
            paginas_txt: List[Tuple[int, str]] = []
            for page in lista:
                try:
                    numero = int(page.get("page_number") or 0) or len(paginas_txt) + 1
                except (TypeError, ValueError):
                    numero = len(paginas_txt) + 1
                paginas_txt.append((numero, str(page.get("content") or page.get("text") or "")))
            mascaradas = _paginas_mascaradas(paginas_txt)
            t0 = monotonic()
            degrau: Dict[str, Any] = {"degrau": "modelo"}
            try:
                resposta = await leitor(_texto_marcado(mascaradas), company_id=company_id)
                custo, estimado, nome = _custo_da_resposta(resposta)
                leitura["custo_usd"] = round(float(leitura["custo_usd"]) + custo, 6)
                leitura["custo_estimado"] = bool(leitura["custo_estimado"] or estimado)
                leitura["modelo"] = nome or leitura["modelo"] or PAPEL_DA_LEITURA
                linhas_m, descartadas = _linhas_do_modelo(
                    _json_da_resposta(resposta), mascaradas, base=base,
                    exigir_trecho_literal=True, metodo="modelo")
                candidata = _sem_as_linhas_do_regex(evidence) + linhas_m
                juizo_m = _julgar(candidata, esperado)
                degrau.update({"linhas": juizo_m["linhas"], "soma": str(juizo_m["soma"]),
                               "fecha": juizo_m["fecha"], "descartadas": descartadas})
                # 🔴 o modelo VENCE se fecha — ou se o regex não leu NADA e ele leu algo
                if linhas_m and (juizo_m["fecha"] or juizo["linhas"] == 0):
                    evidence, juizo = candidata, juizo_m
                    degrau["venceu"] = True
            except Exception as exc:  # noqa: BLE001 — o degrau falha, a leitura não
                degrau["erro"] = type(exc).__name__
                logger.warning("[LeitorDeApolice] degrau do modelo falhou: %s", type(exc).__name__)
            degrau["duracao_s"] = round(monotonic() - t0, 3)
            leitura["degraus"].append(degrau)

        # --- degrau 3: a visão, SÓ nas páginas sem texto -------------------------
        if esperado is not None and not juizo["fecha"] and modelo_ligado and sem_texto and file_bytes:
            leitor_v = leitor_visao or _leitor_visao_padrao
            t0 = monotonic()
            degrau = {"degrau": "visao", "paginas_enviadas": sem_texto[:MAX_PAGINAS_NA_VISAO]}
            try:
                imagens = await asyncio.to_thread(_renderizar_paginas, file_bytes, sem_texto)
                if imagens:
                    resposta = await leitor_v(imagens, company_id=company_id)
                    custo, estimado, nome = _custo_da_resposta(resposta)
                    leitura["custo_usd"] = round(float(leitura["custo_usd"]) + custo, 6)
                    leitura["custo_estimado"] = bool(leitura["custo_estimado"] or estimado)
                    leitura["modelo"] = nome or leitura["modelo"] or PAPEL_DA_LEITURA
                    paginas_v = {n: "" for n, _ in imagens}
                    linhas_v, descartadas = _linhas_do_modelo(
                        _json_da_resposta(resposta), paginas_v, base=base,
                        exigir_trecho_literal=False, metodo="visao")
                    candidata = evidence + linhas_v
                    juizo_v = _julgar(candidata, esperado)
                    degrau.update({"linhas": juizo_v["linhas"], "soma": str(juizo_v["soma"]),
                                   "fecha": juizo_v["fecha"], "descartadas": descartadas})
                    if linhas_v and (juizo_v["fecha"] or juizo["linhas"] == 0):
                        evidence, juizo = candidata, juizo_v
                        degrau["venceu"] = True
            except Exception as exc:  # noqa: BLE001
                degrau["erro"] = type(exc).__name__
                logger.warning("[LeitorDeApolice] degrau da visão falhou: %s", type(exc).__name__)
            degrau["duracao_s"] = round(monotonic() - t0, 3)
            leitura["degraus"].append(degrau)

        leitura["linhas"] = juizo["linhas"]
        leitura["soma_linhas"] = str(juizo["soma"])
        leitura["diferenca"] = _texto_de_dinheiro(juizo["diferenca"])
        if esperado is None:
            leitura["estado"] = "sem_premio_para_conferir"
        else:
            leitura["estado"] = "fechou" if juizo["fecha"] else "nao_fechou"
    except Exception as exc:  # noqa: BLE001 — a leitura registra a falha, não derruba o atendimento
        logger.warning("[LeitorDeApolice] leitura falhou: %s", type(exc).__name__)
        leitura["estado"] = "falhou"
        leitura["motivo"] = type(exc).__name__
    leitura["duracao_s"] = round(monotonic() - inicio, 3)
    return {"evidence_items": evidence, "leitura": leitura, "objeto_do_risco": objeto}


def ficha_para_o_modelo(resultado: Dict[str, Any], *, audiencia: str = "segurado") -> str:
    """A ficha LEGÍVEL e MASCARADA — o que pode ir ao modelo da conversa (D-130B-05).

    `segurado`: só coberturas, plano e o estado da conferência. `corretor`: +
    o objeto do risco (mascarado). ⛔ Nunca o texto cru.
    """
    from app.providers.policy_data_provider import reais

    resultado = resultado or {}
    leitura = resultado.get("leitura") or {}
    tipo = str(leitura.get("tipo_documento") or "desconhecido")
    linhas_txt: List[str] = ["Documento: %s." % {
        "apolice": "apólice", "proposta": "proposta", "endosso": "endosso", "cotacao": "cotação",
        "crlv": "CRLV (documento do veículo)"}.get(tipo, "documento de seguro (tipo não identificado)")]
    estado = str(leitura.get("estado") or "")
    if estado == "fechou":
        linhas_txt.append("Conferida: a soma das coberturas bate com o prêmio líquido (%s)."
                          % reais(leitura.get("premio_esperado")))
    elif estado == "nao_fechou":
        linhas_txt.append("NÃO conferida: li %s de %s do prêmio líquido — pode faltar cobertura; não afirme "
                          "que a lista está completa." % (reais(leitura.get("soma_linhas")),
                                                          reais(leitura.get("premio_esperado"))))
    elif estado == "pendente":
        linhas_txt.append("Leitura completa ainda em andamento: a lista abaixo pode estar incompleta.")
    elif estado == "sem_premio_para_conferir":
        linhas_txt.append("Sem prêmio líquido para conferir a soma: não afirme que a lista está completa.")
    else:
        linhas_txt.append("O documento não pôde ser lido por inteiro.")
    coberturas: List[str] = []
    planos: List[str] = []
    for item in resultado.get("evidence_items") or []:
        e = (item or {}).get("structured") or {}
        if e.get("kind") == "coverage_row":
            partes = [str(e.get("label") or "").strip()]
            if e.get("lmi"):
                partes.append("limite %s" % e.get("lmi"))
            if e.get("premium"):
                partes.append("prêmio %s" % e.get("premium"))
            if e.get("participation"):
                partes.append("franquia %s" % e.get("participation"))
            coberturas.append("- " + " · ".join(p for p in partes if p) + " (pág. %s)" % item.get("page_number"))
        elif e.get("kind") == "assistance_plan":
            planos.append("- %s%s" % (e.get("plan"), (" · prêmio %s" % e.get("premium")) if e.get("premium") else ""))
    if coberturas:
        linhas_txt.append("Coberturas:")
        linhas_txt.extend(coberturas)
    if planos:
        linhas_txt.append("Assistência:")
        linhas_txt.extend(planos)
    if str(audiencia or "").strip().lower() == "corretor":
        objeto = resultado.get("objeto_do_risco") or {}
        rotulos = {"ano_modelo": "ano/modelo", "atividade": "atividade",
                   "importancia_segurada": "importância segurada", "placa": "placa", "chassi": "chassi",
                   "cep": "CEP"}
        partes = ["%s: %s" % (rotulos[k], objeto[k]) for k in rotulos if objeto.get(k)]
        if partes:
            linhas_txt.append("Objeto do risco: " + " · ".join(partes) + ".")
    return mascarar_texto_de_apolice("\n".join(linhas_txt))


async def ler_anexo_de_seguro(
    file_bytes: bytes,
    file_name: str,
    *,
    company_id: str,
    orcamento_s: float = 40.0,
    leitor_modelo: Optional[Callable[..., Awaitable[Any]]] = None,
) -> Dict[str, Any]:
    """O anexo do WhatsApp/chat lido EM MEMÓRIA pelo MESMO leitor (nada é gravado).

    Estourou o orçamento → a resposta vai com o regex e `estado="pendente"`.
    O resultado traz `texto_mascarado` (para o CORRETOR, que pergunta de cláusula).
    """
    nome = str(file_name or "").lower()
    dados = bytes(file_bytes or b"")
    if not dados or not (nome.endswith(".pdf") or dados[:5] == b"%PDF-"):
        return {"evidence_items": [], "objeto_do_risco": {}, "texto_mascarado": "",
                "leitura": {"leitor_versao": LEITOR_VERSAO, "estado": "falhou", "motivo": "nao_e_pdf",
                            "tipo_documento": "desconhecido", "degraus": [], "linhas": 0}}
    try:
        from app.services.document_service import extrair_paginas_tolerante

        pages, parser, total = await asyncio.to_thread(extrair_paginas_tolerante, dados)
    except Exception as exc:  # noqa: BLE001
        return {"evidence_items": [], "objeto_do_risco": {}, "texto_mascarado": "",
                "leitura": {"leitor_versao": LEITOR_VERSAO, "estado": "falhou", "motivo": type(exc).__name__,
                            "tipo_documento": "desconhecido", "degraus": [], "linhas": 0}}
    conteudo_hash = hashlib.sha256(dados).hexdigest()
    comum = dict(company_id=company_id, file_bytes=dados, total_paginas=total, parser_por_pagina=parser,
                 document_id="anexo-" + conteudo_hash[:12], content_hash=conteudo_hash)
    try:
        resultado = await asyncio.wait_for(
            ler_documento_de_seguro(pages, permitir_modelo=True, leitor_modelo=leitor_modelo, **comum),
            timeout=max(1.0, float(orcamento_s or 40.0)))
    except asyncio.TimeoutError:
        resultado = await ler_documento_de_seguro(pages, permitir_modelo=False, **comum)
        if resultado["leitura"].get("estado") != "fechou":
            resultado["leitura"]["estado"] = "pendente"
            resultado["leitura"]["motivo"] = "orcamento_estourado"
    resultado["texto_mascarado"] = mascarar_texto_de_apolice(build_document_plain_text(pages))
    return resultado


def _chave_da_trava(company_id: str, connection_id: str, content_hash: str) -> str:
    """A trava do 2º plano: por corretora + conexão + conteúdo (hashes, nunca o valor).

    ⚠️ 16 caracteres do conteúdo: é o que o HIT conhece (o nome do arquivo guarda
    16) — com 24 no miss e 16 no hit, a mesma leitura teria duas travas."""
    return "leitor_apolice:%s:%s:%s" % (
        _short_hash(company_id, 16), _short_hash(connection_id or "-", 12), str(content_hash or "")[:16])


async def _redis_padrao() -> Any:
    try:
        from app.core.redis import get_async_redis_client

        return await asyncio.wait_for(get_async_redis_client(), timeout=2.0)
    except Exception:  # noqa: BLE001 — sem Redis: não há 2º plano (só registra)
        return None


#: As tarefas em 2º plano vivas — referência forte (o asyncio só guarda fraca).
_TAREFAS_EM_SEGUNDO_PLANO: set = set()


class PolicyDocumentEvidenceService:
    """Coordinates official policy document retrieval, cache and snippets."""

    def __init__(
        self,
        *,
        document_service: Any = None,
        ingestion_service: Any = None,
        docling_parser: Optional[Callable[..., List[Dict[str, Any]]]] = None,
        leitor_modelo: Optional[Callable[..., Awaitable[Any]]] = None,
        leitor_visao: Optional[Callable[..., Awaitable[Any]]] = None,
        redis_factory: Optional[Callable[[], Awaitable[Any]]] = None,
    ) -> None:
        self.document_service = document_service
        self.ingestion_service = ingestion_service
        self.docling_parser = docling_parser
        # SPEC-130-B: os degraus 2/3 e a trava são injetáveis (dublê nos testes).
        self.leitor_modelo = leitor_modelo
        self.leitor_visao = leitor_visao
        self.redis_factory = redis_factory
        self.tarefas_em_segundo_plano = _TAREFAS_EM_SEGUNDO_PLANO

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

    # ----- SPEC-130-B: a leitura REGISTRADA, com orçamento e 2º plano ----------
    @staticmethod
    def _guardar_leitura(
        doc_service: Any,
        *,
        document_id: str,
        company_id: str,
        content_hash: str,
        resultado: Dict[str, Any],
    ) -> None:
        """Ficha inteira → MinIO; resumo (sem objeto do risco) → `documents.metadata`."""
        if not hasattr(doc_service, "guardar_leitura"):
            return
        leitura = dict(resultado.get("leitura") or {})
        ficha = {
            "company_id": company_id,
            "document_id": document_id,
            "content_hash": content_hash,
            "leitor_versao": LEITOR_VERSAO,
            "evidence_items": resultado.get("evidence_items") or [],
            "leitura": leitura,
            "objeto_do_risco": resultado.get("objeto_do_risco") or {},
            "gravado_em": datetime.now(timezone.utc).isoformat(),
        }
        try:
            doc_service.guardar_leitura(document_id, company_id, ficha, leitura)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[LeitorDeApolice] leitura não registrada: %s", type(exc).__name__)

    @staticmethod
    def _leitura_guardada(
        doc_service: Any,
        *,
        document_id: str,
        company_id: str,
        content_hash: str,
        premio_esperado: Any,
    ) -> Optional[Dict[str, Any]]:
        """A ficha guardada que SERVE: desta corretora, deste conteúdo, desta versão,
        num estado final — e julgada contra o MESMO prêmio esperado."""
        if not hasattr(doc_service, "carregar_leitura"):
            return None
        try:
            ficha = doc_service.carregar_leitura(document_id, company_id)
        except Exception:  # noqa: BLE001
            return None
        if not isinstance(ficha, dict) or str(ficha.get("company_id") or "") != str(company_id):
            return None
        if content_hash and str(ficha.get("content_hash") or "")[:16] != str(content_hash)[:16]:
            return None
        leitura = ficha.get("leitura") or {}
        if leitura.get("leitor_versao") != LEITOR_VERSAO or leitura.get("estado") not in ESTADOS_FINAIS:
            return None
        # ⚠️ "não fechou" lido SÓ pelo regex (o modelo estava desligado) não é leitura
        #    pelo modelo: com o modelo ligado de novo, ele merece a sua vez.
        if (leitura.get("estado") == "nao_fechou" and leitor_por_modelo_ligado()
                and not any(d.get("degrau") in ("modelo", "visao") for d in (leitura.get("degraus") or [])
                            if isinstance(d, dict))):
            return None
        if premio_esperado is not None:
            novo = _decimal(premio_esperado)
            if novo is not None and str(novo) != str(leitura.get("premio_esperado")):
                return None   # o prêmio de referência mudou: julga de novo (o regex é grátis)
        return {
            "evidence_items": list(ficha.get("evidence_items") or []),
            "leitura": dict(leitura),
            "objeto_do_risco": dict(ficha.get("objeto_do_risco") or {}),
        }

    async def _redis(self) -> Any:
        fabrica = self.redis_factory or _redis_padrao
        try:
            return await fabrica()
        except Exception:  # noqa: BLE001
            return None

    async def _ler_e_registrar(
        self,
        *,
        doc_service: Any,
        pages: List[Dict[str, Any]],
        company_id: str,
        connection_id: str,
        document_id: str,
        content_hash: str,
        policy_locator: Dict[str, Any],
        premio_esperado: Any,
        file_bytes: Optional[bytes],
        total_paginas: Optional[int],
        parser_por_pagina: Optional[Dict[str, str]],
        extraction_method: str = "direct_text",
    ) -> Dict[str, Any]:
        """A cascata com ORÇAMENTO (D-130B-08).

        1. o regex (grátis) — fechou, ou não há prêmio para conferir? acabou.
        2. senão, o modelo: trava Redis `SET NX EX 600` por corretora+conexão+hash
           (a outra chamada simultânea NÃO chama o modelo: devolve `pendente`).
        3. o modelo estourou o orçamento → a resposta de AGORA vai com o regex e
           `pendente`, e a leitura CONTINUA em 2º plano; ao terminar, grava.
           Sem Redis não há 2º plano: a tarefa é cancelada e a próxima tenta.
        """
        comum = dict(
            company_id=company_id, premio_esperado=premio_esperado,
            fonte_do_esperado="corp" if premio_esperado is not None else None,
            file_bytes=file_bytes, total_paginas=total_paginas, parser_por_pagina=parser_por_pagina,
            document_id=document_id, policy_locator=policy_locator, content_hash=content_hash,
            extraction_method=extraction_method,
        )
        regex = await ler_documento_de_seguro(pages, permitir_modelo=False, **comum)
        estado = regex["leitura"].get("estado")
        if estado != "nao_fechou" or not leitor_por_modelo_ligado():
            if estado in ESTADOS_FINAIS:
                self._guardar_leitura(doc_service, document_id=document_id, company_id=company_id,
                                      content_hash=content_hash, resultado=regex)
            return regex

        def _pendente(motivo: str) -> Dict[str, Any]:
            regex["leitura"]["estado"] = "pendente"
            regex["leitura"]["motivo"] = motivo
            return regex

        redis = await self._redis()
        chave = _chave_da_trava(company_id, connection_id, content_hash)
        marca = hashlib.sha256(os.urandom(16)).hexdigest()[:16]
        travou = False
        if redis is not None:
            try:
                travou = bool(await redis.set(chave, marca, nx=True, ex=600))
            except Exception as exc:  # noqa: BLE001
                logger.warning("[LeitorDeApolice] trava indisponível: %s", type(exc).__name__)
                redis = None
            if redis is not None and not travou:
                return _pendente("leitura_em_andamento")

        async def _soltar() -> None:
            if redis is None or not travou:
                return
            try:
                if await redis.get(chave) == marca:
                    await redis.delete(chave)
            except Exception:  # noqa: BLE001
                pass

        async def _completa() -> Dict[str, Any]:
            try:
                resultado = await ler_documento_de_seguro(
                    pages, permitir_modelo=True, leitor_modelo=self.leitor_modelo,
                    leitor_visao=self.leitor_visao, **comum)
                if resultado["leitura"].get("estado") in ESTADOS_FINAIS:
                    self._guardar_leitura(doc_service, document_id=document_id, company_id=company_id,
                                          content_hash=content_hash, resultado=resultado)
                return resultado
            finally:
                await _soltar()

        tarefa = asyncio.ensure_future(_completa())
        try:
            return await asyncio.wait_for(asyncio.shield(tarefa), timeout=orcamento_do_modelo_s())
        except asyncio.TimeoutError:
            if redis is not None and travou:
                self.tarefas_em_segundo_plano.add(tarefa)
                tarefa.add_done_callback(self.tarefas_em_segundo_plano.discard)
                return _pendente("orcamento_estourado_segue_em_segundo_plano")
            tarefa.cancel()
            resultado = _pendente("orcamento_estourado_sem_segundo_plano")
            self._guardar_leitura(doc_service, document_id=document_id, company_id=company_id,
                                  content_hash=content_hash, resultado=resultado)
            return resultado

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
        premio_liquido_esperado: Any = None,
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
                # 🔴 SPEC-130-B: a LEITURA guardada desta versão, num estado final,
                #    serve SEM chamar modelo. Senão, a cascata (o regex é grátis).
                lido = self._leitura_guardada(
                    doc_service, document_id=str(cached.get("id")), company_id=company_id,
                    content_hash=content_hash, premio_esperado=premio_liquido_esperado)
                if lido is None:
                    resumo = cached.get("metadata") or {}
                    parser_por_pagina = resumo.get("parser_por_pagina") if isinstance(resumo, dict) else None
                    bytes_originais = None
                    if (isinstance(parser_por_pagina, dict) and "sem_texto" in parser_por_pagina.values()
                            and hasattr(doc_service, "carregar_pdf_original")):
                        bytes_originais = doc_service.carregar_pdf_original(cached, company_id)
                    lido = await self._ler_e_registrar(
                        doc_service=doc_service, pages=pages, company_id=company_id,
                        connection_id=connection_id, document_id=str(cached.get("id")),
                        content_hash=content_hash, policy_locator=policy_locator,
                        premio_esperado=premio_liquido_esperado, file_bytes=bytes_originais,
                        total_paginas=(resumo.get("total_paginas") if isinstance(resumo, dict) else None),
                        parser_por_pagina=parser_por_pagina)
                evidence = lido["evidence_items"]
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
                    leitura=lido.get("leitura"),
                    objeto_do_risco=lido.get("objeto_do_risco"),
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
                # 🔴 SPEC-130-B: o docling é SÍNCRONO (HTTP + arquivo temporário) e
                #    rodava DENTRO do laço async — travando todo atendimento do
                #    processo enquanto lia. Agora vai para uma thread.
                docling_pages = await asyncio.to_thread(
                    fallback_parser, file_bytes=body_bytes, policy_metadata=metadata) or []
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

        # 🔴 SPEC-130-B: a CASCATA sobre o texto que se leu (o do docling, quando
        #    foi ele que achou algo). O degrau 1 refaz o MESMO regex acima.
        texto_lido = docling_pages if (parser_used == "docling" and evidence) else pages
        lido = await self._ler_e_registrar(
            doc_service=doc_service, pages=texto_lido, company_id=company_id,
            connection_id=connection_id, document_id=str(document_id), content_hash=content_hash,
            policy_locator=policy_locator, premio_esperado=premio_liquido_esperado,
            file_bytes=body_bytes, total_paginas=metadata.get("total_paginas"),
            parser_por_pagina=metadata.get("parser_por_pagina"),
            extraction_method="docling" if texto_lido is docling_pages else "direct_text")
        evidence = lido["evidence_items"]
        if evidence and document_status != "evidence_ready":
            document_status = "evidence_ready"

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
            leitura=lido.get("leitura"),
            objeto_do_risco=lido.get("objeto_do_risco"),
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
        leitura: Optional[Dict[str, Any]] = None,
        objeto_do_risco: Optional[Dict[str, Any]] = None,
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
            # 🔴 SPEC-130-B §4: o estado da leitura (fechou / não fechou / …) e o
            #    objeto do risco. ⚠️ O objeto vai no PACK (servidor), nunca no
            #    `documents.metadata`.
            "leitura": dict(leitura or {}),
            "objeto_do_risco": dict(objeto_do_risco or {}),
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
