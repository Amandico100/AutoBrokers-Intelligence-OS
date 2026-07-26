"""Demand Radar — demanda agregada e anonima. SPEC-059 §19.

A fronteira que este modulo protege
-----------------------------------
O cluster e visao de **plataforma**. Ele responde "quantas corretoras querem
isto", e essa pergunta nao precisa saber QUAIS corretoras. Por isso
`demand_cluster_members` guarda `tenant_hash` — um digest com sal — e nao
`company_id`. Sem isso, a anonimizacao seria decorativa: bastaria ler a coluna.

O sal vem de `DEMAND_CLUSTER_SALT`. Sem ele, o hash de um UUID conhecido e
reversivel por forca bruta em segundos, porque o espaco de corretoras e
pequeno.
"""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from .redaction_service import contem_pii, resumo_seguro
from .signal_service import registrar_evento

logger = logging.getLogger(__name__)

ESTADOS = ("new", "triaged", "researching", "planned", "building",
           "released", "rejected", "merged")


def hash_de_tenant(company_id: str) -> str:
    """Digest com sal. Permite CONTAR corretoras distintas sem identifica-las."""
    sal = os.getenv("DEMAND_CLUSTER_SALT") or "autobrokers-demand-v1"
    return hashlib.sha256(f"{sal}|{company_id}".encode("utf-8")).hexdigest()[:24]


def calcular_score(*, tenant_count: int, request_count: int,
                   feasibility: float = 50.0, risk: float = 20.0) -> dict:
    """Score de demanda — §19.2. Puro.

    `tenant_count` pesa mais que `request_count` de proposito: dez pedidos de
    uma corretora sao um caso; um pedido de dez corretoras e um produto.
    """
    frequencia = min(100.0, 12.0 * float(request_count))
    alcance = min(100.0, 25.0 * float(tenant_count))
    impacto = round(0.65 * alcance + 0.35 * frequencia, 2)
    score = round(
        impacto * 0.45 + frequencia * 0.20 + float(feasibility) * 0.25
        - float(risk) * 0.10, 2)
    return {"impact_score": impacto, "frequency_score": round(frequencia, 2),
            "feasibility_score": round(float(feasibility), 2),
            "risk_score": round(float(risk), 2),
            "demand_score": max(0.0, min(100.0, score))}


