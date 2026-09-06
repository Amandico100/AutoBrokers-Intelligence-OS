# -*- coding: utf-8 -*-
"""O ACOMPANHAMENTO — a PORTA ÚNICA por onde o produto fala com o cliente
fora do turno dele. SPEC-097.1 R10/U5.

🔴 **UMA PORTA SÓ, e é o ponto inteiro deste arquivo.** Dois gatilhos falam
com o segurado sem ele ter perguntado agora:

    (a) o corredor mudou o estado/previsão  → `registrar_checkpoint` (U5.1)
    (b) a espera venceu no vigia de 10 min  → `varrer_esperas_vencidas` (U5.2)

Se cada um tivesse a sua saída, haveria **dois** lugares para esquecer o
desligador — e desligador esquecido não é bug de teste: é mensagem no WhatsApp
de um segurado de verdade, com todos os agentes desligados (R7).

⛔ **NENHUM MOTOR NOVO (§5).** Não há job, cron, fila nem laço aqui: os dois
gatilhos já existem e já rodam. Este arquivo é só a porta que eles atravessam.

⚠️ **Os QUATRO desligadores moram aqui, e só aqui:**

    conversa assumida por gente     `pausar_ia` (SPEC-097 U2.3)
    agente da corretora desligado   `companies.agent_enabled`
    nenhum agente de atendimento    `agents.is_active` (📊 4 agentes, todos
                                    `false` em 05/09/2026)
    acompanhamento desligado        `companies.acionamento_profile.acompanhamento`
                                    (ausente = LIGADO — U5.3)

📊 Em produção, hoje, os quatro conspiram para o mesmo desfecho: **nada sai**.
A 097.1 deixa PRONTO e DESLIGADO, e é o `suprimida_por` gravado que prova que
a novidade existiu e foi calada de propósito.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

#: O tipo de evento com que a supressão fica CONTÁVEL.
#: ⚠️ Suprimir em silêncio seria pior que enviar: ninguém saberia que o produto
#: teve algo a dizer (a lição do `resolvido_em` NULL em 728/728).
EVENTO_NOVIDADE = "atendimento.novidade_ao_cliente"

#: A mensagem honesta do vigia (R3/U5.2). ⛔ Sem data, sem previsão, sem prazo.
MENSAGEM_SEM_NOVIDADE = (
    "Passando para dizer que ainda não houve novidade no seu caso. "
    "A corretora está cobrando e, assim que tiver resposta, eu te aviso aqui."
)


def _perfil(companhia: Any) -> Dict[str, Any]:
    perfil = (companhia or {}).get("acionamento_profile")
    return perfil if isinstance(perfil, dict) else {}


def acompanhamento_ligado(companhia: Any) -> bool:
    """`acionamento_profile.acompanhamento` — **ausente = LIGADO** (U5.3).

    ⚠️ O padrão é LIGADO porque a fase nasce ligada (R10). Uma corretora que
    não quer o acompanhamento escreve `false`; nenhuma corretora precisa
    escrever `true` para ter o que a SPEC promete.
    """
    valor = _perfil(companhia).get("acompanhamento")
    return True if valor is None else bool(valor)


async def pode_falar_com_o_cliente(db, company_id: str,
                                   conversa: Any) -> Tuple[bool, str]:
    """A porta. Devolve `(pode, porque_nao)` — **e nunca levanta**.

    🔴 A ordem das perguntas é a ordem do DANO: a conversa assumida vem
    primeiro porque falar por cima de uma atendente que já está no teclado é
    o único erro desta lista que o segurado VÊ (R7).
    """
    try:
        from app.services.o_fim_do_atendimento import pausar_ia

        if pausar_ia(conversa or {}):
            return False, "conversa_assumida"
    except Exception as erro:  # noqa: BLE001
        # ⚠️ Não saber se alguém assumiu é razão para CALAR, não para falar.
        logger.warning("[ACOMPANHAMENTO] `pausar_ia` indisponível (%s) — calando",
                       type(erro).__name__)
        return False, "estado_da_conversa_desconhecido"

    empresa = str(company_id or "").strip()
    if not empresa:
        return False, "sem_corretora"

    companhia: Dict[str, Any] = {}
    try:
        achado = await (db.client.table("companies")
                        .select("id, agent_enabled, acionamento_profile")
                        .eq("id", empresa).limit(1).execute())
        companhia = (achado.data or [{}])[0] or {}
    except Exception as erro:  # noqa: BLE001
        logger.warning("[ACOMPANHAMENTO] corretora não lida (%s) — calando",
                       type(erro).__name__)
        return False, "corretora_nao_lida"

    if companhia.get("agent_enabled") is False:
        return False, "agente_desligado_na_corretora"
    if not acompanhamento_ligado(companhia):
        return False, "acompanhamento_desligado"

    try:
        agentes = await (db.client.table("agents")
                         .select("id, is_active, agent_role")
                         .eq("company_id", empresa)
                         .eq("agent_role", "attendance").execute())
        linhas = agentes.data or []
    except Exception as erro:  # noqa: BLE001
        logger.warning("[ACOMPANHAMENTO] agentes não lidos (%s) — calando",
                       type(erro).__name__)
        return False, "agentes_nao_lidos"

    if not any(bool(a.get("is_active")) for a in linhas):
        # 📊 05/09/2026: é ESTE ramo que roda em produção — 4 agentes
        #    `attendance`, todos `is_active=false`.
        return False, "agente_de_atendimento_desligado"
    return True, ""


async def _conversa_da_novidade(db, company_id: str,
                                conversation_id: str) -> Optional[Dict[str, Any]]:
    try:
        achado = await (db.client.table("conversations")
                        .select("id, company_id, session_id, status, claimed_by, "
                                "claimed_by_name, user_phone, resolvido_em")
                        .eq("company_id", str(company_id))       # 🔴 §7
                        .eq("id", str(conversation_id)).limit(1).execute())
        linhas = achado.data or []
        return linhas[0] if linhas else None
    except Exception as erro:  # noqa: BLE001
        logger.warning("[ACOMPANHAMENTO] conversa não lida (%s)", type(erro).__name__)
        return None


async def _run_da_conversa(db, company_id: str, conversation_id: str) -> Optional[str]:
    """O `work_run_id` da espera ativa — para o evento não nascer órfão."""
    try:
        achado = await (db.client.table("work_waits")
                        .select("id, work_run_id, scope")
                        .eq("company_id", str(company_id))       # 🔴 §7
                        .eq("conversation_id", str(conversation_id))
                        .eq("status", "ativo").limit(1).execute())
        for linha in (achado.data or []):
            if linha.get("work_run_id"):
                return str(linha["work_run_id"])
    except Exception as erro:  # noqa: BLE001
        logger.warning("[ACOMPANHAMENTO] espera não lida (%s)", type(erro).__name__)
    return None


async def _registrar(db, *, company_id: str, work_run_id: Optional[str],
                     gatilho: str, entregue: bool, suprimida_por: str) -> None:
    """A novidade fica CONTÁVEL — entregue ou calada."""
    try:
        await db.client.table("work_events").insert({
            "company_id": str(company_id),                      # 🔴 §7
            "work_run_id": work_run_id or None,
            "event_type": EVENTO_NOVIDADE,
            "actor_type": "system",
            "severity": "info" if entregue else "warning",
            "message_human": ("O acompanhamento avisou o cliente."
                              if entregue else
                              "O acompanhamento tinha uma novidade e ela foi "
                              "suprimida antes de sair."),
            # ⛔ Sem o TEXTO e sem telefone: quem guarda conteúdo é o Espelho.
            "payload_redacted": {"gatilho": str(gatilho or ""),
                                 "entregue": bool(entregue),
                                 "suprimida_por": str(suprimida_por or "")},
        }).execute()
    except Exception as erro:  # noqa: BLE001
        logger.warning("[ACOMPANHAMENTO] novidade não registrada (%s)",
                       type(erro).__name__)


async def entregar_novidade(db, *, company_id: str, conversation_id: str,
                            texto: str, gatilho: str = "corredor") -> Dict[str, Any]:
    """Gera a novidade e a entrega — **ou a cala e diz por quê**.

    Devolve `{"gerada", "entregue", "suprimida_por", "texto", "enviado"}`.

    ⛔ **Nunca levanta.** Chamada de dentro do checkpoint do corredor e de
    dentro do vigia: uma exceção aqui custaria o acionamento ou a varredura
    inteira, que valem mais que uma mensagem de cortesia.

    ⚠️ `entregue` é a decisão da PORTA cumprida até o canal — o contrato de
    `WhatsappService.send_message` é **levantar** em falha, e é por isso que
    "não levantou" é o critério. O booleano do canal viaja em `enviado`.
    """
    resposta: Dict[str, Any] = {"gerada": True, "entregue": False,
                                "suprimida_por": "", "texto": str(texto or ""),
                                "enviado": False}
    if not str(texto or "").strip():
        # Uma novidade vazia não é novidade. ⛔ E não vira mensagem em branco.
        resposta["gerada"] = False
        resposta["suprimida_por"] = "texto_vazio"
        return resposta

    conversa = await _conversa_da_novidade(db, company_id, conversation_id)
    run_id = await _run_da_conversa(db, company_id, conversation_id)

    if conversa is None:
        resposta["suprimida_por"] = "conversa_nao_encontrada"
        await _registrar(db, company_id=company_id, work_run_id=run_id,
                         gatilho=gatilho, entregue=False,
                         suprimida_por=resposta["suprimida_por"])
        return resposta

    if conversa.get("resolvido_em"):
        # ⛔ O atendimento já terminou. Falar depois do desfecho reabre um caso
        #    que a corretora fechou.
        resposta["suprimida_por"] = "atendimento_ja_encerrado"
        await _registrar(db, company_id=company_id, work_run_id=run_id,
                         gatilho=gatilho, entregue=False,
                         suprimida_por=resposta["suprimida_por"])
        return resposta

    pode, porque = await pode_falar_com_o_cliente(db, company_id, conversa)
    if not pode:
        resposta["suprimida_por"] = porque or "desligado"
        await _registrar(db, company_id=company_id, work_run_id=run_id,
                         gatilho=gatilho, entregue=False,
                         suprimida_por=resposta["suprimida_por"])
        logger.info("[ACOMPANHAMENTO] novidade GERADA e SUPRIMIDA (%s) gatilho=%s",
                    resposta["suprimida_por"], gatilho)
        return resposta

    telefone = str(conversa.get("user_phone") or "").strip()
    if not telefone:
        resposta["suprimida_por"] = "conversa_sem_telefone"
        await _registrar(db, company_id=company_id, work_run_id=run_id,
                         gatilho=gatilho, entregue=False,
                         suprimida_por=resposta["suprimida_por"])
        return resposta

    integracao = None
    try:
        # ⚠️ O leitor de integração é SÍNCRONO — o mesmo seam que o corredor
        #    usa (`dispatch_router:194`). Passar o cliente assíncrono aqui
        #    devolvia uma corrotina onde o código espera `.data`, e o erro só
        #    aparecia no log.
        from app.core.database import get_supabase_client
        from app.services.integration_service import get_integration_service

        integracao = get_integration_service(
            get_supabase_client().client).get_whatsapp_integration(str(company_id))
    except Exception as erro:  # noqa: BLE001
        # Sem integração o canal recusa, e a recusa aparece em `entregue=False`
        # — nunca em silêncio.
        logger.warning("[ACOMPANHAMENTO] integração não lida (%s)", type(erro).__name__)

    try:
        from app.services.whatsapp_service import get_whatsapp_service

        enviado = get_whatsapp_service().send_message(telefone, str(texto), integracao)
        resposta["entregue"] = True
        resposta["enviado"] = bool(enviado)
    except Exception as erro:  # noqa: BLE001
        logger.error("[ACOMPANHAMENTO] o canal recusou a novidade (%s) gatilho=%s",
                     type(erro).__name__, gatilho)
        resposta["suprimida_por"] = "canal_indisponivel"

    await _registrar(db, company_id=company_id, work_run_id=run_id,
                     gatilho=gatilho, entregue=bool(resposta["entregue"]),
                     suprimida_por=str(resposta["suprimida_por"]))
    return resposta


__all__ = ["EVENTO_NOVIDADE", "MENSAGEM_SEM_NOVIDADE", "acompanhamento_ligado",
           "pode_falar_com_o_cliente", "entregar_novidade"]
