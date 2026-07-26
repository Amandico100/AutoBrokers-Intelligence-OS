"""Registro de fontes, snapshots e cache. SPEC-060 §10.3, §10.4, §24.

A fonte é global; a pesquisa é privada
--------------------------------------
`research_sources` não tem `company_id`. A identidade de
`planalto.gov.br/lei-x` é a mesma para todas as corretoras — inventar uma
cópia por tenant multiplicaria a mesma página por mil e destruiria o dedupe.

O que é privado é a PESQUISA que consultou a fonte, e isso vive no snapshot
(`company_id`) e no claim. O CHECK `research_snapshots_publico_e_anonimo_ck`
garante que um snapshot sem tenant nunca carregue contexto privado — é ele
que torna o cache compartilhável sem virar vazamento (§24.2).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from .content_sanitizer import ConteudoSaneado
from .schemas import ResultadoDeFonte, chave
from .source_policy import cache_permitido, classificar, politica_para
from .urls import dominio, fingerprint, normalizar

logger = logging.getLogger(__name__)

RETENCAO_PADRAO = "short"
EXCERTO_MAXIMO = 1_200


def _agora() -> datetime:
    return datetime.now(timezone.utc)


class SourceRegistry:
    def __init__(self, supabase_client: Any):
        self.db = getattr(supabase_client, "client", supabase_client)

    # ------------------------------------------------------------------
    # Fontes
    # ------------------------------------------------------------------

    def registrar_fonte(self, url: str, *, titulo: Optional[str] = None,
                        publisher: Optional[str] = None,
                        idioma: Optional[str] = None,
                        tipo: str = "web_page") -> Optional[dict]:
        """Cria ou atualiza a identidade da fonte. Idempotente por fingerprint."""
        canonica = normalizar(url)
        if not canonica:
            return None

        fp = fingerprint(canonica)
        tier, oficial = classificar(canonica, titulo=titulo or "")
        politica = politica_para(canonica)

        try:
            existente = (self.db.table("research_sources")
                         .select("id, trust_tier, official, title")
                         .eq("url_fingerprint", fp).maybe_single().execute()).data
        except Exception:  # noqa: BLE001
            existente = None

        if existente:
            try:
                self.db.table("research_sources").update({
                    "last_seen_at": _agora().isoformat(),
                    "title": titulo or existente.get("title"),
                }).eq("id", existente["id"]).execute()
            except Exception:  # noqa: BLE001
                pass
            return {**existente, "canonical_url": canonica}

        linha = {
            "canonical_url": canonica, "url_fingerprint": fp,
            "normalized_domain": dominio(canonica), "source_type": tipo,
            "publisher": publisher or (politica.name if politica else None),
            "title": (titulo or "")[:400] or None,
            "country": politica.country if politica else "BR",
            "language": idioma or (politica.language if politica else None),
            "trust_tier": tier, "official": oficial,
            "metadata": {"policy_key": politica.policy_key} if politica else {},
        }
        try:
            r = self.db.table("research_sources").insert(linha).execute()
            return (r.data or [{}])[0]
        except Exception as exc:  # noqa: BLE001
            if "duplicate" in str(exc).lower() or "unique" in str(exc).lower():
                try:
                    r = (self.db.table("research_sources").select("*")
                         .eq("url_fingerprint", fp).maybe_single().execute())
                    return r.data
                except Exception:  # noqa: BLE001
                    return None
            logger.error("[SourceRegistry] fonte nao registrada: %s", type(exc).__name__)
            return None

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    def gravar_snapshot(self, *, fonte: ResultadoDeFonte,
                        saneado: ConteudoSaneado,
                        company_id: Optional[str] = None,
                        research_request_id: Optional[str] = None,
                        work_run_id: Optional[str] = None,
                        compartilhavel: bool = True) -> Optional[dict]:
        """Grava o estado da fonte agora, com hash e classificação de injeção.

        `compartilhavel=True` grava SEM tenant quando o conteúdo é público e
        não carrega contexto privado — é o que permite outra corretora
        reaproveitar a leitura do mesmo PDF da SUSEP sem pagá-la de novo. A
        decisão é conservadora: qualquer sinal de privado força o tenant.
        """
        registro = self.registrar_fonte(fonte.url, titulo=fonte.titulo,
                                        idioma=fonte.idioma)
        if not registro or not registro.get("id"):
            return None

        # §24.2: o que pode ser compartilhado é o conteúdo público. A pergunta
        # do usuário e a estratégia nunca entram no snapshot — e por isso o
        # `contains_private_context` só é verdadeiro quando alguém marca.
        privado = not compartilhavel
        politica = politica_para(fonte.url)

        linha = {
            "company_id": company_id if privado else None,
            "research_source_id": registro["id"],
            "work_run_id": work_run_id,
            "research_request_id": research_request_id,
            "provider_key": fonte.provider,
            "retrieved_at": _agora().isoformat(),
            "published_at": fonte.publicado_em,
            "http_status": fonte.http_status,
            "content_type": (fonte.metadata or {}).get("content_type"),
            "content_hash": saneado.content_hash(),
            "structure_hash": chave(len(saneado.texto), saneado.trechos_ocultos),
            "excerpt_redacted": _excerto(saneado.texto),
            "word_count": len(saneado.texto.split()),
            "retention_class": (politica.retention_class if politica
                                else RETENCAO_PADRAO),
            "valid_until": (_agora() + timedelta(
                seconds=cache_permitido(fonte.url))).isoformat(),
            "prompt_injection_status": saneado.status,
            "injection_score": round(saneado.injection_score, 3),
            "contains_private_context": privado,
            "metadata": saneado.como_metadata(),
        }
        try:
            r = self.db.table("research_source_snapshots").insert(linha).execute()
            snap = (r.data or [{}])[0]
            snap["_tier"] = registro.get("trust_tier", fonte.tier)
            snap["_oficial"] = registro.get("official", fonte.oficial)
            snap["_url"] = registro.get("canonical_url") or fonte.url
            snap["_titulo"] = fonte.titulo
            return snap
        except Exception as exc:  # noqa: BLE001
            logger.error("[SourceRegistry] snapshot nao gravado: %s", type(exc).__name__)
            return None

    def ultimo_snapshot(self, url: str, *,
                        company_id: Optional[str] = None) -> Optional[dict]:
        """O snapshot mais recente desta fonte. Base do diff dos monitores."""
        fp = fingerprint(url)
        try:
            fonte = (self.db.table("research_sources").select("id")
                     .eq("url_fingerprint", fp).maybe_single().execute()).data
            if not fonte:
                return None
            q = (self.db.table("research_source_snapshots")
                 .select("*").eq("research_source_id", fonte["id"]))
            if company_id:
                q = q.or_(f"company_id.eq.{company_id},company_id.is.null")
            r = q.order("retrieved_at", desc=True).limit(1).execute()
            return (r.data or [None])[0]
        except Exception:  # noqa: BLE001
            return None

    # ------------------------------------------------------------------
    # Cache — §24
    # ------------------------------------------------------------------

    def buscar_cache(self, cache_key: str, *,
                     company_id: Optional[str] = None) -> Optional[dict]:
        """Cache válido, ou `None`. Público primeiro; tenant depois.

        Público primeiro porque é o que faz a segunda corretora não pagar a
        leitura que a primeira já fez. O tenant só é consultado para o que é
        realmente privado — síntese, plano, seleção.
        """
        agora = _agora().isoformat()
        try:
            r = (self.db.table("research_cache_entries").select("*")
                 .eq("scope", "public").eq("cache_key", cache_key)
                 .gt("fresh_until", agora).limit(1).execute())
            if r.data:
                self._marcar_hit(r.data[0]["id"], r.data[0].get("hit_count") or 0)
                return r.data[0]
        except Exception:  # noqa: BLE001
            pass

        if not company_id:
            return None
        try:
            r = (self.db.table("research_cache_entries").select("*")
                 .eq("scope", "tenant").eq("company_id", company_id)
                 .eq("cache_key", cache_key).gt("fresh_until", agora)
                 .limit(1).execute())
            if r.data:
                self._marcar_hit(r.data[0]["id"], r.data[0].get("hit_count") or 0)
                return r.data[0]
        except Exception:  # noqa: BLE001
            pass
        return None

    def _marcar_hit(self, cache_id: str, atual: int) -> None:
        try:
            self.db.table("research_cache_entries").update({
                "hit_count": int(atual) + 1,
                "last_hit_at": _agora().isoformat(),
            }).eq("id", cache_id).execute()
        except Exception:  # noqa: BLE001
            pass

    def gravar_cache(self, cache_key: str, *, payload: dict,
                     segundos: int = 21_600, company_id: Optional[str] = None,
                     snapshot_id: Optional[str] = None,
                     publico: bool = True) -> None:
        """Grava no cache. Público exige ausência de tenant — o banco cobra."""
        escopo = "public" if publico else "tenant"
        if escopo == "tenant" and not company_id:
            return  # cache de tenant sem tenant não existe
        linha = {
            "scope": escopo,
            "company_id": None if publico else company_id,
            "cache_key": cache_key,
            "source_snapshot_id": snapshot_id,
            "result_payload": payload,
            "content_hash": chave(payload),
            "fresh_until": (_agora() + timedelta(seconds=max(60, segundos))).isoformat(),
            "stale_until": (_agora() + timedelta(seconds=max(60, segundos) * 3)).isoformat(),
            "policy_class": "standard",
        }
        try:
            self.db.table("research_cache_entries").upsert(
                linha, on_conflict="scope,company_id,cache_key").execute()
        except Exception as exc:  # noqa: BLE001
            # Cache que falha não pode derrubar a pesquisa. O pior efeito é
            # pagar o provider de novo.
            logger.debug("[SourceRegistry] cache nao gravado: %s", type(exc).__name__)

    # ------------------------------------------------------------------
    # Catálogo de políticas
    # ------------------------------------------------------------------

    def semear_politicas(self) -> int:
        """Publica o catálogo inicial de §18.1. Idempotente por `policy_key`."""
        from .source_policy import todas_as_politicas

        inseridas = 0
        for p in todas_as_politicas():
            try:
                existe = (self.db.table("research_source_policies").select("id")
                          .eq("policy_key", p.policy_key).maybe_single().execute()).data
                if existe:
                    continue
                self.db.table("research_source_policies").insert(
                    p.como_linha()).execute()
                inseridas += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("[SourceRegistry] politica %s: %s",
                               p.policy_key, type(exc).__name__)
        return inseridas

    def listar_politicas(self, *, limite: int = 200) -> list[dict]:
        try:
            r = (self.db.table("research_source_policies")
                 .select("id, policy_key, domain_pattern, name, trust_tier, "
                         "category, official, status, retention_class, "
                         "cache_seconds, terms_reviewed_at, notes")
                 .order("trust_tier").limit(limite).execute())
            return r.data or []
        except Exception:  # noqa: BLE001
            return []

    def fontes_recentes(self, *, limite: int = 100) -> list[dict]:
        try:
            r = (self.db.table("research_sources")
                 .select("id, canonical_url, normalized_domain, publisher, "
                         "title, trust_tier, official, status, last_seen_at")
                 .order("last_seen_at", desc=True).limit(limite).execute())
            return r.data or []
        except Exception:  # noqa: BLE001
            return []


def _excerto(texto: str) -> str:
    """Trecho curto para o Admin conferir sem abrir o storage.

    §34.4: não republicar conteúdo integral. O excerto existe para provar que
    a leitura aconteceu e mostrar do que se trata — não para substituir a
    fonte.
    """
    limpo = " ".join((texto or "").split())
    if len(limpo) <= EXCERTO_MAXIMO:
        return limpo
    return limpo[:EXCERTO_MAXIMO - 1].rstrip() + "…"
