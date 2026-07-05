"""F2 — Tools de rotinas para o Chat Principal (Claude-Rotinas por conversa).

O corretor pede em linguagem natural ("todo dia às 8h me manda X no WhatsApp")
e o Chat Principal cria a rotina de verdade. Listar/pausar pela mesma conversa.
"""

from __future__ import annotations

import logging
from datetime import timezone
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CreateRoutineInput(BaseModel):
    name: str = Field(description="Nome curto da rotina (ex: 'Notícias de seguros diárias')")
    instructions: str = Field(description="Instruções COMPLETAS do que fazer em cada execução (a receita)")
    schedule_kind: str = Field(description="'daily' (horário fixo) ou 'interval' (a cada N minutos)")
    time_of_day: Optional[str] = Field(default=None, description="Para daily: horário HH:MM (hora de Brasília)")
    weekdays: Optional[str] = Field(default=None, description="Para daily (opcional): dias 0-6 separados por vírgula, 0=segunda (ex: '0,1,2,3,4' = dias úteis)")
    interval_minutes: Optional[int] = Field(default=None, description="Para interval: intervalo em minutos (mínimo 5)")
    delivery_channel: str = Field(default="whatsapp", description="'whatsapp' (enviar no número) ou 'none' (só registrar)")
    delivery_number: Optional[str] = Field(default=None, description="Número WhatsApp de destino com DDI (ex: 5547999998888) quando delivery_channel=whatsapp")


class CreateRoutineTool(BaseTool):
    name: str = "create_routine"
    description: str = (
        "Cria uma ROTINA AUTOMÁTICA da corretora (executa sozinha no horário agendado e entrega o "
        "resultado). Use quando o corretor pedir algo recorrente: 'todo dia às 8h...', 'a cada hora...'. "
        "Antes de criar, confirme com o corretor: o que fazer, quando, e para onde enviar."
    )
    args_schema: Type[BaseModel] = CreateRoutineInput
    company_id: str = ""
    user_id: str = ""
    supabase_client: object = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, company_id: str, user_id: str = "", supabase_client=None, **kwargs):
        super().__init__(**kwargs)
        self.company_id = str(company_id or "")
        self.user_id = str(user_id or "")
        self.supabase_client = supabase_client

    def _run(self, **kwargs) -> dict:
        from app.services.routine_engine import compute_next_run, describe_missing_dependency, validate_schedule

        # SPEC-019 A2 — pré-checagem INSTRUTIVA: nunca criar rotina que não
        # consegue entregar; explicar o passo a passo ao corretor.
        channel_check = str(kwargs.get("delivery_channel") or "whatsapp").strip().lower()
        if channel_check == "whatsapp":
            try:
                client = getattr(self.supabase_client, "client", self.supabase_client)
                res = client.table("integrations").select("id").eq("company_id", self.company_id).eq("is_active", True).limit(1).execute()
                missing = describe_missing_dependency("whatsapp", bool(res.data))
                if missing:
                    return {"content": missing}
            except Exception:  # noqa: BLE001 — checagem nunca bloqueia por erro técnico
                pass

        kind = str(kwargs.get("schedule_kind") or "").strip().lower()
        schedule = {"kind": kind}
        if kind == "daily":
            schedule["time"] = str(kwargs.get("time_of_day") or "").strip()
            raw_days = str(kwargs.get("weekdays") or "").strip()
            if raw_days:
                try:
                    schedule["weekdays"] = [int(d) for d in raw_days.split(",") if d.strip() != ""]
                except ValueError:
                    return {"content": "weekdays inválido — use números 0-6 separados por vírgula (0=segunda)."}
        elif kind == "interval":
            schedule["minutes"] = kwargs.get("interval_minutes")

        ok, reason = validate_schedule(schedule)
        if not ok:
            return {"content": f"Agenda inválida: {reason}. Corrija e chame de novo."}

        channel = str(kwargs.get("delivery_channel") or "whatsapp").strip().lower()
        delivery = {"channel": channel}
        if channel == "whatsapp":
            number = "".join(ch for ch in str(kwargs.get("delivery_number") or "") if ch.isdigit())
            if len(number) < 10:
                return {"content": "Para entrega no WhatsApp preciso do número completo com DDI (ex: 5547999998888). Pergunte ao corretor."}
            delivery["number"] = number

        instructions = str(kwargs.get("instructions") or "").strip()
        if len(instructions) < 10:
            return {"content": "Instruções muito curtas — descreva exatamente o que a rotina deve fazer em cada execução."}

        next_run = compute_next_run(schedule, "America/Sao_Paulo")
        record = {
            "company_id": self.company_id,
            "created_by": self.user_id or None,
            "name": str(kwargs.get("name") or "Rotina")[:120],
            "instructions": instructions,
            "schedule": schedule,
            "delivery": delivery,
            "timezone": "America/Sao_Paulo",
            "is_active": True,
            "next_run_at": next_run.isoformat(),
        }
        try:
            client = getattr(self.supabase_client, "client", self.supabase_client)
            res = client.table("routines").insert(record).execute()
            rid = res.data[0]["id"] if res.data else "?"
        except Exception as e:  # noqa: BLE001
            logger.error(f"[CreateRoutine] insert falhou: {type(e).__name__}")
            return {"content": f"Não consegui salvar a rotina ({type(e).__name__}). Avise o suporte se repetir."}

        from app.services.routine_engine import _tz

        local = next_run.astimezone(_tz("America/Sao_Paulo")).strftime("%d/%m às %H:%M")
        return {
            "content": (
                f"Rotina criada ✅ '{record['name']}' (id {str(rid)[:8]}). Primeira execução: {local} "
                f"(horário de Brasília). Entrega: {channel}. Confirme ao corretor em 1 frase natural."
            )
        }

    async def _arun(self, **kwargs) -> dict:
        return self._run(**kwargs)


