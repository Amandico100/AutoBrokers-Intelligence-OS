"""Admin Inbox — o que precisa de um humano. SPEC-061 §13.

O que ela resolve
-----------------
As SPECs 054–060 produzem trabalho o tempo todo: aprovação pendente, monitor
que não conseguiu ler, conexão degradada, Work Run travado, candidato a
conhecimento esperando curadoria. Cada um mora na sua tabela, com a sua tela.

O operador da plataforma não abre nove telas de manhã. Ele abre uma, e a
pergunta dele é sempre a mesma: **o que precisa de mim agora?**

Projeção, não cópia — §13.1
---------------------------
Esta caixa **lê** as autoridades existentes e não guarda o item. Copiar
criaria uma segunda verdade sobre o mesmo fato: a aprovação seria decidida na
tela de aprovações e continuaria pendente aqui, e a caixa passaria a mentir.

O que é guardado (`admin_inbox_states`) é apenas o estado PESSOAL: eu li, eu
adiei. O item continua pertencendo a quem o criou.

Dedupe por causa — §13.4
------------------------
Oito rotinas quebradas pelo mesmo provider fora do ar são **um** problema, não
oito. Oito cartões idênticos fazem o operador tratar sintoma; um cartão que
diz "afeta 3 corretoras e 8 rotinas" faz ele tratar a causa.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Peso de cada dimensão na prioridade. Declarados, e não embutidos numa
# fórmula, para que a ordem da caixa seja explicável quando alguém perguntar
# "por que isto está no topo?".
PESOS = {"severidade": 4.0, "urgencia": 2.0, "impacto": 2.5,
         "abrangencia": 3.0, "frescor": 1.0}

SEVERIDADE_NUMERICA = {"critical": 100.0, "high": 70.0, "medium": 40.0,
                       "low": 15.0, "info": 5.0}

TETO_POR_FONTE = 40


@dataclass
class ItemDaCaixa:
    """Um item. `fonte` + `chave` é a identidade — nunca um id novo.

    Gerar id próprio faria o mesmo item mudar de identidade a cada leitura, e
    o estado pessoal ("já li isto") deixaria de colar.
    """

    fonte: str
    chave: str
    titulo: str
    detalhe: str
    severidade: str = "medium"
    company_id: Optional[str] = None
    empresas_afetadas: int = 1
    itens_agrupados: int = 1
    ocorrido_em: Optional[str] = None
    href: Optional[str] = None
    acao_sugerida: Optional[str] = None
    permission_para_agir: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def prioridade(self, agora: Optional[datetime] = None) -> float:
        agora = agora or datetime.now(timezone.utc)
        sev = SEVERIDADE_NUMERICA.get(self.severidade, 30.0)

        # Abrangência: um problema que atinge cinco corretoras é de plataforma;
        # o mesmo problema numa só é de suporte. A diferença muda quem age.
        abrangencia = min(100.0, 20.0 * float(self.empresas_afetadas))

        # Frescor: o que acabou de acontecer pesa mais, e o peso cai devagar —
        # um item de ontem que ninguém tratou continua importando.
        frescor = 50.0
        if self.ocorrido_em:
            try:
                quando = datetime.fromisoformat(
                    str(self.ocorrido_em).replace("Z", "+00:00"))
                horas = max(0.0, (agora - quando).total_seconds() / 3600.0)
                frescor = max(10.0, 100.0 - horas * 2.0)
            except Exception:  # noqa: BLE001
                frescor = 50.0

        urgencia = 90.0 if self.severidade in ("critical", "high") else 40.0
        impacto = min(100.0, 10.0 * float(self.itens_agrupados) + sev / 2)

        total = (PESOS["severidade"] * sev + PESOS["urgencia"] * urgencia
                 + PESOS["impacto"] * impacto + PESOS["abrangencia"] * abrangencia
                 + PESOS["frescor"] * frescor)
        return round(total / sum(PESOS.values()), 1)

    def como_dict(self, agora: Optional[datetime] = None) -> dict:
        return {"fonte": self.fonte, "chave": self.chave, "titulo": self.titulo,
                "detalhe": self.detalhe, "severidade": self.severidade,
                "company_id": self.company_id,
                "empresas_afetadas": self.empresas_afetadas,
                "itens_agrupados": self.itens_agrupados,
                "ocorrido_em": self.ocorrido_em, "href": self.href,
                "acao_sugerida": self.acao_sugerida,
                "permission_para_agir": self.permission_para_agir,
                "prioridade": self.prioridade(agora), "metadata": self.metadata}


class CaixaDeEntrada:
    def __init__(self, supabase_client: Any):
        self.raw = supabase_client
        self.db = getattr(supabase_client, "client", supabase_client)

    # ------------------------------------------------------------------

    def montar(self, *, admin_user_id: str, permissions: set[str],
               limite: int = 50) -> dict:
        """A caixa priorizada, já filtrada pelo que a pessoa pode ver.

        Uma fonte que a pessoa não tem permission de ler **não é consultada** —
        não basta esconder o cartão depois. Ler para depois esconder é como
        dados vazam por um log ou por uma contagem que sobrou na tela.
        """
        agora = datetime.now(timezone.utc)
        itens: list[ItemDaCaixa] = []

        if "approvals.read" in permissions:
            itens += self._aprovacoes_pendentes()
        if "work_runs.read" in permissions:
            itens += self._trabalhos_travados()
        if "research.read" in permissions:
            itens += self._monitores_com_falha()
        if "intelligence.read" in permissions:
            itens += self._sinais_criticos()
        if "knowledge.curate" in permissions:
            itens += self._conhecimento_esperando()
        if "security.read" in permissions:
            itens += self._incidentes_abertos()

        agrupados = agrupar_por_causa(itens)
        estados = self._estados_pessoais(admin_user_id)

        visiveis = []
        for item in agrupados:
            estado = estados.get(f"{item.fonte}:{item.chave}", {})
            situacao = str(estado.get("state") or "unread")
            if situacao == "dismissed":
                continue
            if situacao == "snoozed":
                ate = estado.get("snoozed_until")
                try:
                    if ate and datetime.fromisoformat(
                            str(ate).replace("Z", "+00:00")) > agora:
                        continue
                except Exception:  # noqa: BLE001
                    pass  # data ilegível: o item volta a aparecer
            d = item.como_dict(agora)
            d["estado"] = situacao
            visiveis.append(d)

        visiveis.sort(key=lambda x: -float(x["prioridade"]))
        return {
            "ok": True,
            "itens": visiveis[:limite],
            "total": len(visiveis),
            "nao_lidos": sum(1 for v in visiveis if v["estado"] == "unread"),
            # Dizer que está vazio é diferente de não dizer nada: sem esta
            # frase, o operador não sabe se a caixa está limpa ou quebrada.
            "mensagem": ("Nada precisa de você agora." if not visiveis
                         else f"{len(visiveis)} item(ns) precisam de atenção."),
        }

    # ------------------------------------------------------------------
    # Fontes — §13.1. Cada uma LÊ a autoridade de origem.
    # ------------------------------------------------------------------

    def _aprovacoes_pendentes(self) -> list[ItemDaCaixa]:
        # `action_type`, não `action_key`. Escrevi `action_key` de memória e o
        # leitor tolerante engolia o erro de coluna: a caixa nunca mostraria
        # aprovação nenhuma, sem nada indicando por quê.
        #
        # É o risco de um leitor que não derruba a tela — ele também não avisa.
        # Por isso `test_spec061_read_models.py` cobra os nomes de coluna
        # contra a lista real do banco.
        linhas = self._ler("approval_requests",
                           "id, company_id, status, created_at, action_type, "
                           "risk_level",
                           filtros={"status": "pending"})
        return [ItemDaCaixa(
            fonte="approval", chave=str(l["id"]),
            titulo="Aprovação esperando decisão",
            detalhe=f"Ação: {l.get('action_type') or 'não informada'}",
            severidade="high" if str(l.get("risk_level")) in ("high", "critical") else "medium",
            company_id=l.get("company_id"), ocorrido_em=l.get("created_at"),
            href="/admin/aprovacoes",
            acao_sugerida="Aprovar ou recusar",
            permission_para_agir="approvals.decide") for l in linhas]

    def _trabalhos_travados(self) -> list[ItemDaCaixa]:
        """Work Run parado há tempo demais.

        O corte de 30 minutos não é arbitrário: a lease da SPEC-055 é bem mais
        curta, então um run "running" há meia hora sem heartbeat já não é
        lentidão — é trabalho abandonado.
        """
        limite = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
        linhas = self._ler("work_runs",
                           "id, company_id, workflow_key, status, "
                           "heartbeat_at, created_at, error_code",
                           filtros={"status": "running"})
        travados = [l for l in linhas
                    if str(l.get("heartbeat_at") or l.get("created_at") or "") < limite]
        itens = [ItemDaCaixa(
            fonte="work_run", chave=str(l["id"]),
            titulo="Trabalho parado no meio",
            detalhe=f"{l.get('workflow_key')} sem sinal de vida há mais de 30 minutos",
            severidade="high", company_id=l.get("company_id"),
            ocorrido_em=l.get("heartbeat_at") or l.get("created_at"),
            href="/admin/trabalhos",
            acao_sugerida="Reprocessar ou cancelar",
            permission_para_agir="work_runs.retry",
            metadata={"workflow": l.get("workflow_key")}) for l in travados]

        falhos = self._ler("work_runs",
                           "id, company_id, workflow_key, status, error_code, "
                           "updated_at", filtros={"status": "failed"})
        itens += [ItemDaCaixa(
            fonte="work_run", chave=str(l["id"]),
            titulo="Trabalho falhou",
            detalhe=f"{l.get('workflow_key')}: {l.get('error_code') or 'sem código'}",
            severidade="medium", company_id=l.get("company_id"),
            ocorrido_em=l.get("updated_at"), href="/admin/trabalhos",
            acao_sugerida="Ver o motivo e reprocessar",
            permission_para_agir="work_runs.retry",
            metadata={"workflow": l.get("workflow_key"),
                      "erro": l.get("error_code")}) for l in falhos]
        return itens

    def _monitores_com_falha(self) -> list[ItemDaCaixa]:
        linhas = self._ler("research_monitors",
                           "id, company_id, name, health, health_reason, "
                           "last_run_at, is_active")
        ruins = [l for l in linhas
                 if l.get("is_active") and str(l.get("health")) in ("degraded", "error")]
        return [ItemDaCaixa(
            fonte="research_monitor", chave=str(l["id"]),
            titulo="Não consegui acompanhar uma fonte",
            # A frase importa: "nada mudou" seria uma AFIRMAÇÃO, e ela é falsa
            # quando ninguém conseguiu olhar.
            detalhe=(f"{l.get('name')}: {l.get('health_reason') or 'fonte inacessível'}. "
                     "Não afirmo que nada mudou — apenas que não consegui ler."),
            severidade="high" if str(l.get("health")) == "error" else "medium",
            company_id=l.get("company_id"), ocorrido_em=l.get("last_run_at"),
            href="/admin/pesquisa",
            acao_sugerida="Conferir o endereço ou o crédito do provider",
            permission_para_agir="research.manage") for l in ruins]

    def _sinais_criticos(self) -> list[ItemDaCaixa]:
        linhas = self._ler("intelligence_signals",
                           "id, company_id, summary_redacted, severity, "
                           "created_at, signal_type", limite=60)
        criticos = [l for l in linhas if str(l.get("severity")) in ("critical", "high")]
        return [ItemDaCaixa(
            fonte="signal", chave=str(l["id"]),
            titulo="Sinal de alta severidade",
            detalhe=str(l.get("summary_redacted") or "")[:300],
            severidade=str(l.get("severity") or "high"),
            company_id=l.get("company_id"), ocorrido_em=l.get("created_at"),
            href="/admin/inteligencia",
            acao_sugerida="Ver a evidência",
            permission_para_agir="intelligence.read",
            metadata={"tipo": l.get("signal_type")}) for l in criticos]

    def _conhecimento_esperando(self) -> list[ItemDaCaixa]:
        linhas = self._ler("knowledge_candidates",
                           "id, company_id, title, status, created_at",
                           filtros={"status": "pending"})
        if not linhas:
            return []
        # Um cartão só: curadoria é trabalho em lote, e trinta cartões de
        # "candidato esperando" enterrariam o incidente que está embaixo.
        return [ItemDaCaixa(
            fonte="knowledge", chave="pendentes",
            titulo="Conhecimento esperando curadoria",
            detalhe=f"{len(linhas)} candidato(s) aguardando revisão.",
            severidade="low", itens_agrupados=len(linhas),
            ocorrido_em=max((str(l.get("created_at") or "") for l in linhas),
                            default=None) or None,
            href="/admin/knowledge-base",
            acao_sugerida="Revisar e publicar ou descartar",
            permission_para_agir="knowledge.curate")]

    def _incidentes_abertos(self) -> list[ItemDaCaixa]:
        linhas = self._ler("platform_incidents",
                           "id, incident_key, severity, status, scope, "
                           "summary, detected_at")
        abertos = [l for l in linhas
                   if str(l.get("status")) in ("open", "acknowledged", "mitigated")]
        return [ItemDaCaixa(
            fonte="incident", chave=str(l["id"]),
            titulo=f"Incidente {l.get('severity')} em aberto",
            detalhe=str(l.get("summary") or "")[:300],
            severidade="critical" if str(l.get("severity")) == "sev1" else "high",
            ocorrido_em=l.get("detected_at"), href="/admin/governanca",
            acao_sugerida="Acompanhar e resolver",
            permission_para_agir="security.manage") for l in abertos]

    # ------------------------------------------------------------------

    def _ler(self, tabela: str, campos: str, *,
             filtros: Optional[dict] = None,
             limite: int = TETO_POR_FONTE) -> list[dict]:
        """Leitura tolerante: uma fonte indisponível não derruba a caixa.

        Se a tabela de aprovações estiver fora do ar, o operador ainda precisa
        ver os incidentes. Caixa vazia por erro parcial seria a pior resposta
        possível para "o que precisa de mim?".
        """
        try:
            q = self.db.table(tabela).select(campos).limit(limite)
            for campo, valor in (filtros or {}).items():
                q = q.eq(campo, valor)
            return q.execute().data or []
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Inbox] fonte '%s' indisponível: %s", tabela,
                           type(exc).__name__)
            return []

    def _estados_pessoais(self, admin_user_id: str) -> dict[str, dict]:
        try:
            linhas = (self.db.table("admin_inbox_states")
                      .select("source_type, source_id, state, snoozed_until")
                      .eq("admin_user_id", str(admin_user_id))
                      .limit(500).execute()).data or []
            return {f"{l['source_type']}:{l['source_id']}": l for l in linhas}
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Inbox] estados pessoais: %s", type(exc).__name__)
            return {}

    def marcar(self, *, admin_user_id: str, fonte: str, chave: str,
               estado: str, adiar_ate: Optional[str] = None,
               nota: Optional[str] = None) -> dict:
        """Estado pessoal. §13.3: dispensar NÃO altera o objeto de origem."""
        if estado not in ("unread", "read", "acknowledged", "snoozed", "dismissed"):
            return {"ok": False, "erro": "estado desconhecido"}
        if estado == "snoozed" and not adiar_ate:
            return {"ok": False,
                    "erro": ("adiar sem data é dispensar com outro nome — "
                             "informe até quando")}
        linha = {"admin_user_id": str(admin_user_id), "source_type": fonte,
                 "source_id": chave, "state": estado,
                 "snoozed_until": adiar_ate,
                 "updated_at": datetime.now(timezone.utc).isoformat()}
        if nota:
            from .audit import redigir_texto

            linha["note_redacted"] = redigir_texto(nota)
        try:
            self.db.table("admin_inbox_states").upsert(
                linha, on_conflict="admin_user_id,source_type,source_id").execute()
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            logger.error("[Inbox] marcação falhou: %s", type(exc).__name__)
            return {"ok": False, "erro": "não consegui salvar"}


# ---------------------------------------------------------------------------
# Dedupe por causa — §13.4
# ---------------------------------------------------------------------------


def agrupar_por_causa(itens: list[ItemDaCaixa]) -> list[ItemDaCaixa]:
    """Junta itens com a MESMA causa. Puro, e por isso testável.

    O exemplo da SPEC é literal: "Provider WhatsApp degradado — afeta 3
    corretoras e 8 Rotinas", e não oito cartões idênticos. Oito cartões fazem o
    operador tratar sintoma; um cartão com o alcance faz ele tratar a causa.

    A causa é `(fonte, título, motivo)`. Deliberadamente NÃO inclui a
    corretora: é exatamente juntando corretoras diferentes que o cartão revela
    que o problema é de plataforma.
    """
    grupos: dict[tuple, list[ItemDaCaixa]] = {}
    for item in itens:
        causa = (item.fonte, item.titulo,
                 str(item.metadata.get("erro")
                     or item.metadata.get("workflow") or ""))
        grupos.setdefault(causa, []).append(item)

    saida: list[ItemDaCaixa] = []
    for membros in grupos.values():
        if len(membros) == 1:
            saida.append(membros[0])
            continue

        base = max(membros, key=lambda m: SEVERIDADE_NUMERICA.get(m.severidade, 0))
        empresas = {m.company_id for m in membros if m.company_id}
        agrupado = ItemDaCaixa(
            fonte=base.fonte,
            # A chave do grupo é derivada e estável: o estado pessoal precisa
            # colar no grupo, e não em um dos membros.
            chave=f"grupo:{base.fonte}:{abs(hash((base.titulo, len(membros))))%10**10}",
            titulo=base.titulo,
            detalhe=(f"{base.detalhe} — afeta {len(empresas) or 1} corretora(s) "
                     f"e {len(membros)} item(ns)."),
            severidade=base.severidade,
            company_id=base.company_id if len(empresas) == 1 else None,
            empresas_afetadas=max(1, len(empresas)),
            itens_agrupados=len(membros),
            ocorrido_em=max((m.ocorrido_em or "" for m in membros), default=None) or None,
            href=base.href, acao_sugerida=base.acao_sugerida,
            permission_para_agir=base.permission_para_agir,
            metadata={**base.metadata, "agrupou": len(membros),
                      "chaves": [m.chave for m in membros[:20]]})
        saida.append(agrupado)
    return saida
