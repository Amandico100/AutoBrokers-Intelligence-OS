# -*- coding: utf-8 -*-
"""SPEC-132-C C2 — a PORTA de entrada do atalho: quem fala com o número do AutoBrokers, e o que ele recebe.

    ligado()                                         `ATALHO_WHATSAPP_LIGADO` (padrão DESLIGADO)
    eh_do_assistente(db, integracao)                 a integração é o número do AutoBrokers? (`purpose` + plataforma)
    filtrar(envelope)                                o filtro BARATO do webhook (sem banco): o que nem entra
    async turno_do_atalho(db, integracao, envelope)  o turno inteiro (o webhook agenda em 2º plano)

`app/api/webhook.py:evolution_go_webhook_token` desvia para cá a integração `purpose='assistente'` da empresa da
PLATAFORMA — ANTES do desvio do QCM (que mora na MESMA empresa e capturaria a mensagem pelo `company_kind`) e ANTES
do observer (que consome). Toda outra integração (atendimento, observer, QCM) não passa por aqui.

🔴 OS FILTROS, NESTA ORDEM, ANTES DE QUALQUER ENVIO (as mutações da SPEC §6):
   1. fromMe · grupo · status/broadcast/canal · sem telefone ...... ignora (mutação 5)
   2. desligado ........................................................ ignora e conta (só no log)
   3. número de uma instância do PRODUTO (qualquer corretora, o QCM, o próprio assistente) ou destino de suporte
      ......................................................... ignora — anti-laço robô↔robô (mutação 5)
   4. "ATIVAR 123456" ...................... `verificacao.consumir_codigo` — responde só se ela mandar (C1)
   5. número NÃO verificado ............... SILÊNCIO total: nenhuma resposta, nenhuma linha de conteúdo (mutação 1)
   6. membro de 2+ corretoras ............. a conversa ativa decide; sem ela, pergunta UMA vez qual (mutação 6) —
      a pergunta pendente mora no BANCO (`atalho.estado`, cifrada), não no Redis: Redis fora, a escolha vale (P3);
      enquanto ela espera, as falas seguintes se juntam à guardada e NÃO geram outra pergunta (P2)
   7. teto 💭 200 mensagens/dia/membro .... uma frase no 200º, depois silêncio
   8. texto maior que 💭 8.000 caracteres .. cortado ANTES do turno, com um aviso curto (P5)
Depois: `turno.rodar` (o CORE da corretora DELE). Banco ilegível em 3/5/6/7 → CALA (fail-closed).
TODA mensagem que sai passa por `envio.enviar` — o cinto único da SAÍDA: anti-laço e o teto de envios do dia (P2).

⛔ Nenhum telefone inteiro em log (só `mascarar`), nenhum conteúdo em log.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

ENV_LIGADO = "ATALHO_WHATSAPP_LIGADO"
#: 💭 quanto tempo a pergunta "qual corretora?" (e a fala que a provocou) fica pendente — UMA pergunta por janela
VALIDADE_DA_ESCOLHA_S = 15 * 60
#: 💭 o maior texto do corretor que vira turno do chat (o resto é cortado, com aviso — custo de modelo)
LIMITE_DO_TEXTO = 8000
#: 💭 o maior texto guardado enquanto se espera a escolha da corretora
LIMITE_DA_FALA_GUARDADA = 4000

FRASE_DO_TETO = ("Por hoje chegamos ao limite de mensagens por aqui. Amanhã eu continuo — "
                 "se for urgente, use o chat no painel do AutoBrokers.")
FRASE_ESCOLHIDA = "Certo, seguimos pela {corretora}. Pode mandar o que precisa."
FRASE_TEXTO_LONGO = ("Sua mensagem é muito longa para o WhatsApp: li só o começo dela. "
                     "Para textos grandes, mande em arquivo ou use o chat no painel.")
_TROCAR = re.compile(r"^\s*trocar(\s+de)?\s+corretora\s*[.!]?\s*$", re.IGNORECASE)

#: contagem das mensagens que chegaram com o atalho desligado (só para o log — nada é gravado)
_IGNORADAS_DESLIGADO = {"n": 0}
#: um turno por membro por vez (o backend roda em UM processo uvicorn — `backend/Dockerfile:27`); a chave leva o laço
_TRAVAS: Dict[Tuple[int, str], asyncio.Lock] = {}


def ligado() -> bool:
    return str(os.environ.get(ENV_LIGADO) or "").strip().lower() in ("1", "true", "sim", "on", "yes")


def _mascarar(telefone: Any) -> str:
    from app.services.canal.repositorio import mascarar

    return mascarar(telefone)


def _dados(r: Any) -> List[Dict[str, Any]]:
    return [x for x in list(getattr(r, "data", None) or []) if isinstance(x, dict)]


# =====================================================================================================================
# quem é o número
# =====================================================================================================================
def eh_do_assistente(db: Any, integracao: Optional[Dict[str, Any]]) -> bool:
    """A integração é o número do AutoBrokers: `purpose='assistente'` E a empresa é a da PLATAFORMA. Só o `purpose`
    não basta (uma corretora não vira o assistente gravando a palavra). Erro → False (o caminho de sempre)."""
    from app.services.atalho.verificacao import PURPOSE_DO_ASSISTENTE

    if str((integracao or {}).get("purpose") or "").strip().lower() != PURPOSE_DO_ASSISTENTE:
        return False
    try:
        from app.services.canal.repositorio import eh_canal

        return bool(eh_canal(db, str((integracao or {}).get("company_id") or "")))
    except Exception as erro:  # noqa: BLE001
        logger.error("[ATALHO] tipo da empresa do assistente não lido (%s)", type(erro).__name__)
        return False


def numero_do_produto(db: Any, telefone: Any) -> bool:
    """Anti-laço: o número é de uma INSTÂNCIA do produto (integração ativa de QUALQUER empresa — corretora, o QCM, o
    próprio assistente) ou um destino de suporte ativo? O `canal.repositorio.numero_de_corretora` cobre corretoras e
    suporte; aqui somam-se as linhas da plataforma, que ele deixa passar de propósito. Erro → True (cala)."""
    from app.services.canal import repositorio as repo

    fs = repo.formas(telefone)
    if not fs:
        return False
    digitos = [f for f in fs if not f.startswith("+")]
    try:
        if repo.numero_de_corretora(db, telefone):
            return True
        linhas = _dados(db.table("integrations").select("id, purpose").eq("is_active", True)
                        .in_("paired_phone_e164", fs).execute())
        linhas += _dados(db.table("integrations").select("id, purpose").eq("is_active", True)
                         .in_("identifier", digitos).execute())
        # 🔴 SPEC-131-0-B2 (conserto B3) — a LINHA DO USUÁRIO (o WhatsApp PESSOAL de um corretor) não é instância do
        # produto: o número continua sendo de uma pessoa, e o central não a cala por ter conectado a linha. Sem laço: o
        # que o central manda a esse número chega à instância da linha como conversa ALHEIA → descartado no portão dela.
        from app.services.whatsapp.channel_identity import PURPOSE_DA_LINHA

        return any(str(x.get("purpose") or "").strip().lower() != PURPOSE_DA_LINHA for x in linhas)
    except Exception as erro:  # noqa: BLE001
        logger.warning("[ATALHO] anti-laço não conferido (%s) — cala", type(erro).__name__)
        return True


# =====================================================================================================================
# o filtro barato (o webhook chama antes de agendar)
# =====================================================================================================================
def filtrar(envelope: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], str]:
    """`(normalizado, "")` quando a mensagem pode seguir; `(None, motivo)` quando morre aqui. Sem banco, sem rede:
    fromMe, grupo, status/broadcast/canal, sem telefone, sem conteúdo, e o atalho desligado (conta e loga)."""
    from app.services.whatsapp.evolution_inbound import normalize_evolution_inbound

    if not isinstance(envelope, dict):
        return None, "payload_invalido"
    dados = envelope.get("data")
    chave = dados.get("key") if isinstance(dados, dict) else None
    if chave is None:
        chave = {}
    if not isinstance(chave, dict):        # P4 (red team): `key` como lista/texto → ignorado, nunca um 500
        return None, "payload_invalido"
    jid = str(chave.get("remoteJid") or "")
    if chave.get("fromMe") or jid.endswith(("@g.us", "@broadcast", "@newsletter", "@call")):
        return None, "from_me_ou_grupo"
    try:
        normalizado = normalize_evolution_inbound(envelope)
    except Exception as erro:  # noqa: BLE001 — formato que o normalizador não conhece: ignorado
        logger.warning("[ATALHO] envelope ilegível (%s) — ignorado", type(erro).__name__)
        return None, "payload_invalido"
    if not isinstance(normalizado, dict):
        return None, "payload_invalido"
    if normalizado.get("skip"):
        return None, str(normalizado.get("skip_reason") or "skip")
    if normalizado.get("from_me") or normalizado.get("is_group"):
        return None, "from_me_ou_grupo"
    if not ligado():
        _IGNORADAS_DESLIGADO["n"] += 1
        logger.info("[ATALHO] desligado (%s) — %d mensagem(ns) ignorada(s) desde que o processo subiu",
                    ENV_LIGADO, _IGNORADAS_DESLIGADO["n"])
        return None, "desligado"
    return normalizado, ""


# =====================================================================================================================
# a escolha da corretora (membro de duas ou mais)
# =====================================================================================================================
def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(texto or "").lower()) if unicodedata.category(c) != "Mn")


def _escolha(texto: str, membros: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """"1", "2)", "opção 2" ou o NOME exato da corretora → o membro daquela corretora. Qualquer outra coisa → None."""
    t = _sem_acento(texto).strip().rstrip(".!)")
    m = re.fullmatch(r"(?:opcao\s*)?(\d{1,2})", t)
    if m:
        i = int(m.group(1))
        return membros[i - 1] if 1 <= i <= len(membros) else None
    iguais = [x for x in membros if _sem_acento(x.get("nome_da_corretora") or "").strip() == t]
    return iguais[0] if len(iguais) == 1 else None


def _pergunta(membros: List[Dict[str, str]]) -> str:
    linhas = [f"{i}) {m.get('nome_da_corretora') or 'Corretora'}" for i, m in enumerate(membros, start=1)]
    return ("Você está falando por qual corretora?\n" + "\n".join(linhas)
            + "\n\nResponda com o número. Para mudar depois, mande \"trocar corretora\".")


def _pendente(estado: Dict[str, Any]) -> bool:
    """Há uma pergunta "qual corretora?" feita há menos de 💭 15 min?"""
    from datetime import datetime, timezone

    try:
        quando = datetime.fromisoformat(str(estado.get("perguntou_em") or "").replace("Z", "+00:00"))
    except ValueError:
        return False
    if quando.tzinfo is None:
        quando = quando.replace(tzinfo=timezone.utc)
    return 0 <= (datetime.now(timezone.utc) - quando).total_seconds() <= VALIDADE_DA_ESCOLHA_S


def _conversa_mais_recente(db: Any, membros: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
    """Das corretoras do membro, a que tem a conversa ATIVA do atalho mais recente (cada consulta filtra
    company_id + user_id daquela corretora; nenhuma mistura)."""
    from app.services.atalho import turno

    melhor, quando = None, ""
    for m in membros:
        linha = turno.conversa_ativa(db, m["company_id"], m["user_id"])
        if linha and str(linha.get("last_message_at") or "") > quando:
            melhor, quando = m, str(linha.get("last_message_at") or "")
    return melhor


async def _qual_corretora(db: Any, integracao: Dict[str, Any], telefone: str, membros: List[Dict[str, str]],
                          normalizado: Dict[str, Any]) -> Tuple[Optional[Dict[str, str]], Optional[str], bool]:
    """`(membro, fala_guardada, so_escolheu)` — ou `(None, None, False)` quando a pergunta foi feita (agora ou antes).

    `so_escolheu` = a mensagem ERA a resposta ("2") e não havia fala guardada: confirma e abre a conversa.
    🔴 A ESCOLHA vale pela conversa ativa (dura 12 h). A PERGUNTA pendente e a fala que a provocou moram no banco
    (`atalho.estado`, cifradas — P3: sem Redis a escolha funciona). Pergunta pendente: a resposta clara escolhe; qualquer
    outra fala se JUNTA à guardada e não gera nova pergunta (P2 — "qual corretora?" vai UMA vez por janela).
    Banco ilegível → levanta (o turno cala)."""
    from app.services.atalho import envio, estado as EST

    texto = str(normalizado.get("text") or "").strip()
    trocar = bool(_TROCAR.match(texto))
    guardado = await asyncio.to_thread(EST.ler, db, telefone)
    pendente = _pendente(guardado)
    if pendente and not trocar:
        escolhido = _escolha(texto, membros) if texto else None
        if escolhido:
            await asyncio.to_thread(EST.guardar, db, telefone, None)
            fala = str(guardado.get("fala") or "") or None
            return escolhido, fala, fala is None
        if texto:   # a fala seguinte espera junto (uma pergunta só)
            junto = "\n".join(x for x in (str(guardado.get("fala") or ""), texto) if x)[:LIMITE_DA_FALA_GUARDADA]
            await asyncio.to_thread(EST.guardar, db, telefone, {**guardado, "fala": junto})
        return None, None, False
    if not trocar:
        recente = await asyncio.to_thread(_conversa_mais_recente, db, membros)
        if recente:
            return recente, None, False
        escolhido = _escolha(texto, membros) if texto else None
        if escolhido:   # a pergunta venceu e a resposta é clara: vale
            return escolhido, None, True
    # a pergunta; a fala de TEXTO fica guardada para seguir depois da escolha (mídia: pede-se de novo)
    from datetime import datetime, timezone

    fala = texto if (texto and not trocar and not normalizado.get("media")) else ""
    await asyncio.to_thread(EST.guardar, db, telefone, {"perguntou_em": datetime.now(timezone.utc).isoformat(),
                                                        "fala": fala[:LIMITE_DA_FALA_GUARDADA]})
    await envio.enviar_texto(integracao, telefone, _pergunta(membros), db=db)
    return None, None, False


# =====================================================================================================================
# o turno
# =====================================================================================================================
def _trava(telefone: str) -> asyncio.Lock:
    chave = (id(asyncio.get_running_loop()), telefone)
    trava = _TRAVAS.get(chave)
    if trava is None:
        if len(_TRAVAS) > 2000:
            for k in [k for k, v in _TRAVAS.items() if not v.locked()][:1000]:
                _TRAVAS.pop(k, None)
        trava = _TRAVAS[chave] = asyncio.Lock()
    return trava


def _cortar(normalizado: Dict[str, Any]) -> bool:
    """P5 (red team): o texto (e a legenda da mídia) do corretor acima de 💭 8.000 caracteres é cortado ANTES de virar
    turno do chat. True = cortou (o turno manda o aviso curto)."""
    cortou = False
    texto = normalizado.get("text")
    if isinstance(texto, str) and len(texto) > LIMITE_DO_TEXTO:
        normalizado["text"] = texto[:LIMITE_DO_TEXTO]
        cortou = True
    midia = normalizado.get("media")
    if isinstance(midia, dict) and isinstance(midia.get("caption"), str) and len(midia["caption"]) > LIMITE_DO_TEXTO:
        midia["caption"] = midia["caption"][:LIMITE_DO_TEXTO]
        cortou = True
    return cortou


async def turno_do_atalho(db: Any, integracao: Dict[str, Any], envelope: Dict[str, Any]) -> Dict[str, Any]:
    """Uma mensagem ao número do AutoBrokers. Devolve `{"status": …}` (sem conteúdo — para o log e os testes).
    Nunca levanta: o webhook não tem o que fazer com o erro."""
    from app.services.atalho import envio, turno, verificacao
    from app.services.canal.repositorio import canonico

    try:
        normalizado, motivo = filtrar(envelope)
        if normalizado is None:
            return {"status": "ignorado", "motivo": motivo}
        if not await asyncio.to_thread(eh_do_assistente, db, integracao):   # o cinto (o webhook já conferiu)
            return {"status": "ignorado", "motivo": "nao_e_o_assistente"}
        tel = canonico(normalizado.get("phone"))
        if not tel:
            return {"status": "ignorado", "motivo": "sem_telefone"}
        if await asyncio.to_thread(numero_do_produto, db, tel):
            logger.warning("[ATALHO] mensagem de uma instância do produto (%s) ignorada — anti-laço", _mascarar(tel))
            return {"status": "ignorado", "motivo": "anti_laco"}

        cortado = _cortar(normalizado)

        async with _trava(tel):
            texto = str(normalizado.get("text") or "")
            if verificacao.codigo_da_ativacao(texto):
                r = await verificacao.consumir_codigo(db, telefone_remetente_e164=tel, texto=texto)
                if r.responder and r.mensagem:
                    await envio.enviar_texto(integracao, tel, r.mensagem, db=db)
                return {"status": "ativacao", "motivo": r.motivo or "ok", "respondeu": bool(r.responder)}

            membros = await asyncio.to_thread(verificacao.membros_verificados_por_telefone, db, tel)
            if not membros:
                logger.info("[ATALHO] número não verificado (%s) — silêncio", _mascarar(tel))
                return {"status": "silencio", "motivo": "nao_verificado"}

            fala_guardada, so_escolheu = None, False
            if len(membros) == 1:
                membro = membros[0]
            else:
                membro, fala_guardada, so_escolheu = await _qual_corretora(db, integracao, tel, membros, normalizado)
                if membro is None:
                    return {"status": "perguntou_a_corretora"}

            feitas = await asyncio.to_thread(turno.mensagens_de_hoje, db, membro["company_id"], membro["user_id"])
            if feitas > turno.TETO_DE_MENSAGENS_POR_DIA:
                return {"status": "silencio", "motivo": "teto"}
            if feitas == turno.TETO_DE_MENSAGENS_POR_DIA:
                # a 201ª fala é registrada (o contador passa do teto) e recebe a frase UMA vez; depois, silêncio
                agente = await asyncio.to_thread(turno.agente_core, db, membro["company_id"])
                if agente:
                    conversa = await asyncio.to_thread(turno.conversa_do_membro, db, membro["company_id"],
                                                       membro["user_id"], agente)
                    await asyncio.to_thread(turno.gravar_pergunta, db, conversa, membro["company_id"],
                                            texto or "[Mensagem]", [], f"teto-{os.urandom(8).hex()}")
                await envio.enviar_texto(integracao, tel, FRASE_DO_TETO, db=db)
                return {"status": "teto", "company_id": membro["company_id"]}

            if so_escolheu:
                # a resposta "2" sem fala guardada: confirma e abre a conversa (é ela que guarda a escolha, 12 h)
                agente = await asyncio.to_thread(turno.agente_core, db, membro["company_id"])
                if agente:
                    conversa = await asyncio.to_thread(turno.conversa_do_membro, db, membro["company_id"],
                                                       membro["user_id"], agente)
                    await asyncio.to_thread(turno.tocar_conversa, db, conversa["id"], membro["company_id"])
                await envio.enviar_texto(integracao, tel, FRASE_ESCOLHIDA.format(
                    corretora=membro.get("nome_da_corretora") or "sua corretora"), db=db)
                return {"status": "escolheu_a_corretora", "company_id": membro["company_id"]}

            if cortado:
                await envio.enviar_texto(integracao, tel, FRASE_TEXTO_LONGO, db=db)
            r = await turno.rodar(db, integracao, tel, membro, normalizado, texto=fala_guardada)
            return {"status": r.status, "company_id": r.company_id, "user_id": r.user_id,
                    "conversation_id": r.conversation_id, "enviadas": r.enviadas}
    except Exception as erro:  # noqa: BLE001
        logger.error("[ATALHO] mensagem não tratada (%s)", type(erro).__name__)
        return {"status": "erro"}


__all__ = ("ENV_LIGADO", "ligado", "eh_do_assistente", "numero_do_produto", "filtrar", "turno_do_atalho",
           "FRASE_DO_TETO", "FRASE_ESCOLHIDA", "FRASE_TEXTO_LONGO", "LIMITE_DO_TEXTO", "VALIDADE_DA_ESCOLHA_S")
