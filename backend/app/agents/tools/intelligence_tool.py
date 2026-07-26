"""O briefing pelo chat. SPEC-059 §25.8 e §34.

É aqui que a promessa do produto encosta na conversa:

    "O que precisa da minha atenção hoje?"

e o AutoBrokers responde com o que está no banco — não com um texto plausível.

Por que quatro ferramentas e não nove
-------------------------------------
A §27.3 nomeia nove operações. Todas existem e estão disponíveis pelas APIs.
No CHAT elas chegam agrupadas em quatro, porque o Tool Gateway tem teto de 12
ferramentas por execução (SPEC-053 §13.1) e o Core já carrega perto disso.
Anexar nove ferramentas novas degradaria a escolha do modelo em TODA conversa
— inclusive nas que nada têm a ver com briefing. Registrado em CHANGE-ADDENDA.

O contrato com o modelo
-----------------------
Estas ferramentas devolvem **texto já pronto**, com os números formatados a
partir do que está gravado. O modelo apresenta; não recalcula, não arredonda,
não completa lacuna. Se o dado não existe, a ferramenta diz que não existe —
e essa frase é para ser repassada, não reescrita.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Briefing
# ---------------------------------------------------------------------------


class _BriefingIn(BaseModel):
    tipo: str = Field(
        default="hoje",
        description="'hoje' para as prioridades do dia, 'semana' para o "
                    "executivo semanal. Use 'hoje' quando estiver em dúvida.")


class BriefingTool(BaseTool):
    name: str = "briefing_da_corretora"
    description: str = (
        "Use SEMPRE que o corretor perguntar o que precisa da atenção dele, o que "
        "aconteceu, como está a operação, se há pendências, ou pedir um resumo do "
        "dia ou da semana. Devolve os pontos reais com evidência, já priorizados. "
        "Não invente nada além do que vier aqui: se a ferramenta disser que não há "
        "dado, diga isso ao corretor."
    )
    args_schema: Type[BaseModel] = _BriefingIn

    company_id: Optional[str] = None
    supabase: Any = None
    user_id: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True

    def _run(self, **_: Any) -> str:
        return "Ferramenta assíncrona; o runtime deve chamá-la por `arun`."

    async def _arun(self, tipo: str = "hoje", **_: Any) -> str:
        import asyncio

        if not self.company_id or self.supabase is None:
            return "Não consegui identificar a corretora."

        from ...services.intelligence.briefing_service import BriefingService

        alvo = "weekly_executive" if str(tipo).lower().startswith("sem") else "daily_operational"
        servico = BriefingService(self.supabase)

        def _obter() -> dict:
            atual = servico.atual(self.company_id, briefing_type=alvo)
            if atual and atual.get("payload"):
                return {"payload": atual["payload"], "novo": False}
            # Sem briefing publicado para o período, gera SOB DEMANDA (§16.4).
            # É o que impede a resposta "ainda não gerei" — o corretor
            # perguntou agora, e o dado para responder já existe.
            r = servico.gerar(self.company_id, briefing_type=alvo)
            return {"payload": (r.get("spec") or {}), "novo": True}

        try:
            r = await asyncio.to_thread(_obter)
        except Exception as exc:  # noqa: BLE001
            logger.exception("[Intelligence] briefing falhou")
            return (f"Não consegui montar o briefing agora ({type(exc).__name__}). "
                    "Diga isso ao corretor sem inventar o conteúdo.")

        return formatar_briefing(r["payload"])


def formatar_briefing(spec: dict) -> str:
    """Briefing Spec → texto para o chat. Puro, e sem inventar número."""
    if not spec:
        return ("Ainda não há briefing para este período. Diga isso ao corretor "
                "em vez de descrever o que ele provavelmente contém.")

    linhas = [f"**{spec.get('headline') or 'Briefing'}**",
              str(spec.get("executive_summary") or "")]

    for secao in spec.get("sections") or []:
        itens = secao.get("items") or []
        if not itens:
            continue  # §16.1 — seção vazia não vira texto
        linhas.append("")
        linhas.append(f"*{secao.get('title')}*")
        for item in itens[:6]:
            marca = "•"
            if float(item.get("priority_score") or 0) >= 85:
                marca = "🔴"
            texto = f"{marca} {item.get('headline')}"
            if item.get("summary"):
                texto += f" — {item['summary']}"
            linhas.append(texto)
            if item.get("evidence_summary"):
                linhas.append(f"   _fato:_ {item['evidence_summary']}")
            if item.get("action_label"):
                rid = (item.get("action_payload") or {}).get("recommendation_id")
                linhas.append(f"   _posso:_ {item['action_label']}"
                              + (f" (id {rid})" if rid else ""))

    faltando = spec.get("missing_data") or []
    if faltando:
        linhas.append("")
        linhas.append("*O que ainda não dá para afirmar*")
        for f in faltando[:3]:
            linhas.append(f"• {f}")

    linhas.append("")
    linhas.append("[Apresente isto com suas palavras, mantendo os números "
                  "exatamente como estão. Não acrescente conclusões que não "
                  "estejam acima.]")
    return "\n".join(l for l in linhas if l is not None)


# ---------------------------------------------------------------------------
# Prioridades e explicação
# ---------------------------------------------------------------------------


class _FindingsIn(BaseModel):
    explicar_id: Optional[str] = Field(
        default=None,
        description="Id do ponto de atenção quando o corretor perguntar por que "
                    "aquilo apareceu. Vazio lista tudo que está ativo.")


class PrioridadesTool(BaseTool):
    name: str = "prioridades_da_corretora"
    description: str = (
        "Lista os pontos de atenção ativos da corretora, ou explica a origem de um "
        "deles quando o corretor perguntar 'por que você está me mostrando isso'. "
        "A explicação traz o fato observado, a fonte e o período."
    )
    args_schema: Type[BaseModel] = _FindingsIn

    company_id: Optional[str] = None
    supabase: Any = None
    user_id: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True

    def _run(self, **_: Any) -> str:
        return "Ferramenta assíncrona; o runtime deve chamá-la por `arun`."

    async def _arun(self, explicar_id: Optional[str] = None, **_: Any) -> str:
        import asyncio

        if not self.company_id or self.supabase is None:
            return "Não consegui identificar a corretora."

        from ...services.intelligence.finding_engine import FindingEngine
        from ...services.intelligence.recommendation_service import RecommendationService

        def _buscar() -> dict:
            engine = FindingEngine(self.supabase)
            findings = engine.ativos(self.company_id, limite=20)
            recs = RecommendationService(self.supabase).elegiveis(
                self.company_id, limite=20)
            return {"findings": findings, "recs": recs}

        try:
            dados = await asyncio.to_thread(_buscar)
        except Exception as exc:  # noqa: BLE001
            return f"Não consegui consultar as prioridades agora ({type(exc).__name__})."

        findings = dados["findings"]
        if explicar_id:
            alvo = next((f for f in findings if str(f.get("id")) == str(explicar_id)), None)
            if not alvo:
                return ("Não encontrei esse ponto de atenção. Ele pode ter sido "
                        "resolvido ou expirado.")
            return explicar(alvo)

        if not findings:
            return ("Nenhum ponto de atenção ativo no momento. Diga isso — não "
                    "procure um problema para relatar.")

        linhas = ["Pontos ativos, do mais para o menos prioritário:"]
        for f in findings[:8]:
            linhas.append(
                f"• [{f.get('id')}] {f.get('title')} — {f.get('summary')} "
                f"(prioridade {float(f.get('priority_score') or 0):.0f})")
        rec_por_finding = {str(r.get("finding_id")): r for r in dados["recs"]
                           if r.get("finding_id")}
        if rec_por_finding:
            linhas.append("")
            linhas.append("Com ação disponível:")
            for fid, r in list(rec_por_finding.items())[:5]:
                linhas.append(f"• [{r.get('id')}] {r.get('title')}")
        return "\n".join(linhas)


def explicar(finding: dict) -> str:
    """§15.5 e §34.4 — de onde veio, com fato e leitura separados."""
    partes = [f"**{finding.get('title')}**", ""]
    if finding.get("fact_statement"):
        partes.append(f"**O fato:** {finding['fact_statement']}")
    partes.append(f"**Por que agora:** {finding.get('why_now')}")
    if finding.get("inference_statement"):
        partes.append(f"**Leitura (não confirmada):** {finding['inference_statement']}")
    if finding.get("missing_data"):
        partes.append(f"**O que ainda não se sabe:** {finding['missing_data']}")
    if finding.get("next_step"):
        partes.append(f"**Próximo passo:** {finding['next_step']}")

    explicacao = (finding.get("metadata") or {}).get("explicacao") or {}
    if explicacao.get("dimensoes"):
        d = explicacao["dimensoes"]
        partes.append("")
        partes.append(
            f"_Prioridade {explicacao.get('score')}: impacto {d.get('impacto'):.0f}, "
            f"urgência {d.get('urgencia'):.0f}, confiança {d.get('confianca'):.0f}, "
            f"quanto dá para agir {d.get('actionability'):.0f}._")
    partes.append("")
    partes.append("[Explique com suas palavras, mas NÃO transforme a leitura em "
                  "fato nem preencha o que está faltando.]")
    return "\n".join(partes)


# ---------------------------------------------------------------------------
# Responder
# ---------------------------------------------------------------------------


class _ResponderIn(BaseModel):
    recommendation_id: str = Field(description="Id da recomendação, como aparece na lista")
    acao: str = Field(
        description="accept (o corretor quer que eu resolva), snooze (me lembre "
                    "depois), dismiss (dispensar), not_relevant (não é útil), "
                    "already_solved (já resolvi), wrong_data (o número está errado)")
    comentario: Optional[str] = Field(
        default=None, description="O que o corretor falou, nas palavras dele")


class ResponderRecomendacaoTool(BaseTool):
    name: str = "responder_recomendacao"
    description: str = (
        "Registra a resposta do corretor a uma recomendação: aceitar, adiar, "
        "dispensar, marcar como já resolvido ou avisar que o dado está errado. "
        "Aceitar abre o trabalho pelo caminho governado — NÃO executa ação externa "
        "por conta própria, e ação sensível continua passando por aprovação."
    )
    args_schema: Type[BaseModel] = _ResponderIn

    company_id: Optional[str] = None
    supabase: Any = None
    user_id: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True

    def _run(self, **_: Any) -> str:
        return "Ferramenta assíncrona; o runtime deve chamá-la por `arun`."

    async def _arun(self, recommendation_id: str, acao: str,
                    comentario: Optional[str] = None, **_: Any) -> str:
        import asyncio

        if not self.company_id or self.supabase is None:
            return "Não consegui identificar a corretora."

        from ...services.intelligence.execution import executar_recomendacao
        from ...services.intelligence.feedback_service import FeedbackService

        def _registrar() -> dict:
            return FeedbackService(self.supabase).registrar(
                company_id=self.company_id, recommendation_id=recommendation_id,
                acao=acao, user_id=self.user_id, comentario=comentario)

        try:
            r = await asyncio.to_thread(_registrar)
        except Exception as exc:  # noqa: BLE001
            return f"Não consegui registrar a resposta ({type(exc).__name__})."

        if not r.get("ok"):
            return str(r.get("erro") or "Não consegui registrar a resposta.")

        if not r.get("executar"):
            return r.get("mensagem") or "Anotado."

        def _executar() -> dict:
            return executar_recomendacao(
                self.supabase, company_id=self.company_id,
                recommendation_id=recommendation_id, user_id=self.user_id)

        try:
            saida = await asyncio.to_thread(_executar)
        except Exception as exc:  # noqa: BLE001
            logger.exception("[Intelligence] execução falhou")
            return ("Anotei o aceite, mas não consegui abrir o trabalho agora "
                    f"({type(exc).__name__}). Ele não foi perdido — está registrado.")

        return saida.get("mensagem") or "Combinado, vou cuidar disso."


# ---------------------------------------------------------------------------
# Preferências
# ---------------------------------------------------------------------------


class _PreferenciasIn(BaseModel):
    horario: Optional[str] = Field(default=None, description="HH:MM do briefing diário")
    pausar: Optional[bool] = Field(default=None, description="true para pausar o briefing")
    detalhe: Optional[str] = Field(
        default=None, description="minimal, standard ou detailed")
    max_avisos_por_dia: Optional[int] = Field(default=None)


class PreferenciasTool(BaseTool):
    name: str = "preferencias_de_briefing"
    description: str = (
        "Ajusta como e quando o corretor recebe o briefing: horário, nível de "
        "detalhe, limite de avisos por dia, ou pausar. Use quando ele disser que "
        "está recebendo demais, de menos, ou na hora errada."
    )
    args_schema: Type[BaseModel] = _PreferenciasIn

    company_id: Optional[str] = None
    supabase: Any = None
    user_id: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True

    def _run(self, **_: Any) -> str:
        return "Ferramenta assíncrona; o runtime deve chamá-la por `arun`."

    async def _arun(self, horario: Optional[str] = None,
                    pausar: Optional[bool] = None, detalhe: Optional[str] = None,
                    max_avisos_por_dia: Optional[int] = None, **_: Any) -> str:
        import asyncio

        if not self.company_id or self.supabase is None:
            return "Não consegui identificar a corretora."

        campos: dict = {}
        if horario:
            campos["schedule_spec"] = {"time": horario}
        if pausar is not None:
            campos["is_active"] = not pausar
        if detalhe in ("minimal", "standard", "detailed"):
            campos["detail_level"] = detalhe
        if max_avisos_por_dia is not None:
            campos["max_pushes_per_day"] = max(0, min(20, int(max_avisos_por_dia)))
        if not campos:
            return "Não entendi o que mudar. Pergunte o horário ou o nível de detalhe."

        from ...services.intelligence.briefing_service import BriefingService

        def _salvar():
            return BriefingService(self.supabase).atualizar_preferencias(
                self.company_id, cadencia="daily", user_id=None, campos=campos)

        try:
            r = await asyncio.to_thread(_salvar)
        except Exception as exc:  # noqa: BLE001
            return f"Não consegui salvar a preferência ({type(exc).__name__})."
        if not r:
            return "Não consegui salvar a preferência."

        mudancas = []
        if horario:
            mudancas.append(f"briefing às {horario}")
        if pausar is not None:
            mudancas.append("briefing pausado" if pausar else "briefing reativado")
        if detalhe:
            mudancas.append(f"nível de detalhe {detalhe}")
        if max_avisos_por_dia is not None:
            mudancas.append(f"no máximo {max_avisos_por_dia} avisos por dia")
        return "Pronto: " + ", ".join(mudancas) + "."


# ---------------------------------------------------------------------------


def ferramentas_de_inteligencia(*, company_id: Optional[str], supabase: Any,
                                user_id: Optional[str] = None) -> list[BaseTool]:
    if not company_id or supabase is None:
        return []
    comum = {"company_id": company_id, "supabase": supabase, "user_id": user_id}
    return [
        BriefingTool(**comum),
        PrioridadesTool(**comum),
        ResponderRecomendacaoTool(**comum),
        PreferenciasTool(**comum),
    ]
