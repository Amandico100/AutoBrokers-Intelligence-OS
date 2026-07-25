"""Tool Gateway — autoridade ÚNICA de seleção e execução de ferramentas.

SPEC-056 §6.2, §11, §12, §16.

Antes desta SPEC existiam autorizações paralelas: `tools_config` decidia tools
legadas, o cadastro do Agent decidia MCPs, o HTTP router entrava por conta
própria e o Capability Registry só valia com `AUTHORITY_STRICT_MODE` ligado —
que estava desligado. Quatro caminhos, quatro respostas possíveis para a mesma
pergunta *"este agente pode usar isto?"*.

A partir daqui há **uma** resposta, e ela é composta:

    Skill escolhida
      → Capability Pack declarado
        → capability ATIVA no Registry (SPEC-014/054, com scope)
          → tool release publicada
            → limites da Skill
              → aprovação quando o efeito exigir
                → ferramenta liberada

Qualquer negativa em qualquer elo **nega**. Nunca o contrário — um `scope`
ausente ou um Registry inacessível resultam em negação, não em liberação.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Teto de ferramentas simultâneas. Existe porque anexar dezenas de tools
# degrada a escolha do modelo — SPEC-053 §13.1.
MAX_TOOLS_POR_EXECUCAO = 12


@dataclass
class ToolGrant:
    """Uma ferramenta liberada, com o contrato que a acompanha."""

    tool_key: str
    tool_release_id: str
    capability_key: str
    implementation_kind: str
    name: str
    description: str
    input_schema: dict
    side_effect_class: str
    risk_level: str
    requires_approval: bool
    requires_connection: bool
    max_calls: Optional[int] = None
    phase_key: Optional[str] = None


@dataclass
class GatewayDecision:
    """Resultado da seleção — inclui o que foi negado e por quê."""

    granted: list[ToolGrant] = field(default_factory=list)
    denied: list[dict] = field(default_factory=list)
    skill_key: Optional[str] = None
    skill_release_id: Optional[str] = None
    pack_key: Optional[str] = None

    def keys(self) -> list[str]:
        return [g.tool_key for g in self.granted]

    def resumo_humano(self) -> str:
        if not self.granted:
            return "Nenhuma ferramenta liberada para este trabalho."
        nomes = ", ".join(g.name for g in self.granted[:6])
        extra = f" e mais {len(self.granted) - 6}" if len(self.granted) > 6 else ""
        return f"Ferramentas disponíveis: {nomes}{extra}."


class ToolGateway:
    def __init__(self, supabase_client: Any):
        self.db = getattr(supabase_client, "client", supabase_client)

    # ------------------------------------------------------------------

    def selecionar(
        self,
        *,
        company_id: str,
        agent_role: str,
        active_capabilities: dict[str, dict],
        skill: Optional[Any] = None,
        pack_key: Optional[str] = None,
        max_tools: int = MAX_TOOLS_POR_EXECUCAO,
    ) -> GatewayDecision:
        """Decide o conjunto mínimo de ferramentas para esta execução.

        `active_capabilities` vem do Capability Resolver — já traz status e
        `scope`. O Gateway **não reinterpreta** poder; ele apenas escolhe, do
        que já está autorizado, o que a Skill precisa.
        """
        decisao = GatewayDecision()

        if skill is not None:
            decisao.skill_key = getattr(skill, "skill_key", None)
            decisao.skill_release_id = getattr(skill, "release_id", None)
            pack_key = pack_key or getattr(skill, "pack_key", None)
        decisao.pack_key = pack_key

        # 1. Quais tools o pacote/Skill declara
        tool_keys, limites = self._tools_declaradas(skill, pack_key)
        if not tool_keys:
            logger.info("[ToolGateway] nenhuma tool declarada (pack=%s) — Core sem ferramentas", pack_key)
            return decisao

        # 2. Definições e releases publicadas
        definicoes = self._definicoes(tool_keys)
        if not definicoes:
            return decisao

        releases = self._releases_publicadas([d["id"] for d in definicoes])

        ativas = {k for k, v in (active_capabilities or {}).items() if v.get("status") == "active"}

        for d in definicoes:
            tool_key = d["tool_key"]
            cap = d["capability_key"]

            if not d.get("is_active", True):
                decisao.denied.append({"tool_key": tool_key, "motivo": "tool_desativada"})
                continue

            # A capability é a autoridade. Sem ela ativa, a tool não existe
            # para esta execução — independentemente do que a Skill peça.
            if cap not in ativas:
                estado = (active_capabilities or {}).get(cap, {}).get("status", "ausente")
                decisao.denied.append({
                    "tool_key": tool_key, "capability_key": cap,
                    "motivo": f"capability_{estado}",
                    "mensagem_humana": self._motivo_humano(estado, cap),
                })
                continue

            rel = releases.get(d["id"])
            if not rel:
                decisao.denied.append({"tool_key": tool_key, "motivo": "sem_release_publicada"})
                continue

            escopo = (active_capabilities or {}).get(cap, {}).get("scope") or {}

            # Aprovação é o MAIOR entre: tool, capability scope e override da
            # Skill. Override só aumenta proteção (o CHECK do banco garante).
            requer_aprovacao = bool(
                d.get("requires_approval")
                or escopo.get("requires_approval")
                or limites.get(tool_key, {}).get("approval_override") == "always"
            )

            # Limite de chamadas: o MENOR entre o que a Skill pede e o que o
            # escopo da capability permite.
            max_skill = limites.get(tool_key, {}).get("max_calls")
            max_escopo = escopo.get("max_calls_per_run")
            max_calls = min([x for x in (max_skill, max_escopo) if x is not None], default=None)

            decisao.granted.append(ToolGrant(
                tool_key=tool_key,
                tool_release_id=rel["id"],
                capability_key=cap,
                implementation_kind=d["implementation_kind"],
                name=d["name"],
                description=d["description"],
                input_schema=rel.get("input_schema") or {},
                side_effect_class=d["side_effect_class"],
                risk_level=d["risk_level"],
                requires_approval=requer_aprovacao,
                requires_connection=bool(d.get("requires_connection")),
                max_calls=max_calls,
                phase_key=limites.get(tool_key, {}).get("phase_key"),
            ))

        # 3. Teto — prioriza menor risco primeiro (leitura antes de escrita)
        if len(decisao.granted) > max_tools:
            ordem = {"none": 0, "read": 1, "prepare": 2, "write_reversible": 3,
                     "communication": 4, "write_irreversible": 5, "financial": 6,
                     "external_commitment": 7}
            decisao.granted.sort(key=lambda g: ordem.get(g.side_effect_class, 9))
            cortadas = decisao.granted[max_tools:]
            decisao.granted = decisao.granted[:max_tools]
            for g in cortadas:
                decisao.denied.append({"tool_key": g.tool_key, "motivo": "limite_de_ferramentas"})
            logger.warning("[ToolGateway] %d ferramenta(s) cortada(s) pelo teto de %d",
                           len(cortadas), max_tools)

        logger.info("[ToolGateway] skill=%s pack=%s liberadas=%d negadas=%d",
                    decisao.skill_key, pack_key, len(decisao.granted), len(decisao.denied))
        return decisao

    # ------------------------------------------------------------------

    def _motivo_humano(self, estado: str, cap: str) -> str:
        return {
            "needs_connection": "Falta conectar este sistema. Posso te mostrar como.",
            "disabled": "Este recurso está desligado para a sua corretora.",
            "provider_unavailable": "O serviço externo está indisponível no momento.",
            "scope_missing": "Este recurso ainda não foi configurado com segurança.",
            "ausente": "Este recurso não faz parte das suas permissões.",
        }.get(estado, "Recurso indisponível.")

    def _tools_declaradas(self, skill: Any, pack_key: Optional[str]) -> tuple[list[str], dict]:
        """Tools que a Skill exige + as do Capability Pack."""
        keys: list[str] = []
        limites: dict[str, dict] = {}

        for req in (getattr(skill, "tool_requirements", None) or []):
            if req.get("requirement") == "forbidden":
                continue
            tk = req.get("tool_key")
            if tk:
                keys.append(tk)
                limites[tk] = {
                    "max_calls": req.get("max_calls"),
                    "approval_override": req.get("approval_override"),
                    "phase_key": req.get("phase_key"),
                }

        if pack_key:
            try:
                pack = (self.db.table("capability_packs").select("id")
                        .eq("pack_key", pack_key).eq("is_active", True).maybe_single().execute()).data
                if pack:
                    rel = (self.db.table("capability_pack_releases").select("id")
                           .eq("capability_pack_id", pack["id"]).eq("status", "published")
                           .eq("is_default", True).maybe_single().execute()).data
                    if rel:
                        membros = (self.db.table("capability_pack_members")
                                   .select("member_type, member_key, limits")
                                   .eq("pack_release_id", rel["id"]).eq("member_type", "tool")
                                   .order("ordinal").execute()).data or []
                        for m in membros:
                            mk = m["member_key"]
                            if mk not in keys:
                                keys.append(mk)
                                lim = m.get("limits") or {}
                                limites.setdefault(mk, {"max_calls": lim.get("max_calls"),
                                                        "approval_override": None,
                                                        "phase_key": None})
            except Exception as exc:  # noqa: BLE001
                logger.error("[ToolGateway] falha ao ler pack '%s': %s", pack_key, type(exc).__name__)

        return keys, limites

    def _definicoes(self, tool_keys: list[str]) -> list[dict]:
        try:
            return (self.db.table("tool_definitions")
                    .select("id, tool_key, name, description, implementation_kind, capability_key, "
                            "risk_level, side_effect_class, requires_connection, requires_approval, is_active")
                    .in_("tool_key", tool_keys).execute()).data or []
        except Exception as exc:  # noqa: BLE001
            logger.error("[ToolGateway] falha ao ler definições: %s", type(exc).__name__)
            return []

    def _releases_publicadas(self, tool_ids: list[str]) -> dict[str, dict]:
        try:
            linhas = (self.db.table("tool_releases")
                      .select("id, tool_id, version, input_schema, output_schema, execution_manifest, is_default")
                      .in_("tool_id", tool_ids).eq("status", "published").execute()).data or []
        except Exception as exc:  # noqa: BLE001
            logger.error("[ToolGateway] falha ao ler releases: %s", type(exc).__name__)
            return {}

        por_tool: dict[str, dict] = {}
        for r in linhas:
            atual = por_tool.get(r["tool_id"])
            if atual is None or r.get("is_default"):
                por_tool[r["tool_id"]] = r
        return por_tool

    # ------------------------------------------------------------------
    # Registro de invocação
    # ------------------------------------------------------------------

    def registrar_invocacao(
        self, *, company_id: str, grant: ToolGrant, invocation_key: str,
        input_fingerprint: str, status: str = "running",
        work_run_id: Optional[str] = None, work_step_id: Optional[str] = None,
        skill_release_id: Optional[str] = None, input_summary: Optional[dict] = None,
        error_code: Optional[str] = None, trace_id: Optional[str] = None,
    ) -> Optional[str]:
        """Grava a invocação. Idempotente por `(company_id, invocation_key)`.

        Registrar a NEGATIVA é tão importante quanto registrar o sucesso: é
        assim que o Admin descobre que um corretor está esbarrando numa
        conexão faltando, em vez de só ver o agente "não conseguindo".
        """
        try:
            res = self.db.table("tool_invocations").insert({
                "company_id": company_id,
                "work_run_id": work_run_id,
                "work_step_id": work_step_id,
                "skill_release_id": skill_release_id,
                "tool_release_id": grant.tool_release_id,
                "capability_key": grant.capability_key,
                "invocation_key": invocation_key,
                "status": status,
                "input_fingerprint": input_fingerprint,
                "input_summary": input_summary or {},
                "error_code": error_code,
                "trace_id": trace_id,
            }).execute()
            return (res.data or [{}])[0].get("id")
        except Exception as exc:  # noqa: BLE001
            if "duplicate" in str(exc).lower() or "unique" in str(exc).lower():
                return None  # já registrada
            logger.warning("[ToolGateway] invocação não registrada: %s", type(exc).__name__)
            return None

    def finalizar_invocacao(self, invocation_id: str, *, status: str,
                            output_summary: Optional[dict] = None,
                            provider_reference: Optional[str] = None,
                            latency_ms: Optional[int] = None,
                            error_code: Optional[str] = None) -> None:
        from datetime import datetime, timezone

        try:
            self.db.table("tool_invocations").update({
                "status": status,
                "output_summary": output_summary or {},
                "provider_reference": provider_reference,
                "latency_ms": latency_ms,
                "error_code": error_code,
                "finished_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", invocation_id).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[ToolGateway] finalização não registrada: %s", type(exc).__name__)
