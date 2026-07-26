"""Auxiliar global "Radar de Mercado e Regulação". SPEC-060 §37.

O que ele resolve
-----------------
Regulação de seguro muda sem avisar ninguém. A corretora descobre por um
cliente, por um concorrente ou por um sinistro negado — e nas três formas
descobre tarde. Quem acompanha o Diário Oficial todo dia é uma pessoa que
existe em corretora grande e não existe em corretora de cinco pessoas.

Este Auxiliar é essa pessoa. Instalado, ele:

1. cria monitores nas fontes **oficiais** (SUSEP, CNSP, DOU, Planalto);
2. verifica cada uma na cadência da Rotina;
3. junta o que mudou na semana e entrega uma peça — o Radar Regulatório;
4. avisa pelo Briefing quando algo exige ação.

Por que não é um motor novo
---------------------------
Ele não agenda nada: quem dispara é o **routine_engine**. Não monitora nada:
quem compara é o **MonitorService**. Não compõe peça: quem compõe é o
**Artifact Hub**. Não avisa ninguém: quem entrega é o **Intelligence Fabric**
da SPEC-059. Este arquivo é a *composição* dessas quatro peças em um trabalho
que a corretora reconhece pelo nome — que é exatamente o que a §37 pede de um
Auxiliar.

Sem crédito de provider (D18), a instalação continua funcionando: a leitura
direta não depende de fatura, e o que falhar é declarado com o motivo real.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

SLUG = "radar-mercado-regulacao"

# Fontes que o Radar acompanha por padrão. Somente oficiais: notícia sobre a
# norma não é a norma, e um radar regulatório que dispara por manchete ensina
# a corretora a ignorá-lo em duas semanas.
FONTES_PADRAO: tuple[tuple[str, str, str], ...] = (
    ("SUSEP — normas e circulares", "https://www.gov.br/susep/pt-br/assuntos/legislacao",
     "diaria"),
    ("SUSEP — notícias oficiais", "https://www.gov.br/susep/pt-br/assuntos/noticias",
     "diaria"),
    ("CNSP — resoluções", "https://www.gov.br/susep/pt-br/assuntos/legislacao/resolucoes-cnsp",
     "semanal"),
)

# Termos que fazem uma mudança virar aviso. Sem eles, o monitor avisa sobre
# reorganização de menu — e §18.3 já mostrou o custo disso.
TERMOS_REGULATORIOS = (
    "circular", "resolução", "resolucao", "cnsp", "susep", "deliberação",
    "deliberacao", "vigência", "vigencia", "prazo", "cobertura", "obrigatória",
    "obrigatoria", "revoga", "altera", "consulta pública", "consulta publica",
)

CADENCIA_DO_RADAR = "weekly"


class RadarDeMercado:
    """Instala, executa e reporta o Auxiliar Radar de uma corretora."""

    def __init__(self, supabase_client: Any):
        self.raw = supabase_client
        self.db = getattr(supabase_client, "client", supabase_client)

    # ------------------------------------------------------------------
    # Instalação
    # ------------------------------------------------------------------

    def instalar(self, *, company_id: str, user_id: Optional[str] = None,
                 fontes: Optional[list[dict]] = None) -> dict:
        """Cria os monitores do Radar. Idempotente por corretora.

        Reinstalar não duplica: um Radar instalado duas vezes viraria aviso
        em dobro, e aviso em dobro é o começo do fim da confiança na tela.
        """
        from .monitor_service import MonitorService

        ja = self._monitores_do_radar(company_id)
        if ja:
            return {"ok": True, "ja_instalado": True,
                    "monitores": len(ja),
                    "mensagem": (f"O Radar já está instalado, acompanhando "
                                 f"{len(ja)} fonte(s) oficial(is).")}

        alvos = fontes or [{"nome": n, "url": u, "cadencia": c}
                           for n, u, c in FONTES_PADRAO]
        servico = MonitorService(self.raw)
        criados, falhas = [], []
        for alvo in alvos:
            cadencia = "daily" if alvo.get("cadencia") == "diaria" else "weekly"
            r = servico.criar(
                company_id=company_id,
                nome=f"Radar · {alvo['nome']}"[:180],
                urls=[alvo["url"]],
                topico="regulacao",
                cadencia=cadencia,
                user_id=user_id,
                canais=["dashboard", "briefing"],
                termos=list(TERMOS_REGULATORIOS))
            if r.get("ok"):
                criados.append(r["monitor"])
            else:
                # Falha por fonte é declarada, não engolida: um Radar que
                # instala "com sucesso" acompanhando duas de três fontes mente
                # sobre a própria cobertura.
                falhas.append({"fonte": alvo["nome"], "motivo": r.get("erro")})

        if not criados:
            return {"ok": False,
                    "erro": "não consegui criar nenhum monitor do Radar",
                    "falhas": falhas}

        fechamento = self._criar_rotina_de_fechamento(company_id, user_id)
        if not fechamento:
            # Monitores sem fechamento ainda avisam mudança a mudança. O que
            # se perde é a leitura do conjunto — e dizer isso é melhor que
            # entregar um Radar que promete uma peça semanal que não vem.
            falhas.append({"fonte": "fechamento semanal",
                           "motivo": "não consegui criar a rotina de consolidação"})

        return {"ok": True, "ja_instalado": False,
                "monitores": len(criados), "falhas": falhas,
                "rotina_de_fechamento": fechamento,
                "mensagem": self._mensagem_de_instalacao(len(criados), falhas)}

    def _criar_rotina_de_fechamento(self, company_id: str,
                                    user_id: Optional[str]) -> Optional[str]:
        """A Rotina que consolida a semana.

        Ela declara o workflow em `config.workflow`; a ponte de Rotinas da
        SPEC-055 lê essa declaração. É assim que o Radar entrega uma peça
        semanal sem que exista um agendador de radares em lugar nenhum.
        """
        from ..routine_engine import compute_next_run

        agenda = {"kind": "daily", "time": "07:30", "weekdays": [0]}
        try:
            proximo = compute_next_run(agenda, "America/Sao_Paulo")
            r = self.db.table("routines").insert({
                "company_id": company_id,
                "name": "Radar · fechamento semanal",
                "instructions": ("Consolidar as mudanças da semana nas fontes "
                                 "oficiais e entregar o radar regulatório."),
                "schedule": agenda,
                "delivery": {"channel": "none"},
                "timezone": "America/Sao_Paulo",
                "config": {"workflow": "research.radar_weekly",
                           "params": {"dias": 7},
                           "auxiliar": SLUG},
                "is_active": True,
                "next_run_at": proximo.isoformat(),
                "created_by": user_id,
            }).execute()
            return (r.data or [{}])[0].get("id")
        except Exception as exc:  # noqa: BLE001
            logger.error("[Radar] rotina de fechamento não criada: %s",
                         type(exc).__name__)
            return None

    def _mensagem_de_instalacao(self, criados: int, falhas: list[dict]) -> str:
        base = (f"Radar instalado. A partir de agora acompanho {criados} fonte"
                f"{'s' if criados > 1 else ''} oficial"
                f"{'is' if criados > 1 else ''} e aviso quando algo mudar.")
        if falhas:
            nomes = ", ".join(f["fonte"] for f in falhas)
            base += (f" Não consegui acompanhar: {nomes}. "
                     "Elas ficam de fora até serem reconfiguradas.")
        return base

    def desinstalar(self, *, company_id: str) -> dict:
        """Pausa os monitores do Radar. Não apaga histórico.

        Apagar seria perder a linha do tempo do que já mudou — e a linha do
        tempo é justamente o que dá valor ao próximo radar.
        """
        monitores = self._monitores_do_radar(company_id)
        if not monitores:
            return {"ok": True, "mensagem": "O Radar não estava instalado."}
        pausados = 0
        for m in monitores:
            try:
                (self.db.table("research_monitors").update({"is_active": False})
                 .eq("id", m["id"]).eq("company_id", company_id).execute())
                if m.get("routine_id"):
                    (self.db.table("routines").update({"is_active": False})
                     .eq("id", m["routine_id"]).eq("company_id", company_id)
                     .execute())
                pausados += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("[Radar] pausa falhou: %s", type(exc).__name__)

        # A rotina de fechamento também para. Deixá-la viva produziria um
        # radar semanal de um Radar desinstalado — o tipo de fantasma que faz
        # o corretor desconfiar de tudo que o sistema entrega.
        try:
            (self.db.table("routines").update({"is_active": False})
             .eq("company_id", company_id)
             .eq("name", "Radar · fechamento semanal").execute())
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Radar] fechamento não pausado: %s", type(exc).__name__)

        return {"ok": True, "pausados": pausados,
                "mensagem": (f"Radar pausado ({pausados} fonte(s)). O histórico "
                             "do que já mudou continua disponível.")}

    def status(self, *, company_id: str) -> dict:
        monitores = self._monitores_do_radar(company_id)
        ativos = [m for m in monitores if m.get("is_active")]
        return {
            "instalado": bool(monitores),
            "ativo": bool(ativos),
            "fontes": len(monitores),
            "fontes_ativas": len(ativos),
            "ultima_verificacao": max(
                (m.get("last_run_at") or "" for m in monitores), default="") or None,
        }

    # ------------------------------------------------------------------
    # Entrega semanal
    # ------------------------------------------------------------------

    def compor_semanal(self, *, company_id: str, dias: int = 7,
                       work_run_id: Optional[str] = None) -> dict:
        """Junta o que mudou no período e entrega a peça.

        Quando nada mudou, **não** compõe peça. Um radar que entrega um
        documento vazio toda semana treina o corretor a não abrir o próximo —
        e o próximo pode ser o que importava.
        """
        mudancas = self.mudancas_do_periodo(company_id=company_id, dias=dias)
        if not mudancas:
            return {"ok": True, "sem_mudanca": True,
                    "mensagem": ("Nenhuma mudança relevante nas fontes oficiais "
                                 f"nos últimos {dias} dias.")}

        artifact_id = self._compor_artifact(
            company_id=company_id, mudancas=mudancas, dias=dias,
            work_run_id=work_run_id)
        sinal_id = self._avisar(company_id=company_id, mudancas=mudancas,
                                dias=dias, artifact_id=artifact_id)
        return {"ok": True, "mudancas": len(mudancas),
                "artifact_id": artifact_id, "signal_id": sinal_id,
                "mensagem": (f"{len(mudancas)} mudança(s) relevante(s) nas "
                             f"fontes oficiais nos últimos {dias} dias.")}

    def mudancas_do_periodo(self, *, company_id: str, dias: int = 7) -> list[dict]:
        """Observações relevantes dos monitores do Radar, mais recentes antes.

        Só entra o que o `MonitorService` já classificou como relevante ou
        maior: o filtro de ruído é o dele, e refazê-lo aqui criaria duas
        definições de "mudança" que divergiriam na primeira calibragem.
        """
        monitores = self._monitores_do_radar(company_id)
        ids = [m["id"] for m in monitores]
        if not ids:
            return []
        desde = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
        try:
            linhas = (self.db.table("research_observations")
                      .select("id, research_monitor_id, observed_at, "
                              "change_class, significance_score, summary, "
                              "evidence, source_snapshot_id, signal_id")
                      .eq("company_id", company_id)
                      .in_("research_monitor_id", ids)
                      .gte("observed_at", desde)
                      .in_("change_class", ["relevant", "major"])
                      .order("observed_at", desc=True)
                      .limit(50).execute()).data or []
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Radar] leitura de observações falhou: %s",
                           type(exc).__name__)
            return []

        nomes = {m["id"]: m.get("name") for m in monitores}
        urls = self._urls_dos_snapshots(
            [l.get("source_snapshot_id") for l in linhas])
        for l in linhas:
            l["fonte"] = nomes.get(l.get("research_monitor_id")) or "fonte oficial"
            l["url"] = urls.get(l.get("source_snapshot_id"))
            l["termos"] = ((l.get("evidence") or {}).get("termos") or [])
        return linhas

    def _urls_dos_snapshots(self, snapshot_ids: list) -> dict[str, str]:
        """Endereço de cada observação, pela cadeia snapshot → fonte.

        A observação guarda o que mudou, não onde: o endereço é atributo da
        FONTE, e duplicá-lo na observação criaria duas verdades sobre a mesma
        URL na hora em que uma delas fosse normalizada de novo.
        """
        ids = [s for s in snapshot_ids if s]
        if not ids:
            return {}
        try:
            snaps = (self.db.table("research_source_snapshots")
                     .select("id, research_source_id")
                     .in_("id", ids).execute()).data or []
            fontes_ids = list({s["research_source_id"] for s in snaps
                               if s.get("research_source_id")})
            if not fontes_ids:
                return {}
            fontes = (self.db.table("research_sources")
                      .select("id, canonical_url")
                      .in_("id", fontes_ids).execute()).data or []
            por_fonte = {f["id"]: f.get("canonical_url") for f in fontes}
            return {s["id"]: por_fonte.get(s.get("research_source_id"))
                    for s in snaps if por_fonte.get(s.get("research_source_id"))}
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Radar] leitura de fontes falhou: %s",
                           type(exc).__name__)
            return {}

    # ------------------------------------------------------------------

    def _compor_artifact(self, *, company_id: str, mudancas: list[dict],
                         dias: int, work_run_id: Optional[str]) -> Optional[str]:
        from ..artifacts.service import ArtifactService

        maiores = [m for m in mudancas if m.get("change_class") == "major"]
        veredito = (f"{len(mudancas)} mudança(s) nas fontes oficiais"
                    + (f", {len(maiores)} exigindo atenção imediata."
                       if maiores else "."))
        blocos = [
            {"block": "cover",
             "props": {"eyebrow": "Radar regulatório",
                       "title": "O que mudou na regulação",
                       "subtitle": f"Últimos {dias} dias",
                       "verdict": veredito,
                       "headline_label": "mudanças relevantes",
                       "headline_value": str(len(mudancas))}},
            {"block": "callout",
             "props": {"tone": "warning" if maiores else "info",
                       "title": ("Há mudança que exige ação" if maiores
                                 else "Nada exige ação imediata"),
                       "body": ("As linhas marcadas como alta relevância abaixo "
                                "mudaram texto de norma ou prazo."
                                if maiores else
                                "As mudanças abaixo foram registradas para "
                                "acompanhamento.")}},
            {"block": "table",
             "props": {"eyebrow": "Linha do tempo",
                       "title": "O que mudou e onde",
                       "columns": ["Quando", "Fonte", "O que mudou", "Relevância"],
                       "rows": [[
                           (m.get("observed_at") or "")[:10],
                           m.get("fonte") or "-",
                           (m.get("summary") or "")[:220] or "mudança registrada",
                           "alta" if m.get("change_class") == "major" else "média",
                       ] for m in mudancas[:30]]}},
            {"block": "sources",
             "props": {"title": "Publicações oficiais",
                       "note": ("Somente fontes oficiais. Notícia sobre a norma "
                                "não substitui a norma."),
                       "items": [{"title": m.get("fonte"), "url": m.get("url"),
                                  "retrieved_at": m.get("observed_at")}
                                 for m in mudancas[:30] if m.get("url")]}},
            {"block": "footer",
             "props": {"disclaimer": ("Resumo informativo do que mudou nas "
                                      "páginas acompanhadas. O texto oficial "
                                      "publicado prevalece.")}},
        ]
        try:
            servico = ArtifactService(self.raw)
            r = servico.criar(
                company_id=company_id,
                title="Radar regulatório",
                template_key="research.regulatory_radar",
                payload={"dias": dias, "mudancas": len(mudancas)},
                composition=blocos,
                subtitle=f"Últimos {dias} dias",
                summary=veredito,
                kind="report", origin="routine", work_run_id=work_run_id,
                data_sources=[{"kind": "research_monitor",
                               "id": m.get("research_monitor_id")}
                              for m in mudancas[:10]])
            versao = (r.get("version") or {}).get("id")
            if versao:
                servico.renderizar(company_id=company_id, version_id=versao)
                servico.publicar(company_id=company_id, version_id=versao)
            return (r.get("artifact") or {}).get("id")
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Radar] peça não gerada: %s", type(exc).__name__)
            return None

    def _avisar(self, *, company_id: str, mudancas: list[dict], dias: int,
                artifact_id: Optional[str]) -> Optional[str]:
        """Entrega pelo Intelligence Fabric — não por um canal próprio.

        Cada mudança já virou aviso no dia em que foi detectada, pelo
        `research.monitor_check`. Este é o aviso do CONJUNTO, e por isso tem
        entrada própria no adapter em vez de reaproveitar a de observação: os
        dois falam de fatos diferentes e precisam deduplicar separado.
        """
        from .adapters import IntelligenceAdapter

        try:
            criado = IntelligenceAdapter(self.raw).sinal_de_radar(
                company_id=company_id, mudancas=mudancas,
                periodo_dias=dias, artifact_id=artifact_id)
            return (criado or {}).get("id")
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Radar] aviso não entregue: %s", type(exc).__name__)
            return None

    # ------------------------------------------------------------------

    def _monitores_do_radar(self, company_id: str) -> list[dict]:
        try:
            return (self.db.table("research_monitors")
                    .select("id, name, is_active, routine_id, last_run_at")
                    .eq("company_id", company_id)
                    .eq("topic", "regulacao")
                    .like("name", "Radar ·%")
                    .execute()).data or []
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Radar] leitura de monitores falhou: %s",
                           type(exc).__name__)
            return []
