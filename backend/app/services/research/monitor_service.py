"""Monitores e detecção de mudança. SPEC-060 §22.

O problema real de um monitor não é detectar mudança — é **não avisar sobre
mudança que não importa**. Toda página muda todo dia: banner de cookie,
ordem dos cards, timestamp de rodapé, contador de visitas. Um monitor ingênuo
dispara sempre, e na segunda semana o corretor desliga — perdendo junto a
mudança que importava.

Por isso a detecção é em camadas (§22.2) e o ruído é suprimido **antes** de
qualquer score (§22.3). E por isso o CHECK
`research_observations_signal_exige_relevancia_ck` existe no banco: mudança
cosmética não vira Signal nem por engano de código.

Nenhum agendador novo
---------------------
Monitor ativo exige `routine_id` — o banco recusa o contrário. Quem dispara é
a Rotina da SPEC-019/055, que já tem claim atômico, e a execução é um Work Run.
"""

from __future__ import annotations

import difflib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# §22.3 — o que nunca conta como mudança de conteúdo. Cada linha aqui é uma
# fonte de falso positivo que já derrubou a confiança de algum monitor.
PADROES_DE_RUIDO: tuple[re.Pattern, ...] = (
    re.compile(r"\b\d{1,2}[/:]\d{2}(:\d{2})?\b"),          # relógio
    re.compile(r"\b\d{1,2}\s+de\s+\w+\s+de\s+\d{4}\b", re.I),  # data por extenso
    re.compile(r"\b(hoje|ontem|agora|há \d+ (minutos?|horas?|dias?))\b", re.I),
    re.compile(r"\b\d+\s*(visualiza|acesso|visita|compartilhament)\w*", re.I),
    re.compile(r"(aceit\w+ cookies?|pol[íi]tica de privacidade|lgpd)", re.I),
    re.compile(r"(copyright|todos os direitos reservados)\s*©?\s*\d{4}", re.I),
    re.compile(r"\b(carregando|loading)\b\W*", re.I),
    re.compile(r"csrf[-_]?token\W*[\w-]+", re.I),
)

# Palavras que marcam mudança que IMPORTA num contexto de seguros.
TERMOS_RELEVANTES = (
    "cobertura", "exclusão", "exclusao", "carência", "carencia", "franquia",
    "vigência", "vigencia", "prazo", "resolução", "resolucao", "circular",
    "portaria", "revoga", "altera", "passa a valer", "entra em vigor",
    "suspende", "cancelamento", "reajuste", "condições gerais",
    "condicoes gerais", "assistência", "assistencia", "telefone", "0800",
    "sinistro", "aviso de sinistro", "produto", "novo produto",
)

LIMIAR_RELEVANTE = 50.0
LIMIAR_MAIOR = 75.0


def limpar_ruido(texto: str) -> str:
    """Remove o que muda sozinho. Puro — §22.3."""
    limpo = texto or ""
    for padrao in PADROES_DE_RUIDO:
        limpo = padrao.sub(" ", limpo)
    return " ".join(limpo.split()).lower()


@dataclass
class Mudanca:
    """O que mudou, e o quanto isso importa — §22.4."""

    change_class: str = "none"
    significance_score: float = 0.0
    resumo: str = ""
    trechos_novos: list[str] = field(default_factory=list)
    trechos_removidos: list[str] = field(default_factory=list)
    proporcao_alterada: float = 0.0
    termos_relevantes: list[str] = field(default_factory=list)

    @property
    def vira_signal(self) -> bool:
        """§28.2 — só mudança relevante. O banco também recusa o resto."""
        return (self.change_class in ("relevant", "major")
                and self.significance_score >= LIMIAR_RELEVANTE)


