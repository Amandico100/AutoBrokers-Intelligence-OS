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
  corretora. Uma tela é o guarda mais barato que existe — e a prévia que ela
  mostra **carrega identidade mascarada**, de propósito (ver `previa`);
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

import asyncio
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
        # 🔴 NÃO ENVIA — e o motivo é escrito, porque "não enviou" sem motivo é
        # indistinguível de "esqueceu".
        #
        # ⚠️ **"Fila humana" aqui é a que JÁ EXISTE, não uma nova.** A conversa
        # continua sem resposta e continua na tela de Conversas, que é onde a
        # corretora já olha. Este bloco não cria fila, não notifica e não muda
        # status — ele **se recusa a falar**, e diz por quê. Criar uma segunda
        # fila ao lado da que existe é a proibição estrutural do §5.
        return {"envia": False, "motivo": "velha_demais_nao_saudamos",
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


#: ⛔ `marcar_desligamento` FOI REMOVIDA — SPEC-093, conserto do painel.
#:
#: 📊 Ela não tinha nenhum chamador: quem escreve `agents.desligado_em` é
#: `lib/admin/tenant-agent-store.ts`, no próprio toggle, onde a transição
#: acontece. Duas cópias do mesmo escritor, uma delas morta — `CLAUDE.md` §5.

async def conversas_elegiveis(company_id: str, *,
                              agora: Optional[datetime] = None,
                              limite: int = 500) -> List[Dict[str, Any]]:
    """Quem recebe: mensagem do cliente **sem resposta depois dela**.

    ⛔ Nunca devolve telefone nem conteúdo para fora — o `resumo_para_tela` sai
    mascarado, e é o único campo que uma tela deve mostrar (`CLAUDE.md` §13.3).
    """
    agora = agora or datetime.now(timezone.utc)
    # ⚠️ DUAS VEZES O LIMITE, e o dobro tem razão de ser: conversas entre 24h e
    # 48h **precisam ser lidas** para aparecerem na prévia como recusadas. Sem a
    # folga, "velha demais" nunca apareceria em `por_motivo` e a tela diria que
    # não havia ninguém em vez de dizer que havia e não dá para falar.
    #
    # 📊 E as 181 conversas com mais de 7 dias ficam de fora por construção:
    # nem são lidas. Ali a saudação seria exumação.
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

    ids = [str(c.get("id") or "") for c in linhas if c.get("id")]

    # 🔴 A ANTI-DUPLICATA É CONSULTADA **POR CONVERSA**, NÃO EM BLOCO.
    #
    # 📊 A primeira versão lia `saudacoes_enviadas` inteira com
    # `.limit(5000)` — e o PostgREST **entrega no máximo 1000**. Uma corretora
    # com mais de mil saudações no histórico receberia uma lista truncada, e
    # tudo o que ficou de fora **seria saudado de novo**.
    #
    # ⚠️ O guarda `test_ninguem_pede_mais_de_mil_linhas_de_novo` pegou isso na
    # bateria inteira, 40 minutos depois de eu escrever. Truncamento silencioso
    # é a família de defeito mais cara deste projeto: parece que funcionou.
    #
    # Aqui a consulta é **limitada pelo que está em jogo** — no máximo `limite`
    # conversas, e nunca o histórico inteiro.
    ja = await _ja_saudadas(db, company_id, ids)

    # 🔴 UMA QUERY DE MENSAGENS PARA TODAS AS CONVERSAS — NÃO UMA POR CONVERSA.
    #
    # 📊 O painel mediu: uma corretora tem **86 conversas** na janela de 48h.
    # A primeira versão fazia 1 SELECT de `conversations` + 86 SELECTs de
    # `messages`, **aguardados um a um** = 87 idas ao PostgREST. E a tela que
    # decide se uma mensagem real sai para um segurado real ficava pendurada.
    ultimas = await _ultimas_inbound(db, ids)

    elegiveis: List[Dict[str, Any]] = []
    for c in linhas:
        ultima = ultimas.get(str(c.get("id") or ""))
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


#: O teto do PostgREST. 📊 Pedir mais devolve mil, em silêncio.
_TETO_DO_POSTGREST = 1000


async def _ja_saudadas(db, company_id: str, conversation_ids: List[str]) -> set:
    """Quais (conversa, mensagem) desta corretora já foram saudadas.

    ⚠️ **Só as conversas em jogo.** Ler a tabela inteira parece mais simples e
    é pior: 📊 o PostgREST entrega no máximo 1000 linhas, e uma lista truncada
    aqui vira **saudação repetida** — o único dano desta função que não tem
    desfazer.

    🔴 E vai em lotes: uma corretora pode ter mais de mil conversas na janela.
    """
    alvos = [i for i in dict.fromkeys(conversation_ids) if i]
    if not alvos:
        return set()
    try:
        vistos = set()
        for i in range(0, len(alvos), _TETO_DO_POSTGREST):
            lote = alvos[i:i + _TETO_DO_POSTGREST]
            r = await (db.client.table("saudacoes_enviadas")
                       .select("conversation_id, inbound_message_id")
                       .eq("company_id", str(company_id))
                       .in_("conversation_id", lote)
                       .limit(_TETO_DO_POSTGREST).execute())
            vistos |= {(str(l.get("conversation_id")), str(l.get("inbound_message_id")))
                       for l in (getattr(r, "data", None) or [])}
        return vistos
    except Exception as e:  # noqa: BLE001
        # 🔴 FALHA FECHADA. Não conseguir ler o que já foi enviado nunca pode
        # virar permissão para enviar de novo — e um `set()` vazio aqui é
        # exatamente isso. Levanta.
        logger.error("[SAUDACAO] anti-duplicata ilegível (%s) — nada será "
                     "enviado nesta rodada", type(e).__name__)
        raise


#: Quantas mensagens recentes bastam para decidir. ⚠️ Uma conversa em que o
#: cliente escreveu 30 vezes seguidas sem resposta ainda decide certo: se
#: nenhuma das últimas N é `assistant`, ela não foi respondida.
_MENSAGENS_POR_CONVERSA = 20

#: Quantas conversas são consultadas ao mesmo tempo.
#:
#: ⚠️ É latência, não corretude: 92 conversas viram ~9 idas em vez de 92. Subir
#: muito troca a lentidão por pressão no PostgREST, que é compartilhado com o
#: atendimento acontecendo ao mesmo tempo.
_CONSULTAS_EM_PARALELO = 10


async def _ultimas_inbound(db, conversation_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Por conversa: a última mensagem do cliente, e se veio `assistant` depois.

    📊 As linhas do Espelho chegam como `role='assistant'` — resposta humana
    pelo celular **já conta como respondida**. Não é acidente feliz: é a razão
    de a checagem ser por PAPEL e não por autor.

    ## 🔴 UMA QUERY POR CONVERSA — E O TETO GLOBAL JÁ FOI TENTADO

    A primeira versão fazia 87 idas **sequenciais**; a segunda tentou uma query
    só, com `.in_(conversas).order(created_at desc).limit(N × 20)`.

    ⚠️ **A segunda era pior.** 📊 Medido em 26/08/2026, em produção:

    ```
    conversas ativas nas 48h ................    92
    mensagens nas 48h ....................... 2.119
    a MAIOR conversa, só nas 48h ............   267
    a maior conversa no histórico ........... 1.145
    teto do PostgREST ....................... 1.000
    ```

    O teto é **global e ordenado por data**: uma conversa tagarela come o
    orçamento inteiro e as outras voltam com **zero linhas** — que este código lê
    como *"sem mensagem do cliente"*. A pessoa simplesmente **não é saudada**, em
    silêncio. 📊 Uma única conversa do banco tem 1.145 mensagens: sozinha, ela
    estoura o teto.

    > 🔴 O N+1 era lento e **certo**. O meu era rápido e **errado**.

    A resposta é **concorrência**, não teto global: `.limit()` por conversa (que
    é divisível), N consultas em paralelo. 92 conversas viram ~9 idas de
    latência, e nenhuma pode faminar outra.

    ⚠️ `.order("created_at", desc=True)` **importa** e está testado: o algoritmo
    percorre do mais novo para o mais velho, e invertê-lo faria a chave de
    idempotência apontar para a mensagem mais ANTIGA, a faixa de idade sair
    errada e `respondida` sair ao contrário.
    """
    alvos = [i for i in dict.fromkeys(conversation_ids) if i]
    if not alvos:
        return {}

    fora: Dict[str, Dict[str, Any]] = {}
    for i in range(0, len(alvos), _CONSULTAS_EM_PARALELO):
        lote = alvos[i:i + _CONSULTAS_EM_PARALELO]
        respostas = await asyncio.gather(
            *[_uma_conversa(db, cid) for cid in lote], return_exceptions=True)
        for cid, r in zip(lote, respostas):
            if isinstance(r, BaseException):
                # ⚠️ FALHA FECHADA POR CONVERSA: não conseguir ler as mensagens
                # desta conversa a tira da rodada. Saudação a menos é
                # recuperável; saudação para quem já foi respondido, não.
                logger.warning("[SAUDACAO] mensagens de uma conversa ilegíveis "
                               "(%s) — ela fica fora desta rodada",
                               type(r).__name__)
                continue
            if r:
                fora[cid] = r
    return fora


async def _uma_conversa(db, conversation_id: str) -> Optional[Dict[str, Any]]:
    """A última mensagem do cliente nesta conversa, e se veio `assistant` depois.

    ⚠️ `.limit()` POR CONVERSA, e é exatamente por isso que é uma query por
    conversa: um teto global não é divisível entre elas.
    """
    r = await (db.client.table("messages")
               .select("id, role, created_at")
               .eq("conversation_id", conversation_id)
               .order("created_at", desc=True)
               .limit(_MENSAGENS_POR_CONVERSA).execute())
    respondida = False
    for m in (getattr(r, "data", None) or []):  # do mais novo para o mais velho
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
                 agora: Optional[datetime] = None,
                 linhas: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """D.5 — a contagem e a lista, **antes** de qualquer mensagem sair.

    ## ⚠️ ESTA RESPOSTA CARREGA IDENTIDADE, E É DE PROPÓSITO

    🔴 O campo `quem` traz **primeiro nome + os quatro últimos dígitos** do
    telefone. Isso é identidade mascarada, não contagem — e a SPEC pede
    exatamente isso: *"mostra a CONTAGEM **e a lista**"*. 📊 O robô teve 4
    conversas de WhatsApp em toda a história do produto; quem confirma o maior
    envio que ele já fez precisa **ver para quem**.

    ⛔ **Então trate a resposta como dado do segurado:** ela não vai para log,
    não vai para `work_events`, não vai para RAG e não sai da sessão de quem
    pediu. §13.3 (*"presença, nunca conteúdo"*) governa log e `/health` — não a
    tela que a pessoa autorizada está olhando para decidir.

    ⚠️ O painel pegou três docstrings deste bloco afirmando que a prévia era só
    contagem. **O texto estava errado, não o campo** — e texto que mente sobre o
    que um campo guarda reinfecta todo leitor seguinte (`CLAUDE.md` §12.1).
    """
    # ⚠️ `linhas` recebido = a varredura JÁ FOI FEITA pelo chamador.
    #
    # 📊 O painel mediu: `enviar_saudacoes(confirmado=False)` — que é o caso
    # normal do primeiro religamento — varria tudo, e depois chamava esta
    # função, que varria tudo de novo. ~174 idas ao banco numa resposta HTTP.
    if linhas is None:
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
    """A linha que a tela mostra. ⚠️ **Identidade mascarada** — ver `previa`.

    Primeiro nome e os quatro últimos dígitos: o mínimo para uma pessoa
    reconhecer de quem se trata, e não mais que isso.
    """
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
                "previa": await previa(company_id, agora=agora, linhas=linhas)}

    from app.services.platform_outbound import FRIA, send_to_client_guarded

    db = await _db()
    resultado = {"ok": True, "enviadas": 0, "enfileiradas": 0, "recusadas": 0,
                 "ja_saudadas": 0, "erros": 0}
    for c in envia:
        chave = chave_da_saudacao(company_id, str(c.get("id") or ""),
                                  str(c.get("inbound_message_id") or ""))
        reserva = await _reservar(db, chave)
        if reserva != "reservada":
            # ⚠️ DUPLICATA E ERRO NÃO SÃO A MESMA COISA, e contá-los juntos fazia
            # o número mentir sobre o motivo: `saudacoes_enviadas` indisponível
            # devolvia `{"ok": true, "enviadas": 0, "ja_saudadas": N}` — e quem
            # lesse concluiria *"todas já tinham sido saudadas"* quando a
            # verdade era *"nenhuma saudação foi possível"*.
            resultado["ja_saudadas" if reserva == "duplicada" else "erros"] += 1
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


async def _reservar(db, chave: Dict[str, str]) -> str:
    """Reserva a chave. Devolve `reservada` | `duplicada` | `falhou`.

    🔴 O UNIQUE do banco é o guarda de verdade: a checagem em Python é o
    caminho rápido, e este INSERT é o que sobrevive a **duas réplicas do
    drenador rodando juntas** — o caso em que o cache em memória de cada uma
    diz que ninguém saudou.

    ⚠️ **Três respostas, não duas.** Devolver `False` para duplicata e para erro
    fazia o resultado dizer *"todas já tinham sido saudadas"* quando a verdade
    era *"a tabela está fora do ar"*. A direção é segura nas duas (não envia),
    mas o número mentia sobre o motivo.
    """
    try:
        await db.client.table("saudacoes_enviadas").insert(dict(chave)).execute()
        return "reservada"
    except Exception as e:  # noqa: BLE001
        texto = str(e).lower()
        if "duplicate" in texto or "23505" in texto or "unique" in texto:
            return "duplicada"
        logger.error("[SAUDACAO] reserva falhou (%s) — esta conversa NÃO será "
                     "saudada nesta rodada", type(e).__name__)
        return "falhou"
