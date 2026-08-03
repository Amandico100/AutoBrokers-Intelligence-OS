"""Devolver para humano — e o humano precisa FICAR SABENDO.

O que esta ferramenta fazia, medido em 02/08/2026
-------------------------------------------------
Um `UPDATE conversations SET status='HUMAN_REQUESTED'`. Só isso.

    sem envio         nenhum import de WhatsApp, e-mail ou push
    sem contexto      o humano teria de reconstruir a conversa sozinho
    sem company_id    `.eq("session_id", …)` — viola CLAUDE.md §7
    e mentia          "Um atendente foi solicitado." era devolvido TAMBÉM
                      quando o UPDATE não achava a conversa E quando
                      estourava exceção

A última é a pior. O segurado ouvia que um humano viria, o humano nunca soube,
e ninguém no sistema ficou sabendo que a promessa não foi cumprida. **Falha
declarando sucesso é pior que falha.**

E havia um segundo defeito, na direção oposta: o prompt do atendimento MANDA
chamar humano em sinistro e em risco grave — mas a ferramenta só era anexada
se `tools_config.human_handoff.enabled` fosse verdadeiro, e 📊 `tools_config`
estava vazio nos agentes de atendimento. **O prompt prometia o que a ferramenta
não tinha como cumprir.**

O que ela faz agora
-------------------
1. Exige `company_id` — sem ele não escreve nada e diz por quê.
2. Filtra a conversa por `company_id` **e** `session_id`.
3. Resolve o destino pelo resolvedor canônico, que **recusa destino
   compartilhado entre corretoras** (o dossiê leva CPF do segurado).
4. Monta um dossiê com as últimas mensagens e envia.
5. **Devolve ao segurado o que de fato aconteceu.** Se ninguém foi avisado, a
   resposta não promete atendente. Nunca inventa uma transferência que não houve.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Quantas mensagens vão no dossiê. Suficiente para o humano entrar sabendo,
# curto o bastante para caber num WhatsApp sem virar parede de texto.
_MSGS_NO_DOSSIE = 12


class HumanHandoffInput(BaseModel):
    """Input schema para a HumanHandoffTool."""

    reason: Optional[str] = Field(
        default=None,
        description="Motivo da transferência. Exemplo: 'sinistro — exige humano', "
        "'risco grave', 'cliente pediu pessoa', 'não há corredor para esta seguradora'.",
    )


class HumanHandoffTool(BaseTool):
    """
    Ferramenta para solicitar transferência para atendimento humano.

    Use esta ferramenta quando:
    - For SINISTRO (sempre — sinistro não se resolve sozinho)
    - Não existir corredor para acionar aquela seguradora/serviço
    - Houver risco grave à pessoa (fogo, fumaça, choque, água com energia)
    - O usuário pedir explicitamente para falar com uma pessoa
    - Você travar: duas tentativas sem avançar

    A ferramenta avisa o suporte da corretora com um resumo do caso.
    """

    name: str = "request_human_agent"
    description: str = """
    Transfere a conversa para um atendente humano da corretora e avisa o suporte
    com um resumo do caso. Use em SINISTRO (sempre), quando não houver corredor
    para acionar a seguradora, em risco grave, quando o cliente pedir pessoa, ou
    quando você travar. Informe o motivo.
    """
    args_schema: Type[BaseModel] = HumanHandoffInput

    supabase_client: object = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, supabase_client, **kwargs):
        super().__init__(**kwargs)
        self.supabase_client = supabase_client
        logger.info("[HumanHandoff] Tool inicializada")

    # ------------------------------------------------------------------ #
    # o dossiê
    # ------------------------------------------------------------------ #
    def _montar_dossie(self, conversa: Dict[str, Any], motivo: str) -> str:
        """O que o humano precisa saber para entrar sem reperguntar.

        Quem recebe isto está no meio do dia dele. Se o dossiê não disser quem
        é, o que a pessoa quer e o que já foi perguntado, ele recomeça do zero —
        e o segurado repete tudo. Repetir é exatamente o que o produto existe
        para evitar.
        """
        linhas = [
            "🔔 *ATENDIMENTO PRECISA DE VOCÊ*",
            "",
            f"*Cliente:* {conversa.get('user_name') or 'não identificado'}",
            f"*WhatsApp:* {conversa.get('user_phone') or '—'}",
            f"*Motivo:* {motivo or 'não informado pelo agente'}",
        ]
        try:
            msgs = (self.supabase_client.table("messages")
                    .select("role, content, created_at")
                    .eq("conversation_id", conversa["id"])
                    .order("created_at", desc=True)
                    .limit(_MSGS_NO_DOSSIE).execute().data or [])
            if msgs:
                linhas += ["", "*Últimas mensagens:*"]
                for m in reversed(msgs):
                    quem = "Cliente" if str(m.get("role")) == "user" else "Agente"
                    texto = str(m.get("content") or "").strip().replace("\n", " ")
                    linhas.append(f"• _{quem}:_ {texto[:180]}")
        except Exception as exc:  # noqa: BLE001
            # Dossiê sem histórico continua melhor que silêncio — mas o humano
            # precisa saber que está entrando às cegas.
            logger.warning("[HumanHandoff] histórico indisponível (%s)", type(exc).__name__)
            linhas += ["", "_(não foi possível carregar o histórico desta conversa)_"]
        linhas += ["", "Abra em *Atendimentos → Conversas* para assumir."]
        return "\n".join(linhas)

    async def _avisar_suporte(self, company_id: str, conversa: Dict[str, Any],
                              motivo: str) -> Dict[str, Any]:
        """Envia o dossiê. Devolve o que aconteceu — sem arredondar."""
        from app.services.dispatch_router import resolver_destino_de_suporte

        alvo = await resolver_destino_de_suporte(company_id)
        if alvo.get("recusa"):
            return {"avisado": False, "motivo": alvo["recusa"]}
        destino = alvo.get("destino") or ""
        if not destino:
            return {"avisado": False,
                    "motivo": "a corretora não tem destino de suporte humano configurado"}

        try:
            from app.services.integration_service import get_integration_service
            from app.services.whatsapp_service import get_whatsapp_service

            integ = get_integration_service(self.supabase_client).get_whatsapp_integration(company_id)
            if not integ:
                return {"avisado": False,
                        "motivo": "a corretora não tem canal de WhatsApp conectado para avisar"}
            get_whatsapp_service().send_message(destino, self._montar_dossie(conversa, motivo), integ)
            logger.info("[HumanHandoff] dossiê enviado | empresa=%s | fonte=%s",
                        company_id, alvo.get("fonte"))
            return {"avisado": True, "motivo": ""}
        except Exception as exc:  # noqa: BLE001
            logger.error("[HumanHandoff] falha ao avisar o suporte (%s)", type(exc).__name__)
            return {"avisado": False, "motivo": f"falha no envio ({type(exc).__name__})"}

    # ------------------------------------------------------------------ #
    # execução
    # ------------------------------------------------------------------ #
    async def _arun(self, reason: Optional[str] = None, session_id: Optional[str] = None,
                    company_id: Optional[str] = None, **kwargs) -> str:
        motivo = str(reason or "").strip()
        logger.info("[HumanHandoff] 🔔 pedido | empresa=%s | sessao=%s | motivo=%s",
                    company_id, session_id, motivo)

        if not session_id or not company_id:
            # Antes isto devolvia "Erro interno" e seguia. Agora é explícito:
            # não dá para transferir uma conversa que não sabemos qual é.
            logger.error("[HumanHandoff] faltou %s",
                         "session_id" if not session_id else "company_id")
            return ("Não consegui transferir esta conversa agora. "
                    "Vou continuar te ajudando por aqui — me diga o que precisa.")

        if not self.supabase_client:
            logger.error("[HumanHandoff] supabase_client não configurado")
            return ("Não consegui transferir esta conversa agora. "
                    "Vou continuar te ajudando por aqui.")

        # 1) marcar a conversa — SEMPRE com company_id (CLAUDE.md §7)
        conversa: Optional[Dict[str, Any]] = None
        try:
            dados: Dict[str, Any] = {"status": "HUMAN_REQUESTED"}
            if motivo:
                dados["human_handoff_reason"] = motivo
            res = (self.supabase_client.table("conversations")
                   .update(dados)
                   .eq("company_id", company_id)
                   .eq("session_id", session_id)
                   .execute())
            if res.data:
                conversa = res.data[0]
        except Exception as exc:  # noqa: BLE001
            logger.error("[HumanHandoff] falha ao marcar a conversa (%s)", type(exc).__name__)

        if not conversa:
            # A conversa não foi marcada. Antes, esta linha devolvia
            # "Um atendente foi solicitado." — promessa sobre algo que não
            # aconteceu, e ninguém no sistema ficava sabendo.
            logger.error("[HumanHandoff] ❌ conversa não encontrada/atualizada | "
                         "empresa=%s | sessao=%s — NADA foi prometido ao cliente",
                         company_id, session_id)
            return ("Não consegui abrir a transferência agora. "
                    "Me passe seu telefone e o melhor horário que eu registro o pedido "
                    "para a equipe retornar.")

        # 2) avisar o humano de verdade
        aviso = await self._avisar_suporte(company_id, conversa, motivo)

        if aviso["avisado"]:
            return ("Já chamei um atendente da equipe e passei o resumo do seu caso — "
                    "ele entra aqui na conversa em instantes. Pode aguardar por aqui.")

        # Marcou mas não avisou: a conversa aparece na Fila do painel, então
        # alguém PODE ver — só não foi empurrado. A resposta diz a verdade sem
        # jogar o problema interno no colo do segurado.
        logger.error("[HumanHandoff] ⚠️ conversa marcada mas SUPORTE NÃO AVISADO | "
                     "empresa=%s | motivo=%s", company_id, aviso["motivo"])
        return ("Registrei seu pedido de atendimento humano e ele já está na fila da equipe. "
                "Se for urgente, me diga — enquanto isso eu sigo aqui com você.")

    def _run(self, reason: Optional[str] = None, session_id: Optional[str] = None,
             company_id: Optional[str] = None, **kwargs) -> str:
        """Caminho síncrono desativado.

        Avisar o suporte exige I/O assíncrono (resolver destino + enviar). Uma
        versão síncrona que só marcasse a conversa seria exatamente o defeito
        que esta correção desfez: parece que funcionou, e ninguém é avisado.
        """
        raise RuntimeError(
            "HumanHandoffTool exige execução assíncrona (_arun): o aviso ao "
            "suporte humano faz I/O. O tool_node já força _arun."
        )
