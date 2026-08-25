# -*- coding: utf-8 -*-
"""A saudação do religamento — SPEC-093, BLOCO D.

> 🔴 **Decisão do Founder, 25/08:** ao religar, o agente **saúda e pergunta**.
> Não retoma, não age, não presume.

## O que este arquivo NÃO faz, e é o mais importante

📊 O robô teve **4 conversas de WhatsApp em toda a história do produto** — 21.901
das 23.028 mensagens são Espelho de conversa **humana**. A primeira vez que isto
rodar será a maior coisa que este produto já mandou sozinho.

Por isso:

- ⛔ **não constrói limitador nenhum.** 📊 `platform_outbound` já tem teto de
  12/h e 20/dia, espaçamento sorteado de 241–479 s, janela 08:00–20:00, domingo
  bloqueado e parada de emergência por corretora. A saudação sai por
  `send_to_client_guarded(temperatura=FRIA)` e **o problema das "cinquenta às
  8h" se resolve por roteamento, não por código novo** (`CLAUDE.md` §5);
- ⛔ **não envia sem confirmação explícita no primeiro religar** de cada
  corretora. Uma tela é o guarda mais barato que existe;
- ⛔ **não toca em conversa com mais de 24h.** 📊 Acima disso a janela da Meta já
  exige template — a regra de produto e a regra do canal dão a mesma resposta. E
  📊 **181 das 234 têm mais de 7 dias**: ali a saudação é exumação, não
  recuperação.

## A idempotência é a MENSAGEM, não o clique

```
chave:  (company_id, conversation_id, inbound_message_id)
```

🔴 Desligar e ligar duas vezes gera a **mesma** chave → a segunda é no-op.
Chavear no evento de toggle mandaria duas saudações para a mesma pessoa.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

#: ≤ 12h — saúda e pergunta se ainda precisa.
IDADE_DIRETA_H = 12
#: 12h < idade ≤ 24h — saúda **nomeando a demora**.
IDADE_LIMITE_H = 24

#: `kind` do envio, para telemetria do governador.
KIND = "saudacao_religamento"

#: Status que significa *"uma pessoa foi chamada para esta conversa"*.
STATUS_HUMANO = "HUMAN_REQUESTED"


# ---------------------------------------------------------------------------
# PURO — dá para percorrer as famílias sem banco, sem Redis e sem rede
# ---------------------------------------------------------------------------

def decidir_saudacao(conversa: Dict[str, Any], *,
                     agora: Optional[datetime] = None) -> Dict[str, Any]:
    """PURO. Esta conversa recebe saudação? E de que tipo?

    🔴 **A ORDEM DAS RECUSAS IMPORTA, e não é estilo.** As três proibições vêm
    antes da idade porque uma conversa reivindicada por uma pessoa não deve ser
    saudada **nem quando é recente** — e testar a idade primeiro esconderia isso
    atrás de um caso que passa.

    ⚠️ *"já existe mensagem `assistant` posterior à do cliente"* funciona a favor
    sozinho: 📊 as linhas do Espelho chegam como `role='assistant'`, então
    **resposta humana pelo celular já conta como respondida**. Não é acidente
    feliz — é a razão de a checagem ser por papel e não por autor.
    """
    agora = agora or datetime.now(timezone.utc)

    if conversa.get("claimed_by") or conversa.get("claimed_by_name"):
        return {"envia": False, "motivo": "reivindicada_por_pessoa", "faixa": None}

    if str(conversa.get("status") or "").upper() == STATUS_HUMANO:
        return {"envia": False, "motivo": "handoff_humano", "faixa": None}

    if conversa.get("ja_respondida"):
        return {"envia": False, "motivo": "ja_respondida", "faixa": None}

    quando = _instante(conversa.get("ultima_inbound_em"))
    if quando is None:
        return {"envia": False, "motivo": "sem_mensagem_do_cliente", "faixa": None}

    horas = (agora - quando).total_seconds() / 3600.0
    if horas < 0:
        # Relógio adiantado do outro lado. Trata como agora — nunca como futuro
        # elegível para "demora".
        horas = 0.0
    if horas > IDADE_LIMITE_H:
        # 🔴 NÃO ENVIA. Vai para a fila humana — e o motivo é escrito, porque
        # "não enviou" sem motivo é indistinguível de "esqueceu".
        return {"envia": False, "motivo": "velha_demais_vai_para_fila_humana",
                "faixa": "velha", "horas": round(horas, 1)}
    if horas > IDADE_DIRETA_H:
        return {"envia": True, "motivo": "demora_nomeada", "faixa": "demorada",
                "horas": round(horas, 1)}
    return {"envia": True, "motivo": "recente", "faixa": "recente",
            "horas": round(horas, 1)}


def texto_da_saudacao(faixa: str, *, nome: Optional[str] = None) -> str:
    """A saudação **saúda e pergunta**. Não retoma, não age, não presume.

    ⚠️ Ela não repete o que a pessoa escreveu, de propósito: repetir é presumir
    que ainda vale, e 📊 a decisão do Founder foi explicitamente o contrário.
    """
    quem = f" {str(nome).strip().split()[0]}" if str(nome or "").strip() else ""
    if faixa == "demorada":
        return (f"Oi{quem}! Desculpe a demora em retornar. "
                "Vi a sua mensagem aqui — você ainda precisa de ajuda com isso?")
    return (f"Oi{quem}! Tudo bem? "
            "Vi a sua mensagem aqui — você ainda precisa de ajuda com isso?")


def chave_da_saudacao(company_id: str, conversation_id: str,
                      inbound_message_id: str) -> Dict[str, str]:
    """🔴 A CHAVE É A MENSAGEM, NÃO O CLIQUE.

    Desligar e ligar duas vezes gera a **mesma** chave → a segunda é no-op.
    Chavear no evento de toggle mandaria duas saudações para a mesma pessoa.
    """
    return {"company_id": str(company_id),
            "conversation_id": str(conversation_id),
            "inbound_message_id": str(inbound_message_id)}


def _instante(valor: Any) -> Optional[datetime]:
    if isinstance(valor, datetime):
        return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)
    texto = str(valor or "").strip()
    if not texto:
        return None
    try:
        d = datetime.fromisoformat(texto.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# IO — leitura
# ---------------------------------------------------------------------------

async def _db():
    """O cliente ASSINCRONO -- e a escolha nao e' estilo.

    📊 Medido: `get_supabase_client()` devolve o `SupabaseClient` SÍNCRONO,
    cujo `.execute()` **não é aguardável**. `create_async_supabase_client()` é o
    que `dispatch_router._db()` usa, e é o único em que `await ... .execute()`
    está certo.

    ⚠️ Misturar os dois produz `coroutine ... never awaited`: **um SELECT que
    nunca acontece**, em silêncio, devolvendo um objeto que não é resposta.
    """
    from app.core.database import create_async_supabase_client

    return await create_async_supabase_client()


async def marcar_desligamento(company_id: str, *, desligado: bool) -> bool:
    """D.1 — *"desde quando estávamos fora"*.

    📊 `agents.updated_at` **não serve**: `tenant-agent-store.ts` o reescreve em
    `patch`, em `reset` e no próprio toggle. Um ajuste de prompt no meio do
    desligamento apagaria a resposta — e a idade é o que decide entre saudar e
    mandar para a fila humana.

    ⚠️ Escrita **só** na transição; ligar **limpa**.
    """
    try:
        db = await _db()
        agora = datetime.now(timezone.utc).isoformat()
        await (db.client.table("agents")
               .update({"desligado_em": agora if desligado else None})
               .eq("company_id", str(company_id))
               .eq("agent_role", "attendance").execute())
        return True
    except Exception as e:  # noqa: BLE001
        logger.error("[SAUDACAO] `desligado_em` de %s NÃO gravado (%s) — a idade "
                     "do desligamento vai ficar indisponível", company_id,
                     type(e).__name__)
        return False


async def conversas_elegiveis(company_id: str, *,
                              agora: Optional[datetime] = None,
                              limite: int = 500) -> List[Dict[str, Any]]:
    """Quem recebe: mensagem do cliente **sem resposta depois dela**.

    ⛔ Nunca devolve telefone nem conteúdo para fora — o `resumo_para_tela` sai
    mascarado, e é o único campo que uma tela deve mostrar (`CLAUDE.md` §13.3).
    """
    agora = agora or datetime.now(timezone.utc)
    corte = (agora - timedelta(hours=IDADE_LIMITE_H * 2)).isoformat()
    db = await _db()

    conversas = await (db.client.table("conversations")
                 .select("id, company_id, status, claimed_by, claimed_by_name, "
                         "user_name, user_phone, last_message_at, channel")
                 .eq("company_id", str(company_id))
                 .gte("last_message_at", corte)
                 .order("last_message_at", desc=True)
                 .limit(int(limite)).execute())
    linhas = getattr(conversas, "data", None) or []

    ja = await _ja_saudadas(db, company_id)
    elegiveis: List[Dict[str, Any]] = []
    for c in linhas:
        ultima = await _ultima_inbound_sem_resposta(db, str(c.get("id") or ""))
        if not ultima:
            continue
        candidata = dict(c)
        candidata["ultima_inbound_em"] = ultima.get("created_at")
        candidata["inbound_message_id"] = str(ultima.get("id") or "")
        candidata["ja_respondida"] = bool(ultima.get("respondida"))
        veredito = decidir_saudacao(candidata, agora=agora)
        candidata["veredito"] = veredito
        if (str(c.get("id")), candidata["inbound_message_id"]) in ja:
            candidata["veredito"] = {"envia": False, "motivo": "ja_saudada",
                                     "faixa": veredito.get("faixa")}
        elegiveis.append(candidata)
    return elegiveis


async def _ja_saudadas(db, company_id: str) -> set:
    try:
        r = await (db.client.table("saudacoes_enviadas")
             .select("conversation_id, inbound_message_id")
             .eq("company_id", str(company_id)).limit(5000).execute())
        return {(str(l.get("conversation_id")), str(l.get("inbound_message_id")))
                for l in (getattr(r, "data", None) or [])}
    except Exception as e:  # noqa: BLE001
        # 🔴 FALHA FECHADA. Não conseguir ler o que já foi enviado nunca pode
        # virar permissão para enviar de novo — e um `set()` vazio aqui é
        # exatamente isso. Levanta.
        logger.error("[SAUDACAO] anti-duplicata ilegível (%s) — nada será "
                     "enviado nesta rodada", type(e).__name__)
        raise


async def _ultima_inbound_sem_resposta(db, conversation_id: str) -> Optional[Dict[str, Any]]:
    """A última mensagem do cliente e se veio `assistant` DEPOIS dela.

    📊 As linhas do Espelho chegam como `role='assistant'` — resposta humana
    pelo celular **já conta como respondida**.
    """
    if not conversation_id:
        return None
    r = await (db.client.table("messages")
         .select("id, role, created_at")
         .eq("conversation_id", conversation_id)
         .order("created_at", desc=True).limit(20).execute())
    linhas = getattr(r, "data", None) or []
    respondida = False
    for m in linhas:  # do mais novo para o mais velho
        papel = str(m.get("role") or "").lower()
        if papel == "user":
            return {"id": m.get("id"), "created_at": m.get("created_at"),
                    "respondida": respondida}
        if papel == "assistant":
            respondida = True
    return None


# ---------------------------------------------------------------------------
# IO — a prévia e o envio
# ---------------------------------------------------------------------------

async def previa(company_id: str, *,
                 agora: Optional[datetime] = None) -> Dict[str, Any]:
    """D.5 — a contagem e a lista, **antes** de qualquer mensagem sair.

    ⛔ `resumo` é o único campo para tela e vai mascarado: nome só o primeiro,
    telefone só os quatro últimos (`CLAUDE.md` §13.3).
    """
    linhas = await conversas_elegiveis(company_id, agora=agora)
    envia = [c for c in linhas if c["veredito"].get("envia")]
    recusa = [c for c in linhas if not c["veredito"].get("envia")]
    return {
        "primeiro_religamento": await _primeiro_religamento(company_id),
        "total": len(envia),
        "conversas": [_para_tela(c) for c in envia],
        "recusadas": len(recusa),
        "por_motivo": _contar(recusa),
    }


async def _primeiro_religamento(company_id: str) -> bool:
    """Esta corretora já saudou alguém alguma vez?

    🔴 Sem estado novo: a própria tabela de anti-duplicata responde. Um campo
    "já_confirmou_uma_vez" seria uma segunda verdade sobre a mesma coisa.
    """
    try:
        db = await _db()
        r = await (db.client.table("saudacoes_enviadas").select("id")
             .eq("company_id", str(company_id)).limit(1).execute())
        return not (getattr(r, "data", None) or [])
    except Exception:  # noqa: BLE001
        return True  # na dúvida, EXIGE confirmação


def _para_tela(c: Dict[str, Any]) -> Dict[str, Any]:
    telefone = str(c.get("user_phone") or "")
    nome = str(c.get("user_name") or "").strip()
    return {
        "conversation_id": str(c.get("id") or ""),
        "quem": (nome.split()[0] if nome else "sem nome")
                + (f" ····{telefone[-4:]}" if len(telefone) >= 4 else ""),
        "horas": c["veredito"].get("horas"),
        "faixa": c["veredito"].get("faixa"),
    }


def _contar(linhas: List[Dict[str, Any]]) -> Dict[str, int]:
    fora: Dict[str, int] = {}
    for l in linhas:
        m = str(l["veredito"].get("motivo") or "?")
        fora[m] = fora.get(m, 0) + 1
    return fora


async def enviar_saudacoes(company_id: str, *, confirmado: bool = False,
                           agora: Optional[datetime] = None) -> Dict[str, Any]:
    """Envia a saudação por `send_to_client_guarded(temperatura=FRIA)`.

    🔴 **No primeiro religamento de cada corretora, `confirmado=False` NÃO
    ENVIA** — devolve a prévia e para. 📊 O robô teve 4 conversas em toda a
    história do produto; a primeira vez que isto rodar será a maior coisa que
    ele já mandou sozinho.

    ## A reserva vem ANTES do envio, e é de propósito

    ⚠️ A linha em `saudacoes_enviadas` é gravada **antes** de chamar o envio. Se
    o processo morrer no meio, o pior caso é uma saudação que não sai — nunca
    duas que saem. Mandar a mesma mensagem duas vezes para um segurado é o dano
    que não tem desfazer.

    ⚠️ E `queued=True` **é sucesso**: o governador aceitou e a fila entrega. Não
    devolver a reserva nesse caso mandaria a segunda quando a primeira já está a
    caminho.
    """
    linhas = await conversas_elegiveis(company_id, agora=agora)
    envia = [c for c in linhas if c["veredito"].get("envia")]

    if not confirmado and await _primeiro_religamento(company_id):
        return {"ok": False, "enviadas": 0, "motivo": "confirmacao_necessaria",
                "previa": await previa(company_id, agora=agora)}

    from app.services.platform_outbound import FRIA, send_to_client_guarded

    db = await _db()
    resultado = {"ok": True, "enviadas": 0, "enfileiradas": 0, "recusadas": 0,
                 "ja_saudadas": 0, "erros": 0}
    for c in envia:
        chave = chave_da_saudacao(company_id, str(c.get("id") or ""),
                                  str(c.get("inbound_message_id") or ""))
        if not await _reservar(db, chave):
            resultado["ja_saudadas"] += 1
            continue
        try:
            r = await send_to_client_guarded(
                str(company_id), str(c.get("user_phone") or ""),
                texto_da_saudacao(str(c["veredito"].get("faixa") or "recente"),
                                  nome=c.get("user_name")),
                kind=KIND,
                summary="Saudação de religamento do atendimento",
                temperatura=FRIA)
        except Exception as e:  # noqa: BLE001
            logger.error("[SAUDACAO] envio falhou (%s)", type(e).__name__)
            resultado["erros"] += 1
            continue
        if r.get("queued"):
            resultado["enfileiradas"] += 1
        elif r.get("ok"):
            resultado["enviadas"] += 1
        else:
            resultado["recusadas"] += 1
    return resultado


async def _reservar(db, chave: Dict[str, str]) -> bool:
    """Reserva a chave. `False` = alguém já saudou esta mensagem.

    🔴 O UNIQUE do banco é o guarda de verdade: a checagem em Python é o caminho
    rápido, e este INSERT é o que sobrevive a duas réplicas do drenador rodando
    juntas.
    """
    try:
        await db.client.table("saudacoes_enviadas").insert(dict(chave)).execute()
        return True
    except Exception as e:  # noqa: BLE001
        texto = str(e).lower()
        if "duplicate" in texto or "23505" in texto or "unique" in texto:
            return False
        logger.error("[SAUDACAO] reserva falhou (%s) — esta conversa NÃO será "
                     "saudada nesta rodada", type(e).__name__)
        return False
