"""Claims, citações, contradição e verificação. SPEC-060 §16.

Claim-first (§16.1): antes de escrever qualquer texto, o sistema estrutura as
afirmações. A inversão é o ponto — quando o texto vem primeiro, as citações
viram decoração colada no fim, e ninguém consegue dizer *qual fonte sustenta
qual frase*.

O que o verifier existe para impedir
------------------------------------
Não é fonte errada. É **conclusão que excede a evidência**: três páginas dizem
que a seguradora mudou o telefone da assistência, e o texto sai afirmando que
ela mudou o processo de acionamento. As três fontes são verdadeiras; a
afirmação não. §16.4 lista essa checagem por último de propósito — é a que
mais escapa.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from .schemas import (TIER_NAO_VERIFICADO, ClaimDraft, ResultadoDeFonte,
                      confianca_do_claim, esta_stale, status_do_claim)
from .source_policy import rotulo_da_fonte

logger = logging.getLogger(__name__)

# Palavras que ampliam o alcance de uma afirmação além do que uma fonte
# pontual sustenta. Não proíbem o claim — obrigam evidência mais forte.
GENERALIZADORES = ("todos", "todas", "sempre", "nunca", "qualquer", "nenhum",
                   "obrigatoriamente", "em todos os casos", "toda seguradora",
                   "qualquer apólice")

# Um número no claim exige fonte e período (§16.3). Este é o detector.
_NUMERO = re.compile(r"\b\d+(?:[.,]\d+)?\s*(%|por cento|reais|r\$|mil|milh)", re.I)
_ANO = re.compile(r"\b(19|20)\d{2}\b")


@dataclass
class Veredito:
    """O que o verifier concluiu sobre um claim — §16.4."""

    aprovado: bool
    status: str
    confianca: float
    motivos: list[str] = field(default_factory=list)
    limitacoes: list[str] = field(default_factory=list)

    def como_dict(self) -> dict:
        return {"aprovado": self.aprovado, "status": self.status,
                "confianca": self.confianca, "motivos": self.motivos,
                "limitacoes": self.limitacoes}


# ---------------------------------------------------------------------------
# Verificação — pura
# ---------------------------------------------------------------------------


def verificar(rascunho: ClaimDraft, *,
              agora: Optional[datetime] = None) -> Veredito:
    """As oito checagens de §16.4. Pura, e por isso testável caso a caso.

    Devolve `aprovado=False` quando o claim NÃO pode ser apresentado como
    sustentado — mas o claim continua existindo, com o status certo. Descartar
    silenciosamente esconderia do usuário que a pergunta foi investigada e não
    teve resposta suficiente, que é uma informação útil.
    """
    motivos: list[str] = []
    limitacoes: list[str] = []
    agora = agora or datetime.now(timezone.utc)

    ok, motivo = rascunho.valido()
    if not ok:
        return Veredito(False, "unsupported", 0.1, [motivo])

    apoio = rascunho.citacoes_que_sustentam()
    oficiais = rascunho.citacoes_oficiais()
    contra = rascunho.contradicoes()
    risco = rascunho.risk_level
    texto = (rascunho.claim_text or "").lower()

    # 1. Suporte.
    if not apoio:
        motivos.append("nenhuma fonte sustenta esta afirmação")

    # 2. Fonte adequada ao risco.
    if risco in ("high", "critical") and not oficiais:
        motivos.append(
            "afirmação de cobertura, prazo legal ou regulação sem fonte oficial")
        limitacoes.append(
            "Não encontramos fonte oficial para esta afirmação. Ela aparece "
            "como indicação, não como regra confirmada.")

    # 3. Contradição.
    if contra:
        limitacoes.append(
            f"{len(contra)} fonte(s) apresentam informação divergente — "
            "a divergência está registrada junto do resultado.")

    # 4. Freshness.
    for c in apoio:
        if esta_stale(c.get("retrieved_at"), rascunho.freshness, agora):
            limitacoes.append(
                "Parte das fontes é mais antiga que a janela pedida; o dado "
                "vale como histórico, não como situação atual.")
            break

    # 5. Números exigem fonte E período.
    if _NUMERO.search(texto) or rascunho.claim_type == "numeric":
        if not apoio:
            motivos.append("número sem fonte")
        elif not any(c.get("locator") or c.get("source_excerpt") for c in apoio):
            limitacoes.append(
                "O número não pôde ser localizado dentro da fonte — confira "
                "antes de usar.")

    # 6. Claim temporal exige data.
    if rascunho.claim_type == "temporal" and not (_ANO.search(texto)
                                                  or rascunho.valid_from):
        motivos.append("afirmação sobre data sem data declarada")

    # 7. Regulatório exige vigência.
    if rascunho.claim_type == "regulatory" and not rascunho.valid_from:
        limitacoes.append(
            "A vigência desta norma não foi confirmada na fonte. Uma apólice "
            "antiga pode seguir a versão anterior.")

    # 8. Conclusão que excede a evidência — a que mais escapa.
    if any(g in texto for g in GENERALIZADORES) and len(apoio) < 2:
        motivos.append(
            "a afirmação generaliza ('todos', 'sempre') com uma fonte só")

    if rascunho.claim_type == "causal" and not oficiais:
        limitacoes.append(
            "A relação de causa é leitura nossa a partir das fontes, não uma "
            "afirmação delas.")

    status = status_do_claim(rascunho)
    confianca = confianca_do_claim(rascunho)
    if motivos:
        confianca = min(confianca, 0.45)

    aprovado = status in ("supported", "partially_supported") and not any(
        m.startswith("nenhuma fonte") or m.startswith("número sem fonte")
        for m in motivos)

    return Veredito(aprovado, status, confianca, motivos, limitacoes)


def detectar_contradicoes(claims: list[ClaimDraft]) -> list[dict]:
    """Claims do mesmo assunto que se negam — §16.8. Puro e conservador.

    Léxico de propósito: detecta a negação explícita sobre o mesmo conjunto de
    termos. Uma versão semântica erraria com mais confiança, e aqui o custo do
    falso positivo é baixo (mostra a divergência) enquanto o do falso negativo
    é alto (afirma como certo algo que as fontes disputam).
    """
    negacoes = ("não ", "nao ", "nunca ", "jamais ", "deixou de ", "sem ")
    saida: list[dict] = []
    for i, a in enumerate(claims):
        termos_a = {t for t in (a.claim_text or "").lower().split() if len(t) > 4}
        if len(termos_a) < 3:
            continue
        for b in claims[i + 1:]:
            termos_b = {t for t in (b.claim_text or "").lower().split() if len(t) > 4}
            if not termos_b:
                continue
            sobreposicao = len(termos_a & termos_b) / max(1, min(len(termos_a), len(termos_b)))
            if sobreposicao < 0.6:
                continue
            nega_a = any(n in (a.claim_text or "").lower() for n in negacoes)
            nega_b = any(n in (b.claim_text or "").lower() for n in negacoes)
            if nega_a != nega_b:
                saida.append({"a": a.claim_key(), "b": b.claim_key(),
                              "texto_a": a.claim_text, "texto_b": b.claim_text,
                              "sobreposicao": round(sobreposicao, 2)})
    return saida


def montar_citacao(fonte: ResultadoDeFonte, snapshot: dict, *,
                   papel: str = "supports", trecho: Optional[str] = None,
                   localizador: Optional[dict] = None) -> dict:
    """Citação no nível da afirmação — §16.5.

    O `source_trust_tier` é copiado para a citação de propósito: ele é o que o
    CHECK do banco usa para recusar Tier 5 como sustentação. Deixá-lo só na
    fonte tornaria a regra dependente de um JOIN — e uma constraint que
    depende de JOIN não existe.
    """
    tier = int(snapshot.get("_tier", fonte.tier))
    oficial = bool(snapshot.get("_oficial", fonte.oficial))
    return {
        "source_snapshot_id": snapshot.get("id"),
        "citation_role": papel,
        "support_strength": 0.9 if oficial else (0.7 if tier <= 2 else 0.5),
        "source_excerpt": (trecho or "")[:800] or None,
        "locator": localizador or {},
        "source_trust_tier": tier,
        "source_official": oficial,
        # Campos só para a apresentação — não vão para o banco.
        "url": snapshot.get("_url") or fonte.url,
        "titulo": snapshot.get("_titulo") or fonte.titulo or rotulo_da_fonte(fonte.url),
        "publisher": rotulo_da_fonte(fonte.url),
        "retrieved_at": snapshot.get("retrieved_at"),
        "published_at": snapshot.get("published_at"),
    }


def localizar_trecho(conteudo: str, claim: str, *, janela: int = 320) -> Optional[str]:
    """Acha na fonte o trecho que sustenta o claim — §16.5 (`locator`).

    Sem isto a citação aponta para a página inteira, e conferir vira ler
    sessenta páginas de PDF. Busca pelos termos mais distintivos do claim, não
    pela frase inteira — a fonte quase nunca usa as mesmas palavras.
    """
    texto = conteudo or ""
    if not texto:
        return None
    termos = sorted({t.strip(".,;:()") for t in (claim or "").lower().split()
                     if len(t) > 5}, key=len, reverse=True)[:6]
    baixo = texto.lower()
    for termo in termos:
        pos = baixo.find(termo)
        if pos >= 0:
            inicio = max(0, pos - janela // 2)
            return " ".join(texto[inicio:inicio + janela].split())
    return None


# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------


class ClaimService:
    def __init__(self, supabase_client: Any):
        self.db = getattr(supabase_client, "client", supabase_client)

    def gravar(self, *, company_id: str, research_request_id: str,
               rascunho: ClaimDraft, veredito: Veredito,
               work_run_id: Optional[str] = None) -> Optional[dict]:
        """Grava claim e citações. As citações vêm ANTES do status final.

        A ordem não é estética: os contadores que o CHECK de "alto risco exige
        fonte oficial" consulta são mantidos por trigger a partir das citações.
        Gravar o claim já como `supported` antes de existir citação seria
        recusado pelo banco — e é assim que deve ser.
        """
        linha = {
            "company_id": company_id,
            "research_request_id": research_request_id,
            "work_run_id": work_run_id,
            "claim_key": rascunho.claim_key(),
            "claim_text": rascunho.claim_text[:4_000],
            "claim_type": rascunho.claim_type,
            "status": "draft",
            "confidence": round(float(veredito.confianca), 3),
            "risk_level": rascunho.risk_level,
            "freshness": rascunho.freshness,
            "valid_from": rascunho.valid_from,
            "valid_until": rascunho.valid_until,
            "contradiction_status": "confirmada" if rascunho.contradicoes() else "nenhuma",
            "verification_status": ("verificado" if veredito.aprovado
                                    else "reprovado" if veredito.motivos
                                    else "inconclusivo"),
            "notes": "; ".join(veredito.motivos + veredito.limitacoes)[:2_000] or None,
        }
        try:
            r = self.db.table("research_claims").insert(linha).execute()
            claim = (r.data or [{}])[0]
        except Exception as exc:  # noqa: BLE001
            if "duplicate" in str(exc).lower() or "unique" in str(exc).lower():
                try:
                    claim = (self.db.table("research_claims").select("*")
                             .eq("research_request_id", research_request_id)
                             .eq("claim_key", rascunho.claim_key())
                             .maybe_single().execute()).data or {}
                except Exception:  # noqa: BLE001
                    return None
            else:
                logger.error("[ClaimService] claim nao gravado: %s", type(exc).__name__)
                return None

        claim_id = claim.get("id")
        if not claim_id:
            return None

        gravadas = 0
        for c in rascunho.citacoes:
            if not c.get("source_snapshot_id"):
                continue
            if int(c.get("source_trust_tier", 5)) == TIER_NAO_VERIFICADO \
               and c.get("citation_role") == "supports":
                continue  # o banco recusaria; recusar aqui evita o ruído
            try:
                self.db.table("research_claim_citations").insert({
                    "company_id": company_id, "claim_id": claim_id,
                    "source_snapshot_id": c["source_snapshot_id"],
                    "citation_role": c.get("citation_role", "supports"),
                    "support_strength": float(c.get("support_strength", 0.5)),
                    "source_excerpt": c.get("source_excerpt"),
                    "locator": c.get("locator") or {},
                    "source_trust_tier": int(c.get("source_trust_tier", 3)),
                    "source_official": bool(c.get("source_official")),
                }).execute()
                gravadas += 1
            except Exception as exc:  # noqa: BLE001
                if "duplicate" not in str(exc).lower():
                    logger.warning("[ClaimService] citacao: %s", type(exc).__name__)

        # Só agora o status final — com os contadores já atualizados pelo
        # trigger. Se o banco recusar, o claim fica em `draft` com a nota, o
        # que é a verdade: ele não pôde ser sustentado.
        if gravadas and veredito.status != "draft":
            try:
                self.db.table("research_claims").update(
                    {"status": veredito.status}).eq("id", claim_id).execute()
                claim["status"] = veredito.status
            except Exception as exc:  # noqa: BLE001
                logger.info("[ClaimService] claim '%s' permanece em draft: %s",
                            rascunho.claim_key()[:8], type(exc).__name__)

        claim["_citacoes"] = gravadas
        return claim

    def do_pedido(self, company_id: str, research_request_id: str) -> list[dict]:
        try:
            r = (self.db.table("research_claims").select("*")
                 .eq("company_id", company_id)
                 .eq("research_request_id", research_request_id)
                 .order("risk_level", desc=True).limit(200).execute())
            return r.data or []
        except Exception:  # noqa: BLE001
            return []

    def citacoes(self, company_id: str, claim_ids: list[str]) -> dict[str, list[dict]]:
        if not claim_ids:
            return {}
        try:
            r = (self.db.table("research_claim_citations")
                 .select("claim_id, citation_role, support_strength, "
                         "source_excerpt, locator, source_trust_tier, "
                         "source_official, source_snapshot_id")
                 .eq("company_id", company_id).in_("claim_id", claim_ids)
                 .limit(1000).execute())
        except Exception:  # noqa: BLE001
            return {}
        agrupado: dict[str, list[dict]] = {}
        for c in r.data or []:
            agrupado.setdefault(c["claim_id"], []).append(c)
        return agrupado

    def cobertura_de_citacao(self, claims: list[dict]) -> Optional[float]:
        """§31.5 — quanto dos claims tem pelo menos uma citação.

        `None` quando não há claim: devolver 100% para lista vazia diria
        "cobertura perfeita" onde não houve pesquisa.
        """
        if not claims:
            return None
        com = sum(1 for c in claims if int(c.get("citation_count") or 0) > 0)
        return round(100.0 * com / len(claims), 1)