class ListRoutinesInput(BaseModel):
    include_inactive: bool = Field(default=False, description="Incluir rotinas pausadas/desativadas")


class ListRoutinesTool(BaseTool):
    name: str = "list_routines"
    description: str = "Lista as rotinas automáticas da corretora (nome, agenda, próxima execução, status)."
    args_schema: Type[BaseModel] = ListRoutinesInput
    company_id: str = ""
    supabase_client: object = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, company_id: str, supabase_client=None, **kwargs):
        super().__init__(**kwargs)
        self.company_id = str(company_id or "")
        self.supabase_client = supabase_client

    def _run(self, include_inactive: bool = False) -> dict:
        try:
            client = getattr(self.supabase_client, "client", self.supabase_client)
            q = client.table("routines").select(
                "id, name, schedule, delivery, is_active, next_run_at, consecutive_failures"
            ).eq("company_id", self.company_id).order("created_at")
            if not include_inactive:
                q = q.eq("is_active", True)
            res = q.execute()
        except Exception as e:  # noqa: BLE001
            return {"content": f"Não consegui listar as rotinas ({type(e).__name__})."}
        rows = res.data or []
        if not rows:
            return {"content": "Nenhuma rotina cadastrada ainda. Ofereça criar uma."}
        lines = []
        for r in rows:
            sch = r.get("schedule") or {}
            when = f"diária às {sch.get('time')}" if sch.get("kind") == "daily" else f"a cada {sch.get('minutes')} min"
            status = "ativa" if r.get("is_active") else "pausada"
            lines.append(f"- {r.get('name')} · {when} · entrega {((r.get('delivery') or {}).get('channel'))} · {status} · próxima: {str(r.get('next_run_at') or '-')[:16]}")
        return {"content": "Rotinas da corretora:\n" + "\n".join(lines)}

    async def _arun(self, include_inactive: bool = False) -> dict:
        return self._run(include_inactive=include_inactive)


class ManageRoutineInput(BaseModel):
    routine_id: str = Field(description="Id da rotina (use list_routines para descobrir; prefixo de 8+ chars serve)")
    action: str = Field(description="'pause' | 'activate' | 'delete' | 'update'")
    name: Optional[str] = Field(default=None, description="update: novo nome")
    instructions: Optional[str] = Field(default=None, description="update: novas instruções COMPLETAS (substituem as atuais)")
    schedule_kind: Optional[str] = Field(default=None, description="update: 'daily' ou 'interval' (com os campos abaixo)")
    time_of_day: Optional[str] = Field(default=None, description="update daily: HH:MM Brasília")
    weekdays: Optional[str] = Field(default=None, description="update daily: dias 0-6 por vírgula (0=segunda)")
    interval_minutes: Optional[int] = Field(default=None, description="update interval: minutos (mín 5)")
    delivery_number: Optional[str] = Field(default=None, description="update: novo WhatsApp de destino com DDI")


