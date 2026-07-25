"""Skill Registry — procedimentos versionados. SPEC-056 §10.

O problema: hoje o Core recebe ~13 ferramentas fixas em toda invocação,
decoradas no grafo. Isso custa tokens, reduz a chance de escolher a ferramenta
certa (pesquisa de MCP mostra queda de precisão conforme o número de tools
cresce) e obriga um deploy para publicar qualquer capacidade nova.

**Progressive disclosure** inverte isso:

    índice compacto de Skills   (barato, sempre carregado)
        → resolver por intenção
        → carregar UM SkillManifest
        → carregar só as tools daquele Capability Pack
        → instruções e templates sob demanda

A Skill é o procedimento. A capability continua sendo a autoridade de poder —
uma Skill nunca concede acesso que a capability negue.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

MAX_SHORTLIST = 5


def content_hash(manifest: Any, instrucao: str = "") -> str:
    """Hash estável do conteúdo de uma release.

    É o que garante que duas releases com o mesmo conteúdo não coexistam e que
    alterar o manifesto obrigue nova versão.
    """
    base = json.dumps(manifest, sort_keys=True, ensure_ascii=False, default=str) + "\n" + (instrucao or "")
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


@dataclass
class SkillCandidate:
    """Entrada do índice compacto — o que o resolver enxerga antes de decidir."""

    skill_key: str
    name: str
    description: str
    category: str
    release_id: str
    version: str
    triggers: list[str] = field(default_factory=list)
    pack_key: Optional[str] = None
    confidence: float = 0.0


@dataclass
class ResolvedSkill:
    """Skill escolhida, com tudo que o runtime precisa e nada além."""

    skill_key: str
    release_id: str
    version: str
    manifest: dict
    instruction_markdown: str
    pack_key: Optional[str]
    capability_requirements: list[dict] = field(default_factory=list)
    tool_requirements: list[dict] = field(default_factory=list)


class SkillRegistry:
    def __init__(self, supabase_client: Any):
        self.db = getattr(supabase_client, "client", supabase_client)

    # ------------------------------------------------------------------
    # Índice compacto
    # ------------------------------------------------------------------

    def indice(self, *, agent_role: str, company_id: Optional[str] = None) -> list[SkillCandidate]:
        """Skills disponíveis para este papel/tenant, em forma compacta.

        Devolve apenas nome, descrição e gatilhos — nunca o manifesto inteiro.
        Carregar todos os manifestos aqui anularia o ganho do progressive
        disclosure.
        """
        try:
            bindings = (
                self.db.table("skill_bindings")
                .select("skill_id, skill_release_id, target_type, target_key, company_id, priority, enabled")
                .eq("enabled", True)
                .execute()
            ).data or []
        except Exception as exc:  # noqa: BLE001
            logger.error("[SkillRegistry] falha ao ler bindings: %s", type(exc).__name__)
            return []

        aplicaveis = [
            b for b in bindings
            if (
                (b["target_type"] == "platform")
                or (b["target_type"] == "agent_role" and b["target_key"] == agent_role)
                or (b["target_type"] == "tenant" and company_id and b.get("company_id") == company_id)
            )
        ]
        if not aplicaveis:
            return []

        skill_ids = list({b["skill_id"] for b in aplicaveis})
        try:
            skills = (
                self.db.table("skills")
                .select("id, skill_key, name, description, category, is_active")
                .in_("id", skill_ids).eq("is_active", True).execute()
            ).data or []

            releases = (
                self.db.table("skill_releases")
                .select("id, skill_id, version, manifest, status, is_default")
                .in_("skill_id", skill_ids).eq("status", "published").execute()
            ).data or []
        except Exception as exc:  # noqa: BLE001
            logger.error("[SkillRegistry] falha ao ler catálogo: %s", type(exc).__name__)
            return []

        por_skill: dict[str, dict] = {}
        for r in releases:
            atual = por_skill.get(r["skill_id"])
            if atual is None or r.get("is_default"):
                por_skill[r["skill_id"]] = r

        saida: list[SkillCandidate] = []
        for s in skills:
            rel = por_skill.get(s["id"])
            if not rel:
                continue  # sem release publicada não entra no índice
            manifesto = rel.get("manifest") or {}
            saida.append(SkillCandidate(
                skill_key=s["skill_key"], name=s["name"], description=s["description"],
                category=s["category"], release_id=rel["id"], version=rel["version"],
                triggers=list(manifesto.get("triggers") or []),
                pack_key=manifesto.get("capability_pack"),
            ))
        return saida

    # ------------------------------------------------------------------
    # Resolução
    # ------------------------------------------------------------------

    def shortlist(self, candidatos: list[SkillCandidate], texto: str,
                  limite: int = MAX_SHORTLIST) -> list[SkillCandidate]:
        """Ranqueia por sinal léxico dos gatilhos e do nome.

        Deliberadamente determinístico e barato. A seleção final por LLM é da
        SPEC-056 §10.3; aqui reduzimos o espaço antes de gastar token — e um
        ranqueamento explicável é mais fácil de auditar do que um embedding.
        """
        alvo = (texto or "").lower()
        if not alvo:
            return candidatos[:limite]

        palavras = {p for p in alvo.replace("?", " ").replace(",", " ").split() if len(p) > 3}

        for c in candidatos:
            score = 0.0
            for t in c.triggers:
                t_low = t.lower()
                if t_low and t_low in alvo:
                    score += 3.0
                elif any(p in t_low for p in palavras):
                    score += 1.0
            nome = c.name.lower()
            if any(p in nome for p in palavras):
                score += 1.5
            if any(p in (c.description or "").lower() for p in palavras):
                score += 0.5
            c.confidence = score

        ordenado = sorted(candidatos, key=lambda x: x.confidence, reverse=True)
        return ordenado[:limite]

    def carregar(self, release_id: str) -> Optional[ResolvedSkill]:
        """Carrega o manifesto completo de UMA release. Só depois de escolher."""
        try:
            rel = (self.db.table("skill_releases")
                   .select("id, skill_id, version, manifest, instruction_markdown, status")
                   .eq("id", release_id).maybe_single().execute()).data
            if not rel or rel.get("status") != "published":
                return None

            skill = (self.db.table("skills").select("skill_key")
                     .eq("id", rel["skill_id"]).maybe_single().execute()).data or {}

            caps = (self.db.table("skill_capability_requirements")
                    .select("capability_key, requirement, phase_key, scope_required, limits_required, ordinal")
                    .eq("skill_release_id", release_id).order("ordinal").execute()).data or []

            tools = (self.db.table("skill_tool_requirements")
                     .select("tool_key, requirement, phase_key, max_calls, approval_override, conditions, ordinal")
                     .eq("skill_release_id", release_id).order("ordinal").execute()).data or []
        except Exception as exc:  # noqa: BLE001
            logger.error("[SkillRegistry] falha ao carregar release: %s", type(exc).__name__)
            return None

        manifesto = rel.get("manifest") or {}
        return ResolvedSkill(
            skill_key=skill.get("skill_key", "?"),
            release_id=rel["id"], version=rel["version"],
            manifest=manifesto,
            instruction_markdown=rel.get("instruction_markdown") or "",
            pack_key=manifesto.get("capability_pack"),
            capability_requirements=caps, tool_requirements=tools,
        )

    def resolver(self, *, agent_role: str, texto: str,
                 company_id: Optional[str] = None) -> Optional[ResolvedSkill]:
        """Índice → shortlist → carrega a melhor. Sem match, devolve `None`.

        `None` significa *"siga o caminho conversacional normal"* — nem toda
        pergunta é um procedimento, e forçar uma Skill onde não cabe piora a
        resposta.
        """
        candidatos = self.indice(agent_role=agent_role, company_id=company_id)
        if not candidatos:
            return None
        top = self.shortlist(candidatos, texto)
        if not top or top[0].confidence <= 0:
            return None
        logger.info("[SkillRegistry] Skill '%s' selecionada (confiança %.1f)",
                    top[0].skill_key, top[0].confidence)
        return self.carregar(top[0].release_id)

    # ------------------------------------------------------------------
    # Publicação
    # ------------------------------------------------------------------

    def publicar(self, release_id: str, aprovador_user_id: Optional[str] = None,
                 tornar_default: bool = True) -> bool:
        """Publica uma release. A partir daqui ela é imutável."""
        from datetime import datetime, timezone

        agora = datetime.now(timezone.utc).isoformat()
        try:
            rel = (self.db.table("skill_releases").select("id, skill_id, status")
                   .eq("id", release_id).maybe_single().execute()).data
            if not rel:
                return False
            if rel["status"] == "published":
                return True

            if tornar_default:
                # Só uma default por Skill — a UNIQUE parcial recusaria duas.
                self.db.table("skill_releases").update({"is_default": False}) \
                    .eq("skill_id", rel["skill_id"]).eq("is_default", True).execute()

            self.db.table("skill_releases").update({
                "status": "published", "published_at": agora,
                "approved_at": agora, "approved_by_user_id": aprovador_user_id,
                "is_default": tornar_default,
            }).eq("id", release_id).execute()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("[SkillRegistry] falha ao publicar: %s", type(exc).__name__)
            return False
