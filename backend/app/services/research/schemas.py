"""Contratos da pesquisa. SPEC-060 §5, §7, §8, §16, §17.

Puro: sem banco, sem rede, sem LLM. É o contrato que separa *o que se pediu*
de *o que se encontrou* — e um contrato que precisa de infraestrutura para ser
testado não é testado.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

SCHEMA_VERSION = "1.0"


# ---------------------------------------------------------------------------
# Modos — §7
# ---------------------------------------------------------------------------

QUICK = "quick"
VERIFIED = "verified"
DEEP = "deep"
SITE_AUDIT = "site_audit"
BUSINESS_DISCOVERY = "business_discovery"
MONITOR = "monitor"
CLAIM_CHECK = "claim_check"

MODOS = (QUICK, VERIFIED, DEEP, SITE_AUDIT, BUSINESS_DISCOVERY, MONITOR, CLAIM_CHECK)

# Modos que EXIGEM Work Run próprio (§25.1). `quick` cabe num passo da conversa.
MODOS_COM_WORK_RUN = (VERIFIED, DEEP, SITE_AUDIT, BUSINESS_DISCOVERY, MONITOR)

# Quantas fontes cada modo persegue, e quantas bastam para parar.
PERFIL_DO_MODO: dict[str, dict] = {
    QUICK:              {"min_fontes": 1, "max_fontes": 3,  "exige_oficial": False,
                         "artifact": False, "max_segundos": 30},
    VERIFIED:           {"min_fontes": 2, "max_fontes": 6,  "exige_oficial": True,
                         "artifact": False, "max_segundos": 120},
    DEEP:               {"min_fontes": 5, "max_fontes": 25, "exige_oficial": True,
                         "artifact": True,  "max_segundos": 900},
    SITE_AUDIT:         {"min_fontes": 1, "max_fontes": 60, "exige_oficial": False,
                         "artifact": True,  "max_segundos": 600},
    BUSINESS_DISCOVERY: {"min_fontes": 1, "max_fontes": 60, "exige_oficial": False,
                         "artifact": True,  "max_segundos": 600},
    MONITOR:            {"min_fontes": 1, "max_fontes": 10, "exige_oficial": False,
                         "artifact": False, "max_segundos": 180},
    CLAIM_CHECK:        {"min_fontes": 2, "max_fontes": 8,  "exige_oficial": True,
                         "artifact": False, "max_segundos": 180},
}


# ---------------------------------------------------------------------------
# Tiers de fonte — §8.2
# ---------------------------------------------------------------------------

TIER_OFICIAL = 0        # legislação, SUSEP, órgão regulador, site oficial
TIER_PRIMARIA = 1       # comunicação oficial da empresa, doc técnica
TIER_ESPECIALIZADA = 2  # entidade setorial, estudo com metodologia
TIER_IMPRENSA = 3       # veículo reconhecido, análise com autoria
TIER_COMUNIDADE = 4     # fórum, rede social, avaliação, blog
TIER_NAO_VERIFICADO = 5 # agregador sem origem, texto de IA sem fonte, anônimo

# §8.3 — claims de cobertura, exclusão, obrigação legal e regulação exigem
# Tier 0/1. A lista é curta de propósito: cada exceção aqui vira uma resposta
# regulatória apoiada em blog.
TIERS_OFICIAIS = (TIER_OFICIAL, TIER_PRIMARIA)
TIERS_QUE_SUSTENTAM = (TIER_OFICIAL, TIER_PRIMARIA, TIER_ESPECIALIZADA,
                       TIER_IMPRENSA, TIER_COMUNIDADE)

ROTULO_DE_TIER = {
    TIER_OFICIAL: "fonte oficial",
    TIER_PRIMARIA: "fonte primária da empresa",
    TIER_ESPECIALIZADA: "fonte especializada",
    TIER_IMPRENSA: "imprensa ou análise",
    TIER_COMUNIDADE: "relato de comunidade",
    TIER_NAO_VERIFICADO: "não verificada",
}


def sustenta_claim(tier: int) -> bool:
    """Tier 5 nunca sustenta — §8.3. O banco também recusa."""
    return int(tier) in TIERS_QUE_SUSTENTAM


def e_oficial(tier: int) -> bool:
    return int(tier) in TIERS_OFICIAIS


# ---------------------------------------------------------------------------
# Tipos de claim e risco — §16.2
# ---------------------------------------------------------------------------

TIPOS_DE_CLAIM = ("factual", "temporal", "numeric", "comparative", "regulatory",
                  "causal", "strategic", "attributed_opinion")

# Assunto que sempre nasce de alto risco: errar aqui faz o corretor repetir ao
# cliente uma informação sobre cobertura, prazo legal ou obrigação.
TERMOS_DE_ALTO_RISCO = (
    "cobertura", "cobre", "exclusão", "exclusao", "franquia", "carência",
    "carencia", "indenização", "indenizacao", "sinistro", "obrigatório",
    "obrigatorio", "obrigação", "obrigacao", "lei ", "resolução", "resolucao",
    "circular", "susep", "cnsp", "anpd", "lgpd", "vigência", "vigencia",
    "prazo legal", "multa", "penalidade", "regulament",
)


def classificar_risco(texto: str, tipo: str = "factual") -> str:
    """Risco do claim. Regulatório é sempre alto — §16.3.

    A classificação é léxica e conservadora: ela erra para MAIS risco, nunca
    para menos. Um claim comum tratado como crítico só custa uma fonte
    oficial a mais; um claim regulatório tratado como comum vira uma
    afirmação sobre a lei sem procedência.
    """
    if tipo == "regulatory":
        return "critical"
    alvo = (texto or "").lower()
    if any(t in alvo for t in TERMOS_DE_ALTO_RISCO):
        return "high"
    if tipo in ("numeric", "temporal", "comparative"):
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# Freshness — §17
# ---------------------------------------------------------------------------

FRESHNESS = ("real_time", "hourly", "daily", "weekly", "monthly", "stable",
             "historical")

JANELA_DE_FRESHNESS = {
    "real_time": timedelta(minutes=15),
    "hourly": timedelta(hours=2),
    "daily": timedelta(days=1),
    "weekly": timedelta(days=7),
    "monthly": timedelta(days=30),
    "stable": timedelta(days=180),
    "historical": timedelta(days=3650),
}


def esta_stale(recuperado_em: Any, classe: str = "stable",
               agora: Optional[datetime] = None) -> bool:
    """§17.3 — resultado stale pode ser mostrado como histórico, não como atual."""
    d = _para_datetime(recuperado_em)
    if d is None:
        return True  # sem data, assume o pior: não dá para afirmar atualidade
    limite = JANELA_DE_FRESHNESS.get(classe, JANELA_DE_FRESHNESS["stable"])
    return (agora or _agora()) - d > limite


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _para_datetime(valor: Any) -> Optional[datetime]:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)
    try:
        d = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# Pedido
# ---------------------------------------------------------------------------


@dataclass
class ResearchRequest:
    """O pedido, já normalizado — §11."""

    company_id: str
    question: str
    objective: str = ""
    mode: str = QUICK
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    requested_by_kind: str = "user"
    escopo: dict = field(default_factory=dict)
    restricoes: dict = field(default_factory=dict)
    saidas: list[str] = field(default_factory=list)
    freshness: Optional[str] = None
    requisitos_de_fonte: dict = field(default_factory=dict)
    tempo_maximo_s: Optional[int] = None
    orcamento_brl: Optional[float] = None
    idempotency_key: Optional[str] = None

    def valido(self) -> tuple[bool, str]:
        if self.mode not in MODOS:
            return False, f"modo desconhecido: {self.mode}"
        if len((self.question or "").strip()) < 8:
            return False, "a pergunta é curta demais para virar pesquisa"
        if not self.company_id:
            return False, "pesquisa sem corretora"
        return True, ""

    def chave_idempotente(self) -> str:
        if self.idempotency_key:
            return self.idempotency_key
        base = f"{self.company_id}|{self.mode}|{' '.join(self.question.lower().split())}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:40]

    def perfil(self) -> dict:
        return PERFIL_DO_MODO.get(self.mode, PERFIL_DO_MODO[QUICK])

    def exige_work_run(self) -> bool:
        return self.mode in MODOS_COM_WORK_RUN

    def como_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Resultado de provider
# ---------------------------------------------------------------------------


@dataclass
class ResultadoDeFonte:
    """Uma fonte encontrada ou lida. Forma única, venha de qual provider vier.

    Uniformizar aqui não é elegância: é o que permite trocar de provider sem
    reescrever Skill (§4.4). Se cada adapter devolvesse seu formato, o
    orquestrador teria um `if provider ==` em cada passo.
    """

    url: str
    titulo: str = ""
    resumo: str = ""
    conteudo: str = ""
    publicado_em: Optional[str] = None
    provider: str = "desconhecido"
    tier: int = TIER_IMPRENSA
    oficial: bool = False
    idioma: Optional[str] = None
    http_status: Optional[int] = None
    metadata: dict = field(default_factory=dict)

    def content_hash(self) -> str:
        base = (self.conteudo or self.resumo or self.titulo or "").strip()
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    def tem_conteudo(self) -> bool:
        """§13.3 — snippet não é evidência final."""
        return len((self.conteudo or "").strip()) >= 200


@dataclass
class RespostaDeProvider:
    """O que um adapter devolve. Falha é resultado, não exceção."""

    ok: bool
    provider: str
    operacao: str
    fontes: list[ResultadoDeFonte] = field(default_factory=list)
    creditos: float = 0.0
    credito_estimado: bool = True
    duracao_ms: int = 0
    cache_hit: bool = False
    erro: Optional[str] = None
    motivo_humano: Optional[str] = None
    sem_credito: bool = False

    def como_usage(self) -> dict:
        return {
            "provider_key": self.provider, "operation": self.operacao,
            "units": self.creditos, "cost_is_estimated": self.credito_estimado,
            "latency_ms": self.duracao_ms, "cache_hit": self.cache_hit,
            "status": ("no_credit" if self.sem_credito
                       else "ok" if self.ok else "error"),
            "error_code": self.erro,
        }


# ---------------------------------------------------------------------------
# Claim
# ---------------------------------------------------------------------------


@dataclass
class ClaimDraft:
    """Uma afirmação antes de ir ao banco, com suas citações — §16.1."""

    claim_text: str
    claim_type: str = "factual"
    subquestao: Optional[str] = None
    confidence: float = 0.5
    freshness: str = "stable"
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    citacoes: list[dict] = field(default_factory=list)

    @property
    def risk_level(self) -> str:
        return classificar_risco(self.claim_text, self.claim_type)

    def claim_key(self) -> str:
        base = " ".join((self.claim_text or "").lower().split())[:300]
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:32]

    def citacoes_que_sustentam(self) -> list[dict]:
        return [c for c in self.citacoes if c.get("citation_role") == "supports"]

    def citacoes_oficiais(self) -> list[dict]:
        return [c for c in self.citacoes_que_sustentam() if c.get("source_official")]

    def contradicoes(self) -> list[dict]:
        return [c for c in self.citacoes if c.get("citation_role") == "contradicts"]

    def valido(self) -> tuple[bool, str]:
        """Recusa antes do banco, com mensagem legível.

        As mesmas regras existem como CHECK, mas o CHECK devolve um erro de
        constraint. Recusar aqui permite dizer *por que* — e o "por que" é o
        que faz o próximo detector nascer certo.
        """
        if self.claim_type not in TIPOS_DE_CLAIM:
            return False, f"tipo de claim desconhecido: {self.claim_type}"
        if len((self.claim_text or "").strip()) < 12:
            return False, "claim curto demais"
        if any(int(c.get("source_trust_tier", 5)) == TIER_NAO_VERIFICADO
               for c in self.citacoes_que_sustentam()):
            return False, "fonte não verificada não sustenta claim (§8.3)"
        return True, ""


def status_do_claim(rascunho: ClaimDraft) -> str:
    """Estado a partir da evidência — §10.5. Puro e sem margem.

    A ordem é deliberada: contradição vence suporte. Um claim com três fontes
    a favor e uma fonte OFICIAL contra não é "majoritariamente verdadeiro" —
    é contestado, e apresentá-lo como sustentado seria esconder a única fonte
    que mais importa.
    """
    contra = rascunho.contradicoes()
    if any(int(c.get("source_trust_tier", 5)) <= TIER_PRIMARIA for c in contra):
        return "contradicted"

    apoio = rascunho.citacoes_que_sustentam()
    if not apoio:
        return "unsupported"

    risco = rascunho.risk_level
    if risco in ("high", "critical") and not rascunho.citacoes_oficiais():
        # Tem apoio, mas não do tipo que este risco exige. É "parcialmente
        # sustentado" com a limitação declarada — nunca "sustentado".
        return "partially_supported"
    if contra:
        return "partially_supported"
    if len(apoio) >= 2 or risco == "low":
        return "supported"
    return "partially_supported"


def confianca_do_claim(rascunho: ClaimDraft) -> float:
    """Confiança 0–1 a partir do tier das fontes e da quantidade. Puro."""
    apoio = rascunho.citacoes_que_sustentam()
    if not apoio:
        return 0.1
    melhor = min(int(c.get("source_trust_tier", 5)) for c in apoio)
    base = {0: 0.95, 1: 0.88, 2: 0.75, 3: 0.65, 4: 0.45, 5: 0.2}.get(melhor, 0.4)
    if len(apoio) >= 3:
        base = min(0.98, base + 0.05)
    elif len(apoio) == 1:
        base -= 0.1
    if rascunho.contradicoes():
        base -= 0.25
    return round(max(0.05, min(0.99, base)), 3)


def chave(*partes: Any) -> str:
    base = "|".join(str(p) for p in partes if p is not None)
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:40]


def json_estavel(valor: Any) -> str:
    return json.dumps(valor, sort_keys=True, ensure_ascii=False, default=str)
