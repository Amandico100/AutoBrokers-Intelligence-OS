# -*- coding: utf-8 -*-
"""A saída do canal de cotação — SPEC-133-A F1 (U3).

Um motor só (CLAUDE.md §5): `whatsapp_service.send_message` (provider multi-seam, digital da própria voz, nova
tentativa) — nunca outro cliente de envio. A integração é a do CANAL, achada pelo banco a cada envio; esta função
RECUSA empresa que não seja o canal: ela não pode virar atalho para falar pelo número calado de uma corretora.

⚠️ O pareamento grava TODA integração do hub com `purpose='observer'` (`channel_identity.purpose_canonico`, BLOCO 0
§1.2), e os seletores de saída de plataforma proíbem observer (`IntegrationService.PROPOSITOS_QUE_NUNCA_ENVIAM`,
SPEC-063 D). A proibição existe para a CORRETORA que pareou para ficar calada; o número do canal é da plataforma e
existe para conversar — por isso o canal resolve a própria integração aqui, filtrando `company_kind='platform_canal'`.

Os balões chegam PRONTOS (a conversa e `mensagem_para` já picotam): cada um sai como UMA mensagem (`bloco_unico=True`,
para `split_whatsapp_balloons` não re-picotar um balão de 301+ caracteres — BLOCO 0 §1.4) e a cadência humana de 0,7 s
fica entre eles, aqui.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.services.canal import repositorio as repo

logger = logging.getLogger(__name__)

#: a mesma cadência de `whatsapp_service.send_message` entre balões
PAUSA_ENTRE_BALOES_S = 0.7
_PROVEDORES = ("evolution-go", "evolution", "evolution-api", "z-api", "zapi")


def integracao_do_canal(db, company_id: str) -> Optional[Dict[str, Any]]:
    """A integração ATIVA do canal (conectada primeiro), com os segredos decifrados para o envio. Sem ela → None."""
    cid = repo._cid(company_id)
    linhas = repo._dados(db.table("integrations").select("*").eq("company_id", cid).eq("is_active", True).execute())
    linhas = [x for x in repo._da_empresa(linhas, cid)
              if str(x.get("provider") or "").strip().lower() in _PROVEDORES]
    if not linhas:
        return None
    linhas.sort(key=lambda x: 0 if str(x.get("channel_status") or "").lower() == "connected" else 1)
    from app.services.whatsapp.integration_secrets import prepare_integration_for_runtime

    return prepare_integration_for_runtime(linhas[0])


async def enviar(db, company_id: str, telefone_e164: str, baloes: List[str]) -> int:
    """Manda os balões ao telefone pela integração do CANAL. Devolve quantos saíram (para no 1º que falhar)."""
    textos = [str(b).strip() for b in (baloes or []) if str(b or "").strip()]
    tel = repo.canonico(telefone_e164)
    if not textos or not tel:
        return 0
    if not await asyncio.to_thread(repo.eh_canal, db, company_id):
        logger.error("[CANAL] envio recusado: a empresa não é o canal")
        return 0
    integracao = await asyncio.to_thread(integracao_do_canal, db, company_id)
    if not integracao:
        logger.error("[CANAL] sem integração ativa do canal — nada sai para %s", repo.mascarar(tel))
        return 0
    from app.services.whatsapp_service import get_whatsapp_service

    servico = get_whatsapp_service()
    saiu = 0
    for i, texto in enumerate(textos):
        if i:
            await asyncio.sleep(PAUSA_ENTRE_BALOES_S)
        try:
            ok = await asyncio.to_thread(servico.send_message, tel, texto, integracao, bloco_unico=True)
        except Exception as erro:  # noqa: BLE001 — o contrato legado levanta na falha
            logger.error("[CANAL] balão %d/%d não saiu para %s (%s)", i + 1, len(textos), repo.mascarar(tel),
                         type(erro).__name__)
            break
        if ok is False:
            logger.error("[CANAL] balão %d/%d recusado para %s", i + 1, len(textos), repo.mascarar(tel))
            break
        saiu += 1
    return saiu