class DemandClusterService:
    def __init__(self, supabase_client: Any):
        self.db = getattr(supabase_client, "client", supabase_client)

    # ------------------------------------------------------------------

    def agregar(self, *, dias: int = 90, limite: int = 500) -> dict:
        """Le pedidos e lacunas de todas as corretoras e monta os clusters.

        Roda como Work Run de plataforma (§28.2), nunca dentro do fluxo de uma
        corretora — um tenant nao pode disparar processamento que le dado
        agregado de todos.
        """
        desde = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
        membros: list[dict] = []

        try:
            pedidos = (self.db.table("auxiliary_requests")
                       .select("id, company_id, request_fingerprint, requested_outcome, "
                               "classified_work_pattern, created_at")
                       .gte("created_at", desde).limit(limite).execute()).data or []
            for p in pedidos:
                if not p.get("request_fingerprint") or not p.get("company_id"):
                    continue
                membros.append({
                    "tipo": "auxiliary_request", "id": p["id"],
                    "assinatura": p["request_fingerprint"],
                    "tenant": str(p["company_id"]),
                    "resumo": str(p.get("requested_outcome") or ""),
                    "quando": p.get("created_at"),
                    "padrao": p.get("classified_work_pattern")})
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Demand] auxiliary_requests: %s", type(exc).__name__)

        try:
            lacunas = (self.db.table("capability_gaps")
                       .select("id, company_id, fingerprint, description_redacted, "
                               "gap_type, capability_key, frequency_count, first_seen_at")
                       .gte("first_seen_at", desde).limit(limite).execute()).data or []
            for l in lacunas:
                if not l.get("fingerprint"):
                    continue
                membros.append({
                    "tipo": "capability_gap", "id": l["id"],
                    "assinatura": l["fingerprint"],
                    "tenant": str(l.get("company_id") or "plataforma"),
                    "resumo": str(l.get("description_redacted") or ""),
                    "quando": l.get("first_seen_at"),
                    "gap_type": l.get("gap_type"),
                    "capability_key": l.get("capability_key"),
                    "peso": int(l.get("frequency_count") or 1)})
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Demand] capability_gaps: %s", type(exc).__name__)

        try:
            sinais = (self.db.table("intelligence_signals")
                      .select("id, company_id, subject_id, summary_redacted, "
                              "signal_type, occurrence_count, created_at")
                      .in_("signal_type", ["feature_request", "broker_desire",
                                           "repeated_task", "capability_gap"])
                      .gte("created_at", desde).limit(limite).execute()).data or []
            for s in sinais:
                if not s.get("subject_id"):
                    continue
                membros.append({
                    "tipo": "intelligence_signal", "id": s["id"],
                    "assinatura": str(s["subject_id"]),
                    "tenant": str(s["company_id"]),
                    "resumo": str(s.get("summary_redacted") or ""),
                    "quando": s.get("created_at"),
                    "peso": int(s.get("occurrence_count") or 1)})
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Demand] intelligence_signals: %s", type(exc).__name__)

        return self._materializar(membros)

    def _materializar(self, membros: list[dict]) -> dict:
        grupos: dict[str, list[dict]] = {}
        for m in membros:
            grupos.setdefault(m["assinatura"], []).append(m)

        criados, atualizados = 0, 0
        for assinatura, itens in grupos.items():
            tenants = {hash_de_tenant(i["tenant"]) for i in itens}
            pedidos = sum(int(i.get("peso") or 1) for i in itens)
            exemplo = max(itens, key=lambda i: len(str(i.get("resumo") or "")))
            problema = resumo_seguro(str(exemplo.get("resumo") or ""), 240)
            if not problema or contem_pii(problema):
                # Nao sobe para o agregado global o que ainda carrega PII —
                # §18.5 e a fronteira mais cara de errar do sistema inteiro.
                continue

            scores = calcular_score(tenant_count=len(tenants), request_count=pedidos)
            gaps = [i for i in itens if i["tipo"] == "capability_gap"]
            linha = {
                "cluster_key": assinatura,
                "category": "capability" if gaps else "automation",
                "canonical_problem": problema,
                "canonical_outcome": "",
                "tenant_count": len(tenants),
                "request_count": pedidos,
                "last_seen_at": datetime.now(timezone.utc).isoformat(),
                "capability_gap_summary": {
                    "gap_types": sorted({str(g.get("gap_type") or "") for g in gaps} - {""}),
                    "capability_keys": sorted({str(g.get("capability_key") or "")
                                               for g in gaps} - {""}),
                },
                **scores,
            }
            cluster_id = self._upsert(linha)
            if not cluster_id:
                continue
            criados += 1
            self._gravar_membros(cluster_id, itens)
            atualizados += len(itens)

        registrar_evento(self.db, company_id=None, tipo="demand.clustered",
                         subject_type="demand", mensagem=f"{criados} cluster(s) atualizado(s)",
                         detalhe={"clusters": criados, "membros": atualizados})
        return {"clusters": criados, "membros": atualizados,
                "assinaturas": len(grupos)}

    def _upsert(self, linha: dict) -> Optional[str]:
        try:
            existente = (self.db.table("demand_clusters").select("id, status")
                         .eq("cluster_key", linha["cluster_key"])
                         .maybe_single().execute()).data
            if existente:
                # `status` NAO e sobrescrito: o produto ja pode ter triado,
                # planejado ou rejeitado este cluster, e a agregacao automatica
                # nao pode desfazer decisao humana.
                self.db.table("demand_clusters").update(
                    {k: v for k, v in linha.items() if k != "cluster_key"}
                ).eq("id", existente["id"]).execute()
                return existente["id"]
            r = self.db.table("demand_clusters").insert(linha).execute()
            return (r.data or [{}])[0].get("id")
        except Exception as exc:  # noqa: BLE001
            logger.error("[Demand] upsert falhou: %s", type(exc).__name__)
            return None

    def _gravar_membros(self, cluster_id: str, itens: list[dict]) -> None:
        linhas = []
        for i in itens:
            resumo = resumo_seguro(str(i.get("resumo") or ""), 200)
            if contem_pii(resumo):
                continue
            linhas.append({
                "cluster_id": cluster_id,
                "member_type": i["tipo"],
                "member_id": i["id"],
                "member_fingerprint": i["assinatura"],
                "tenant_hash": hash_de_tenant(i["tenant"]),
                "summary_redacted": resumo,
                "occurred_at": i.get("quando") or datetime.now(timezone.utc).isoformat(),
            })
        if not linhas:
            return
        try:
            self.db.table("demand_cluster_members").upsert(
                linhas,
                on_conflict="cluster_id,member_type,member_fingerprint,tenant_hash"
            ).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Demand] membros nao gravados: %s", type(exc).__name__)

    # ------------------------------------------------------------------
    # Administracao — §26.5
    # ------------------------------------------------------------------

    def listar(self, *, status: Optional[str] = None, limite: int = 60) -> list[dict]:
        try:
            q = self.db.table("demand_clusters").select("*")
            if status:
                q = q.eq("status", status)
            r = q.order("demand_score", desc=True).limit(limite).execute()
            return r.data or []
        except Exception:  # noqa: BLE001
            return []

    def alterar(self, cluster_id: str, *, status: Optional[str] = None,
                nota: Optional[str] = None, outcome: Optional[str] = None,
                candidato_auxiliar: Optional[str] = None,
                candidato_skill: Optional[str] = None,
                ator: Optional[str] = None) -> bool:
        campos: dict[str, Any] = {}
        if status:
            if status not in ESTADOS or status == "merged":
                return False  # merge tem caminho proprio
            campos["status"] = status
        if nota is not None:
            campos["review_note"] = resumo_seguro(nota, 600)
        if outcome is not None:
            campos["canonical_outcome"] = resumo_seguro(outcome, 300)
        if candidato_auxiliar is not None:
            campos["candidate_auxiliary_key"] = candidato_auxiliar
        if candidato_skill is not None:
            campos["candidate_skill_key"] = candidato_skill
        if ator:
            campos["reviewed_by_user_id"] = ator
        if not campos:
            return False
        try:
            self.db.table("demand_clusters").update(campos).eq("id", cluster_id).execute()
        except Exception as exc:  # noqa: BLE001
            logger.error("[Demand] alteracao falhou: %s", type(exc).__name__)
            return False
        registrar_evento(self.db, company_id=None, tipo="demand.reviewed",
                         subject_type="demand_cluster", subject_id=cluster_id,
                         actor_kind="admin", actor_id=ator,
                         mensagem=f"cluster atualizado: {campos.get('status') or 'revisão'}")
        return True

    def fundir(self, *, origem_id: str, destino_id: str,
               ator: Optional[str] = None) -> bool:
        """Funde dois clusters preservando linhagem — §26.5.

        A origem nao e apagada: vira `merged` apontando para o destino. Apagar
        perderia o historico de que aquilo ja foi pedido de outra forma.
        """
        if origem_id == destino_id:
            return False
        try:
            membros = (self.db.table("demand_cluster_members").select("*")
                       .eq("cluster_id", origem_id).limit(500).execute()).data or []
            for m in membros:
                m.pop("id", None)
                m["cluster_id"] = destino_id
            if membros:
                self.db.table("demand_cluster_members").upsert(
                    membros,
                    on_conflict="cluster_id,member_type,member_fingerprint,tenant_hash"
                ).execute()
            self.db.table("demand_clusters").update({
                "status": "merged", "merged_into_id": destino_id,
                "reviewed_by_user_id": ator,
            }).eq("id", origem_id).execute()
            self._recontar(destino_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("[Demand] fusao falhou: %s", type(exc).__name__)
            return False
        registrar_evento(self.db, company_id=None, tipo="demand.merged",
                         subject_type="demand_cluster", subject_id=destino_id,
                         actor_kind="admin", actor_id=ator,
                         mensagem="dois clusters foram fundidos",
                         detalhe={"origem": origem_id, "destino": destino_id})
        return True

    def _recontar(self, cluster_id: str) -> None:
        try:
            membros = (self.db.table("demand_cluster_members")
                       .select("tenant_hash").eq("cluster_id", cluster_id)
                       .limit(1000).execute()).data or []
            tenants = {m["tenant_hash"] for m in membros}
            scores = calcular_score(tenant_count=len(tenants),
                                    request_count=len(membros))
            self.db.table("demand_clusters").update({
                "tenant_count": len(tenants), "request_count": len(membros), **scores,
            }).eq("id", cluster_id).execute()
        except Exception:  # noqa: BLE001
            pass
