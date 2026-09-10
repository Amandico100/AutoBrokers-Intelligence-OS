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


# =============================================================================
# 🔴 A JANELA DO FOLLOW-UP — decisão do Founder, 08/09/2026
# =============================================================================
#
# > *"O follow-up tem que sair um tempo DEPOIS do horário que o prestador
# >  combinou. E nunca depois das 19h nem antes das 8h — o que cair fora fica
# >  para o outro dia."*
#
# 🔴 **Por que 8–19 e não a janela que já existe.** `platform_outbound` tem uma
# janela de envio (`dentro_da_janela`, 08:00–20:00, domingo bloqueado) e ela
# governa o OUTBOUND DA PLATAFORMA — prospecção fria, mensagem que ninguém
# pediu. O follow-up é outra coisa: é a continuação de um atendimento que o
# próprio segurado abriu, e o Founder fixou 19h para ele.
#
# ⚠️ **O que NÃO é duplicado:** o leitor de fuso. `fuso_da_corretora` é
# importado de `platform_outbound` — dois lugares lendo
# `AGENT_OS_TENANT_TIMEZONE` com padrões diferentes é exatamente o motor
# paralelo que a `CLAUDE.md` §5 proíbe. O que muda aqui é a POLÍTICA (as horas),
# não o mecanismo.
#
# ⛔ E o domingo NÃO é bloqueado de propósito: guincho, chaveiro e encanador
# acontecem no domingo, e perguntar "o prestador foi?" na segunda-feira sobre um
# serviço de domingo é perguntar tarde demais para servir de alguma coisa.
HORA_ABRE = 8
HORA_FECHA = 19


def fuso_da_corretora(tz: Any = None):
    """O fuso em que a janela é lida — **o mesmo leitor do outbound**.

    Aceita um nome (`'America/Manaus'`), um `tzinfo` já pronto, ou `None`
    (`AGENT_OS_TENANT_TIMEZONE`, senão `America/Sao_Paulo`).
    """
    from datetime import tzinfo as _tzinfo

    if isinstance(tz, _tzinfo):
        return tz
    from app.services.platform_outbound import fuso_da_corretora as _leitor

    return _leitor(tz if isinstance(tz, str) and tz.strip() else None)


def _com_fuso(quando: Any, padrao: Any):
    """Datetime ingênuo ganha o fuso `padrao`; o que já tem fuso é respeitado."""
    return quando if quando.tzinfo is not None else quando.replace(tzinfo=padrao)


def _empurrar_para_a_janela(local: Any) -> Any:
    """Um instante LOCAL cai dentro de 08:00–19:00 — ou vai para a manhã seguinte.

    🔴 **PURA.** É a única regra de horário deste produto, e ela precisa
    conseguir ficar vermelha: `18:59` sai `18:59`, `19:00` sai `08:00 do dia
    seguinte`. Um guarda que aceitasse os dois não guardaria nada (§9.3).
    """
    from datetime import timedelta

    if local.hour < HORA_ABRE:
        return local.replace(hour=HORA_ABRE, minute=0, second=0, microsecond=0)
    if local.hour >= HORA_FECHA:
        amanha = local + timedelta(days=1)
        return amanha.replace(hour=HORA_ABRE, minute=0, second=0, microsecond=0)
    return local


def calcular_envio_do_follow_up(agora_utc: Any,
                                horario_combinado_local: Any = None,
                                espera_min: int = 90,
                                tz: Any = None) -> Any:
    """Quando o *"o prestador foi? deu tudo certo?"* deve sair — **PURA**, em UTC.

    ```
    base  = o horário que o prestador COMBINOU, quando se sabe
            (fim do período, se ele veio como 'manhã'/'tarde')
            senão, o momento do protocolo — que é `agora`
    envio = base + espera
    janela: < 08:00 → 08:00 do MESMO dia · >= 19:00 → 08:00 do dia SEGUINTE
    ```

    ⚠️ **Nunca no passado.** Um agendamento que já passou (a seguradora
    respondeu tarde, o corredor reprocessou) daria um envio anterior a `agora`,
    e a espera nasceria vencida — o vigia dispararia na passada seguinte, sem
    esperar nada. O `max` corrige antes da janela, nunca depois: corrigir depois
    devolveria o envio para fora do horário.
    """
    from datetime import timedelta, timezone

    fuso = fuso_da_corretora(tz)
    agora = _com_fuso(agora_utc, timezone.utc).astimezone(fuso)
    base = (agora if horario_combinado_local is None
            else _com_fuso(horario_combinado_local, fuso).astimezone(fuso))

    envio = base + timedelta(minutes=max(1, int(espera_min)))
    if envio < agora:
        envio = agora
    return _empurrar_para_a_janela(envio).astimezone(timezone.utc)


