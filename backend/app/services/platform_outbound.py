"""SPEC-045 — Envios de PLATAFORMA a segurados com guardas anti-conflito.

O medo do founder virou três regras determinísticas (custo zero de LLM):

1. FILA DE CORTESIA (outbound): antes de um auxiliar enviar (cobrança,
   campanha, aviso) a um cliente, checa se ele está em ATENDIMENTO ativo
   (acionamento vivo no Redis OU conversa recente aberta). Ocupado = o envio
   espera na fila (retry via scheduler) — nunca atropela o atendimento.
2. REGISTRO (platform_sends): todo envio de plataforma fica registrado.
3. NOTA DE CONTEXTO (inbound): quando o cliente responde, o atendente recebe
   "há X dias este cliente recebeu {cobrança da parcela Y}" — responde sabendo
   do que se trata, sem confusão.

Canal: get_platform_whatsapp_integration (o mesmo caminho do Vigia) — número
dedicado de auxiliares quando existir (purpose=auxiliary), senão o do
atendimento. Corretora pequena com 1 número = suportada com segurança.

SPEC-063 Bloco C — O GOVERNADOR DE VAZÃO
========================================

A fila acima resolve *quando não atropelar um atendimento*. Ela nunca resolveu
*quanto sai por hora* — e essa era a metade que faltava.

O defeito, medido em 02/08/2026::

    controle de vazão no repositório inteiro .....  NENHUM
    único espaçamento existente .................  time.sleep(0.7) entre balões
    billing_collection, por execução ............  até 50 itens × 2 mensagens
                                                   = 100 mensagens em rajada

Cem mensagens seguidas, sem pausa, saindo do **WhatsApp da corretora**. Um
número novo que faz isso é banido — e quem perde o canal não somos nós, é a
corretora. Ela perde o número que os segurados dela têm na agenda.

Por que este governador vive AQUI, e não num módulo novo
--------------------------------------------------------
Metade dele já existia neste arquivo, escrita para outro fim: fila persistente
em Redis (``_QUEUE_KEY``), janela de ocupado (``_BUSY_WINDOW_H``), backoff
(``_RETRY_MIN_S``), teto de tentativas (``_MAX_ATTEMPTS``) e o drenador
periódico (``check_platform_queue``, a cada 600 s). Um governador ao lado disso
seria uma segunda fila de saída — CLAUDE.md §5, motor paralelo.

O que o Bloco C acrescenta é só o que faltava: **espaçamento, tetos, janela e
um interruptor de emergência**. O adiamento reusa a fila que já estava aqui: o
governador apenas escreve um ``next_try`` diferente.

O que ele governa — e o que ele NUNCA governa
---------------------------------------------
> **Só mensagem FRIA passa pelo governador.**

*Fria* é a plataforma falando primeiro: cobrança, campanha, briefing, aviso.
*Quente* é resposta a um segurado que acabou de escrever — e essa **não pode
ser atrasada nem um segundo**, porque tem uma pessoa do outro lado esperando.
Atrasar resposta de atendimento para "proteger o número" seria trocar um risco
de banimento por um dano certo à corretora.

Por isso ``temperatura`` é um argumento explícito, com ``FRIA`` como padrão:
quem esquece de declarar cai no caminho governado, que é o seguro. O caminho
rápido exige um ato deliberado — ``temperatura=QUENTE``.

Os números, e de onde eles vêm
------------------------------
====================  ==========  ==================================================
espaçamento           4–8 min     entre aproximações frias do mesmo canal
teto por hora         12          batente; o espaçamento já entrega ~10/h em média
teto diário (novo)    20          número sem histórico
teto diário (maduro)  200         ≥30 dias de uso E ≥200 envios registrados
janela                08:00–20:00 fuso da corretora, **domingo bloqueado**
====================  ==========  ==================================================

💭 Os limites são calibração de risco, não medição: não existe API que informe
a reputação de um número em canal não-oficial. A referência pública mais
próxima é o tiering da WhatsApp Cloud API, que começa um número novo em 250
destinatários únicos/24 h e só sobe depois de qualidade sustentada. 20/dia é
deliberadamente mais conservador que isso.

O regulador de verdade é o **espaçamento**, não o teto: sorteando 4–8 min saem
~10 mensagens por hora. O teto de 12/h existe para o caso de uma sequência de
sorteios curtos. 📊 Consequência aritmética: com 12/h dentro de uma janela de
12 h, o máximo diário efetivo é 144 — o teto de 200 do número maduro é folga,
nunca a restrição ativa.

O "segundo redondo" que entrega o robô
--------------------------------------
O intervalo é sorteado em segundos e **nunca cai em múltiplo de 30**. Cadência
humana não bate no minuto cheio; uma sequência de mensagens separadas por
exatamente 5 min é uma assinatura de automação legível por qualquer heurística
antispam — e o espaçamento existia justamente para não parecer automação.

Quando o governador não sabe, ele não deixa passar
--------------------------------------------------
Sem Redis não há como garantir espaçamento nem ler o interruptor de emergência.
Não saber se a parada está puxada **não é** permissão para enviar. Mensagem
fria falha fechada. Mensagem quente não passa por aqui e continua saindo.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
from datetime import datetime, time, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

_QUEUE_KEY = "platform_queue:{company_id}"
_BUSY_WINDOW_H = 2          # conversa com atividade nas últimas N horas = ocupado
_RETRY_MIN_S = 2 * 3600     # re-tenta a partir de 2h
_MAX_ATTEMPTS = 12          # ~24h de tentativas; depois expira com atividade

# --- SPEC-063 Bloco C: o governador -----------------------------------------

FRIA = "fria"      # a plataforma fala primeiro — governada
QUENTE = "quente"  # o segurado escreveu e está esperando — NUNCA governada

_GATE_KEY = "platform_gate:{company_id}"   # lease de espaçamento (TTL = intervalo)
_STOP_KEY = "platform_stop:{company_id}"   # parada de emergência da corretora

# Intervalo entre aproximações frias. Os extremos são 241 e 479 — e não 240 e
# 480 — porque 4:00 e 8:00 cravados são exatamente o tipo de borda redonda que
# o sorteio existe para evitar.
_INTERVALO_MIN_S = 241
_INTERVALO_MAX_S = 479

_TETO_HORA = 12
_TETO_DIA_NOVO = 20
_TETO_DIA_MADURO = 200

_JANELA_ABRE_H = 8
_JANELA_FECHA_H = 20
_DOMINGO = 6  # datetime.weekday(): segunda=0 … domingo=6

# Maturidade do canal. As DUAS condições valem: tempo sem tempo de uso é um
# número parado, e volume sem tempo é um número que acabou de fazer rajada.
_MADURO_DIAS = 30
_MADURO_ENVIOS = 200

# Adiamento por vazão tem contador próprio, separado de `attempts`. Misturar os
# dois faria uma mensagem legítima expirar por ter sido *bem* espaçada.
_MAX_ADIAMENTOS = 200

_TZ_PADRAO = "America/Sao_Paulo"
_TZ_VAR = "AGENT_OS_TENANT_TIMEZONE"


class Veredito:
    """A resposta do governador: pode, por quê, e em quanto tempo tentar de novo.

    ``esperar_s`` carrega a diferença que importa para quem chamou:

        > 0   é uma espera — vai sair, mais tarde. Enfileire.
        == 0  é uma recusa estrutural (parada de emergência). Não enfileire:
              guardar mensagem enquanto o freio está puxado faz tudo sair de
              uma vez quando ele soltar, que é o defeito de origem.
    """

    __slots__ = ("pode", "motivo", "esperar_s")

    def __init__(self, pode: bool, motivo: str, esperar_s: int = 0):
        self.pode = bool(pode)
        self.motivo = str(motivo)
        self.esperar_s = int(esperar_s)

    def como_dict(self) -> Dict[str, Any]:
        return {"pode": self.pode, "motivo": self.motivo, "esperar_s": self.esperar_s}

    def __repr__(self) -> str:  # pragma: no cover — só para log e teste
        return f"Veredito(pode={self.pode}, esperar_s={self.esperar_s}, motivo={self.motivo!r})"


def _agora() -> datetime:
    """O relógio do governador, num lugar só.

    Existe porque a primeira versão deste teste passou às 14:00 e reprovou às
    01:12 — janela e domingo são decisões sobre HORAS, e um teste que consulta
    o relógio de verdade só é verde no turno certo. O mesmo `_agora()` já é o
    padrão em `intelligence/delivery_executor.py`.
    """
    return datetime.now(timezone.utc)


def _digits(v: Any) -> str:
    return "".join(ch for ch in str(v or "") if ch.isdigit())


def _phone_variants(phone: str) -> set:
    from app.services.atlas.observer_intake import _br_variants

    return _br_variants(phone)


# Estados em que o cliente NÃO está ocupado, para os fins da fila de cortesia.
#
# `test_aborted` e `insurer_closed`: o acionamento acabou.
#
# `monitoring` é diferente, e entrou em 03/08/2026: o serviço foi aberto e
# estamos acompanhando. É exatamente o estado em que o follow-up pergunta *"o
# prestador já chegou?"* — a única mensagem do produto que existe para ser
# mandada nesse momento.
#
# Sem esta exceção, plugar o follow-up no canal governado o adiaria **para
# sempre**: ele só roda em `monitoring`, e `monitoring` o marcaria como ocupado.
#
# A fila de cortesia existe para o cliente não ser interrompido no meio de um
# atendimento — não para ele deixar de receber notícia do atendimento que ele
# mesmo pediu.
# `encaminhado` (P-46) entra pelo mesmo motivo de `test_aborted`: o acionamento
# ACABOU. Sem ele, a mensagem que entrega o formulário de vidro ao segurado
# ficaria na fila de cortesia esperando o fim de um atendimento que já terminou.
_ESTADOS_QUE_NAO_OCUPAM = ("test_aborted", "insurer_closed", "monitoring", "encaminhado")


async def client_busy(company_id: str, phone: str) -> Optional[str]:
    """Cliente em atendimento? Retorna o MOTIVO ('acionamento'|'conversa')
    ou None. Determinístico: Redis (dispatch ativo) + conversations recentes."""
    variants = _phone_variants(phone)
    if not variants:
        return None
    try:  # 1) acionamento vivo com este cliente
        from app.services.dispatch_router import list_active_dispatches

        for s in await list_active_dispatches(str(company_id)):
            if _digits(s.get("client_phone")) in variants and \
                    str(s.get("state") or "") not in _ESTADOS_QUE_NAO_OCUPAM:
                return "acionamento"
    except Exception:  # noqa: BLE001
        pass
    try:  # 2) conversa de atendimento aberta com atividade recente
        from app.core.database import get_supabase_client

        since = (_agora() - timedelta(hours=_BUSY_WINDOW_H)).isoformat()

        def _q() -> list:
            db = get_supabase_client()
            return (db.client.table("conversations")
                    .select("id, user_phone, status, last_message_at")
                    .eq("company_id", str(company_id)).eq("channel", "whatsapp")
                    .neq("status", "closed").gte("last_message_at", since)
                    .limit(50).execute().data or [])

        for c in await asyncio.to_thread(_q):
            if _digits(c.get("user_phone")) in variants:
                return "conversa"
    except Exception:  # noqa: BLE001
        pass
    return None


def _record_send_sync(company_id: str, phone: str, kind: str, summary: str) -> None:
    from app.core.database import get_supabase_client

    db = get_supabase_client()
    db.client.table("platform_sends").insert({
        "company_id": str(company_id), "phone": _digits(phone),
        "kind": str(kind or "other")[:40], "summary": str(summary or "")[:300],
        "sent_at": _agora().isoformat(),
    }).execute()


async def record_platform_send(company_id: str, phone: str, kind: str, summary: str) -> None:
    """Registra um envio de plataforma (para a nota de contexto do atendente)."""
    try:
        await asyncio.to_thread(_record_send_sync, company_id, phone, kind, summary)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[PLATFORM SEND] registro falhou: {type(e).__name__}")


# ===========================================================================
# O GOVERNADOR — parte pura
# ===========================================================================
#
# Tudo abaixo é função de entrada→saída, sem I/O. É de propósito: a decisão de
# vazão precisa ser testável com um relógio de mentira e contadores na mão. Um
# governador que só se prova em produção não se prova.


def intervalo_entre_frias(sorteio=None) -> int:
    """Segundos até a próxima mensagem fria. 4–8 min, nunca em minuto redondo.

    `sorteio` existe para o teste fixar o dado. Em produção é `random.randint`.
    """
    escolher = sorteio or random.randint
    s = int(escolher(_INTERVALO_MIN_S, _INTERVALO_MAX_S))
    s = max(_INTERVALO_MIN_S, min(_INTERVALO_MAX_S, s))
    if s % 30 == 0:
        # 270, 300, 330 … caem aqui. +7 nunca estoura o teto (450+7 = 457).
        s += 7
    return s


def fuso_da_corretora(nome: Optional[str] = None):
    """O fuso em que a janela de envio é lida.

    Hoje `AGENT_OS_TENANT_TIMEZONE` não existe em nenhum `.env` — o valor real
    de todas as corretoras é America/Sao_Paulo. A variável está lida assim
    mesmo para que a primeira corretora fora do fuso não exija mudar código.
    """
    escolhido = (nome or os.getenv(_TZ_VAR) or _TZ_PADRAO).strip() or _TZ_PADRAO
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(escolhido)
    except Exception:  # noqa: BLE001 — contêiner sem tzdata
        return timezone(timedelta(hours=-3))


def proxima_abertura(agora_utc: datetime, tz_nome: Optional[str] = None) -> datetime:
    """Quando a janela reabre. Pula o domingo inteiro."""
    tz = fuso_da_corretora(tz_nome)
    local = agora_utc.astimezone(tz)
    candidato = local.replace(hour=_JANELA_ABRE_H, minute=0, second=0, microsecond=0)
    if candidato <= local:
        candidato += timedelta(days=1)
    while candidato.weekday() == _DOMINGO:
        candidato += timedelta(days=1)
    return candidato.astimezone(timezone.utc)


def dentro_da_janela(agora_utc: datetime, tz_nome: Optional[str] = None) -> Veredito:
    """08:00–20:00 no fuso da corretora, e domingo não conta como dia útil.

    Domingo é bloqueado inteiro, não só de noite: cobrança de domingo é a
    mensagem que o segurado marca como spam mesmo quando a dívida é real.
    """
    tz = fuso_da_corretora(tz_nome)
    local = agora_utc.astimezone(tz)
    if local.weekday() == _DOMINGO:
        espera = int((proxima_abertura(agora_utc, tz_nome) - agora_utc).total_seconds())
        return Veredito(False, "é domingo — a corretora não fala com segurado hoje",
                        max(60, espera))
    abre = time(_JANELA_ABRE_H, 0)
    fecha = time(_JANELA_FECHA_H, 0)
    if abre <= local.time() < fecha:
        return Veredito(True, "dentro da janela de 08:00 às 20:00")
    espera = int((proxima_abertura(agora_utc, tz_nome) - agora_utc).total_seconds())
    return Veredito(False,
                    f"fora da janela de 08:00 às 20:00 (agora são {local.strftime('%H:%M')} "
                    f"na corretora)", max(60, espera))


def maturidade_do_canal(dias_de_uso: int, envios_no_total: int) -> str:
    """`'maduro'` ou `'novo'`. Na dúvida, novo.

    Maduro = **≥30 dias de histórico E ≥200 envios registrados**. As duas
    condições existem porque cada uma sozinha mente:

    * só tempo → um número criado há um ano e nunca usado é tão novo quanto o
      de ontem, do ponto de vista de reputação;
    * só volume → 200 envios feitos numa tarde é exatamente a rajada que este
      arquivo existe para impedir.

    Trinta dias é a janela em que um número que fez rajada já teria sido
    derrubado; 200 envios acumulados é prova de entrega sustentada. Os dois
    limiares são alcançáveis pelo caminho lento: 20/dia × 10 dias = 200.
    """
    if int(dias_de_uso or 0) >= _MADURO_DIAS and int(envios_no_total or 0) >= _MADURO_ENVIOS:
        return "maduro"
    return "novo"


def teto_do_dia(maturidade: str) -> int:
    return _TETO_DIA_MADURO if maturidade == "maduro" else _TETO_DIA_NOVO


def _segundos_ate_a_proxima_hora(agora_utc: datetime) -> int:
    prox = (agora_utc.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
    return max(60, int((prox - agora_utc).total_seconds()))


def avaliar_vazao(*, agora_utc: datetime, temperatura: str = FRIA,
                  parado: Optional[str] = None, gate_livre: bool = True,
                  faltam_no_gate_s: int = 0, na_hora: int = 0, no_dia: int = 0,
                  maturidade: str = "novo", tz_nome: Optional[str] = None,
                  redis_ok: bool = True) -> Veredito:
    """O núcleo da decisão. Puro: relógio, contadores e estado entram como dados.

    A ordem das checagens é a ordem do dano:

    1. **quente** — nem chega a ser governada;
    2. **parada de emergência** — decisão humana, vence tudo;
    3. **Redis mudo** — não sei se o freio está puxado nem quanto já saiu;
    4. **janela / domingo** — hora errada é dano de reputação imediato;
    5. **tetos** — hora e dia;
    6. **espaçamento** — o regulador do dia a dia.
    """
    if temperatura == QUENTE:
        return Veredito(True, "resposta a um segurado que está esperando — "
                              "não passa pelo governador")

    if parado:
        return Veredito(False, f"envios desta corretora estão parados: {parado}", 0)

    if not redis_ok:
        # Falha fechada. Só para mensagem fria — a quente já saiu lá em cima.
        return Veredito(False, "não consigo garantir o espaçamento agora (Redis "
                               "indisponível) — mensagem fria não sai sem governador",
                        _RETRY_MIN_S)

    janela = dentro_da_janela(agora_utc, tz_nome)
    if not janela.pode:
        return janela

    if int(na_hora) >= _TETO_HORA:
        return Veredito(False, f"teto de {_TETO_HORA} mensagens por hora já atingido",
                        _segundos_ate_a_proxima_hora(agora_utc))

    teto_dia = teto_do_dia(maturidade)
    if int(no_dia) >= teto_dia:
        espera = int((proxima_abertura(agora_utc, tz_nome) - agora_utc).total_seconds())
        return Veredito(False,
                        f"teto diário de {teto_dia} mensagens já atingido "
                        f"(canal {maturidade})", max(60, espera))

    if not gate_livre:
        return Veredito(False, "espaçamento entre mensagens frias ainda não venceu",
                        max(30, int(faltam_no_gate_s or 60)))

    return Veredito(True, f"dentro da janela, {na_hora}/{_TETO_HORA} na hora e "
                          f"{no_dia}/{teto_dia} no dia (canal {maturidade})")


# ===========================================================================
# O GOVERNADOR — parte com estado
# ===========================================================================


async def parar_envios(company_id: str, motivo: str = "parada manual") -> bool:
    """Puxa o freio desta corretora. **Não** afeta nenhuma outra.

    A chave é por `company_id`, e é a única coisa que o governador consulta
    antes de qualquer outra: quem puxou o freio não quer negociar com teto nem
    com janela.
    """
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        await r.set(_STOP_KEY.format(company_id=company_id), str(motivo or "parada manual")[:200])
    except Exception as e:  # noqa: BLE001
        logger.error(f"[GOVERNADOR] não consegui parar company={company_id}: {type(e).__name__}")
        return False
    try:
        from app.services.activity_log import log_activity

        await log_activity(str(company_id), "atendimentos", "Envios de plataforma PARADOS",
                           f"{motivo} — nenhuma mensagem fria sai desta corretora até retomar.")
    except Exception:  # noqa: BLE001
        pass
    logger.warning(f"[GOVERNADOR] envios PARADOS company={company_id}: {motivo}")
    return True


async def retomar_envios(company_id: str) -> bool:
    """Solta o freio. O espaçamento e os tetos continuam valendo — retomar não
    é abrir as comportas."""
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        await r.delete(_STOP_KEY.format(company_id=company_id))
    except Exception as e:  # noqa: BLE001
        logger.error(f"[GOVERNADOR] não consegui retomar company={company_id}: {type(e).__name__}")
        return False
    try:
        from app.services.activity_log import log_activity

        await log_activity(str(company_id), "atendimentos", "Envios de plataforma retomados",
                           "Os tetos e o espaçamento continuam valendo.")
    except Exception:  # noqa: BLE001
        pass
    return True


async def envios_parados(company_id: str) -> Optional[str]:
    """O motivo da parada, ou `None`. Levanta se o Redis não responder — quem
    chama precisa saber a diferença entre 'não está parado' e 'não sei'."""
    from app.core.redis import get_async_redis_client

    r = await get_async_redis_client()
    v = await r.get(_STOP_KEY.format(company_id=company_id))
    if not v:
        return None
    return v.decode() if isinstance(v, (bytes, bytearray)) else str(v)


async def _tentar_gate(company_id: str, intervalo_s: int) -> Tuple[bool, int]:
    """Reserva o próximo slot de envio. `(livre, faltam_s)`.

    É um lease com TTL — o uso canônico de Redis segundo CLAUDE.md §6, e a
    única forma de dois workers não passarem pela mesma brecha. Guardar o
    "último envio" e comparar depois teria janela de corrida entre a leitura e
    a escrita; `SET NX EX` decide e reserva no mesmo comando.
    """
    from app.core.redis import get_async_redis_client

    r = await get_async_redis_client()
    chave = _GATE_KEY.format(company_id=company_id)
    try:
        reservou = await r.set(chave, str(int(_agora().timestamp())),
                               ex=int(intervalo_s), nx=True)
    except TypeError:
        # Cliente sem `nx` (dublê de teste, cliente antigo). Degrada para
        # ler-e-escrever: mantém o espaçamento, perde a atomicidade. Só é
        # alcançável fora de produção — o `redis.asyncio` real suporta `nx`.
        if await r.get(chave):
            return False, int(intervalo_s)
        await r.set(chave, str(int(_agora().timestamp())), ex=int(intervalo_s))
        return True, 0
    if reservou:
        return True, 0
    faltam = int(intervalo_s)
    try:
        restante = await r.ttl(chave)
        if isinstance(restante, int) and restante > 0:
            faltam = restante
    except Exception:  # noqa: BLE001
        pass
    return False, faltam


def _historico_sync(company_id: str) -> Tuple[list, list, int]:
    from app.core.database import get_supabase_client

    db = get_supabase_client()
    desde = (_agora() - timedelta(hours=26)).isoformat()
    recentes = (db.client.table("platform_sends").select("sent_at")
                .eq("company_id", str(company_id)).gte("sent_at", desde)
                .order("sent_at", desc=True).limit(1000).execute().data or [])
    primeiro = (db.client.table("platform_sends").select("sent_at")
                .eq("company_id", str(company_id))
                .order("sent_at", desc=False).limit(1).execute().data or [])
    total_res = (db.client.table("platform_sends").select("id", count="exact")
                 .eq("company_id", str(company_id)).limit(1).execute())
    return recentes, primeiro, int(getattr(total_res, "count", 0) or 0)


def _ler_instante(v: Any) -> Optional[datetime]:
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:  # noqa: BLE001
        return None


async def historico_de_envios(company_id: str, agora_utc: Optional[datetime] = None,
                              tz_nome: Optional[str] = None) -> Dict[str, int]:
    """Quanto já saiu, e há quanto tempo este canal existe.

    A fonte é `platform_sends`, que já registra todo envio de plataforma desde
    a SPEC-045. Ela é DURÁVEL de propósito: contador de teto diário em Redis
    zeraria num restart, e um teto que zera sozinho é o mesmo que não existir —
    justamente no dia em que o Redis reinicia por causa da rajada.
    """
    agora = agora_utc or _agora()
    tz = fuso_da_corretora(tz_nome)
    hoje_local = agora.astimezone(tz).date()
    uma_hora = agora - timedelta(hours=1)

    recentes, primeiro, total = await asyncio.to_thread(_historico_sync, company_id)

    na_hora = no_dia = 0
    for linha in recentes:
        quando = _ler_instante((linha or {}).get("sent_at"))
        if not quando:
            continue
        if quando >= uma_hora:
            na_hora += 1
        if quando.astimezone(tz).date() == hoje_local:
            no_dia += 1

    dias = 0
    nascimento = _ler_instante((primeiro or [{}])[0].get("sent_at")) if primeiro else None
    if nascimento:
        dias = max(0, (agora - nascimento).days)

    # `count="exact"` é o número certo; alguns dublês de teste não o expõem, e
    # aí o que temos é a janela de 26 h — que subestima. Subestimar empurra
    # para "novo", que é o lado seguro.
    return {"na_hora": na_hora, "no_dia": no_dia, "dias_de_uso": dias,
            "total": max(total, len(recentes))}


async def governar_envio(company_id: str, *, temperatura: str = FRIA,
                         agora_utc: Optional[datetime] = None,
                         tz_nome: Optional[str] = None,
                         reservar: bool = True) -> Veredito:
    """A pergunta que todo envio frio faz antes de sair: **posso agora?**

    Quando devolve `pode=True` com `reservar=True`, o slot **já foi
    consumido** — o próximo só sai depois do intervalo sorteado. Perguntar sem
    a intenção de enviar (`reservar=False`) serve para relatório e diagnóstico.
    """
    agora = agora_utc or _agora()
    if temperatura == QUENTE:
        return avaliar_vazao(agora_utc=agora, temperatura=QUENTE)

    try:
        parado = await envios_parados(company_id)
    except Exception as e:  # noqa: BLE001
        logger.error(f"[GOVERNADOR] Redis mudo em company={company_id}: {type(e).__name__}")
        return avaliar_vazao(agora_utc=agora, redis_ok=False, tz_nome=tz_nome)
    if parado:
        return avaliar_vazao(agora_utc=agora, parado=parado, tz_nome=tz_nome)

    try:
        h = await historico_de_envios(company_id, agora, tz_nome)
    except Exception as e:  # noqa: BLE001
        # Não saber quanto já saiu é o mesmo que não saber se estouramos o
        # teto. Trata como teto de número novo já batido: adia, não descarta.
        logger.error(f"[GOVERNADOR] histórico ilegível em company={company_id}: {type(e).__name__}")
        h = {"na_hora": _TETO_HORA, "no_dia": _TETO_DIA_NOVO, "dias_de_uso": 0, "total": 0}

    maturidade = maturidade_do_canal(h["dias_de_uso"], h["total"])

    # Janela e tetos primeiro, SEM tocar no gate: reservar um slot que a janela
    # ia recusar desperdiçaria o espaçamento de quem vem depois.
    previa = avaliar_vazao(agora_utc=agora, na_hora=h["na_hora"], no_dia=h["no_dia"],
                           maturidade=maturidade, tz_nome=tz_nome, gate_livre=True)
    if not previa.pode:
        return previa

    intervalo = intervalo_entre_frias()
    if not reservar:
        return avaliar_vazao(agora_utc=agora, na_hora=h["na_hora"], no_dia=h["no_dia"],
                             maturidade=maturidade, tz_nome=tz_nome, gate_livre=True)
    try:
        livre, faltam = await _tentar_gate(company_id, intervalo)
    except Exception as e:  # noqa: BLE001
        logger.error(f"[GOVERNADOR] gate indisponível em company={company_id}: {type(e).__name__}")
        return avaliar_vazao(agora_utc=agora, redis_ok=False, tz_nome=tz_nome)

    return avaliar_vazao(agora_utc=agora, na_hora=h["na_hora"], no_dia=h["no_dia"],
                         maturidade=maturidade, tz_nome=tz_nome,
                         gate_livre=livre, faltam_no_gate_s=faltam)


def governar_envio_sync(company_id: str, *, temperatura: str = FRIA,
                        reservar: bool = True) -> Veredito:
    """O mesmo veredito, para quem vive em código síncrono (o executor de
    entrega do briefing).

    `asyncio.run` dentro de um loop vivo levanta `RuntimeError`; por isso o
    caminho com loop vai para uma thread com loop próprio, em vez de fingir
    que não há loop.
    """
    coro = governar_envio(company_id, temperatura=temperatura, reservar=reservar)
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(asyncio.run, coro).result(timeout=30)


# ===========================================================================


async def send_to_client_guarded(company_id: str, phone: str, text: str,
                                 kind: str = "other", summary: str = "",
                                 *, temperatura: str = FRIA,
                                 tentativas: int = 0, adiamentos: int = 0) -> Dict[str, Any]:
    """Envio guardado: cliente ocupado → FILA (retry); livre → governador → envia.

    `temperatura` tem padrão **FRIA** de propósito. Quem esquecer de declarar
    cai no caminho governado — o único jeito de sair rápido é dizer, em
    palavras, que há um segurado esperando (`temperatura=QUENTE`).
    """
    if str(temperatura) == QUENTE:
        # Sem fila de cortesia e sem governador: a conversa em andamento É o
        # motivo de estar enviando. Adiar aqui seria deixar a pessoa no vácuo.
        return await _entregar_agora(company_id, phone, text, kind, summary)

    # 1) Cortesia primeiro. Ela não consome slot do governador: uma mensagem
    #    que nem vai sair agora não pode gastar o espaçamento de quem vai.
    reason = await client_busy(company_id, phone)
    if reason:
        await _enfileirar(company_id, phone, text, kind, summary,
                          espera_s=_RETRY_MIN_S, tentativas=int(tentativas) + 1,
                          adiamentos=int(adiamentos))
        try:
            from app.services.activity_log import log_activity

            await log_activity(str(company_id), "atendimentos",
                               "Envio adiado — cliente em atendimento",
                               f"{kind}: aguardando o atendimento terminar (fila de cortesia).")
        except Exception:  # noqa: BLE001
            pass
        logger.info(f"[PLATFORM SEND] adiado ({reason}) company={company_id}")
        return {"ok": True, "queued": True, "reason": reason}

    # 2) O governador. Daqui em diante, `pode=True` já reservou o slot.
    veredito = await governar_envio(company_id, temperatura=FRIA)
    if not veredito.pode:
        if veredito.esperar_s <= 0:
            # Recusa estrutural (freio puxado). Enfileirar aqui faria tudo sair
            # junto quando o freio soltar — o defeito original, adiado.
            logger.warning(f"[GOVERNADOR] recusado company={company_id}: {veredito.motivo}")
            return {"ok": False, "queued": False, "reason": "governador",
                    "motivo": veredito.motivo}
        enfileirou = await _enfileirar(company_id, phone, text, kind, summary,
                                       espera_s=veredito.esperar_s,
                                       tentativas=int(tentativas),
                                       adiamentos=int(adiamentos) + 1)
        logger.info(f"[GOVERNADOR] adiado {veredito.esperar_s}s company={company_id}: "
                    f"{veredito.motivo}")
        return {"ok": bool(enfileirou), "queued": bool(enfileirou), "reason": "governador",
                "motivo": veredito.motivo, "esperar_s": veredito.esperar_s}

    return await _entregar_agora(company_id, phone, text, kind, summary)


async def _enfileirar(company_id: str, phone: str, text: str, kind: str, summary: str,
                      *, espera_s: int, tentativas: int = 0, adiamentos: int = 0) -> bool:
    """Guarda na fila que já existia, com o `next_try` que o chamador mandou.

    Os dois contadores viajam com a entrada. Antes eles nasciam zerados a cada
    passagem por aqui — o que fazia uma mensagem re-enfileirada pelo drenador
    nunca expirar, porque `attempts` voltava a 0 toda vez.
    """
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        entry = {"phone": _digits(phone), "text": str(text), "kind": kind,
                 "summary": summary, "attempts": int(tentativas),
                 "adiamentos": int(adiamentos),
                 "next_try": (_agora() + timedelta(seconds=int(espera_s))).isoformat()}
        await r.rpush(_QUEUE_KEY.format(company_id=company_id),
                      json.dumps(entry, ensure_ascii=False))
        return True
    except Exception as e:  # noqa: BLE001
        logger.error(f"[PLATFORM SEND] fila falhou: {type(e).__name__}")
        return False


async def _entregar_agora(company_id: str, phone: str, text: str,
                          kind: str, summary: str) -> Dict[str, Any]:
    """O envio propriamente dito. Único ponto que chama o canal de WhatsApp."""
    try:
        from app.services.integration_service import get_integration_service
        from app.services.whatsapp_service import get_whatsapp_service

        integration = get_integration_service().get_platform_whatsapp_integration(str(company_id))
        if not integration:
            return {"ok": False, "queued": False, "reason": "sem_canal"}
        ok = await asyncio.to_thread(get_whatsapp_service().send_message, _digits(phone), text, integration)
        if ok:
            await record_platform_send(company_id, phone, kind, summary or text[:120])
        return {"ok": bool(ok), "queued": False, "reason": None}
    except Exception as e:  # noqa: BLE001
        logger.error(f"[PLATFORM SEND] envio falhou: {type(e).__name__}")
        return {"ok": False, "queued": False, "reason": "erro_envio"}


async def check_platform_queue() -> int:
    """Task periódica: drena as filas de cortesia e de vazão. Best-effort.

    Roda a cada 600 s (`buffer_processor`). 📊 Consequência aritmética: como o
    espaçamento sorteado (241–479 s) é menor que o intervalo do drenador, sai
    **no máximo uma mensagem fria por corretora a cada 10 minutos** — 6/h, bem
    abaixo do teto de 12/h. O teto nunca é a restrição ativa aqui; ele existe
    para os caminhos que enviam fora do drenador.

    Duas expirações, por motivos diferentes:

    * `attempts` ≥ 12 — o cliente ficou 24 h em atendimento. A mensagem perdeu
      a validade e vira registro em Atividades.
    * `adiamentos` ≥ 200 — a vazão nunca abriu. Uma fila de 50 itens num
      número novo (20/dia) leva ~3 dias; 200 adiamentos cobrem isso com folga
      e ainda assim terminam, em vez de circular para sempre.
    """
    sent = 0
    try:
        from app.core.database import get_supabase_client
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()

        def _companies() -> list:
            db = get_supabase_client()
            return [row["id"] for row in (db.client.table("companies").select("id")
                                          .limit(200).execute().data or [])]

        now = _agora()
        for company_id in await asyncio.to_thread(_companies):
            key = _QUEUE_KEY.format(company_id=company_id)
            try:
                size = await r.llen(key)
            except Exception:  # noqa: BLE001
                continue
            for _ in range(min(int(size or 0), 20)):
                raw = await r.lpop(key)
                if not raw:
                    break
                try:
                    entry = json.loads(raw.decode() if isinstance(raw, (bytes, bytearray)) else raw)
                except Exception:  # noqa: BLE001
                    continue
                try:
                    if str(entry.get("next_try") or "") > now.isoformat():
                        await r.rpush(key, json.dumps(entry, ensure_ascii=False))
                        continue
                    if int(entry.get("attempts") or 0) >= _MAX_ATTEMPTS:
                        from app.services.activity_log import log_activity

                        await log_activity(str(company_id), "atendimentos",
                                           "Envio da fila expirou",
                                           f"{entry.get('kind')}: não foi possível entregar em 24h.")
                        continue
                    if int(entry.get("adiamentos") or 0) >= _MAX_ADIAMENTOS:
                        from app.services.activity_log import log_activity

                        await log_activity(str(company_id), "atendimentos",
                                           "Envio da fila expirou (vazão)",
                                           f"{entry.get('kind')}: a janela de envio nunca abriu "
                                           f"a tempo. Nada foi enviado.")
                        continue
                    if await client_busy(str(company_id), entry.get("phone") or ""):
                        entry["attempts"] = int(entry.get("attempts") or 0) + 1
                        entry["next_try"] = (now + timedelta(seconds=_RETRY_MIN_S)).isoformat()
                        await r.rpush(key, json.dumps(entry, ensure_ascii=False))
                        continue
                    res = await send_to_client_guarded(
                        str(company_id), entry.get("phone") or "",
                        entry.get("text") or "", entry.get("kind") or "other",
                        entry.get("summary") or "",
                        tentativas=int(entry.get("attempts") or 0),
                        adiamentos=int(entry.get("adiamentos") or 0))
                    if res.get("ok") and not res.get("queued"):
                        sent += 1
                except Exception as e:  # noqa: BLE001
                    logger.warning(f"[PLATFORM QUEUE] entrada falhou: {type(e).__name__}")
    except Exception as e:  # noqa: BLE001
        logger.error(f"[PLATFORM QUEUE] check falhou: {type(e).__name__}")
    return sent


async def context_note_for(company_id: str, phone: str) -> Optional[str]:
    """Nota de contexto p/ o atendente: envios de plataforma recentes (7d) a
    este cliente. None quando não há nada — zero ruído no prompt."""
    try:
        from app.core.database import get_supabase_client

        variants = _phone_variants(phone)
        if not variants:
            return None
        since = (_agora() - timedelta(days=7)).isoformat()

        def _q() -> list:
            db = get_supabase_client()
            return (db.client.table("platform_sends")
                    .select("phone, kind, summary, sent_at").eq("company_id", str(company_id))
                    .gte("sent_at", since).order("sent_at", desc=True).limit(30).execute().data or [])

        hits = [x for x in await asyncio.to_thread(_q) if _digits(x.get("phone")) in variants]
        if not hits:
            return None
        parts = []
        for h in hits[:3]:
            when = str(h.get("sent_at") or "")[:10]
            parts.append(f"{h.get('summary') or h.get('kind')} (em {when})")
        return ("[CONTEXTO DA PLATAFORMA] Este cliente recebeu recentemente da corretora: "
                + "; ".join(parts) + ". Se a mensagem dele for sobre isso, responda com esse contexto.")
    except Exception:  # noqa: BLE001
        return None
