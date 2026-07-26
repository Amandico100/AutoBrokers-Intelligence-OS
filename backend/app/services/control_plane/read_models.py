"""Read models do Control Plane. SPEC-061 §5.1, §14, §15.

O que é um read model aqui
--------------------------
Uma **projeção de leitura** montada para responder uma pergunta de tela — não
uma cópia dos dados. Nada aqui grava, e nada aqui é a verdade sobre coisa
alguma: a verdade continua nas tabelas das SPECs 054–060.

A diferença importa porque a tentação é sempre a mesma: guardar "o número de
trabalhos falhados por corretora" numa tabela para a tela abrir rápido. No dia
em que um trabalho for reprocessado por fora, o número fica errado e ninguém
descobre.

Regra de todo módulo daqui: **filtra por `company_id` sempre que a pergunta é
de uma corretora**, e nunca devolve conteúdo de segurado.
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Estados que a tela agrupa como "precisa de gente". `pending_approval` é
# diferente de `failed`: o primeiro está esperando uma DECISÃO, o segundo
# esperando um conserto. Misturar os dois faz o operador procurar bug onde só
# falta alguém clicar.
ESPERANDO_HUMANO = ("pending_approval", "paused")
PROBLEMA = ("failed", "cancelled")


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _humanizar_estado(status: str) -> str:
    return {
        "queued": "na fila",
        "running": "em andamento",
        "paused": "pausado",
        "pending_approval": "esperando aprovação",
        "completed": "concluído",
        "failed": "falhou",
        "cancelled": "cancelado",
    }.get(status, status)


class CentralDeTrabalhos:
    """§15 — o que está rodando, o que travou, o que falhou."""

    def __init__(self, supabase_client: Any):
        self.raw = supabase_client
        self.db = getattr(supabase_client, "client", supabase_client)

    def resumo(self, *, company_id: Optional[str] = None,
               dias: int = 7) -> dict:
        """Agregado primeiro — §CA-014: toda tela do Admin responde por N.

        Uma lista dos últimos 40 trabalhos responde bem com 5 corretoras e
        deixa de responder qualquer coisa com mil. O agregado continua
        respondendo: ele diz *quantos* e *de que tipo*, e a lista vira o
        detalhe de quem já sabe o que procurar.
        """
        desde = (_agora() - timedelta(days=dias)).isoformat()
        linhas = self._ler(company_id=company_id, desde=desde, limite=1000)

        por_status = Counter(str(l.get("status")) for l in linhas)
        por_workflow = Counter(str(l.get("workflow_key")) for l in linhas)
        empresas_com_problema = {
            str(l.get("company_id")) for l in linhas
            if str(l.get("status")) in PROBLEMA and l.get("company_id")}

        travados = self._travados(company_id=company_id)

        return {
            "ok": True,
            "periodo_dias": dias,
            "total": len(linhas),
            "por_estado": [{"estado": k, "rotulo": _humanizar_estado(k), "n": v}
                           for k, v in por_status.most_common()],
            "esperando_humano": sum(por_status[e] for e in ESPERANDO_HUMANO),
            "com_problema": sum(por_status[e] for e in PROBLEMA),
            "travados": len(travados),
            "corretoras_afetadas": len(empresas_com_problema),
            "tipos_mais_comuns": [{"workflow": k, "n": v}
                                  for k, v in por_workflow.most_common(8)],
            "mensagem": self._frase(por_status, len(travados)),
        }

    def _frase(self, por_status: Counter, travados: int) -> str:
        """A frase que resume. Sem ela, o operador lê números e não conclui."""
        problemas = sum(por_status[e] for e in PROBLEMA)
        esperando = sum(por_status[e] for e in ESPERANDO_HUMANO)
        if not por_status:
            return "Nenhum trabalho no período."
        partes = []
        if travados:
            partes.append(f"{travados} parado(s) sem sinal de vida")
        if problemas:
            partes.append(f"{problemas} com problema")
        if esperando:
            partes.append(f"{esperando} esperando uma decisão")
        if not partes:
            return "Tudo andou sem precisar de ninguém."
        return "Precisa de atenção: " + ", ".join(partes) + "."

    def listar(self, *, company_id: Optional[str] = None,
               estado: Optional[str] = None, limite: int = 50) -> list[dict]:
        """A lista, já traduzida. Nunca devolve `input_payload`.

        O payload de um Work Run carrega o pedido do corretor, que pode conter
        dado de segurado. A tela de operação não precisa dele para reprocessar
        — precisa saber o que é, de quem é e o que houve.
        """
        filtros = {}
        if estado:
            filtros["status"] = estado
        linhas = self._ler(company_id=company_id, limite=limite, filtros=filtros)
        agora = _agora()
        saida = []
        for l in linhas:
            saida.append({
                "id": l.get("id"),
                "company_id": l.get("company_id"),
                "tipo": l.get("workflow_key"),
                "titulo": l.get("outcome_title"),
                "estado": l.get("status"),
                "rotulo": _humanizar_estado(str(l.get("status"))),
                "erro": l.get("error_code"),
                "criado_em": l.get("created_at"),
                "atualizado_em": l.get("updated_at"),
                "parado": _sem_sinal(l, agora),
            })
        return saida

    def detalhe(self, run_id: str, *,
                company_id: Optional[str] = None) -> dict:
        """Um trabalho, com etapas e TENTATIVAS.

        As tentativas são o que o Bloco 0 fez existir. Sem elas, esta tela
        mostraria "falhou" e o operador não saberia se falhou na primeira vez
        ou na quarta — que é a diferença entre "instabilidade" e "quebrado".
        """
        try:
            q = self.db.table("work_runs").select(
                "id, company_id, workflow_key, outcome_title, status, "
                "error_code, error_message, created_at, updated_at, "
                "started_at, finished_at, progress_percent, current_step_key, "
                "lease_owner, heartbeat_at").eq("id", run_id)
            if company_id:
                q = q.eq("company_id", company_id)
            run = (q.limit(1).execute().data or [None])[0]
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Trabalhos] leitura falhou: %s", type(exc).__name__)
            return {"ok": False, "erro": "não consegui ler este trabalho"}

        if not run:
            return {"ok": False, "erro": "trabalho não encontrado"}

        etapas = self._etapas(run_id)
        tentativas = self._tentativas(run_id)
        por_etapa: dict[str, list[dict]] = {}
        for t in tentativas:
            por_etapa.setdefault(str(t.get("work_step_id")), []).append(t)

        for e in etapas:
            e["tentativas"] = sorted(
                por_etapa.get(str(e.get("id")), []),
                key=lambda t: int(t.get("attempt_number") or 0))
            e["rotulo"] = _humanizar_estado(str(e.get("status")))

        return {
            "ok": True,
            "trabalho": {**run, "rotulo": _humanizar_estado(str(run.get("status"))),
                         "parado": _sem_sinal(run, _agora())},
            "etapas": etapas,
            "total_de_tentativas": len(tentativas),
            "repetiu": sum(1 for t in tentativas
                           if int(t.get("attempt_number") or 1) > 1),
        }

    # ------------------------------------------------------------------

    def _ler(self, *, company_id: Optional[str] = None,
             desde: Optional[str] = None, limite: int = 200,
             filtros: Optional[dict] = None) -> list[dict]:
        try:
            q = (self.db.table("work_runs")
                 .select("id, company_id, workflow_key, outcome_title, status, "
                         "error_code, created_at, updated_at, heartbeat_at")
                 .order("created_at", desc=True).limit(limite))
            if company_id:
                q = q.eq("company_id", company_id)
            if desde:
                q = q.gte("created_at", desde)
            for c, v in (filtros or {}).items():
                q = q.eq(c, v)
            return q.execute().data or []
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Trabalhos] leitura falhou: %s", type(exc).__name__)
            return []

    def _travados(self, *, company_id: Optional[str] = None) -> list[dict]:
        agora = _agora()
        linhas = self._ler(company_id=company_id, limite=300,
                           filtros={"status": "running"})
        return [l for l in linhas if _sem_sinal(l, agora)]

    def _etapas(self, run_id: str) -> list[dict]:
        try:
            return (self.db.table("work_steps")
                    .select("id, step_key, name, ordinal, status, step_type, "
                            "started_at, finished_at, capability_key")
                    .eq("work_run_id", run_id)
                    .order("ordinal").limit(100).execute()).data or []
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Trabalhos] etapas: %s", type(exc).__name__)
            return []

    def _tentativas(self, run_id: str) -> list[dict]:
        try:
            return (self.db.table("work_attempts")
                    .select("id, work_step_id, attempt_number, worker_id, "
                            "status, started_at, finished_at, error_class, "
                            "error_message_redacted, retryable, metrics")
                    .eq("work_run_id", run_id).limit(200).execute()).data or []
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Trabalhos] tentativas: %s", type(exc).__name__)
            return []


def _sem_sinal(run: dict, agora: datetime, minutos: int = 30) -> bool:
    """Rodando há tempo demais sem heartbeat.

    O corte não é arbitrário: a lease da SPEC-055 é bem mais curta, então um
    run `running` há meia hora sem heartbeat já não é lentidão — é trabalho
    abandonado por um worker que morreu.
    """
    if str(run.get("status")) != "running":
        return False
    marca = run.get("heartbeat_at") or run.get("created_at")
    if not marca:
        return True
    try:
        quando = datetime.fromisoformat(str(marca).replace("Z", "+00:00"))
        return (agora - quando) > timedelta(minutes=minutos)
    except Exception:  # noqa: BLE001
        return False


class CentralDeAprovacoes:
    """§16 — o que espera uma decisão humana.

    A diferença para a Central de Trabalhos: lá o operador conserta, aqui ele
    **decide**. São dois estados de espera diferentes, e misturá-los faz o
    operador procurar defeito onde só falta alguém clicar.

    Uma aprovação tem uma propriedade que trabalho falhado não tem: ela
    **envelhece contra alguém**. Um pedido parado há três dias não é um item
    da lista — é um cliente sem resposta. Por isso a idade é o primeiro
    critério de ordem, e não a severidade.
    """

    def __init__(self, supabase_client: Any):
        self.raw = supabase_client
        self.db = getattr(supabase_client, "client", supabase_client)

    def listar(self, *, company_id: Optional[str] = None,
               status: str = "pending", limite: int = 50) -> dict:
        try:
            q = (self.db.table("approval_requests")
                 .select("id, company_id, action_type, subject_type, subject_id, "
                         "status, risk_level, preview, requested_at, created_at, "
                         "expires_at, work_run_id, error_message")
                 .order("created_at", desc=False)  # mais antigo primeiro
                 .limit(limite))
            if status:
                q = q.eq("status", status)
            if company_id:
                q = q.eq("company_id", company_id)
            linhas = q.execute().data or []
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Aprovações] leitura falhou: %s", type(exc).__name__)
            return {"ok": False, "erro": "não consegui ler as aprovações",
                    "itens": []}

        agora = _agora()
        itens = []
        for l in linhas:
            criado = l.get("requested_at") or l.get("created_at")
            itens.append({
                "id": l.get("id"),
                "company_id": l.get("company_id"),
                "o_que": l.get("action_type") or "ação",
                "sobre": f"{l.get('subject_type') or ''} {l.get('subject_id') or ''}".strip(),
                "risco": l.get("risk_level") or "low",
                # `preview` é o que a ação FARIA. É o que permite decidir sem
                # abrir outra tela — e sem ele "aprovar" vira assinar em branco.
                "previa": l.get("preview") or {},
                "criado_em": criado,
                "expira_em": l.get("expires_at"),
                "horas_esperando": _horas(criado, agora),
                "vencida": _venceu(l.get("expires_at"), agora),
                "work_run_id": l.get("work_run_id"),
                "status": l.get("status"),
            })

        vencidas = [i for i in itens if i["vencida"]]
        return {
            "ok": True,
            "itens": itens,
            "total": len(itens),
            "vencidas": len(vencidas),
            "mais_antiga_horas": max((i["horas_esperando"] or 0 for i in itens),
                                     default=0),
            "mensagem": self._frase(itens, vencidas),
        }

    def _frase(self, itens: list[dict], vencidas: list[dict]) -> str:
        if not itens:
            return "Nenhuma decisão esperando você."
        partes = [f"{len(itens)} esperando decisão"]
        if vencidas:
            # Vencida é pior que pendente: o prazo passou, e quem pediu já
            # sentiu. Dizer isso separado evita que se perca no total.
            partes.append(f"{len(vencidas)} já passaram do prazo")
        mais_velha = max((i["horas_esperando"] or 0 for i in itens), default=0)
        if mais_velha >= 24:
            partes.append(f"a mais antiga há {int(mais_velha // 24)} dia(s)")
        return " · ".join(partes) + "."


def _horas(quando: Optional[str], agora: datetime) -> Optional[float]:
    if not quando:
        return None
    try:
        d = datetime.fromisoformat(str(quando).replace("Z", "+00:00"))
        return round((agora - d).total_seconds() / 3600.0, 1)
    except Exception:  # noqa: BLE001
        return None


def _venceu(expira: Optional[str], agora: datetime) -> bool:
    if not expira:
        return False
    try:
        return datetime.fromisoformat(str(expira).replace("Z", "+00:00")) < agora
    except Exception:  # noqa: BLE001
        return False


class CockpitDaCorretora:
    """§14 — tudo sobre UMA corretora, em uma tela.

    Cada bloco é uma leitura da autoridade de origem. Se uma delas estiver
    indisponível, o bloco vem vazio **com o motivo** e o resto da tela continua
    respondendo — a alternativa seria uma tela em branco que não diz nada.
    """

    def __init__(self, supabase_client: Any):
        self.raw = supabase_client
        self.db = getattr(supabase_client, "client", supabase_client)

    def montar(self, company_id: str, *, dias: int = 30) -> dict:
        empresa = self._empresa(company_id)
        if not empresa:
            return {"ok": False, "erro": "corretora não encontrada"}

        trabalhos = CentralDeTrabalhos(self.raw).resumo(
            company_id=company_id, dias=dias)

        return {
            "ok": True,
            "corretora": empresa,
            "trabalhos": trabalhos,
            "atividade": self._atividade(company_id, dias),
            "inteligencia": self._contar("intelligence_signals", company_id),
            "pesquisas": self._contar("research_requests", company_id),
            "monitores": self._contar("research_monitors", company_id,
                                      filtros={"is_active": True}),
            "auxiliares": self._contar("tenant_auxiliaries", company_id),
            "artifacts": self._contar("artifacts", company_id),
            "conexoes": self._saude_das_conexoes(company_id),
        }

    def _empresa(self, company_id: str) -> Optional[dict]:
        try:
            r = (self.db.table("companies")
                 .select("id, company_name, created_at")
                 .eq("id", company_id).limit(1).execute())
            return (r.data or [None])[0]
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Cockpit] empresa: %s", type(exc).__name__)
            return None

    def _atividade(self, company_id: str, dias: int) -> dict:
        """Última vez que algo aconteceu. Silêncio prolongado é sintoma.

        Corretora provisionada que não gera Work Run há duas semanas não está
        "estável" — está sem uso, e isso precisa aparecer antes da renovação.
        """
        desde = (_agora() - timedelta(days=dias)).isoformat()
        try:
            r = (self.db.table("work_runs").select("created_at")
                 .eq("company_id", company_id)
                 .order("created_at", desc=True).limit(1).execute())
            ultimo = (r.data or [{}])[0].get("created_at")
        except Exception:  # noqa: BLE001
            ultimo = None

        dias_parada = None
        if ultimo:
            try:
                quando = datetime.fromisoformat(str(ultimo).replace("Z", "+00:00"))
                dias_parada = (_agora() - quando).days
            except Exception:  # noqa: BLE001
                pass

        return {"ultima_atividade": ultimo, "dias_sem_atividade": dias_parada,
                "desde": desde,
                "alerta": (dias_parada is not None and dias_parada >= 14)}

    def _contar(self, tabela: str, company_id: str,
                filtros: Optional[dict] = None) -> dict:
        try:
            q = self.db.table(tabela).select("id").eq("company_id", company_id)
            for c, v in (filtros or {}).items():
                q = q.eq(c, v)
            return {"n": len(q.limit(1000).execute().data or []), "ok": True}
        except Exception as exc:  # noqa: BLE001
            # Bloco indisponível vem declarado. "0" seria uma afirmação falsa.
            return {"n": None, "ok": False,
                    "motivo": f"não consegui ler ({type(exc).__name__})"}

    def _saude_das_conexoes(self, company_id: str) -> dict:
        """Conexões da corretora. Tabela `integrations`, coluna `channel_status`.

        Só conta como problema a conexão **ativa** em estado ruim. Integração
        aposentada (`is_active=false`) em estado `close` é o falso positivo que
        o canário da SPEC-059 encontrou com dado real — e `close` precisa estar
        na lista de estados ruins, porque sem ele o canal genuinamente caído
        ficava invisível.
        """
        try:
            linhas = (self.db.table("integrations")
                      .select("id, provider, is_active, channel_status, purpose")
                      .eq("company_id", company_id).limit(50).execute()).data or []
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "motivo": f"não consegui ler ({type(exc).__name__})"}

        ativas = [l for l in linhas if l.get("is_active")]
        ruins = [l for l in ativas
                 if str(l.get("channel_status") or "").lower() in
                 ("error", "disconnected", "close", "closed", "failed")]
        return {"ok": True, "total": len(linhas), "ativas": len(ativas),
                "com_problema": len(ruins),
                "tipos": sorted({str(l.get("provider")) for l in ativas})}