class ManageRoutineTool(BaseTool):
    name: str = "manage_routine"
    description: str = (
        "Gerencia uma rotina existente: pausar, reativar, excluir ou ATUALIZAR (nome, instruções, "
        "horário, destino). Sempre confirme com o corretor antes de excluir."
    )
    args_schema: Type[BaseModel] = ManageRoutineInput
    company_id: str = ""
    supabase_client: object = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, company_id: str, supabase_client=None, **kwargs):
        super().__init__(**kwargs)
        self.company_id = str(company_id or "")
        self.supabase_client = supabase_client

    def _find(self, client, routine_id: str):
        res = client.table("routines").select("*").eq("company_id", self.company_id).execute()
        rid = str(routine_id or "").strip()
        for row in res.data or []:
            if str(row["id"]).startswith(rid) or rid == str(row["id"]):
                return row
        return None

    def _run(self, **kwargs) -> dict:
        from app.services.routine_engine import compute_next_run, validate_schedule

        client = getattr(self.supabase_client, "client", self.supabase_client)
        action = str(kwargs.get("action") or "").strip().lower()
        row = self._find(client, str(kwargs.get("routine_id") or ""))
        if not row:
            return {"content": "Rotina não encontrada. Use list_routines e confira o id."}

        try:
            if action == "delete":
                client.table("routines").delete().eq("id", row["id"]).execute()
                return {"content": f"Rotina '{row['name']}' excluída. Confirme ao corretor."}
            if action in ("pause", "activate"):
                patch = {"is_active": action == "activate"}
                if action == "activate":
                    patch["consecutive_failures"] = 0
                    patch["next_run_at"] = compute_next_run(row.get("schedule") or {}, row.get("timezone") or "America/Sao_Paulo").isoformat()
                client.table("routines").update(patch).eq("id", row["id"]).execute()
                return {"content": f"Rotina '{row['name']}' {'reativada' if action == 'activate' else 'pausada'}."}
            if action == "update":
                patch: dict = {}
                if kwargs.get("name"):
                    patch["name"] = str(kwargs["name"])[:120]
                if kwargs.get("instructions"):
                    patch["instructions"] = str(kwargs["instructions"])
                if kwargs.get("schedule_kind"):
                    kind = str(kwargs["schedule_kind"]).strip().lower()
                    schedule = {"kind": kind}
                    if kind == "daily":
                        schedule["time"] = str(kwargs.get("time_of_day") or "").strip()
                        raw_days = str(kwargs.get("weekdays") or "").strip()
                        if raw_days:
                            schedule["weekdays"] = [int(d) for d in raw_days.split(",") if d.strip() != ""]
                    elif kind == "interval":
                        schedule["minutes"] = kwargs.get("interval_minutes")
                    ok, reason = validate_schedule(schedule)
                    if not ok:
                        return {"content": f"Agenda inválida: {reason}."}
                    patch["schedule"] = schedule
                    patch["next_run_at"] = compute_next_run(schedule, row.get("timezone") or "America/Sao_Paulo").isoformat()
                if kwargs.get("delivery_number"):
                    number = "".join(ch for ch in str(kwargs["delivery_number"]) if ch.isdigit())
                    if len(number) < 10:
                        return {"content": "Número de destino inválido (use DDI+DDD+número)."}
                    delivery = dict(row.get("delivery") or {})
                    delivery["channel"] = "whatsapp"
                    delivery["number"] = number
                    patch["delivery"] = delivery
                if not patch:
                    return {"content": "Nada para atualizar — informe o que mudar (nome, instruções, horário ou destino)."}
                client.table("routines").update(patch).eq("id", row["id"]).execute()
                return {"content": f"Rotina '{row['name']}' atualizada ({', '.join(patch.keys())}). Confirme ao corretor."}
        except Exception as e:  # noqa: BLE001
            logger.error(f"[ManageRoutine] {action} falhou: {type(e).__name__}")
            return {"content": f"Não consegui concluir ({type(e).__name__}). Tente de novo."}
        return {"content": "Ação inválida: use pause, activate, delete ou update."}

    async def _arun(self, **kwargs) -> dict:
        return self._run(**kwargs)
