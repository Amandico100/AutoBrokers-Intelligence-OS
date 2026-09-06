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


async def _ja_avisado_recentemente(conversa_id: str, horas: int) -> bool:
    from app.agents.tools.human_handoff import reivindicar_o_aviso

    return await reivindicar_o_aviso(conversa_id, horas)


async def _devolver_a_vez(conversa_id: str) -> None:
    from app.agents.tools.human_handoff import devolver_a_vez

    await devolver_a_vez(conversa_id)


async def _contar_lembrete(conversa_id: str) -> int:
    from app.agents.tools.human_handoff import contar_lembrete

    return await contar_lembrete(conversa_id)


def _max_lembretes() -> int:
    from app.agents.tools.human_handoff import MAX_LEMBRETES_POR_CONVERSA

    return _env_int("HANDOFF_MAX_LEMBRETES", MAX_LEMBRETES_POR_CONVERSA)


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
                   .order("last_message_at", desc=False)
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

    try:
        from app.agents.tools.human_handoff import HumanHandoffTool
    except Exception as exc:  # noqa: BLE001
        logger.error("[HandoffWatchdog] ferramenta de handoff indisponível (%s)",
                     type(exc).__name__)
        return

    for conversa in paradas:
        company_id = str(conversa.get("company_id") or "")
        conversa_id = str(conversa.get("id") or "")
        # Sem company_id não há destino de suporte que se possa resolver com
        # segurança, e mandar o dossiê "para alguém" é vazamento (CLAUDE.md §7).
        if not company_id or not conversa_id:
            logger.error("[HandoffWatchdog] conversa sem company_id — ignorada")
            continue

        # 🔴 CLAIM FRESCO CALA; CLAIM ABANDONADO NÃO — painel da SPEC-085.
        #
        # A primeira versão deste conserto filtrava `claimed_by IS NULL` **na
        # consulta**, e estava errada pelo lado que importa: uma conversa
        # ASSUMIDA E ABANDONADA — alguém clicou em assumir, foi almoçar e não
        # voltou — ficava PERMANENTEMENTE invisível ao Vigia. Antes do conserto
        # ela gerava lembrete: chato, mas visível. Depois, silêncio.
        #
        # ⚠️ Trocar um excesso de aviso por um silêncio é trocar um defeito por
        # um pior — é literalmente o que a SPEC-086 existe para impedir, por
        # uma porta nova.
        #
        # A regra é por IDADE do claim, não pela existência dele. Enquanto a
        # pessoa está com o caso na mão (menos que a cadência de re-alerta), o
        # Vigia cala. Passado isso, ele volta a cobrar — e o texto DIZ que
        # alguém assumiu, porque cobrar "ninguém assumiu" de um caso que tem
        # dono é a mesma mentira ao contrário.
        _dono = str(conversa.get("claimed_by") or "").strip()

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

        if _dono:
            # 🔴 `claimed_at` ILEGÍVEL AVISA, NÃO CALA — juiz de confirmação.
            #
            # 📊 `_parado_ha_ms` devolve **0.0** para `None` e para `""`. Com o
            # corte escrito como "idade < janela ⇒ continue", uma data ausente
            # ou ilegível dava 0, passava no corte e calava a conversa **para
            # sempre** — o mesmo furo que este bloco existe para fechar, mudado
            # de `claimed_by` para `claimed_at`.
            #
            # A regra do módulo é "na dúvida, avisa". Data que não dá para ler
            # é dúvida, então o claim conta como VELHO e o Vigia cobra.
            _quando = conversa.get("claimed_at")
            _idade_claim_ms = (_parado_ha_ms({"last_message_at": _quando}, agora)
                               if _quando else None)
            _janela_ms = realerta_h * 3_600_000
            if _idade_claim_ms is not None and _idade_claim_ms < _janela_ms:
                continue
            logger.warning(
                "[HandoffWatchdog] conversa ASSUMIDA e parada há mais de %sh "
                "(ou sem data de claim legível) — o dono não voltou. empresa=%s",
                realerta_h, company_id)

        if await _ja_avisado_recentemente(conversa_id, realerta_h):
            continue

        # 🔴 O TETO — e ele avisa que vai calar, em vez de sumir.
        #
        # Quatro lembretes a cada 6h cobrem 24 horas. Passado isso, mais
        # mensagem não resolve: o que falta é gente, não aviso. E repetir para
        # sempre é o jeito mais rápido de a equipe aprender a rolar o grupo
        # sem ler — que é o defeito que este vigia existe para evitar.
        #
        # A ÚLTIMA mensagem diz que é a última. Parar em silêncio seria
        # trocar um defeito por outro pior.
        _n = await _contar_lembrete(conversa_id)
        if _n > _MAX_LEMBRETES:
            # 🔴 SPEC-085 BLOCO F.3 — o teto deixa de ser um `continue` MUDO.
            #
            # Ele estava certo em calar o grupo e errado em calar o REGISTRO:
            # uma conversa passando do teto é o sinal mais forte que existe de
            # que ninguém assumiu em 24 horas, e ele não aparecia em lugar
            # nenhum. Quem olhasse o log via a conversa sumir.
            #
            # ⚠️ E a promessa da última mensagem — *"ela continua na Fila do
            # painel, de lá ninguém a tira sozinho"* — só é verdade porque o
            # `release` parou de devolver a conversa para `open` quando o
            # handoff ainda está aberto (E.4). As duas coisas são um conserto
            # só; separadas, esta frase seria mentira.
            logger.warning(
                "[HandoffWatchdog] conversa passou do teto de %s lembretes e o "
                "grupo NÃO será avisado de novo — ela segue na Fila, esperando "
                "alguém. empresa=%s", _MAX_LEMBRETES, company_id)
            # 🔴 SPEC-086 BLOCO C.1 — O TETO DEIXA DE SER INVISÍVEL.
            #
            # A SPEC pergunta: *"o teto já foi atingido alguma vez? (se nunca,
            # ou ele é frouxo demais, ou não há volume — e as duas conclusões
            # são diferentes)"*. ⛔ Sem esta linha, a resposta continuaria
            # sendo um `logger.warning` que ninguém consegue contar.
            await _anotar_no_diario(
                db, company_id, EVENTO_HANDOFF_NO_TETO,
                "Uma conversa passou do teto de lembretes: o grupo não será avisado de novo, e ela segue na Fila.",
                {"teto": _MAX_LEMBRETES, "lembretes": _n,
                 "parada_ms": int(parada_ms), "tem_dono": bool(_dono)})
            continue
        _ultimo = _n == _MAX_LEMBRETES

        horas = parada_ms / 3_600_000
        espera = f"{horas:.0f}h" if horas >= 1 else f"{parada_ms / 60000:.0f}min"
        if _dono:
            motivo = (f"⏳ ASSUMIDA POR {conversa.get('claimed_by_name') or 'alguém'} "
                      f"E PARADA há {espera} — "
                      f"{conversa.get('human_handoff_reason') or 'motivo não registrado'}")
        else:
            motivo = (f"⏳ AINDA SEM ATENDIMENTO há {espera} — "
                      f"{conversa.get('human_handoff_reason') or 'motivo não registrado'}")
        if _ultimo:
            motivo += ("\n\n🔕 Este é o ÚLTIMO lembrete automático desta "
                       "conversa. Ela continua na Fila do painel — de lá "
                       "ninguém a tira sozinho.")
        try:
            aviso = await HumanHandoffTool(db)._avisar_suporte(company_id, conversa, motivo)
            if aviso.get("avisado"):
                logger.info("[HandoffWatchdog] re-alerta enviado | empresa=%s | espera=%s",
                            company_id, espera)
                # 🔴 SPEC-086 BLOCO C.1 — *"quantos alertas saíram?"* passa
                #    a ter resposta, e por corretora.
                await _anotar_no_diario(
                    db, company_id, EVENTO_HANDOFF_REALERTADO,
                    "O vigia lembrou a corretora de uma conversa parada.",
                    {"lembretes": _n, "ultimo": bool(_ultimo),
                     "parada_ms": int(parada_ms), "tem_dono": bool(_dono)})
            else:
                # Ninguém foi avisado, de novo. Isto é o incidente — e agora ele
                # tem uma linha de log com o motivo, em vez de nenhuma.
                logger.error("[HandoffWatchdog] ❌ conversa parada há %s e o suporte "
                             "NÃO foi avisado | empresa=%s | motivo=%s",
                             espera, company_id, aviso.get("motivo"))
                # 🔴 DEVOLVE A VEZ. A linha acima reservou o direito de avisar
                # e o aviso não saiu; manter a reserva calaria a próxima
                # varredura pelas horas inteiras do marcador, justamente no
                # caso em que ninguém ficou sabendo.
                await _devolver_a_vez(conversa_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("[HandoffWatchdog] falha ao re-alertar (%s) | empresa=%s",
                         type(exc).__name__, company_id)
            await _devolver_a_vez(conversa_id)

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
    resumo = {"vencidas": 0, "avisadas": 0, "expiradas": 0, "erros": 0}
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
                texto = (f"⏳ ESPERA VENCIDA — esperava {' e '.join(rotulos)} e o "
                         f"prazo passou. (aviso {avisos} de {AVISOS_ATE_EXPIRAR})")
                aviso = await HumanHandoffTool(db)._avisar_suporte(
                    empresa, linhas[0], texto)
                if aviso.get("avisado"):
                    resumo["avisadas"] += 1
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