def dentro_da_janela_do_follow_up(agora_utc: Any = None, tz: Any = None) -> bool:
    """Dá para falar com o segurado AGORA? — **PURA** e **falha FECHADA**.

    ⛔ Qualquer erro devolve `False`. Não saber que horas são na casa do cliente
    é razão para calar, nunca para mandar mensagem às 3 da manhã.

    ⚠️ 📊 **Um nome de fuso inválido NÃO é um erro aqui**, e é bom saber:
    `platform_outbound.fuso_da_corretora:382-388` cai em `UTC-3` de propósito
    (contêiner sem `tzdata`). O `except` abaixo pega o que sobra — o leitor
    ausente, o relógio que não responde.
    """
    from datetime import datetime, timezone

    try:
        fuso = fuso_da_corretora(tz)
        agora = _com_fuso(agora_utc or datetime.now(timezone.utc), timezone.utc)
        local = agora.astimezone(fuso)
        return HORA_ABRE <= local.hour < HORA_FECHA
    except Exception as erro:  # noqa: BLE001
        logger.warning("[ACOMPANHAMENTO] janela local desconhecida (%s) — calando",
                       type(erro).__name__)
        return False


#: 📊 O formato REAL de `session['captured']['schedule']`
#: (`corridor_playbooks.extract_capture_anchors:9010-9040`), e são três:
#: `{day, at}` (auto) · `{day, from, to}` (janela da Porto) · `{day, periodo}`
#: (residencial). Os dois primeiros já viram instante em
#: `dispatch_router._prazo_do_agendamento`; o terceiro é recusado lá **de
#: propósito** — 'tarde' não é uma hora, e virar uma seria inventar.
#: ⚠️ Aqui ele NÃO vira previsão para o cliente: vira só a BASE do follow-up,
#: que é uma pergunta ("deu tudo certo?"), não uma promessa.
_FIM_DO_PERIODO = ((("manh",), 12), (("tarde", "vesper"), 18), (("noite",), 19))


