"""Motor de regras. SPEC-059 §10.11 e §26.6.

O detector e codigo; a REGRA e dado. Essa separacao e o que permite pausar um
detector barulhento, mudar um limiar ou fazer rollback sem deploy — que e
exatamente o que §26.6 pede do Admin.

O motor tambem e quem respeita o `cooldown_seconds` da regra. Sem isso, um
tick a cada 5 minutos rodaria o detector de qualidade 288 vezes por dia para
comparar as mesmas duas medias.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from .detectors import ContextoDeDeteccao, resolver
from .signal_service import SignalService, registrar_evento

logger = logging.getLogger(__name__)


@dataclass
class ResultadoDaRegra:
    rule_key: str
    executou: bool
    sinais_criados: int = 0
    motivo: str = ""
    erro: Optional[str] = None


@dataclass
class ResultadoDaVarredura:
    company_id: str
    regras: list[ResultadoDaRegra] = field(default_factory=list)

    @property
    def sinais(self) -> int:
        return sum(r.sinais_criados for r in self.regras)

    @property
    def executadas(self) -> int:
        return sum(1 for r in self.regras if r.executou)

    def resumo(self) -> str:
        return (f"{self.executadas} regra(s) executada(s), "
                f"{self.sinais} sinal(is) registrado(s)")


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def deve_rodar(regra: dict, agora: Optional[datetime] = None) -> tuple[bool, str]:
    """Puro: esta regra pode rodar agora?

    A checagem de status vem antes da de cooldown de proposito — uma regra
    pausada nao deve nem consultar quando rodou pela ultima vez, para que
    pausar tenha efeito imediato e obvio.
    """
    agora = agora or _agora()
    if str(regra.get("status")) != "active":
        return False, f"regra {regra.get('status')}"
    ultimo = regra.get("last_run_at")
    if not ultimo:
        return True, "nunca executada"
    try:
        d = datetime.fromisoformat(str(ultimo).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
    except Exception:  # noqa: BLE001
        return True, "última execução ilegível"
    intervalo = int(regra.get("cooldown_seconds") or 86400)
    if (agora - d) < timedelta(seconds=intervalo):
        return False, "dentro do intervalo entre execuções"
    return True, "intervalo vencido"


class RuleEngine:
    def __init__(self, supabase_client: Any):
        self.db = getattr(supabase_client, "client", supabase_client)
        self.sinais = SignalService(supabase_client)

    def regras_ativas(self, *, escopo: str = "tenant") -> list[dict]:
        try:
            r = (self.db.table("intelligence_rules")
                 .select("*").eq("status", "active").eq("scope", escopo)
                 .limit(100).execute())
            return r.data or []
        except Exception as exc:  # noqa: BLE001
            logger.error("[RuleEngine] leitura de regras falhou: %s", type(exc).__name__)
            return []

    def varrer_empresa(self, company_id: str, *,
                       agora: Optional[datetime] = None,
                       apenas: Optional[list[str]] = None) -> ResultadoDaVarredura:
        """Roda os detectores elegiveis para uma corretora."""
        agora = agora or _agora()
        resultado = ResultadoDaVarredura(company_id=company_id)

        for regra in self.regras_ativas():
            chave = regra.get("rule_key")
            if apenas and chave not in apenas:
                continue

            pode, motivo = deve_rodar(regra, agora)
            if not pode and not apenas:
                # `apenas` e o replay manual do Admin (§26.6): ele ignora o
                # intervalo de proposito, porque quem pediu o replay quer o
                # resultado agora.
                resultado.regras.append(ResultadoDaRegra(chave, False, motivo=motivo))
                continue

            detector = resolver(chave)
            if detector is None:
                resultado.regras.append(ResultadoDaRegra(
                    chave, False, motivo="sem detector registrado para esta chave"))
                continue

            ctx = ContextoDeDeteccao(
                company_id=company_id, db=self.db, agora=agora,
                config=regra.get("configuration") or {},
                rule_key=chave, rule_version=str(regra.get("version") or "1.0.0"))

            try:
                rascunhos = detector(ctx) or []
            except Exception as exc:  # noqa: BLE001
                # Um detector quebrado nao pode parar os outros. Cada um e
                # uma leitura independente do mesmo banco.
                logger.exception("[RuleEngine] detector '%s' falhou", chave)
                resultado.regras.append(ResultadoDaRegra(
                    chave, False, motivo="erro no detector", erro=type(exc).__name__))
                continue

            criados = 0
            minimo_conf = float(regra.get("minimum_confidence") or 0)
            minimo_evid = int(regra.get("minimum_evidence") or 1)
            for rascunho in rascunhos:
                if float(rascunho.confidence) < minimo_conf:
                    continue
                if len(rascunho.evidencias) < minimo_evid:
                    continue
                if self.sinais.registrar(rascunho):
                    criados += 1

            self._marcar_execucao(regra.get("id"), criados, agora)
            resultado.regras.append(ResultadoDaRegra(chave, True, criados,
                                                     motivo=motivo))

        return resultado

    def _marcar_execucao(self, rule_id: Optional[str], criados: int,
                         agora: datetime) -> None:
        if not rule_id:
            return
        try:
            self.db.table("intelligence_rules").update({
                "last_run_at": agora.isoformat(),
                "last_run_signals": criados,
            }).eq("id", rule_id).execute()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[RuleEngine] marcacao de execucao falhou: %s",
                           type(exc).__name__)

    # ------------------------------------------------------------------
    # Administracao — §26.6
    # ------------------------------------------------------------------

    def alterar_status(self, rule_key: str, status: str, *,
                       ator: Optional[str] = None) -> bool:
        if status not in ("draft", "active", "paused", "retired"):
            return False
        try:
            self.db.table("intelligence_rules").update({"status": status}) \
                .eq("rule_key", rule_key).execute()
        except Exception as exc:  # noqa: BLE001
            logger.error("[RuleEngine] alteracao de status falhou: %s", type(exc).__name__)
            return False
        registrar_evento(self.db, company_id=None, tipo="rule.status_changed",
                         subject_type="rule", mensagem=f"regra {rule_key} → {status}",
                         detalhe={"rule_key": rule_key, "status": status},
                         actor_kind="admin", actor_id=ator)
        return True

    def alterar_configuracao(self, rule_key: str, configuracao: dict, *,
                             ator: Optional[str] = None) -> bool:
        """Muda limiar e cria versao nova. §10.11 exige regra versionada.

        Sobrescrever a configuracao sem trocar a versao faria os sinais
        antigos e os novos compartilharem `dedupe_key` — e o efeito da
        calibragem ficaria invisivel, porque o sinal novo cairia como
        repeticao do velho.
        """
        try:
            atual = (self.db.table("intelligence_rules")
                     .select("id, version").eq("rule_key", rule_key)
                     .maybe_single().execute()).data
            if not atual:
                return False
            partes = str(atual.get("version") or "1.0.0").split(".")
            partes[-1] = str(int(partes[-1]) + 1) if partes[-1].isdigit() else "1"
            nova = ".".join(partes)
            self.db.table("intelligence_rules").update({
                "configuration": configuracao or {}, "version": nova,
            }).eq("id", atual["id"]).execute()
        except Exception as exc:  # noqa: BLE001
            logger.error("[RuleEngine] alteracao de configuracao falhou: %s",
                         type(exc).__name__)
            return False
        registrar_evento(self.db, company_id=None, tipo="rule.reconfigured",
                         subject_type="rule",
                         mensagem=f"regra {rule_key} reconfigurada (versão {nova})",
                         detalhe={"rule_key": rule_key, "version": nova},
                         actor_kind="admin", actor_id=ator)
        return True

    def qualidade_por_regra(self, *, dias: int = 30) -> list[dict]:
        """O que cada regra produziu, e o que o corretor achou disso.

        Duas métricas diferentes, e a distinção é o ponto:

        * **taxa de rejeição** — quanto do que a regra produz é suprimido ou
          invalidado. Diz que a regra fala demais.
        * **"o número está errado"** — quantas corretoras DISTINTAS disseram
          que o dado desta regra está errado. Diz que o limiar, a fonte ou a
          conta estão errados. É informação sobre o DETECTOR, não sobre o
          silêncio, e por isso não pode ser tratada como preferência.

        Não é precisão estatística. Chamar de "precisão" seria exatamente o
        tipo de número que a SPEC-059 proíbe — por isso os campos se chamam
        `taxa_rejeicao` e `dado_errado_tenants`.

        **Nada é ajustado automaticamente.** A contagem sobe para a tela e
        um humano decide. Detector que se recalibra sozinho a partir de
        reclamação é como se perde a confiança de vez: ninguém consegue
        explicar depois por que o limiar virou o que virou.
        """
        desde = (_agora() - timedelta(days=dias)).isoformat()
        try:
            sinais = (self.db.table("intelligence_signals")
                      .select("rule_key, status, id")
                      .gte("created_at", desde).limit(4000).execute()).data or []
        except Exception:  # noqa: BLE001
            return []

        por_regra: dict[str, dict] = {}
        for s in sinais:
            chave = s.get("rule_key") or "sem_regra"
            g = por_regra.setdefault(chave, {
                "rule_key": chave, "sinais": 0, "suprimidos": 0,
                "invalidados": 0, "dado_errado": 0, "dado_errado_tenants": 0,
                "nao_relevante": 0})
            g["sinais"] += 1
            if s.get("status") == "suppressed":
                g["suprimidos"] += 1
            if s.get("status") == "invalidated":
                g["invalidados"] += 1

        self._contar_feedback_por_regra(por_regra, desde)

        for g in por_regra.values():
            total = max(1, g["sinais"])
            g["taxa_rejeicao"] = round(
                100.0 * (g["suprimidos"] + g["invalidados"]) / total, 1)
            # A revisão é pedida por CORRETORAS DISTINTAS, não por ocorrências.
            # Uma corretora que clica cinco vezes no mesmo item é uma opinião;
            # três corretoras diferentes dizendo o mesmo é um defeito.
            g["revisar_limiar"] = g["dado_errado_tenants"] >= 3
            g["motivo_revisao"] = (
                f"{g['dado_errado_tenants']} corretoras distintas disseram que o "
                f"número desta regra está errado — o limiar ou a fonte merecem revisão"
                if g["revisar_limiar"] else None)

        return sorted(por_regra.values(), key=lambda x: -x["sinais"])

    def _contar_feedback_por_regra(self, por_regra: dict[str, dict],
                                   desde: str) -> None:
        """Liga a resposta do corretor de volta à REGRA que gerou o item.

        O caminho é `resposta → recomendação → finding → sinal → regra`. Ele é
        percorrido aqui, e não numa view, porque cada elo pode estar ausente
        (uma recomendação sem finding, um finding sem sinal) e uma junção
        ingênua simplesmente perderia esses casos em silêncio.
        """
        try:
            respostas = (self.db.table("recommendation_responses")
                         .select("recommendation_id, action, company_id")
                         .in_("action", ["wrong_data", "not_relevant"])
                         .gte("created_at", desde).limit(2000).execute()).data or []
            if not respostas:
                return

            rec_ids = list({str(r["recommendation_id"]) for r in respostas})
            recs = (self.db.table("recommendations").select("id, finding_id")
                    .in_("id", rec_ids).limit(2000).execute()).data or []
            finding_por_rec = {str(r["id"]): str(r.get("finding_id") or "")
                               for r in recs}

            finding_ids = [f for f in set(finding_por_rec.values()) if f]
            if not finding_ids:
                return
            vinculos = (self.db.table("intelligence_finding_signals")
                        .select("finding_id, signal_id, role")
                        .in_("finding_id", finding_ids).limit(4000).execute()).data or []
            signal_ids = list({str(v["signal_id"]) for v in vinculos})
            if not signal_ids:
                return
            sinais = (self.db.table("intelligence_signals")
                      .select("id, rule_key").in_("id", signal_ids)
                      .limit(4000).execute()).data or []
            regra_por_sinal = {str(s["id"]): s.get("rule_key") for s in sinais}

            regras_por_finding: dict[str, set] = {}
            for v in vinculos:
                chave = regra_por_sinal.get(str(v["signal_id"]))
                if chave:
                    regras_por_finding.setdefault(str(v["finding_id"]), set()).add(chave)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[RuleEngine] feedback por regra: %s", type(exc).__name__)
            return

        tenants_por_regra: dict[str, set] = {}
        for r in respostas:
            finding = finding_por_rec.get(str(r["recommendation_id"]))
            if not finding:
                continue
            for chave in regras_por_finding.get(finding, ()):
                g = por_regra.setdefault(chave, {
                    "rule_key": chave, "sinais": 0, "suprimidos": 0,
                    "invalidados": 0, "dado_errado": 0,
                    "dado_errado_tenants": 0, "nao_relevante": 0})
                if r["action"] == "wrong_data":
                    g["dado_errado"] += 1
                    tenants_por_regra.setdefault(chave, set()).add(str(r.get("company_id")))
                else:
                    g["nao_relevante"] += 1

        for chave, tenants in tenants_por_regra.items():
            por_regra[chave]["dado_errado_tenants"] = len(tenants)