def comparar(anterior: str, atual: str, *,
             termos_de_interesse: Optional[list[str]] = None) -> Mudanca:
    """Diff com supressão de ruído e score de relevância. Puro — §22.2.

    A ordem é a defesa: limpar o ruído ANTES de comparar. Se o diff rodasse no
    texto bruto, ele acusaria mudança em toda página com relógio no rodapé — e
    o score depois teria de adivinhar o que era real.
    """
    a = limpar_ruido(anterior)
    b = limpar_ruido(atual)

    if not b:
        return Mudanca("unreachable", 0.0,
                       "A fonte não devolveu conteúdo nesta verificação.")
    if a == b:
        return Mudanca("none", 0.0, "Nada mudou desde a última verificação.")
    if not a:
        return Mudanca("relevant", 60.0,
                       "Primeira leitura desta fonte — não há base de comparação.")

    palavras_a = a.split()
    palavras_b = b.split()
    matcher = difflib.SequenceMatcher(None, palavras_a, palavras_b, autojunk=False)
    razao = matcher.ratio()
    proporcao = round(1.0 - razao, 4)

    novos: list[str] = []
    removidos: list[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("insert", "replace") and (j2 - j1) >= 4:
            novos.append(" ".join(palavras_b[j1:j2])[:300])
        if tag in ("delete", "replace") and (i2 - i1) >= 4:
            removidos.append(" ".join(palavras_a[i1:i2])[:300])

    alterado = " ".join(novos + removidos)
    interesse = [t for t in (termos_de_interesse or TERMOS_RELEVANTES)
                 if t in alterado]

    # O score pesa CONTEÚDO acima de tamanho: uma linha alterada que fala de
    # vigência importa mais que três parágrafos de texto institucional.
    score = 0.0
    score += min(40.0, proporcao * 200.0)
    score += min(45.0, 15.0 * len(interesse))
    if len(novos) >= 3:
        score += 10.0
    score = round(min(100.0, score), 2)

    if proporcao < 0.005 and not interesse:
        classe = "cosmetic"
        score = min(score, 15.0)
    elif score >= LIMIAR_MAIOR:
        classe = "major"
    elif score >= LIMIAR_RELEVANTE:
        classe = "relevant"
    elif score >= 20:
        classe = "minor"
    else:
        classe = "cosmetic"

    if interesse:
        resumo = ("A página mudou em trecho que menciona "
                  + ", ".join(sorted(set(interesse))[:4]) + ".")
    elif classe == "cosmetic":
        resumo = "Mudança pequena, sem efeito no conteúdo relevante."
    else:
        resumo = f"A página mudou em cerca de {proporcao * 100:.0f}% do texto."

    return Mudanca(classe, score, resumo, novos[:5], removidos[:5],
                   proporcao, sorted(set(interesse)))


# ---------------------------------------------------------------------------
# Serviço
# ---------------------------------------------------------------------------


def _agora() -> datetime:
    return datetime.now(timezone.utc)


class MonitorService:
    def __init__(self, supabase_client: Any):
        self.raw = supabase_client
        self.db = getattr(supabase_client, "client", supabase_client)

    # ------------------------------------------------------------------

    def criar(self, *, company_id: str, nome: str, urls: list[str],
              tipo: str = "url", topico: Optional[str] = None,
              cadencia: str = "daily", user_id: Optional[str] = None,
              canais: Optional[list[str]] = None,
              termos: Optional[list[str]] = None) -> dict:
        """Cria o monitor E a Rotina que o dispara.

        A Rotina vem primeiro de propósito: o CHECK do banco recusa monitor
        ativo sem `routine_id`, e essa ordem garante que nunca exista monitor
        "ligado" que ninguém dispara — que é a falha silenciosa clássica de
        sistema de monitoramento.
        """
        from .urls import normalizar

        alvos = [u for u in (normalizar(x) for x in (urls or [])) if u]
        if not alvos and tipo == "url":
            return {"ok": False, "erro": "nenhum endereço válido para monitorar"}

        rotina_id = self._criar_rotina(company_id, nome, cadencia, user_id)
        if not rotina_id:
            return {"ok": False,
                    "erro": "não consegui criar a rotina que dispara o monitor"}

        linha = {
            "company_id": company_id, "user_id": user_id, "name": nome[:200],
            "monitor_type": tipo, "topic": topico,
            "url_filters": alvos,
            "query_spec": {"termos": termos or [], "topico": topico},
            "cadence": cadencia,
            "schedule_spec": {"time": "07:00"} if cadencia != "hourly" else {"minutos": 60},
            "change_policy": {"limiar": LIMIAR_RELEVANTE,
                              "suprimir_cosmetico": True},
            "severity_policy": {"relevant": "medium", "major": "high"},
            "channels": canais or ["dashboard"],
            "is_active": True, "routine_id": rotina_id,
        }
        try:
            r = self.db.table("research_monitors").insert(linha).execute()
            return {"ok": True, "monitor": (r.data or [{}])[0]}
        except Exception as exc:  # noqa: BLE001
            logger.error("[Monitor] criacao falhou: %s", type(exc).__name__)
            return {"ok": False, "erro": "não consegui criar o monitor"}

    def _criar_rotina(self, company_id: str, nome: str, cadencia: str,
                      user_id: Optional[str]) -> Optional[str]:
        """Usa o motor de Rotinas que já existe — nenhum agendador novo."""
        from ..routine_engine import compute_next_run

        agenda = ({"kind": "interval", "minutes": 60} if cadencia == "hourly"
                  else {"kind": "daily", "time": "07:00"}
                  if cadencia == "daily"
                  else {"kind": "daily", "time": "07:00", "weekdays": [0]})
        try:
            proximo = compute_next_run(agenda, "America/Sao_Paulo")
            r = self.db.table("routines").insert({
                "company_id": company_id,
                "name": f"Monitor · {nome}"[:200],
                "instructions": ("Verificar as fontes deste monitor e registrar "
                                 "mudanças relevantes."),
                "schedule": agenda,
                "delivery": {"channel": "none"},
                "timezone": "America/Sao_Paulo",
                "is_active": True,
                "next_run_at": proximo.isoformat(),
                "created_by": user_id,
            }).execute()
            return (r.data or [{}])[0].get("id")
        except Exception as exc:  # noqa: BLE001
            logger.error("[Monitor] rotina nao criada: %s", type(exc).__name__)
            return None

    # ------------------------------------------------------------------

    async def executar(self, monitor_id: str, *,
                       work_run_id: Optional[str] = None) -> dict:
        """Roda uma verificação. Chamado pelo Work Run da Rotina."""
        from .provider_router import ProviderRouter
        from .source_registry import SourceRegistry
        from .urls import fingerprint

        monitor = self._carregar(monitor_id)
        if not monitor:
            return {"ok": False, "erro": "monitor não encontrado"}
        if not monitor.get("is_active"):
            return {"ok": True, "pulado": "monitor pausado"}

        company_id = str(monitor["company_id"])
        registry = SourceRegistry(self.raw)
        router = ProviderRouter(self.raw, company_id=company_id,
                                work_run_id=work_run_id)
        termos = (monitor.get("query_spec") or {}).get("termos") or None

        observacoes: list[dict] = []
        falhas = 0

        for url in (monitor.get("url_filters") or [])[:10]:
            anterior = registry.ultimo_snapshot(url, company_id=company_id)
            aquisicao = await router.ler(url)

            if not (aquisicao.ok and aquisicao.fonte and aquisicao.saneado):
                falhas += 1
                # §22.6 — NUNCA afirmar "sem mudança" quando a fonte não foi
                # acessada. É a diferença entre "está tudo igual" e "não sei".
                observacoes.append(self._gravar_observacao(
                    company_id, monitor_id, work_run_id, None,
                    Mudanca("unreachable", 0.0,
                            aquisicao.limitacao or "fonte inacessível nesta verificação"),
                    conteudo_hash=""))
                continue

            snapshot = registry.gravar_snapshot(
                fonte=aquisicao.fonte, saneado=aquisicao.saneado,
                company_id=company_id, work_run_id=work_run_id,
                compartilhavel=True)

            texto_anterior = ""
            if anterior:
                texto_anterior = str(anterior.get("excerpt_redacted") or "")
            mudanca = comparar(texto_anterior, aquisicao.saneado.texto,
                               termos_de_interesse=termos)

            observacoes.append(self._gravar_observacao(
                company_id, monitor_id, work_run_id,
                (snapshot or {}).get("id"), mudanca,
                conteudo_hash=aquisicao.saneado.content_hash(),
                hash_anterior=(anterior or {}).get("content_hash")))

        relevantes = [o for o in observacoes
                      if o.get("change_class") in ("relevant", "major")]
        self._atualizar_saude(monitor_id, falhas=falhas,
                              total=len(observacoes),
                              houve_mudanca=bool(relevantes))

        return {"ok": True, "verificadas": len(observacoes),
                "relevantes": len(relevantes), "falhas": falhas,
                "observacoes": observacoes}

    def _gravar_observacao(self, company_id: str, monitor_id: str,
                           work_run_id: Optional[str],
                           snapshot_id: Optional[str], mudanca: Mudanca, *,
                           conteudo_hash: str = "",
                           hash_anterior: Optional[str] = None) -> dict:
        linha = {
            "company_id": company_id, "research_monitor_id": monitor_id,
            "work_run_id": work_run_id, "source_snapshot_id": snapshot_id,
            "observation_type": "check",
            "change_class": mudanca.change_class,
            "significance_score": mudanca.significance_score,
            "summary": mudanca.resumo[:1_000],
            "evidence": {"novos": mudanca.trechos_novos,
                         "removidos": mudanca.trechos_removidos,
                         "termos": mudanca.termos_relevantes,
                         "proporcao": mudanca.proporcao_alterada},
            "content_hash": conteudo_hash,
            "previous_content_hash": hash_anterior,
            "status": "recorded",
        }
        try:
            r = self.db.table("research_observations").insert(linha).execute()
            return (r.data or [linha])[0]
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Monitor] observacao nao gravada: %s", type(exc).__name__)
            return linha

    def _atualizar_saude(self, monitor_id: str, *, falhas: int, total: int,
                         houve_mudanca: bool) -> None:
        if total == 0:
            return
        if falhas == 0:
            saude, motivo, consecutivas = "ok", None, 0
        elif falhas >= total:
            saude = "error"
            motivo = "nenhuma fonte deste monitor pôde ser lida"
            consecutivas = None
        else:
            saude = "degraded"
            motivo = f"{falhas} de {total} fontes não puderam ser lidas"
            consecutivas = None

        campos: dict[str, Any] = {
            "last_run_at": _agora().isoformat(),
            "health": saude, "health_reason": motivo,
        }
        if houve_mudanca:
            campos["last_change_at"] = _agora().isoformat()
        if consecutivas == 0:
            campos["consecutive_failures"] = 0
        try:
            if consecutivas is None:
                atual = (self.db.table("research_monitors")
                         .select("consecutive_failures").eq("id", monitor_id)
                         .maybe_single().execute()).data or {}
                campos["consecutive_failures"] = int(
                    atual.get("consecutive_failures") or 0) + 1
            self.db.table("research_monitors").update(campos) \
                .eq("id", monitor_id).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Monitor] saude nao atualizada: %s", type(exc).__name__)

    # ------------------------------------------------------------------

    def _carregar(self, monitor_id: str) -> Optional[dict]:
        try:
            r = (self.db.table("research_monitors").select("*")
                 .eq("id", monitor_id).maybe_single().execute())
            return r.data
        except Exception:  # noqa: BLE001
            return None

    def por_rotina(self, routine_id: str) -> Optional[dict]:
        try:
            r = (self.db.table("research_monitors").select("*")
                 .eq("routine_id", routine_id).maybe_single().execute())
            return r.data
        except Exception:  # noqa: BLE001
            return None

    def listar(self, company_id: str, *, limite: int = 50) -> list[dict]:
        try:
            r = (self.db.table("research_monitors")
                 .select("id, name, monitor_type, topic, cadence, is_active, "
                         "health, health_reason, last_run_at, last_change_at, "
                         "url_filters, channels")
                 .eq("company_id", company_id)
                 .order("created_at", desc=True).limit(limite).execute())
            return r.data or []
        except Exception:  # noqa: BLE001
            return []

    def alterar(self, company_id: str, monitor_id: str, *,
                ativo: Optional[bool] = None, cadencia: Optional[str] = None,
                canais: Optional[list[str]] = None) -> bool:
        campos: dict[str, Any] = {}
        if ativo is not None:
            campos["is_active"] = bool(ativo)
        if cadencia:
            campos["cadence"] = cadencia
        if canais is not None:
            campos["channels"] = canais
        if not campos:
            return False
        try:
            self.db.table("research_monitors").update(campos) \
                .eq("id", monitor_id).eq("company_id", company_id).execute()
            # Pausar o monitor pausa a Rotina: deixar a Rotina rodando faria o
            # Work Run nascer para descobrir que não há nada a fazer.
            if ativo is not None:
                m = self._carregar(monitor_id)
                if m and m.get("routine_id"):
                    self.db.table("routines").update({"is_active": bool(ativo)}) \
                        .eq("id", m["routine_id"]).execute()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("[Monitor] alteracao falhou: %s", type(exc).__name__)
            return False

    def observacoes(self, company_id: str, monitor_id: str, *,
                    limite: int = 30) -> list[dict]:
        try:
            r = (self.db.table("research_observations")
                 .select("id, change_class, significance_score, summary, "
                         "observed_at, status, signal_id, evidence")
                 .eq("company_id", company_id)
                 .eq("research_monitor_id", monitor_id)
                 .order("observed_at", desc=True).limit(limite).execute())
            return r.data or []
        except Exception:  # noqa: BLE001
            return []

    def ruido_por_monitor(self, *, dias: int = 30) -> list[dict]:
        """§31.4 — quanto cada monitor produz de ruído. Para o Admin decidir."""
        desde = (_agora() - timedelta(days=dias)).isoformat()
        try:
            obs = (self.db.table("research_observations")
                   .select("research_monitor_id, change_class")
                   .gte("observed_at", desde).limit(4000).execute()).data or []
        except Exception:  # noqa: BLE001
            return []
        por_monitor: dict[str, dict] = {}
        for o in obs:
            m = str(o.get("research_monitor_id"))
            g = por_monitor.setdefault(m, {"monitor_id": m, "verificacoes": 0,
                                           "cosmeticas": 0, "relevantes": 0,
                                           "inacessiveis": 0})
            g["verificacoes"] += 1
            classe = o.get("change_class")
            if classe in ("cosmetic", "none"):
                g["cosmeticas"] += 1
            elif classe in ("relevant", "major"):
                g["relevantes"] += 1
            elif classe == "unreachable":
                g["inacessiveis"] += 1
        for g in por_monitor.values():
            total = max(1, g["verificacoes"])
            g["taxa_de_silencio"] = round(100.0 * g["cosmeticas"] / total, 1)
        return sorted(por_monitor.values(), key=lambda x: -x["verificacoes"])