def fim_do_periodo_combinado(schedule: Any, tz: Any = None) -> Any:
    """`{day, periodo}` → o FIM do período, em UTC. `None` quando não dá para saber.

    🔴 **Recusa é resposta.** Dia ilegível, período que não é manhã/tarde/noite
    → `None`, e o chamador cai no momento do protocolo. Chutar aqui faria o
    produto perguntar "o prestador foi?" antes de o prestador ter ido.
    """
    import re as _re
    from datetime import datetime, timezone

    if not isinstance(schedule, dict):
        return None
    dia_bruto = str(schedule.get("day") or "").strip()
    periodo = str(schedule.get("periodo") or "").strip().lower()
    if not dia_bruto or not periodo:
        return None

    # ⚠️ O dia vem com o nome da semana colado ('quinta-feira 20/08/2026'), e
    #    `instante_br` casa a string INTEIRA (`^...$`). Extrair o `dd/mm` é o
    #    que faz o motor de verdade ser chamado, em vez de um parser próprio.
    achado = _re.search(r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?", dia_bruto)
    if not achado:
        return None
    ano = achado.group(3) or str(datetime.now(timezone.utc).year)

    # A hora do FIM: a última do texto ('tarde das 13:00 as 18:00' → 18), e o
    # padrão do rótulo quando o texto não traz hora nenhuma.
    horas = _re.findall(r"(\d{1,2})\s*[:h]\s*(\d{2})?", periodo)
    if horas:
        hora, minuto = int(horas[-1][0]), int(horas[-1][1] or 0)
    else:
        hora, minuto = 0, 0
        for apelidos, padrao in _FIM_DO_PERIODO:
            if any(a in periodo for a in apelidos):
                hora = padrao
                break
        if not hora:
            return None
    if not (0 <= hora <= 23 and 0 <= minuto <= 59):
        return None

    from app.services.o_fim_do_atendimento import instante_br

    iso = instante_br("%s/%s/%s %02d:%02d" % (achado.group(1), achado.group(2),
                                              ano, hora, minuto))
    if not iso:
        return None
    return datetime.fromisoformat(iso).astimezone(fuso_da_corretora(tz))


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

    # 🔴 O QUINTO DESLIGADOR — a JANELA, e ela é do Founder (08/09/2026).
    #
    # ⚠️ O cálculo do `vence_em` já faz a espera nascer dentro do horário
    # (`dispatch_router._pos_acionamento_do_checkpoint`). Esta linha é o guarda
    # do CHAMADOR, e existe porque o outro gatilho não passa por aquele cálculo:
    # o corredor pode receber a resposta da seguradora às 23h e chamar
    # `entregar_novidade` na hora. Uma janela calculada num lugar e não conferida
    # no outro é uma janela que protege metade das saídas.
    #
    # ⛔ **Falha FECHADA**: fuso ilegível → `False` → cala.
    if not dentro_da_janela_do_follow_up():
        return False, "fora_da_janela_local"

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

    # 🔴 O SEXTO DESLIGADOR — A JANELA DA PALAVRA HUMANA (§2 do plano, 09/09).
    #
    # ⚠️ **O follow-up é a saída mais perigosa desta regra**, e é por isso que
    # ele tem de perguntar: a atendente que assumiu o caso pelo WhatsApp dela
    # não clicou em botão nenhum (`claimed_by` vazio, status `open`), e o
    # *"deu tudo certo?"* automático chegaria ao segurado por cima da conversa
    # que ela está conduzindo — horas depois, sem ninguém ver.
    #
    # 🔴 **Aqui, e não lá em cima, de propósito.** A porta única
    # (`a_ia_deve_calar`) refaz o `pausar_ia` puro — de graça — e em troca chega
    # com a `companhia` JÁ LIDA, que é o que dá à corretora o seu próprio N
    # (`acionamento_profile.janela_silencio_humano_dias`). Consultar antes
    # pagaria uma leitura de `messages` para conversas que a hora local, o
    # agente desligado ou o acompanhamento desligado já tinham calado.
    #
    # ⛔ O código devolvido é `palavra_humana_recente` porque é ELE que vai para
    # `suprimida_por` — a FRASE vai para o log e para o feed, onde quem lê é a
    # Regina (`CLAUDE.md` §12.1).
    try:
        from app.services.o_fim_do_atendimento import (
            a_ia_deve_calar, anotar_silencio_no_feed, foi_a_janela, pausar_ia,
        )

        calar, motivo = await a_ia_deve_calar(db, company_id=empresa,
                                              conversa=conversa,
                                              companhia=companhia)
    except Exception as erro:  # noqa: BLE001
        logger.warning("[ACOMPANHAMENTO] janela indisponível (%s) — calando",
                       type(erro).__name__)
        return False, "estado_da_conversa_desconhecido"

    if calar:
        if foi_a_janela(motivo):
            logger.info("[ACOMPANHAMENTO] follow-up calado: %s", motivo)
            await anotar_silencio_no_feed(
                company_id=empresa,
                conversation_id=str((conversa or {}).get("id") or ""),
                motivo=motivo)
            return False, "palavra_humana_recente"
        # ⚠️ O código diz a VERDADE sobre a causa: a conversa pode ter sido
        #    assumida entre o `pausar_ia` lá de cima e este instante — ou a
        #    leitura do histórico pode ter falhado, e aí calou por dúvida, que
        #    é outra coisa. `suprimida_por` é o que a Regina vai ler depois.
        return False, ("conversa_assumida" if pausar_ia(conversa or {})
                       else "estado_da_conversa_desconhecido")
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


async def _anotar_na_ficha(db, *, company_id: str, conversation_id: str,
                           gatilho: str, entregue: bool,
                           suprimida_por: str) -> None:
    """A novidade fica contável NA CONVERSA — `ficha_atendimento.acompanhamento`.

    🔴 **É este o registro que sobrevive em produção**, e a razão é medida: 📊
    `work_events.work_run_id` é **NOT NULL** (com FK composta), e só **4 de 729**
    conversas têm `work_run`. O INSERT em `work_events` para uma conversa sem
    sombra viola a coluna, cai no `except` e some — a supressão que a SPEC
    promete deixar PROVADA nunca seria escrita (achado da lente DADO+verdade).

    ⚠️ A fusão é ADITIVA, como `agente_concluiu`: lê a ficha, acrescenta a
    chave, grava. ⛔ Sobrescrever o `jsonb` inteiro apagaria protocolo, serviço
    e seguradora — o dado que o dossiê lê para dizer o que é o caso.

    ⛔ E nunca levanta: um registro perdido não pode custar a mensagem.
    """
    from datetime import datetime, timezone

    empresa = str(company_id or "").strip()
    if not empresa or not str(conversation_id or "").strip():
        return
    try:
        achado = await (db.client.table("conversations")
                        .select("id, ficha_atendimento")
                        .eq("company_id", empresa)              # 🔴 §7
                        .eq("id", str(conversation_id)).limit(1).execute())
        atual = (achado.data or [{}])[0] or {}
        ficha = atual.get("ficha_atendimento")
        ficha = dict(ficha) if isinstance(ficha, dict) else {}

        anterior = ficha.get("acompanhamento")
        anterior = dict(anterior) if isinstance(anterior, dict) else {}
        contagem = int(anterior.get("suprimidas") or 0)
        if not entregue:
            contagem += 1
        ficha["acompanhamento"] = {
            "suprimidas": contagem,
            "entregues": int(anterior.get("entregues") or 0) + (1 if entregue else 0),
            "ultima": {"em": datetime.now(timezone.utc).isoformat(),
                       "gatilho": str(gatilho or ""),
                       "entregue": bool(entregue),
                       # ⛔ Sem o TEXTO: quem guarda conteúdo é o Espelho.
                       "motivo": str(suprimida_por or "")},
        }
        await (db.client.table("conversations")
               .update({"ficha_atendimento": ficha})
               .eq("company_id", empresa)                       # 🔴 §7
               .eq("id", str(conversation_id)).execute())
    except Exception as erro:  # noqa: BLE001
        logger.warning("[ACOMPANHAMENTO] novidade não anotada na ficha (%s)",
                       type(erro).__name__)


async def _registrar(db, *, company_id: str, work_run_id: Optional[str],
                     gatilho: str, entregue: bool, suprimida_por: str,
                     conversation_id: str = "") -> None:
    """A novidade fica CONTÁVEL — entregue ou calada.

    🔴 **Dois destinos, e o primeiro é o que sempre existe.** A ficha da
    conversa é escrita sempre; `work_events` **só quando há `work_run_id`** —
    a coluna é NOT NULL, e insistir nela sem sombra é escrever no `except`.
    """
    await _anotar_na_ficha(db, company_id=company_id,
                           conversation_id=conversation_id, gatilho=gatilho,
                           entregue=entregue, suprimida_por=suprimida_por)
    if not str(work_run_id or "").strip():
        # ⚠️ Não é silêncio: a ficha acima já guardou. 📊 725 de 729 conversas
        #    caem aqui, e antes desta linha as 725 eram um warning por evento.
        logger.info("[ACOMPANHAMENTO] sem `work_run_id` — a novidade fica na "
                    "ficha da conversa (work_events.work_run_id é NOT NULL)")
        return
    try:
        await db.client.table("work_events").insert({
            "company_id": str(company_id),                      # 🔴 §7
            "work_run_id": work_run_id,
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
                     conversation_id=conversation_id,
                         gatilho=gatilho, entregue=False,
                         suprimida_por=resposta["suprimida_por"])
        return resposta

    if conversa.get("resolvido_em"):
        # ⛔ O atendimento já terminou. Falar depois do desfecho reabre um caso
        #    que a corretora fechou.
        resposta["suprimida_por"] = "atendimento_ja_encerrado"
        await _registrar(db, company_id=company_id, work_run_id=run_id,
                     conversation_id=conversation_id,
                         gatilho=gatilho, entregue=False,
                         suprimida_por=resposta["suprimida_por"])
        return resposta

    pode, porque = await pode_falar_com_o_cliente(db, company_id, conversa)
    if not pode:
        resposta["suprimida_por"] = porque or "desligado"
        await _registrar(db, company_id=company_id, work_run_id=run_id,
                     conversation_id=conversation_id,
                         gatilho=gatilho, entregue=False,
                         suprimida_por=resposta["suprimida_por"])
        logger.info("[ACOMPANHAMENTO] novidade GERADA e SUPRIMIDA (%s) gatilho=%s",
                    resposta["suprimida_por"], gatilho)
        return resposta

    telefone = str(conversa.get("user_phone") or "").strip()
    if not telefone:
        resposta["suprimida_por"] = "conversa_sem_telefone"
        await _registrar(db, company_id=company_id, work_run_id=run_id,
                     conversation_id=conversation_id,
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
                     conversation_id=conversation_id,
                     gatilho=gatilho, entregue=bool(resposta["entregue"]),
                     suprimida_por=str(resposta["suprimida_por"]))
    return resposta


__all__ = ["EVENTO_NOVIDADE", "MENSAGEM_SEM_NOVIDADE", "HORA_ABRE", "HORA_FECHA",
           "acompanhamento_ligado", "pode_falar_com_o_cliente",
           "entregar_novidade", "fuso_da_corretora",
           "calcular_envio_do_follow_up", "dentro_da_janela_do_follow_up",
           "fim_do_periodo_combinado"]
