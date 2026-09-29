"""VIGIA DO HANDOFF HUMANO — `HUMAN_REQUESTED` deixa de ser estado sem saída.

📊 03/08/2026, banco de produção: UMA conversa presa em `HUMAN_REQUESTED` há
~730 horas. Trinta dias. A causa não foi a marcação — foi que **nenhum job no
produto olhava `conversations.status`.** O aviso ao suporte sai uma vez, no
instante do pedido; se ninguém viu aquela mensagem, ninguém veria nunca mais, e
o segurado ficou esperando um humano para sempre.

É a MESMA fragilidade que o gatilho da reconciliação de acionamento órfão tinha
(SPEC-063 Bloco E): **um estado que só é observado quando nasce não é
observado.** Este vigia dá a ele um piso — o atraso máximo para alguém ser
lembrado deixa de ser "para sempre" e passa a ser um número.

NADA DE ESCALONAMENTO NOVO
--------------------------
O destino sai de `resolver_destino_de_suporte` — o mesmo resolvedor que recusa
destino compartilhado entre corretoras, porque o dossiê leva CPF do segurado
(CLAUDE.md §7). O texto é o dossiê que `HumanHandoffTool` já monta. O que muda
aqui é só a PERIODICIDADE do lembrete.

POR QUE ESTE ARQUIVO EXISTE, E NÃO UMA FUNÇÃO EM `human_handoff.py`
--------------------------------------------------------------------
`human_handoff.py` mora em `app/agents/tools/`, e importar dali arrasta
`app.agents.__init__` → `graph.py` → `langgraph`. O agendador é registrado por
`start_buffer_scheduler()`, que `main.py` chama **sem `try`** no startup: um
ImportError ali derruba a aplicação inteira, não só este job (CLAUDE.md §9.1 —
"build verde não é prova de que a aplicação sobe").

Então o módulo é leve, e o import pesado acontece DENTRO da função, por
execução, sob `try`. Roda no APScheduler do buffer. Falhas nunca derrubam o
agendador.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

logger = logging.getLogger(__name__)

_ESPERA_ALERTA_MIN_PADRAO = 30      # espera que já constrange
_REALERTA_HORAS_PADRAO = 6          # e a cadência do lembrete depois disso
#: 🔴 SPEC-120 — a janela em que o vigia ainda TENTA DE NOVO um primeiro aviso
#: que NUNCA saiu. Tem de ser MENOR que a reserva do marcador (`realerta_h`):
#: dentro dela, um aviso que saiu ainda está reservado, e por isso nunca se
#: repete. Fora dela, a conversa só é medida.
_AVISO_TARDIO_HORAS_PADRAO = 2
_MAX_POR_PASSADA = 50               # trabalho limitado por varredura


# 🔴 UMA DEFINIÇÃO, DOIS DONOS — 19/08/2026.
#
# `_env_int` e o marcador de Redis moram agora em `human_handoff`, e este
# módulo os importa. Antes o marcador era uma cópia literal daqui, e a partir
# de 18/08 passaram a existir DOIS avisadores da mesma conversa: esta
# varredura e a própria ferramenta (que até então nunca rodava). Duas cópias
# do marcador seriam duas chaves diferentes no Redis, cada uma silenciando só
# a si mesma — e o grupo receberia o dobro dos alertas, que é exatamente o
# problema que o marcador existe para resolver.
#
# A direção do import já existia: este arquivo importa `HumanHandoffTool`
# daquele módulo desde que foi escrito.
#
# ⚠️ TARDIO, e não no topo. `human_handoff` puxa `langchain_core.tools`; um
# import de módulo aqui carregaria o LangChain no boot de uma tarefa de
# varredura e abriria caminho para ciclo de import. O resto deste arquivo já
# importa daquele módulo dentro da função, pelo mesmo motivo.
def _env_int(nome: str, padrao: int, minimo: int = 1) -> int:
    from app.agents.tools.human_handoff import _env_int as _impl

    return _impl(nome, padrao, minimo)


async def _ja_avisado_recentemente(conversa_id: str, horas: int, *,
                                   company_id: str = "", tipo: str = "") -> bool:
    from app.agents.tools.human_handoff import reivindicar_o_aviso

    return await reivindicar_o_aviso(conversa_id, horas,
                                     company_id=company_id, tipo=tipo)


async def _devolver_a_vez(conversa_id: str, *, company_id: str = "",
                          tipo: str = "") -> None:
    from app.agents.tools.human_handoff import devolver_a_vez

    await devolver_a_vez(conversa_id, company_id=company_id, tipo=tipo)


async def _contar_lembrete(conversa_id: str) -> int:
    from app.agents.tools.human_handoff import contar_lembrete

    return await contar_lembrete(conversa_id)


def _max_lembretes() -> int:
    from app.agents.tools.human_handoff import MAX_LEMBRETES_POR_CONVERSA

    return _env_int("HANDOFF_MAX_LEMBRETES", MAX_LEMBRETES_POR_CONVERSA)


async def prova_de_que_o_agente_pediu(db, conversa: Dict[str, Any]) -> bool:
    """🔴 SPEC-121 F1 · D6 (confirmada pelo Founder, 29/09/2026) — a PROVA.

    O aviso tardio só sai com as duas, e cada uma pega o que a outra não pega:

    ```
    ① `human_handoff_reason` preenchido     o `request_human_agent` SEMPRE o
       (e não é o do painel ADMIN)          escreve (MOTIVO_SEM_DECLARACAO no
                                            pior caso); o espelho NUNCA
    ② na conversa, a última fala do AGENTE  o agente estava atendendo quando
       é POSTERIOR à última palavra de gente pediu — não a atendente
    ③ e a última mensagem é do SEGURADO      alguém espera (a regra de 21/08)
    ```

    📊 Por quê (`f1/b0.sql`, 29/09/2026): dos 29 avisos de 21/09, **28** não
    tinham `human_handoff_reason`, e o único que tinha (`dc54572a`, sinistro)
    tinha a última fala do agente ANTES da atendente. Todos saíram pelo status
    `HUMAN_REQUESTED` que o espelho grava quando a ATENDENTE responde.

    ⛔ Na DÚVIDA não há prova: leitura que falha, conversa sem mensagem, lote
    que não mostra a fala do agente — tudo isso é `False` (D4). Lê a conversa
    POR CONVERSA (`janela_de_mensagens`), nunca pelo lote global que o
    PostgREST corta em 1000 linhas.
    """
    try:
        from app.services.o_fim_do_atendimento import (
            MOTIVO_DO_ADMIN, _falas_do_agente, _quando, janela_de_mensagens,
            ultima_palavra_humana,
        )

        motivo = str((conversa or {}).get("human_handoff_reason") or "").strip()
        if not motivo or motivo == MOTIVO_DO_ADMIN:
            return False
        linhas, erro = await janela_de_mensagens(db, str(conversa.get("id") or ""))
        if erro or not linhas:
            return False
        datadas = [(q, m) for q, m in ((_quando((m or {}).get("created_at")), m)
                                       for m in linhas if isinstance(m, dict))
                   if q is not None]
        if not datadas:
            return False
        _, mais_nova = max(datadas, key=lambda par: par[0])
        if str(mais_nova.get("role") or "").strip().lower() != "user":
            return False
        falas = _falas_do_agente(linhas)
        if not falas:
            return False
        do_agente = max(q for q, _ in falas)
        humana = ultima_palavra_humana(linhas)
        return humana is None or do_agente > humana
    except Exception as exc:  # noqa: BLE001
        logger.warning("[HandoffWatchdog] prova do pedido ilegível (%s) — sem aviso",
                       type(exc).__name__)
        return False


def _parado_ha_ms(conversa: Dict[str, Any], agora: datetime) -> float:
    try:
        visto = datetime.fromisoformat(
            str(conversa.get("last_message_at") or "").replace("Z", "+00:00"))
        if visto.tzinfo is None:
            visto = visto.replace(tzinfo=timezone.utc)
        return max(0.0, (agora - visto).total_seconds() * 1000)
    except (TypeError, ValueError):
        return 0.0


async def varrer_handoffs_parados() -> None:
    """Conversa parada em `HUMAN_REQUESTED` → re-alerta o suporte + telemetria."""
    espera_min = _env_int("HANDOFF_ALERTA_MINUTOS", _ESPERA_ALERTA_MIN_PADRAO)
    realerta_h = _env_int("HANDOFF_REALERTA_HORAS", _REALERTA_HORAS_PADRAO)
    _MAX_LEMBRETES = _max_lembretes()
    agora = datetime.now(timezone.utc)
    limite = (agora - timedelta(minutes=espera_min)).isoformat()

    try:
        from app.core.database import get_supabase_client

        bruto = get_supabase_client()
        db = getattr(bruto, "client", bruto)
        if db is None:
            return
        # 🔴 SPEC-085 BLOCO F.2 — `claimed_by` ENTRA NO SELECT.
        #
        # 📊 `HUMAN_REQUESTED` significa DUAS coisas opostas neste produto:
        #
        #   "a IA pediu um humano"     human_handoff.py:608
        #   "um humano JÁ assumiu"     api/dashboard/conversas/[id] (claim)
        #                              e espelho_chat, que grava junto o
        #                              `claimed_by_name`
        #
        # E este select **nem pedia a coluna que distingue as duas**. INFERÊNCIA
        # de alta confiança, agora fechada: uma conversa já assumida por uma
        # pessoa continuava gerando *"ATENDIMENTO PRECISA DE VOCÊ"* a cada 6h
        # sempre que o cliente escrevesse por último.
        #
        # ⚠️ A desambiguação é por DADO, não por estado novo (§F.1, saída (b)):
        # `claimed_by` já existe e já é escrita pelo `claim`. Um estado novo
        # exigiria migration, backfill e todos os leitores — para uma distinção
        # que o dado já carrega.
        paradas = (db.table("conversations")
                   .select("id, company_id, session_id, user_name, user_phone, "
                           "last_message_at, human_handoff_reason, "
                           "claimed_by, claimed_by_name, claimed_at, resolvido_em")
                   .eq("status", "HUMAN_REQUESTED")
                   .lt("last_message_at", limite)
                   # 🔴 SPEC-121 (achado do builder F1): em ordem CRESCENTE o vigia
                   #    lia as 50 MAIS ANTIGAS — 📊 29/09: 475 paradas, a mais nova
                   #    das 50 lidas era de 14/09 — e o aviso tardio (≤ 2 h) nunca
                   #    alcançava um caso recente. As mais novas primeiro.
                   .order("last_message_at", desc=True)
                   .limit(_MAX_POR_PASSADA).execute().data or [])
    except Exception as exc:  # noqa: BLE001
        logger.error("[HandoffWatchdog] não consegui ler as conversas (%s)",
                     type(exc).__name__)
        return

    if not paradas:
        return

    # =====================================================================
    # 🔴 SÓ AVISA QUEM TEM ALGUÉM ESPERANDO — 21/08/2026
    # =====================================================================
    #
    # 📊 O Founder recebeu DEZENAS de "ATENDIMENTO PRECISA DE VOCÊ" no grupo
    # da Resulta, e a frase dele foi: *"não tem coisa pra resolver"*. Tinha
    # razão. As quatro conversas em `HUMAN_REQUESTED` naquele dia terminavam
    # assim:
    #
    #     "Tá bom, obrigado"
    #     "Olha o site desse vídeo. Vai rolando e o carro vai andando."
    #     "Vixi... tô indo então"
    #     "Tem muito passo que ainda não é feito pelo agente"
    #
    # São conversas da própria equipe, capturadas pelo observador. Em TODAS a
    # última mensagem era do lado da corretora — ninguém aguardava resposta.
    #
    # `status = HUMAN_REQUESTED` diz que alguém PEDIU um humano em algum
    # momento. Não diz que alguém ainda espera. A marca é do passado; a
    # pergunta é do presente, e é outra: **a última palavra foi do cliente?**
    #
    # Se foi da corretora, o caso está com a gente, não com ele. Cobrar a
    # equipe nesse estado é o que ensina a ignorar o grupo — e aí, no dia em
    # que um segurado de verdade esperar, ninguém olha. É esse o custo real:
    # não é incômodo, é o alarme perdendo o significado.
    # ⚠️ SPEC-121 F1 — este lote decide só QUEM É MEDIDO (o SLI abaixo). Ele é
    #    cortado pelo PostgREST em 1000 linhas e, na dúvida, trata todas como
    #    pendentes — e por isso NÃO decide mais aviso nenhum: o aviso tardio
    #    lê a conversa inteira, uma a uma (`prova_de_que_o_agente_pediu`).
    ids = [str(c.get("id")) for c in paradas if c.get("id")]
    esperando: set = set(ids)  # sem leitura possível, mantém o comportamento antigo
    try:
        ultimas = (db.table("messages")
                   .select("conversation_id, role, created_at")
                   .in_("conversation_id", ids)
                   .order("created_at", desc=True)
                   .limit(max(200, len(ids) * 30)).execute().data or [])
        vista: Dict[str, str] = {}
        for m in ultimas:  # já vem do mais novo para o mais antigo
            cid = str(m.get("conversation_id") or "")
            if cid and cid not in vista:
                vista[cid] = str(m.get("role") or "")
        if vista:
            # Conversa sem mensagem nenhuma continua elegível: não há motivo
            # para calar sobre um caso que nunca chegou a ter transcrição.
            esperando = {c for c in ids
                         if vista.get(c, "user") == "user"}
    except Exception as exc:  # noqa: BLE001
        # Falha de leitura NÃO pode virar silêncio. Sem saber quem espera,
        # avisa todos — é o comportamento de antes, e o defeito grave aqui
        # sempre foi calar, nunca repetir.
        logger.warning("[HandoffWatchdog] não li quem está esperando (%s) — "
                       "vou tratar todas como pendentes", type(exc).__name__)

    calados = [c for c in paradas if str(c.get("id")) not in esperando]
    if calados:
        logger.info("[HandoffWatchdog] %d conversa(s) em HUMAN_REQUESTED sem "
                    "ninguém esperando (última palavra foi da corretora) — "
                    "não vou cobrar a equipe por elas", len(calados))
    paradas = [c for c in paradas if str(c.get("id")) in esperando]
    if not paradas:
        return

    logger.info("[HandoffWatchdog] %d conversa(s) em HUMAN_REQUESTED há mais de %dmin",
                len(paradas), espera_min)


    for conversa in paradas:
        company_id = str(conversa.get("company_id") or "")
        conversa_id = str(conversa.get("id") or "")
        # Sem company_id não há destino de suporte que se possa resolver com
        # segurança, e mandar o dossiê "para alguém" é vazamento (CLAUDE.md §7).
        if not company_id or not conversa_id:
            logger.error("[HandoffWatchdog] conversa sem company_id — ignorada")
            continue

        parada_ms = _parado_ha_ms(conversa, agora)

        # A TELEMETRIA VEM ANTES DO MARCADOR, e de propósito: ela mede a espera
        # de TODA conversa parada, inclusive as que o marcador vai silenciar. Se
        # dependesse do envio, o número sumiria justamente quando a fila
        # estivesse pior — e o gráfico melhoraria quanto mais gente esperasse.
        #
        # 🔴 E VEM ANTES DO CORTE DE CLAIM TAMBÉM — juiz de confirmação. O corte
        # nasceu ACIMA deste bloco e tirava do `HANDOFF_ESPERA` justamente as
        # conversas que TÊM dono. O comentário dizia "TODA conversa parada"; o
        # código media as sem dono. Contrato quebrado por posição de linha.
        try:
            from app.services.observability import sli

            sli.registrar(sli.HANDOFF_ESPERA, parada_ms, company_id=company_id,
                          contexto={"minutos": round(parada_ms / 60000)})
        except Exception:  # noqa: BLE001
            pass

        # 🔴 SPEC-120 — A ÚNICA COISA QUE O VIGIA AINDA MANDA: o PRIMEIRO aviso
        #    que NUNCA saiu. Não é lembrete.
        #
        # 📊 Achado do juiz (MÉDIO 4). Ao tirar o lembrete, a D16 tirou também a
        # rede de segurança que o desenho CONTAVA existir: `HumanHandoffTool.
        # _arun` reserva o marcador, e se o aviso falha ele o DEVOLVE — o
        # comentário de lá diz *"senão o Vigia fica mudo justamente no caso em
        # que ninguém soube"*. 📊 Com os grupos desativados de 10 a 21/09, é
        # exatamente o caso que existiu: pedido de ajuda que ninguém recebeu.
        # E a regra do Founder tem duas metades — *"um aviso só, na hora"* E
        # *"o agente nunca pode travar sem chamar ninguém"*.
        #
        # Os três limites que impedem isto de virar o lembrete de novo:
        #   ① só caso RECENTE (≤ `_AVISO_TARDIO_HORAS_PADRAO`): o print de 244h
        #      é impossível por construção;
        #   ② só se a vez estiver LIVRE no marcador compartilhado — um primeiro
        #      aviso que SAIU está reservado por `realerta_h`, que é maior que a
        #      janela ①, então nunca se repete;
        #   ③ com humano atendendo, a porta única (`enviar_ao_grupo` →
        #      `o_grupo_pode_saber`) cala, como em todo remetente (D17).
        # ⚠️ O preço declarado: com o Redis fora do ar, `reivindicar_o_aviso`
        #    devolve "a vez é sua" e o aviso pode sair mais de uma vez — mas
        #    só dentro da janela ①.
        _janela_tardia_ms = min(_env_int("HANDOFF_AVISO_TARDIO_HORAS",
                                         _AVISO_TARDIO_HORAS_PADRAO),
                                max(1, realerta_h - 1)) * 3_600_000
        # 🔴 SPEC-121 F1 · D6 — e SÓ COM PROVA de que foi o AGENTE quem pediu.
        #    📊 29 de 29 avisos de 21/09 saíram por `HUMAN_REQUESTED` do espelho
        #    (a atendente respondendo). O status não é prova; o motivo gravado
        #    pelo agente + a fala dele depois da última palavra de gente, é.
        #    ⛔ O motivo inventado ("o segurado pediu para falar com uma
        #    pessoa") saiu: sem motivo do agente, não há aviso.
        if parada_ms <= _janela_tardia_ms and await prova_de_que_o_agente_pediu(
                db, conversa):
            try:
                if not await _ja_avisado_recentemente(conversa_id, realerta_h,
                                                      company_id=company_id):
                    from app.agents.tools.human_handoff import HumanHandoffTool
                    from app.services.o_grupo_so_o_que_importa import (
                        PROVA_PEDIDO_DO_AGENTE,
                    )

                    motivo = str(conversa.get("human_handoff_reason") or "").strip()
                    aviso = await HumanHandoffTool(db)._avisar_suporte(
                        company_id, conversa, motivo, prova=PROVA_PEDIDO_DO_AGENTE)
                    # ⚠️ `calado` NÃO é falha (confirmação do juiz): a porta
                    #    calou porque um humano assumiu (D17). Devolver a vez
                    #    faria o vigia bater nela a cada varredura e inflar o
                    #    "já com a equipe" do resumo das 19h.
                    if not aviso.get("avisado") and not aviso.get("calado"):
                        await _devolver_a_vez(conversa_id, company_id=company_id)
            except Exception as exc:  # noqa: BLE001
                logger.error("[HandoffWatchdog] aviso tardio falhou (%s) | empresa=%s",
                             type(exc).__name__, company_id)
                await _devolver_a_vez(conversa_id, company_id=company_id)

        # =================================================================
        # 🔴 SPEC-120 D16 + D17 — O VIGIA NÃO COBRA MAIS O GRUPO. NUNCA.
        # =================================================================
        #
        # A regra, nas palavras do Founder (28/09/2026):
        #   *"Não deve ficar enviando dossiês antigos. É um aviso só na hora do
        #    atendimento e só se o atendimento for feito pelo agente. Agente não
        #    se mete em atendimento de humano e não envia msg no suporte humano
        #    quando o humano estiver atendendo."*
        #
        # 📊 O que ele viu, e por que esta porta fechou: em 21/09/2026 este
        # varredor mandou **29 lembretes ao grupo no mesmo dia** (14 numa
        # corretora, 15 na outra — `work_events.event_type = handoff.realertado`),
        # sobre conversas paradas há **243 e 244 horas**: tudo o que tinha ficado
        # parado enquanto os grupos de suporte estiveram desativados (10–21/09)
        # saiu de uma vez quando eles voltaram.
        #
        # E a mensagem se contradizia: dizia *"AINDA SEM ATENDIMENTO"* e
        # terminava com *"Atendente pelo celular já assumiu"*. 📊 A causa: este
        # bloco decidia "há dono?" por `claimed_by`, e a atendente que assume
        # PELO CELULAR grava só `claimed_by_name` (`espelho_chat.py:712`) — o
        # porteiro do grupo (`_assumida_com_claim_fresco`) já tinha aprendido
        # isso em 16/09, este bloco não. E mesmo com o campo certo, o desenho da
        # SPEC-085 cobrava de propósito a conversa "assumida e abandonada" — que
        # é exatamente a mensagem que o Founder não quer mais receber.
        #
        # ⚠️ O QUE NÃO SE PERDE: a conversa continua em `HUMAN_REQUESTED`, na
        # **Fila do painel**, e o tempo de espera continua medido pelo SLI logo
        # acima (`HANDOFF_ESPERA`). O que sumiu é o balão repetido no grupo.
        #
        # ⚠️ E o aviso que o Founder QUER continua existindo, em outro lugar e
        # uma vez só: `HumanHandoffTool._arun` → `_avisar_suporte`, na hora em
        # que o agente pede a pessoa. Este varredor nunca foi esse aviso — era o
        # lembrete dele.

# =============================================================================
# 🔴 SPEC-086 BLOCO C — A ESPERA VENCIDA ACORDA ALGUÉM
# =============================================================================
#
# 📊 A razão, medida em 26/08/2026:
#
#     work_runs presos em `queued` ....  5   o mais velho há 29 DIAS
#     a conversa deste módulo .........  ~730 horas (o cabeçalho, linha 3)
#
# ⚠️ E os cinco presos **não são atendimento**: são `intelligence.detect_signals`.
# Isso não os torna menos reais — ninguém foi avisado em 29 dias — mas a prova
# de que o ATENDIMENTO apodrece é a conversa de 730 horas, não eles.
#
# ⛔ ESTE VARREDOR NÃO MANDA MENSAGEM PARA SEGURADO. NENHUMA. NUNCA.
#
# 🔴 Um watchdog que fala com o cliente é um robô que acorda às 3h da manhã. O
# caminho de acordar o segurado já existe, já tem governador
# (`platform_outbound.py`: 12/h · 20 novos/dia · janela · domingo bloqueado) e é
# o BLOCO D da SPEC-093, com corte de 24h e prévia. **Este bloco avisa a
# CORRETORA, e para aí.**
#
# ⚠️ E o destino é o MESMO `_avisar_suporte` do varredor de handoff, de
# propósito: ele já recusa destino compartilhado entre corretoras (§7). Um
# escalonamento novo aqui seria motor paralelo (§5).

_MAX_WAITS_POR_PASSADA = 50

#: O tipo de evento das esperas vencidas. ⚠️ **Tem de ser contável**: a pergunta
#: *"quantas esperas venceram ontem?"* é um `count(*)` sobre este valor.
EVENTO_ESPERA_VENCIDA = "espera.vencida"

#: 🔴 SPEC-086 BLOCO C.1 — O ALERTA DO VIGIA PASSA A SER CONTÁVEL.
#:
#: A SPEC pergunta três coisas sobre o conserto de 21/08, e 📊 medido em
#: 26/08 **nenhuma tem resposta**:
#:
#:     quantos alertas saíram desde o conserto? ..... NÃO DÁ PARA SABER
#:     quantos eram de quem realmente esperava? ..... NÃO DÁ PARA SABER
#:     o teto de lembretes já foi atingido? ......... NÃO DÁ PARA SABER
#:
#: 📊 E a causa está medida: `_avisar_suporte` **não grava em lugar nenhum
#: contável**. `platform_sends` tem 5 linhas na base inteira, todas de outra
#: coisa (`billing`, `acionamento_protocolo`), a mais recente de **19/08** —
#: dois dias ANTES do conserto. E o contador de lembretes vive só no Redis.
#:
#: ⚠️ A SPEC prevê exatamente isto: *"se o dado não existir, esta é a
#: resposta: o conserto não é observável, e torná-lo observável é o trabalho
#: do bloco. ⛔ Não invente que funcionou."*
#:
#: ⛔ E o rastro vai para `work_events`, que JÁ existe e já é contado — não
#: para uma tabela nova (§5).
EVENTO_HANDOFF_REALERTADO = "handoff.realertado"
EVENTO_HANDOFF_NO_TETO = "handoff.teto_de_lembretes"
#: 🔴 SPEC-EXTRA-001.3 §7.2 — o 2º e o 3º aviso da MESMA espera. Eles
#: não vão ao grupo; viram linha do resumo das 19h.
EVENTO_ESPERA_REPETIDA = "espera.vencida.repetida"

#: Como o alerta descreve o que se esperava. ⛔ Sem nome de pessoa.
#: Como se diz cada kind **para a EQUIPE**. ⚠️ 🔴 A fonte dos kinds é
#: `o_fim_do_atendimento.KINDS` (lente DADO+verdade: três listas dos mesmos
#: três valores); o que muda aqui é a FRASE, e ela é de outra audiência — o
#: segurado lê *"esperando você mandar o que falta"*, a atendente lê
#: *"o segurado"*. ⛔ O `.get(..., "alguém")` abaixo é o que impede que um kind
#: novo vire alerta quebrado: ele degrada para uma palavra honesta.
_ROTULO_DO_KIND = {
    "esperando_cliente": "o segurado",
    "esperando_seguradora": "a seguradora",
    "esperando_humano": "alguém da corretora",
}


async def _anotar_no_diario(db, company_id: str, tipo: str, mensagem: str,
                            carga: Dict[str, Any]) -> None:
    """Uma linha contável em `work_events`. ⛔ **Nunca levanta.**

    🔴 SPEC-086 BLOCO C.1. Sem isto, *"quantos alertas saíram?"* não tem
    resposta — e a pergunta é a diferença entre um alarme calibrado e um
    alarme que a corretora desliga na segunda semana.

    ⚠️ `work_run_id` fica NULO: o alerta de handoff é de uma CONVERSA, e
    📊 há 4 `work_runs` de acionamento contra 671 conversas. Forçar um run
    aqui seria inventar origem.

    ⛔ E a carga **nunca** leva nome, telefone ou texto de mensagem: quem
    guarda conteúdo é o Espelho, e `payload_redacted` tem esse nome por um
    motivo.
    """
    try:
        await asyncio.to_thread(
            lambda: db.table("work_events").insert({
                "company_id": str(company_id),          # 🔴 §7
                "event_type": tipo,
                "actor_type": "system",
                "severity": "warning",
                "message_human": mensagem[:400],
                "payload_redacted": carga,
            }).execute())
    except Exception as exc:  # noqa: BLE001
        logger.warning("[HandoffWatchdog] diário não escrito (%s) — o alerta saiu, mas ele não vai aparecer na contagem", type(exc).__name__)


async def varrer_esperas_vencidas() -> Dict[str, int]:
    """`work_waits` vencidos → evento + alerta à CORRETORA + `expirou` no fim.

    ⛔ **Nunca levanta.** Roda no APScheduler do buffer, ao lado do varredor de
    handoff. Uma exceção aqui não derruba o agendador — mas derrubar o job em
    silêncio é exatamente como a espera volta a apodrecer.
    """
    resumo = {"vencidas": 0, "avisadas": 0, "expiradas": 0, "erros": 0,
              "caladas": 0}
    try:
        from app.core.database import create_async_supabase_client
        # ⚠️ Só o teto de avisos é lido aqui: quem escreve status e quem decide
        #    o FIM é `_contar_o_aviso`, e ele importa o que precisa (§5 — uma
        #    decisão, um lugar).
        from app.services.o_fim_do_atendimento import AVISOS_ATE_EXPIRAR

        db = await create_async_supabase_client()
        agora_iso = datetime.now(timezone.utc).isoformat()

        # ⚠️ A varredura é GLOBAL de propósito — como a de handoff. O que
        #    protege não é o filtro DESTA leitura: é que TODA ação abaixo carrega
        #    o `company_id` **da própria linha** (§7).
        achado = await (db.client.table("work_waits")
                        .select("id, company_id, conversation_id, work_run_id, "
                                "kind, scope, vence_em, avisos")
                        .eq("status", "ativo")
                        .lte("vence_em", agora_iso)
                        .order("vence_em")
                        .limit(_MAX_WAITS_POR_PASSADA).execute())
        vencidas = achado.data or []
    except Exception as exc:  # noqa: BLE001
        logger.error("[EsperaWatchdog] não consegui ler as esperas (%s)",
                     type(exc).__name__)
        resumo["erros"] += 1
        return resumo

    if not vencidas:
        return resumo
    resumo["vencidas"] = len(vencidas)

    # ⚠️ 📊 O teto de 50 por passada é DECLARADO, não silencioso — a lição da
    #    P-090-03. Se ele encher, esta linha é o único aviso que existe.
    if len(vencidas) >= _MAX_WAITS_POR_PASSADA:
        logger.warning("[EsperaWatchdog] a passada ENCHEU (%d esperas vencidas) — "
                       "há mais que não foram olhadas nesta rodada",
                       _MAX_WAITS_POR_PASSADA)

    # 🔴 UM ALARME POR CONVERSA, E A CONVERSA É A UNIDADE — [2c] do red team.
    #
    # 📊 A mesma conversa pode ter DUAS esperas ativas ao mesmo tempo, e a
    # SPEC-097.1 criou isso de propósito: o travamento do corredor
    # (`scope='acionamento'`) e a espera da seguradora (`pos_acionamento`)
    # convivem porque o `UNIQUE` é por escopo. Varrendo por LINHA, o grupo da
    # corretora recebia **dois alertas por passada sobre a mesma pessoa** — seis
    # em trinta minutos. ⚠️ O próprio `_anotar_no_diario` já diz por que isso é
    # dano e não ruído: alarme repetido é como se ensina uma equipe a ignorar
    # alarme.
    por_conversa: Dict[str, list] = {}
    for wait in vencidas:
        chave = "%s|%s" % (str(wait.get("company_id") or ""),
                           str(wait.get("conversation_id") or ""))
        por_conversa.setdefault(chave, []).append(wait)

    for chave, esperas in por_conversa.items():
        empresa, _, conversa_id = chave.partition("|")
        if not empresa or not conversa_id:
            continue
        # O contador do alarme é o MAIOR das esperas da conversa: é o que
        # responde "há quanto tempo esta conversa está sendo cobrada".
        avisos = max(int(w.get("avisos") or 0) for w in esperas) + 1

        for wait in esperas:
            await _uma_espera_vencida(db, wait, empresa, conversa_id,
                                      agora_iso, resumo)

        # ---- ② o alerta À CORRETORA — ⛔ NUNCA ao segurado, UM por conversa --
        try:
            conversa = await (db.client.table("conversations")
                              .select("id, company_id, session_id, user_name, "
                                      "user_phone, human_handoff_reason")
                              .eq("company_id", empresa)     # 🔴 §7
                              .eq("id", conversa_id).limit(1).execute())
            linhas = conversa.data or []
            if linhas:
                from app.agents.tools.human_handoff import HumanHandoffTool

                rotulos = []
                for w in esperas:
                    r = _ROTULO_DO_KIND.get(str(w.get("kind") or ""), "alguém")
                    if r not in rotulos:
                        rotulos.append(r)
                # 🔴 SPEC-EXTRA-001.3 §7.2 — UM AVISO AO GRUPO POR VENCIMENTO.
                #
                # 📊 10/09/2026: saíram 3 avisos idênticos em 20 minutos
                # (18:09:58, 18:19:58, 18:29:59) sobre a MESMA espera, porque o
                # job roda a cada 10 min e `AVISOS_ATE_EXPIRAR` é 3.
                #
                # ⚠️ Os avisos 2 e 3 NÃO SOMEM: viram linha do resumo das 19h
                # (*"2 esperas venceram e ninguém respondeu"*). ⛔ E
                # `AVISOS_ATE_EXPIRAR` CONTINUA 3 para o ciclo interno de
                # expiração: quem corta o contador quebra
                # `deve_expirar_a_conversa` (`o_fim_do_atendimento.py:949`) e a
                # conversa NUNCA expira. O que muda é quantos CHEGAM ao grupo.
                from app.services.o_grupo_so_o_que_importa import (
                    PROVA_ESPERA_DO_AGENTE, TIPO_ESPERA_VENCIDA, anotar_no_diario,
                )

                # ⛔ NADA DE `continue` AQUI. Abaixo deste bloco vêm ②b (a
                # mensagem honesta ao segurado) e ③ (`_contar_o_aviso`, que é
                # quem incrementa `avisos` e faz a conversa EXPIRAR). Pular o
                # laço para "não mandar ao grupo" calaria o segurado e deixaria
                # a conversa presa para sempre — trocar um excesso de aviso por
                # um silêncio é trocar um defeito por um pior (:241).
                if avisos > 1:
                    await anotar_no_diario(
                        db, empresa, EVENTO_ESPERA_REPETIDA,
                        "Uma espera continuou vencida e ninguém respondeu.",
                        {"aviso": int(avisos), "de": int(AVISOS_ATE_EXPIRAR),
                         "conversa": str(conversa_id)[:8],
                         "rotulos": list(rotulos)[:3]},
                        severidade="warning")
                    logger.info("[EsperaWatchdog] aviso %d de %d fica para o "
                                "resumo das 19h — o grupo já soube",
                                avisos, AVISOS_ATE_EXPIRAR)
                else:
                    texto = (f"⏳ ESPERA VENCIDA — esperava {' e '.join(rotulos)} "
                             f"e o prazo passou.")
                    # 🔴 SPEC-121 F1 — regra B: toda `work_waits` nasce do
                    #    acionamento do agente (`dispatch_router.abrir_espera`,
                    #    os dois únicos escritores). A e C a porta confere.
                    aviso = await HumanHandoffTool(db)._avisar_suporte(
                        empresa, linhas[0], texto, tipo=TIPO_ESPERA_VENCIDA,
                        prova=PROVA_ESPERA_DO_AGENTE)
                    if aviso.get("avisado"):
                        resumo["avisadas"] += 1
                    elif aviso.get("calado"):
                        resumo["caladas"] = int(resumo.get("caladas") or 0) + 1
                    else:
                        logger.error("[EsperaWatchdog] ❌ espera vencida e o suporte "
                                     "NÃO foi avisado | empresa=%s | motivo=%s",
                                     empresa, aviso.get("motivo"))
        except Exception as exc:  # noqa: BLE001
            logger.error("[EsperaWatchdog] falha ao avisar (%s) | empresa=%s",
                         type(exc).__name__, empresa)
            resumo["erros"] += 1

        # ---- ②b A MENSAGEM HONESTA AO CLIENTE (SPEC-097.1 U5.2) -------------
        #
        # 🔴 SÓ no escopo do PÓS-ACIONAMENTO. A espera do TRAVAMENTO
        # (`scope='acionamento'`) segue exatamente como hoje: avisa a equipe e
        # não fala com o segurado — quem está travado é o corredor, e dizer ao
        # cliente "ainda sem novidade" quando o robô é que parou seria mentir
        # sobre de quem se espera.
        #
        # 🔴 E ela sai pela PORTA ÚNICA do acompanhamento, nunca por saída
        # própria. ⚠️ O bloco ② acima manda o dossiê para o GRUPO DA CORRETORA;
        # mandar por ali o texto do segurado entregaria a mensagem dele à equipe
        # e não a ele. São dois destinos diferentes, e é por isso que são duas
        # chamadas.
        #
        # 🔴 **UMA POR VENCIMENTO, não uma por aviso** — [2b] do red team.
        # 📊 `MENSAGEM_SEM_NOVIDADE` é uma CONSTANTE: "uma por aviso até o teto"
        # entregava ao segurado a **mesma frase três vezes em trinta minutos**.
        # A equipe continua sendo reavisada; o cliente é avisado quando o prazo
        # vira, e depois disso o produto tem a decência de calar até haver
        # notícia de verdade.
        primeiro_vencimento = [w for w in esperas
                               if str(w.get("scope") or "") == "pos_acionamento"
                               and int(w.get("avisos") or 0) == 0]
        if primeiro_vencimento:
            try:
                from app.atendimento.acompanhamento import (
                    MENSAGEM_SEM_NOVIDADE, entregar_novidade,
                )

                await entregar_novidade(
                    db, company_id=empresa,                  # 🔴 §7 — da LINHA
                    conversation_id=conversa_id,
                    texto=MENSAGEM_SEM_NOVIDADE,
                    gatilho="espera_vencida")
            except Exception as exc:  # noqa: BLE001
                logger.warning("[EsperaWatchdog] novidade ao cliente não gerada "
                               "(%s) | empresa=%s", type(exc).__name__, empresa)
                resumo["erros"] += 1

        # ---- ③ o contador, e o FIM depois de N ------------------------------
        for wait in esperas:
            await _contar_o_aviso(db, wait, empresa, conversa_id, agora_iso,
                                  resumo)

    logger.info("[EsperaWatchdog] vencidas=%(vencidas)d avisadas=%(avisadas)d "
                "expiradas=%(expiradas)d erros=%(erros)d", resumo)
    return resumo


async def _uma_espera_vencida(db, wait, empresa: str, conversa_id: str,
                              agora_iso: str, resumo: Dict[str, int]) -> None:
    """① O evento CONTÁVEL — um por ESPERA, sempre.

    ⚠️ O evento continua por LINHA mesmo com o alarme por conversa: quem conta
    esperas vencidas no digest precisa de uma por espera, e o `payload_redacted`
    já carrega o escopo que as distingue.
    """
    avisos = int(wait.get("avisos") or 0) + 1

    # 🔴 `work_events.work_run_id` é NOT NULL, com FK composta — achado da lente
    # DADO+verdade. 📊 Só 4 de 729 conversas têm `work_run`: para as outras 725
    # este INSERT VIOLA a coluna, cai no `except` e vira um warning por passada.
    # ⚠️ A espera vencida não fica sem registro: o `avisos` da própria linha de
    # `work_waits` é o contador durável, e o alerta à corretora saiu.
    if not str(wait.get("work_run_id") or "").strip():
        logger.info("[EsperaWatchdog] espera sem `work_run_id` — o vencimento "
                    "fica em `work_waits.avisos` (work_events exige a sombra)")
        return
    try:
        await db.client.table("work_events").insert({
            "company_id": empresa,                       # 🔴 §7
            "work_run_id": wait.get("work_run_id"),
            "event_type": EVENTO_ESPERA_VENCIDA,
            "actor_type": "system",
            "severity": "warning",
            "message_human": ("Uma espera do atendimento venceu e ninguém "
                              "agiu. A corretora foi avisada."),
            # ⛔ Sem dado de pessoa: quem guarda o conteúdo é o Espelho, e
            #    `payload_redacted` tem esse nome por um motivo.
            "payload_redacted": {"kind": str(wait.get("kind") or ""),
                                 "scope": str(wait.get("scope") or ""),
                                 "avisos": avisos,
                                 "vence_em": str(wait.get("vence_em") or "")},
        }).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[EsperaWatchdog] evento não gravado (%s)", type(exc).__name__)
        resumo["erros"] += 1


async def _contar_o_aviso(db, wait, empresa: str, conversa_id: str,
                          agora_iso: str, resumo: Dict[str, int]) -> None:
    """③ O contador da espera — e o FIM do atendimento, que **não é de todo escopo**.

    🔴 **`pos_acionamento` NUNCA encerra o caso** — [2] do red team, e é defeito
    de PRODUTO. 📊 O caso do pós-acionamento dura 6,9 dias (mediana); com três
    avisos de 10 em 10 minutos o vigia escrevia `resolvido_em` e
    `resolucao_motivo='expirou'` **meia hora depois do prazo**, com a seguradora
    ainda devendo resposta. Nem a SPEC nem a R10 pedem isso: R10 diz que a fase
    *"termina no desfecho"*, e um desfecho fabricado pelo relógio não é desfecho.

    ⚠️ **A ESPERA, essa sim, sai de `ativo`** — ela venceu, e isso é verdade. O
    que morre é a espera; o atendimento do segurado continua aberto, e a
    corretora segue vendo a conversa na fila.

    ⛔ E o status escrito é `'vencido'`, não `'expirou'`: `ck_work_waits_status`
    conhece quatro valores (`ativo`, `satisfeito`, `vencido`, `cancelado`) e
    esta SPEC não aplica migration. `expirou` é motivo de CONVERSA, nunca status
    de espera — e era justamente confundir os dois que fechava o atendimento.

    🔴 O `.eq("status", "ativo")` no UPDATE também é conserto: sem ele, uma
    espera que `marcar_fim` acabou de satisfazer no mesmo instante voltava a
    `vencido` com `satisfeito_por='desfecho'` — duas verdades na mesma linha.
    """
    from app.services.o_fim_do_atendimento import (
        ESCOPO_POS_ACIONAMENTO, EXPIROU, VENCIDO, deve_expirar_a_conversa,
        marcar_fim,
    )

    avisos = int(wait.get("avisos") or 0) + 1
    try:
        campos = {"avisos": avisos, "updated_at": agora_iso}
        if deve_expirar_a_conversa({"avisos": avisos}):
            campos["status"] = VENCIDO
        await (db.client.table("work_waits").update(campos)
               .eq("company_id", empresa)                # 🔴 §7
               .eq("status", "ativo")                    # ⛔ nunca reabre o que fechou
               .eq("id", str(wait["id"])).execute())
        if campos.get("status") != VENCIDO:
            return
        if str(wait.get("scope") or "") == ESCOPO_POS_ACIONAMENTO:
            logger.info("[EsperaWatchdog] espera de pós-acionamento vencida em "
                        "definitivo (conversa %s…) — o vigia para de falar, e o "
                        "atendimento SEGUE ABERTO", conversa_id[:8])
            return
        marcou, _ = await marcar_fim(db, company_id=empresa, motivo=EXPIROU,
                                     conversation_id=conversa_id,
                                     quando_iso=agora_iso)
        if marcou:
            resumo["expiradas"] += 1
    except Exception as exc:  # noqa: BLE001
        logger.warning("[EsperaWatchdog] contador não atualizado (%s)",
                       type(exc).__name__)
        resumo["erros"] += 1
