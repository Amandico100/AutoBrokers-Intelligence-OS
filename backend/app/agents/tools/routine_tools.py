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
        from app.services.routine_engine import compute_next_run, validate_schedule

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
