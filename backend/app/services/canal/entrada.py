# -*- coding: utf-8 -*-
"""A porta de entrada do canal de cotação — SPEC-133-A F1 (U1).

`app/api/webhook.py:process_whatsapp_message_background` desvia para cá TODO turno de uma integração cuja empresa é
`platform_canal` (D-133A-02) — depois do token, do dedup, da mídia e do buffer (a rajada já virou UM turno), e ANTES
do acionamento, da allowlist global do atendimento, do portão de silêncio e do LangChain das corretoras.

🔴 OS FILTROS RODAM ANTES DE QUALQUER ENVIO, nesta ordem (o elo da SPEC: "o canal só fala com quem foi convidado"):
   1. `fromMe` / grupo ............... ignora (o webhook já descarta; aqui é o cinto)
   2. número de CORRETORA ............ ignora + aviso sem o número inteiro (anti-laço robô↔robô, D-133A-06/07)
   3. não convidado .................. ignora — ZERO resposta (piloto fechado, D-133A-04)
   4. acima do limite de cotações .... UMA frase educada por dia, e mais nada
   5. teto de mensagens nossas/dia ... cala (anti-laço extra)
Depois: estado → `conversa.responder` (F2) → salvar o estado → `envio.enviar` → se a conversa fechou o perfil,
`cotacao.disparar` (F2). Banco ou config ilegíveis → CALA (fail-closed: nunca responder às cegas).

⚠️ `conversa` e `cotacao` são da F2 e importados DENTRO de `turno`: o webhook importa este módulo, e um import de
topo puxaria o Work OS para o caminho de todas as corretoras (e quebraria enquanto a F2 não existisse).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.services.canal import envio
from app.services.canal import repositorio as repo

logger = logging.getLogger(__name__)

#: a frase do limite (uma vez por dia). Texto do produto — nenhum nome de corretora (§13.9).
FRASE_DO_LIMITE = ("Por hoje você já chegou ao número de cotações deste teste. "
                   "Amanhã eu faço uma nova para você, combinado?")


def _e_nossa(item: Dict[str, Any]) -> bool:
    return bool((item or {}).get("fromMe") is True or (item or {}).get("from_me") is True)


def _texto_e_midia(itens: List[Dict[str, Any]]) -> Tuple[str, Optional[Dict[str, Any]]]:
    """A rajada vira UMA fala (o texto e as legendas, em ordem) e a 1ª mídia (com o tipo), se houver."""
    partes, midia = [], None
    for item in itens or []:
        if not isinstance(item, dict):
            continue
        t = str(item.get("texto") or item.get("legenda") or "").strip()
        if t:
            partes.append(t)
        if midia is None and isinstance(item.get("midia"), dict):
            midia = {"tipo": str(item.get("tipo") or ""), **item["midia"]}
    return "\n".join(partes), midia


def _comecando(estado: Dict[str, Any], conversa: Any, texto: str) -> bool:
    """A próxima fala abre uma conversa NOVA (o portão do limite vale)? A regra é UMA, da conversa (F2):
    `conversa.abre_conversa_nova` — estado vazio ou etapa de recomeço (`conversa.ETAPAS_DE_RECOMECO`), salvo o
    botão "Quero fechar" da página (a passagem nunca esbarra no limite do dia)."""
    return bool(conversa.abre_conversa_nova(estado, texto))


def _carregar_config(db, company_id: str) -> Dict[str, Any]:
    from app.services.multicalculo.config import carregar

    return carregar(company_id, db=db)


async def _avisar_do_limite(db, company_id: str, tel: str, teto: int) -> None:
    """A frase educada, UMA vez por dia (e dentro do teto anti-laço)."""
    if await asyncio.to_thread(repo.aviso_de_limite_dado_hoje, db, company_id, tel):
        return
    if await asyncio.to_thread(repo.enviadas_hoje, db, company_id, tel) >= teto:
        return
    await asyncio.to_thread(repo.marcar_aviso_de_limite, db, company_id, tel)   # ANTES: aviso duplicado é pior
    saiu = await envio.enviar(db, company_id, tel, [FRASE_DO_LIMITE])
    if saiu:
        await asyncio.to_thread(repo.contar_enviadas, db, company_id, tel, saiu)


async def turno(db, integration: dict, telefone_e164: str, itens: list[dict]) -> None:
    """Um turno do canal (a rajada inteira de UMA pessoa). Nunca levanta: o webhook não tem o que fazer com o erro."""
    company_id = str((integration or {}).get("company_id") or "")
    bruto = str(telefone_e164 or "")
    itens = [i for i in (itens or []) if isinstance(i, dict)]
    # ① fromMe / grupo
    if "@g.us" in bruto or "-" in bruto or any(_e_nossa(i) for i in itens):
        return
    tel = repo.canonico(bruto)
    if not tel or not company_id:
        return
    try:
        # ② anti-laço: a linha de uma corretora nunca recebe resposta do canal
        if await asyncio.to_thread(repo.numero_de_corretora, db, tel):
            logger.warning("[CANAL] mensagem da linha de uma corretora (%s) ignorada — anti-laço", repo.mascarar(tel))
            return
        # ③ piloto fechado
        if await asyncio.to_thread(repo.convidado, db, company_id, tel) is None:
            logger.info("[CANAL] número não convidado (%s) — sem resposta", repo.mascarar(tel))
            return
        config = await asyncio.to_thread(_carregar_config, db, company_id)
        teto = repo.teto_de_mensagens(config)
        estado = await asyncio.to_thread(repo.carregar_estado, db, company_id, tel)
        from app.services.canal import conversa   # F2 — tardio de propósito (ver o cabeçalho)

        # ④ o limite de cotações vale para quem COMEÇA uma conversa; quem está no meio de uma — a pergunta final, o
        #    "quero fechar" — continua. O 2º portão é antes de disparar (abaixo).
        texto, midia = _texto_e_midia(itens)
        if _comecando(estado, conversa, texto) and not await asyncio.to_thread(
                repo.dentro_do_limite, db, company_id, tel, config):
            await _avisar_do_limite(db, company_id, tel, teto)
            return
        # ⑤ o teto de mensagens nossas por conversa por dia
        ja_enviadas = await asyncio.to_thread(repo.enviadas_hoje, db, company_id, tel)
        if ja_enviadas >= teto:
            logger.warning("[CANAL] teto de %d mensagens/dia atingido com %s — o canal cala", teto, repo.mascarar(tel))
            return

        r = await conversa.responder(db, company_id, tel, texto, midia, estado, config=config)
        # 🔴 conserto B2 (a corrida): o run do canal pode ter gravado o RESULTADO enquanto este turno pensava. Relê
        # antes de gravar: se a conversa saiu de "calculando" por fora, o RUN tem precedência — este turno ("ainda
        # estou calculando") não grava nem manda nada; a pessoa já recebeu o resultado. Fora disso, o contador de
        # lembretes que o run somou no meio do turno é preservado.
        atual = await asyncio.to_thread(repo.carregar_estado, db, company_id, tel)
        if atual != estado:
            if str((estado or {}).get("etapa") or "") == "calculando" and str(atual.get("etapa") or "") != "calculando":
                logger.info("[CANAL] o run entregou durante o turno de %s — o run tem precedência",
                            repo.mascarar(tel))
                return
            if atual.get("lembretes") is not None and isinstance(r.estado, dict) and \
                    str(atual.get("pedido_id") or "") == str(r.estado.get("pedido_id") or ""):
                r.estado["lembretes"] = max(int(atual.get("lembretes") or 0), int(r.estado.get("lembretes") or 0))
        await asyncio.to_thread(repo.salvar_estado, db, company_id, tel, r.estado)
        baloes = list(r.baloes or [])[: max(0, teto - ja_enviadas)]
        saiu = await envio.enviar(db, company_id, tel, baloes)
        if saiu:
            await asyncio.to_thread(repo.contar_enviadas, db, company_id, tel, saiu)
        if r.disparar:
            if not await asyncio.to_thread(repo.dentro_do_limite, db, company_id, tel, config):
                await _avisar_do_limite(db, company_id, tel, teto)
                return
            from app.services.canal import cotacao   # F2

            run_id = await cotacao.disparar(db, company_id, tel, r.disparar, r.estado)
            if run_id:   # conserto 8: a cotação que NÃO começou ("" — a pessoa foi avisada) não gasta o limite do dia
                await asyncio.to_thread(repo.contar_cotacao, db, company_id, tel)
    except Exception as erro:  # noqa: BLE001 — o canal cala; o erro vai para o log, sem dado pessoal
        logger.error("[CANAL] turno de %s não concluído (%s)", repo.mascarar(tel), type(erro).__name__)
