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


# ===========================================================================
# SPEC-EXTRA-001 U1 — a allowlist do canário
# ===========================================================================
#
# 🔴 O canário desta SPEC manda mensagem de verdade, num tenant de verdade, pelo
# número de verdade da corretora. A única coisa que separa "teste autorizado" de
# "cobrança acidental num segurado" é esta lista — e por isso ela vigia os DOIS
# lados: o REMETENTE (o `paired_phone_e164` da conexão fixada) e o DESTINATÁRIO.
#
# ⚠️ A comparação é por `telefone_br.variantes_br`, **nunca** por "últimos 4
# dígitos". Dois celulares diferentes terminam nos mesmos 4 dígitos com
# frequência banal; e o mesmo celular aparece com e sem o nono dígito conforme
# quem o gravou. Comparar por sufixo erra dos dois lados ao mesmo tempo.
#
# ⛔ Lista vazia + `canario=True` recusa TUDO. Não saber quem está autorizado
# nunca é permissão para enviar — é a mesma regra do governador sem Redis.
_ENV_ALLOWLIST_CANARIO = "BILLING_CANARIO_ALLOWLIST"


def _allowlist_do_canario(env: Optional[Dict[str, str]] = None) -> set:
    """Os telefones autorizados a participar de um canário, em todas as formas.

    ⛔ Devolve VARIANTES, não os números como foram escritos: assim um número
    gravado com o nono dígito no env casa com o mesmo número sem ele no banco.
    ⛔ Nada aqui vai para log — nem o tamanho da lista sai desta função.
    """
    from app.telefone_br import so_digitos, variantes_br

    bruto = (env if env is not None else os.environ).get(_ENV_ALLOWLIST_CANARIO, "")
    formas: set = set()
    for pedaco in str(bruto or "").replace(";", ",").split(","):
        numero = so_digitos(pedaco)
        if numero:
            formas |= variantes_br(numero)
    return formas


def _autorizado_no_canario(numero: Any, allowlist: Optional[set] = None) -> bool:
    """Este número está na allowlist do canário? Vazio ou ausente → não."""
    from app.telefone_br import variantes_br

    permitidos = _allowlist_do_canario() if allowlist is None else allowlist
    if not permitidos:
        return False
    formas = variantes_br(numero)
    return bool(formas and (formas & permitidos))


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
_ESTADOS_QUE_NAO_OCUPAM = ("test_aborted", "insurer_closed", "monitoring",
                          "encaminhado", "resolvido")


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


#: Espaçamento quando o destino é o PRÓPRIO NÚMERO DE TESTE da corretora.
#:
#: 🔴 Por que existe, e por que é seguro — SPEC-078, 17/08/2026.
#:
#: O espaçamento de 4–8 min protege contra UMA coisa: falar com muitos números
#: DIFERENTES em pouco tempo. É isso que o WhatsApp lê como disparo em massa e
#: é isso que derruba o número da corretora.
#:
#: Em modo teste o destino é **um só**, e é da própria corretora. Não há base
#: de clientes sendo varrida; há uma pessoa conferindo o próprio celular. O
#: risco que o intervalo longo evita simplesmente não está presente.
#:
#: 📊 O custo do intervalo longo aqui é real e foi medido: com 3 boletos, o
#: Founder esperava de 8 a 16 minutos só de espaçamento para conferir se o
#: produto funciona. Testar ficou caro a ponto de não se testar.
#:
#: 25–55s continua sendo CADÊNCIA, não rajada — três mensagens em ~2 minutos,
#: com intervalo irregular. Os tetos de hora e dia, a janela e o freio de
#: emergência continuam valendo integralmente: isto muda o ritmo, não as
#: travas.
_INTERVALO_TESTE_MIN_S = 25
_INTERVALO_TESTE_MAX_S = 55


def intervalo_entre_frias(sorteio=None, *, para_numero_de_teste: bool = False) -> int:
    """Segundos até a próxima mensagem fria. 4–8 min, nunca em minuto redondo.

    `sorteio` existe para o teste fixar o dado. Em produção é `random.randint`.

    `para_numero_de_teste` encurta para 25–55s. Ver `_INTERVALO_TESTE_MIN_S`:
    o destino é o próprio número da corretora, e o risco que o intervalo longo
    evita — falar com muitos números diferentes — não existe ali.
    """
    escolher = sorteio or random.randint
    piso, teto = ((_INTERVALO_TESTE_MIN_S, _INTERVALO_TESTE_MAX_S)
                  if para_numero_de_teste
                  else (_INTERVALO_MIN_S, _INTERVALO_MAX_S))
    s = int(escolher(piso, teto))
    s = max(piso, min(teto, s))
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
                         reservar: bool = True,
                         para_numero_de_teste: bool = False) -> Veredito:
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

    intervalo = intervalo_entre_frias(para_numero_de_teste=para_numero_de_teste)
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


async def _vinculo_do_ator_vigente(company_id: str, actor_user_id: str) -> bool:
    """O ator ainda pertence a esta corretora, AGORA? (SPEC-098 R9)

    ⚠️ Import tardio e delegação a `app.core.auth.vinculo_vigente` — a pergunta
    é UMA e a resposta mora lá (CLAUDE.md §5). Este helper só existe para
    resolver o cliente de banco e traduzir erro em recusa.

    🔴 **Erro de banco → `False`, e AQUI isto é o lado fechado.** `vinculo_vigente`
    levanta de propósito, porque quem pergunta decide; e quem pergunta é a porta
    de saída, onde "não sei" nunca pode virar "pode enviar". É a mesma regra do
    interruptor do atendimento logo abaixo, que assume DESLIGADO quando não
    consegue confirmar.
    """
    try:
        from app.core.auth import vinculo_vigente
        from app.core.database import get_supabase_client

        return await vinculo_vigente(get_supabase_client(), str(company_id), str(actor_user_id))
    except Exception as exc:  # noqa: BLE001
        logger.error("[PLATFORM SEND] não deu para confirmar o vínculo de quem "
                     "pediu o envio em %s (%s) — tratando como NÃO vigente",
                     company_id, type(exc).__name__)
        return False


async def _anotar_recusa_na_ficha(company_id: str, actor_user_id: str,
                                  motivo: str, phone: str) -> None:
    """Sem run, a recusa vai para a FICHA da conversa daquela corretora.

    ⚠️ O precedente e a mesma regra da 097.1 (`atendimento/acompanhamento.py`,
    `_registrar`): `work_events.work_run_id` e NOT NULL, entao o registro que
    sempre existe e o da conversa.

    ⛔ **Sem telefone e sem o texto da mensagem.** A ficha guarda quando, por
    que e quem pediu — nada que identifique o segurado (CLAUDE.md §7). O teto
    de 20 entradas existe para a ficha nao crescer sem fim.

    ⚠️ **Sem conversa para este telefone, o registro e um `logger.warning` com
    a CONTAGEM de variantes procuradas** — nunca o numero. E o caminho de um
    envio a alguem que nunca falou com a corretora; ele nao inventa conversa.
    """
    try:
        from app.core.database import get_supabase_client

        variantes = sorted(_phone_variants(phone))
        if not variantes:
            logger.warning("[PLATFORM SEND] recusa sem telefone utilizável em %s "
                           "— nada anotado", company_id)
            return
        db = get_supabase_client().client

        def _achar():
            return (db.table("conversations")
                    .select("id, ficha_atendimento")
                    .eq("company_id", str(company_id))          # 🔴 §7
                    .in_("user_phone", variantes)
                    .order("last_message_at", desc=True)
                    .limit(1).execute())

        achadas = (await asyncio.to_thread(_achar)).data or []
        if not achadas:
            logger.warning("[PLATFORM SEND] recusa sem conversa para o telefone "
                           "em %s (%d variante(s) procuradas) — nada anotado",
                           company_id, len(variantes))
            return

        conversa = achadas[0]
        ficha = conversa.get("ficha_atendimento")
        ficha = dict(ficha) if isinstance(ficha, dict) else {}
        anteriores = ficha.get("envios_recusados")
        anteriores = list(anteriores) if isinstance(anteriores, list) else []
        anteriores.append({"em": _agora().isoformat(),
                           "motivo": str(motivo or ""),
                           "ator": str(actor_user_id or "")})
        ficha["envios_recusados"] = anteriores[-20:]

        def _gravar():
            return (db.table("conversations")
                    .update({"ficha_atendimento": ficha})
                    .eq("company_id", str(company_id))          # 🔴 §7
                    .eq("id", str(conversa.get("id"))).execute())

        await asyncio.to_thread(_gravar)
    except Exception as exc:  # noqa: BLE001
        logger.error("[PLATFORM SEND] recusa não pôde ser anotada na ficha: %s",
                     type(exc).__name__)


async def _registrar_envio_recusado(company_id: str, actor_user_id: str,
                                    kind: str, summary: str, *,
                                    work_run_id: Optional[str] = None,
                                    phone: str = "") -> None:
    """A recusa fica CONTAVEL — em linguagem humana, e em um de DOIS lugares.

    🔴 **Com `work_run_id` -> Work Event `envio.recusado`. Sem ele -> a ficha
    da conversa.** 📊 Medido em `information_schema.columns` (06/09/2026):
    `work_events.work_run_id` e **NOT NULL** e `id` e `GENERATED ALWAYS AS
    IDENTITY` — insistir no evento sem run levantava `APIError` e a recusa nao
    ficava registrada em lugar nenhum. A docstring anterior afirmava o oposto
    ("aceita `work_run_id` nulo"): era falso, e o canario vivo mostrou o
    `[PLATFORM SEND] recusa nao pode ser registrada: APIError`.

    ⛔ **Sem criar run novo.** Abrir um run so para registrar uma recusa
    inventaria um trabalho que ninguem pediu (SPEC-098 §E, Q4) — e por isso o
    caminho sem run escreve na conversa, como faz a 097.1 em
    `atendimento/acompanhamento.py:_registrar`.

    ⛔ E o INSERT **nao manda `id`**: a coluna e `GENERATED ALWAYS`, e mandar
    valor nela e erro `428C9`. Os dois escritores vivos (`acompanhamento.py`,
    `dispatch_router.py:682`) tambem nao mandam.

    ⚠️ Best-effort: a recusa ja aconteceu quando esta funcao roda. Falhar em
    ESCREVER a recusa nao pode fazer a mensagem sair.
    """
    motivo = ("Mensagem não enviada: o vínculo de quem pediu não está mais "
              "vigente nesta corretora.")
    if not str(work_run_id or "").strip():
        # ⚠️ Nao e silencio: a ficha abaixo guarda. O evento exigiria um run que
        #    este envio nao tem (`work_run_id` e NOT NULL).
        await _anotar_recusa_na_ficha(company_id, actor_user_id, motivo, phone)
        return
    try:
        from app.core.database import get_supabase_client

        db = get_supabase_client().client
        await asyncio.to_thread(lambda: db.table("work_events").insert({
            "company_id": str(company_id),                      # 🔴 §7
            "work_run_id": str(work_run_id),
            "event_type": "envio.recusado",
            "severity": "warning",
            "actor_type": "user",
            "actor_id": str(actor_user_id),
            "message_human": motivo,
            # 🔴 CONSERTO 1 (guarda [J3] do desenhista): a coluna e
            # `payload_redacted`, nao `payload`. 📊 `work_events` em
            # `tests/fixtures/schema_vivo.json`: id, company_id, work_run_id,
            # work_step_id, attempt_id, event_type, actor_type, actor_id,
            # severity, message_human, **payload_redacted**, created_at.
            # ⛔ Sem telefone e sem o texto da mensagem.
            "payload_redacted": {"kind": kind, "resumo": (summary or "")[:200]},
        }).execute())
    except Exception as exc:  # noqa: BLE001
        logger.error("[PLATFORM SEND] recusa não pôde ser registrada: %s",
                     type(exc).__name__)


async def ator_ainda_pode(company_id: str, actor_user_id: Optional[str],
                          *, kind: str = "other", summary: str = "",
                          work_run_id: Optional[str] = None,
                          phone: str = "") -> bool:
    """A pessoa que pediu este efeito AINDA pode pedi-lo? — a porta R9, uma só.

    🔴 SPEC-098 · CONSERTO 1 (red team B4). A revalidação do ator existia e
    estava correta, mas morava DENTRO de `send_to_client_guarded` — e
    📊 medido em 06/09/2026, os 4 chamadores dessa função são jobs de sistema:
    nenhum tem pessoa por trás, nenhum passava `actor_user_id`. **Zero de
    quatro.** O código que fecha o defeito estava escrito, testado em unidade e
    inalcançável (CLAUDE.md §12: existir não é funcionar).

    📊 E o envio que TEM humano por trás não passa por aquela função: é
    `POST /api/webhook/send-message` (`webhook.py`), o único caminho em que a
    atendente do painel fala com o segurado. Extrair a pergunta para cá é o que
    deixa os dois caminhos usarem a MESMA porta — em vez de um segundo
    revalidador ao lado do primeiro (CLAUDE.md §5).

    ⛔ **Sem ator = comportamento de hoje** (`True`). O job de sistema não tem
    pessoa por trás, e exigir uma quebraria tudo que hoje funciona. É também o
    CONTROLE do teste: se o caminho "sem ator" mudasse, um "recusou" não
    provaria nada sobre a revalidação.
    """
    if not actor_user_id:
        return True
    if await _vinculo_do_ator_vigente(company_id, actor_user_id):
        return True
    logger.warning("[PLATFORM SEND] recusado: quem pediu não tem mais "
                   "vínculo vigente em %s (kind=%s)", company_id, kind)
    # 🔴 CONSERTO 2 — o registro tem DOIS destinos, e quem escolhe e a presenca
    #    do run: `work_events.work_run_id` e NOT NULL (📊 information_schema,
    #    06/09/2026). Sem run, a recusa vai para a ficha da conversa.
    await _registrar_envio_recusado(company_id, actor_user_id, kind, summary,
                                    work_run_id=work_run_id, phone=phone)
    return False


# ===========================================================================
# SPEC-EXTRA-001 U1 — a conexão FIXADA, o documento e o ledger
# ===========================================================================


def _conexao_fixada_sync(integration_id: str) -> Optional[Dict[str, Any]]:
    from app.core.database import get_supabase_client
    from app.services.integration_service import get_integration_service

    return get_integration_service(get_supabase_client().client
                                   ).get_integration_by_id(str(integration_id))


async def conexao_fixada(company_id: str, integration_id: Optional[str], *,
                         para_auxiliar: bool = False) -> Tuple[Optional[Dict[str, Any]], str]:
    """A conexão que o chamador FIXOU, relida por id e revalidada agora.

    🔴 SPEC-EXTRA-001 · R09. 📊 Medido em 07/09/2026: `_entregar_agora`
    perguntava `get_platform_whatsapp_integration(company_id)` **no instante do
    efeito** — ou seja, escolhia a conexão de novo, depois de a rotina já ter
    escolhido uma. Duas escolhas independentes do mesmo canal é como uma
    mensagem sai por um número que ninguém autorizou para aquele trabalho.

    ⚠️ **Revalidar não é reescolher.** Divergiu qualquer coisa — sumiu, está
    inativa, é de outra corretora, ou não pode enviar para este uso — a resposta
    é `conexao_trocada` e **nada sai**. Nunca "então uso outra".

    ⚠️ `get_integration_by_id` já filtra `is_active=True`, mas **não** filtra
    `company_id` (📊 `integration_service.py:154-173`) — por isso o `company_id`
    é conferido aqui, do lado de cá (CLAUDE.md §7: o service role não tem RLS).
    """
    if not str(integration_id or "").strip():
        return None, "sem_conexao_fixada"
    try:
        integracao = await asyncio.to_thread(_conexao_fixada_sync, str(integration_id))
    except Exception as exc:  # noqa: BLE001
        logger.error("[PLATFORM SEND] não deu para reler a conexão fixada de %s "
                     "(%s) — tratando como TROCADA", company_id, type(exc).__name__)
        return None, "conexao_trocada"
    if not integracao:
        return None, "conexao_trocada"
    # 🔴 O CINTO ALÉM DO SUSPENSÓRIO. Hoje quem recusa a conexão desligada é o
    #    `.eq("is_active", True)` DENTRO de `get_integration_by_id` — ou seja, a
    #    regra que esta porta precisa está guardada em outra função, e uma
    #    mudança lá a apaga aqui sem ninguém ver (é o §9.4: o que se afirma tem
    #    de ser o comportamento desta porta sobre a linha REAL). As quatro
    #    revalidações do CONTRATOS §3 são feitas aqui, sobre o que chegou.
    if integracao.get("is_active") is False:
        logger.warning("[PLATFORM SEND] a conexão fixada de %s está DESLIGADA "
                       "— recusado", company_id)
        return None, "conexao_trocada"
    if str(integracao.get("company_id") or "") != str(company_id):
        logger.error("[PLATFORM SEND] a conexão fixada não é da corretora %s "
                     "— recusado", company_id)
        return None, "conexao_trocada"

    from app.services.integration_service import IntegrationService

    uso = (IntegrationService.ENVIO_DE_AUXILIAR if para_auxiliar
           else IntegrationService.ENVIO_DE_PLATAFORMA)
    if not IntegrationService.pode_enviar(integracao, para=uso):
        logger.warning("[PLATFORM SEND] a conexão fixada de %s não pode enviar "
                       "para o uso '%s'", company_id, uso)
        return None, "conexao_trocada"
    return integracao, ""


def _assinar_documento_sync(bucket: str, caminho: str, ttl_s: int) -> str:
    from app.core.database import get_supabase_client

    res = get_supabase_client().client.storage.from_(bucket).create_signed_url(caminho, ttl_s)
    if isinstance(res, dict):
        return str(res.get("signedURL") or res.get("signedUrl") or res.get("signed_url") or "")
    dados = getattr(res, "data", None)
    if isinstance(dados, dict):
        return str(dados.get("signedURL") or dados.get("signedUrl") or dados.get("signed_url") or "")
    return ""


#: Validade do link assinado do documento. Curta de propósito: a URL é
#: entregue ao provedor de WhatsApp no ato, e um link que vive uma semana é um
#: boleto de terceiro acessível por quem tiver a URL durante uma semana.
_TTL_DOCUMENTO_S = 15 * 60


async def _assinar_documento(documento: Optional[Dict[str, Any]]) -> Tuple[str, str]:
    """`({"bucket","path","filename"})` → `(url_assinada, nome)`. Falha → `("", nome)`.

    ⚠️ Assinado **no instante do efeito**, e não quando a rotina montou o
    pacote: entre montar e enviar pode haver uma hora de fila de governador, e
    um link que expirou entrega ao segurado um anexo que não abre.
    """
    if not isinstance(documento, dict):
        return "", ""
    caminho = str(documento.get("path") or "").strip().lstrip("/")
    nome = str(documento.get("filename") or "documento.pdf").strip() or "documento.pdf"
    bucket = str(documento.get("bucket") or "portal-evidence").strip() or "portal-evidence"
    if not caminho:
        return "", nome
    try:
        return await asyncio.to_thread(_assinar_documento_sync, bucket, caminho,
                                       _TTL_DOCUMENTO_S), nome
    except Exception as exc:  # noqa: BLE001
        logger.error("[PLATFORM SEND] não consegui assinar o documento (%s)",
                     type(exc).__name__)
        return "", nome


def _marcar_no_ledger_sync(company_id: str, ledger_ref: Dict[str, Any],
                           campos: Dict[str, Any]) -> None:
    from app.core.database import get_supabase_client

    tabela = str(ledger_ref.get("table") or "billing_sent_log")
    (get_supabase_client().client.table(tabela)
     .update(campos)
     .eq("company_id", str(company_id))          # 🔴 CLAUDE.md §7
     .eq("id", str(ledger_ref.get("id")))
     .execute())


def _estado_do_envio(*, kind: str, texto_ok: bool, previa_doc: bool,
                     doc_ok: Optional[bool]) -> str:
    """O estado HONESTO da obrigação, por componente — não por "deu certo".

    📊 R06, medido em 07/09/2026 (`billing_collection.py:1081-1108`): quando o
    texto era aceito e o PDF falhava, a linha era gravada com `doc_sent=False` e
    **contava como enviada**. O segurado recebia "segue o boleto abaixo" e mais
    nada, e o relatório dizia que a cobrança tinha saído. Um estado só para
    dois componentes é o defeito; por isso aqui são dois.
    """
    if not texto_ok:
        return "falhou"
    if not previa_doc:
        return "aceito_pelo_canal"
    if not doc_ok:
        return "parcial"
    # ⚠️ `entregue_equipe` é DIFERENTE de "o cliente recebeu". Ele diz que o
    # pacote chegou a UMA PESSOA DA CORRETORA, que ainda precisa encaminhar —
    # e é por isso que a decisão de encaminhar tem coluna própria no ledger.
    return "entregue_equipe" if kind == "billing_equipe" else "aceito_pelo_canal"


async def send_to_client_guarded(company_id: str, phone: str, text: str,
                                 kind: str = "other", summary: str = "",
                                 *, temperatura: str = FRIA,
                                 tentativas: int = 0, adiamentos: int = 0,
                                 actor_user_id: Optional[str] = None,
                                 work_run_id: Optional[str] = None,
                                 integration_id: Optional[str] = None,
                                 autorizacao_de_auxiliar: bool = False,
                                 documento: Optional[Dict[str, Any]] = None,
                                 enfileirar: bool = True,
                                 destino_interno: bool = False,
                                 ledger_ref: Optional[Dict[str, Any]] = None,
                                 canario: bool = False) -> Dict[str, Any]:
    """Envio guardado: cliente ocupado → FILA (retry); livre → governador → envia.

    `temperatura` tem padrão **FRIA** de propósito. Quem esquecer de declarar
    cai no caminho governado — o único jeito de sair rápido é dizer, em
    palavras, que há um segurado esperando (`temperatura=QUENTE`).

    E **nada** sai daqui com o agente de atendimento desligado — ver o bloco
    abaixo, que é a primeira coisa que esta função faz.

    🔴 SPEC-EXTRA-001 U1 — OS SEIS ARGUMENTOS NOVOS, E POR QUE OS DEFAULTS SÃO O
    CONTROLE
    =========================================================================
    Todos são keyword-only e todos têm default igual ao comportamento de hoje.
    Um chamador que existia antes desta SPEC e não foi editado passa por aqui
    letra por letra como passava — e é isso que dá direito de dizer que um
    "recusou" novo veio da regra nova, e não de uma mudança de caminho.

    ``integration_id``            a conexão FIXADA pelo chamador. Relida por id e
                                  revalidada no efeito; divergiu → `conexao_trocada`,
                                  e **nunca** se escolhe outra no lugar.
    ``autorizacao_de_auxiliar``   `True`: quem autoriza é a CORRETORA (conexão
                                  autorizada + trabalho instalado), não o
                                  interruptor do atendimento. 📊 Medido em
                                  07/09/2026: os 4 agentes `attendance` do banco
                                  estão desligados — exigir o agente para um
                                  trabalho que a corretora instalou e ligou é
                                  travar a cobrança por causa de outro produto.
                                  `False` (default): exige o agente, como hoje.
    ``documento``                 `{"bucket","path","filename"}` — assinado no
                                  instante do efeito e enviado DEPOIS do texto.
    ``enfileirar``                `False`: cortesia e governador devolvem o motivo
                                  em vez de guardar na fila. A cobrança tem
                                  retentador próprio (a próxima execução da
                                  rotina) e não precisa de uma fila que a
                                  represe por dias.
    ``destino_interno``           `True`: o destino é UM número da própria
                                  corretora → intervalo curto do governador, o
                                  mesmo do modo teste.
    ``ledger_ref``                `{"table","id"}` — `_entregar_agora` marca ali
                                  `text_ok`/`doc_ok`/`sent_at`/`status`.
    ``canario``                   `True`: remetente **e** destinatário têm de
                                  estar em `BILLING_CANARIO_ALLOWLIST`.
    """
    # =====================================================================
    # 🔴 SPEC-098 R9 — QUEM PEDIU AINDA PODE PEDIR? A PERGUNTA É FEITA AQUI,
    #    NO INSTANTE DO EFEITO, E NÃO NO INSTANTE DO PEDIDO.
    # =====================================================================
    #
    # 📊 Medido em 06/09/2026: efeitos externos que re-checam o ATOR no instante
    # do efeito = **NENHUM**. Esta função nem recebia o ator, e a fila Redis
    # `platform_queue:{company_id}` faz replay com o `company_id` gravado —
    # 📊 `chat` tem p95 de **5,4 dias** e máximo de 6,9 dias de duração de run.
    # Em 5,4 dias uma pessoa é demitida, tem o acesso revogado, e a mensagem que
    # ela enfileirou sai assinada pela corretora mesmo assim.
    #
    # 🔴 **Snapshot é auditoria, não autorização** (D-098-04). O
    # `requester_user_id` gravado no run prova quem PEDIU; a única coisa que
    # prova que a pessoa AINDA pode é perguntar agora.
    #
    # ⚠️ **POR QUE AQUI, NO TOPO, E NÃO NO DRENADOR:** é a mesma razão do
    # interruptor logo abaixo. O drenador (`check_platform_queue`, :912)
    # **RE-CHAMA** esta função — então uma revalidação aqui cobre o caminho
    # direto E o replay da fila, e todo chamador futuro herda a proteção sem
    # saber que ela existe. No drenador, protegeria só o drenador.
    #
    # ⚠️ E **antes** do atalho `QUENTE`: o atalho é o caminho que sai mais rápido,
    # e é justamente o que menos pode escapar.
    #
    # ⛔ **SEM ATOR = comportamento de hoje.** O job de sistema (cobrança,
    # follow-up, briefing) não tem pessoa por trás, e exigir uma quebraria tudo
    # que hoje funciona. É também o CONTROLE do teste: se o caminho "sem ator"
    # mudasse, um "recusou" não provaria nada sobre a revalidação.
    #
    # ⚠️ A pergunta mora em `ator_ainda_pode` (logo acima) desde o CONSERTO 1:
    # o envio humano do painel (`webhook.admin_send_message`) não passa por esta
    # função, e precisava da MESMA porta — não de uma segunda.
    if not await ator_ainda_pode(company_id, actor_user_id, kind=kind, summary=summary,
                                 work_run_id=work_run_id, phone=phone):
        return {"status": "recusado",
                "motivo": "o vínculo de quem pediu não está mais vigente",
                "ok": False, "queued": False}

    # =====================================================================
    # 🔴 SPEC-EXTRA-001 — O CANÁRIO SÓ FALA COM QUEM FOI AUTORIZADO, DOS DOIS
    #    LADOS. E ele é conferido ANTES da autorização e do governador: um
    #    envio de canário para fora da lista não é "adiado", é proibido.
    # =====================================================================
    conexao: Optional[Dict[str, Any]] = None
    if canario:
        permitidos = _allowlist_do_canario()
        if not permitidos:
            logger.error("[PLATFORM SEND] canário pedido sem allowlist carregada "
                         "em %s — recusado", company_id)
            return {"ok": False, "queued": False, "reason": "fora_da_allowlist"}
        if not _autorizado_no_canario(phone, permitidos):
            logger.error("[PLATFORM SEND] canário recusado em %s: o DESTINATÁRIO "
                         "não está na allowlist", company_id)
            return {"ok": False, "queued": False, "reason": "fora_da_allowlist"}
        # O REMETENTE também. Sem conexão fixada não há remetente para conferir,
        # e "não sei de que número sai" nunca é permissão num teste vivo.
        conexao, motivo_conexao = await conexao_fixada(
            company_id, integration_id, para_auxiliar=autorizacao_de_auxiliar)
        if not conexao:
            logger.error("[PLATFORM SEND] canário recusado em %s: %s",
                         company_id, motivo_conexao or "sem conexão fixada")
            return {"ok": False, "queued": False,
                    "reason": ("fora_da_allowlist"
                               if motivo_conexao == "sem_conexao_fixada"
                               else "conexao_trocada")}
        if not _autorizado_no_canario(conexao.get("paired_phone_e164"), permitidos):
            logger.error("[PLATFORM SEND] canário recusado em %s: o REMETENTE "
                         "(número pareado da conexão) não está na allowlist",
                         company_id)
            return {"ok": False, "queued": False, "reason": "fora_da_allowlist"}

    # =====================================================================
    # 🔴 SPEC-EXTRA-001 — QUEM AUTORIZA ESTE ENVIO: A CORRETORA OU O AGENTE?
    # =====================================================================
    #
    # São duas perguntas diferentes que estavam coladas numa só.
    #
    #   plataforma (default) → o produto fala por conta própria (alerta do
    #        Vigia, follow-up, sugestão). Quem autoriza é o interruptor do
    #        ATENDIMENTO, exatamente como desde a SPEC-078 A.1. Nada muda.
    #
    #   auxiliar → é trabalho que a corretora INSTALOU, configurou e ligou, e
    #        que sai pela conexão que ela autorizou (`permite_envio_de_auxiliar`,
    #        SPEC-078 B). O interruptor do atendimento diz "quem responde
    #        conversa", e não tem nada a dizer sobre a cobrança que a corretora
    #        pediu. 📊 07/09/2026: 4/4 agentes `attendance` desligados — a
    #        cobrança nunca sairia, e o motivo apareceria como "agente_desligado",
    #        que é uma frase sobre outro produto.
    #
    # ⚠️ A autorização de auxiliar NÃO é mais frouxa: ela EXIGE a conexão
    #    fixada, revalidada agora, e que essa conexão passe por `pode_enviar(
    #    para="auxiliar")` — a mesma regra da 078, sem exceção nova.
    if autorizacao_de_auxiliar:
        if conexao is None:
            conexao, motivo_conexao = await conexao_fixada(
                company_id, integration_id, para_auxiliar=True)
        else:
            motivo_conexao = ""
        if not conexao:
            logger.warning("[PLATFORM SEND] bloqueado em %s: %s (kind=%s)",
                           company_id, motivo_conexao or "conexao_trocada", kind)
            return {"ok": False, "queued": False,
                    "reason": motivo_conexao or "conexao_trocada"}
    elif integration_id:
        # Caminho de plataforma que ainda assim fixou a conexão: revalida pelo
        # regime de PLATAFORMA (onde o observador continua proibido).
        conexao, motivo_conexao = await conexao_fixada(
            company_id, integration_id, para_auxiliar=False)
        if not conexao:
            logger.warning("[PLATFORM SEND] bloqueado em %s: %s (kind=%s)",
                           company_id, motivo_conexao or "conexao_trocada", kind)
            return {"ok": False, "queued": False,
                    "reason": motivo_conexao or "conexao_trocada"}

    # 🔴 O INTERRUPTOR DO ATENDIMENTO, LIDO NA FUNÇÃO QUE ENVIA (SPEC-078 A.1).
    #
    # 📊 Medido em 17/08/2026: `check_platform_queue` roda a cada 10 min, para
    # TODAS as corretoras, e chegava até aqui sem nunca perguntar se o agente
    # daquela corretora está ligado. Não mordia por três acidentes — fila
    # vazia, `platform_sends` com 0 linhas e canal recusado por ser observer.
    # Pelo critério escrito no próprio repositório (`webhook.py:578`):
    # "não é trava: é sorte". Um dos três acidentes acabando (e o canal
    # `auxiliary` do Bloco B acaba com o terceiro) põe mensagem na rua de uma
    # corretora que pediu silêncio.
    #
    # POR QUE AQUI, E NÃO NO DRENADOR: o guarda tem de ficar na função que
    # ENVIA. No drenador ele protegeria só o drenador; aqui, todo chamador
    # futuro herda a proteção sem saber que ela existe.
    #
    # POR QUE ANTES DO ATALHO `QUENTE`, e não só no ramo frio: 📊 conferi os
    # quatro chamadores em 17/08/2026 e **todos falam com SEGURADO** — nenhum
    # fala com seguradora. `dispatch_followup.py:282` manda para
    # `client_phone` (o segurado do acionamento, não o telefone da seguradora,
    # que é só a chave da sessão); a cobrança manda para o segurado da
    # parcela; e `delivery_executor._whatsapp` manda o briefing para
    # `recipient_refs["whatsapp"]` do perfil de distribuição — chave que
    # 📊 nenhum escritor do repositório preenche (os três únicos gravadores
    # usam `{"email": [...]}`), então `_telefones` volta vazio e o briefing
    # nunca chega nesta linha. Não havendo caminho legítimo com quem não seja
    # segurado, o guarda pode ficar no topo — o único lugar que também cobre o
    # atalho quente.
    #
    # FALHA FECHADA nas duas metades: `attendance_agent_active` já devolve
    # False quando não consegue confirmar, e o import entra no mesmo `try`
    # porque um interruptor que sumiu não é permissão para falar — é o mesmo
    # padrão de guarda-por-import de `delivery_executor._whatsapp`.
    if not autorizacao_de_auxiliar:
        try:
            from app.services.atlas.attendance_capture import attendance_agent_active

            agente_ligado = await attendance_agent_active(str(company_id))
        except Exception as exc:  # noqa: BLE001
            logger.error("[PLATFORM SEND] não deu para confirmar se o agente de %s "
                         "está ligado (%s) — assumindo DESLIGADO", company_id,
                         type(exc).__name__)
            agente_ligado = False
        if not agente_ligado:
            # `queued: False` explícito: quem drena a fila decide pelo par
            # (ok, queued), e omitir a chave faria uma recusa parecer entrega.
            logger.info("[PLATFORM SEND] bloqueado: agente de atendimento de %s "
                        "está desligado (kind=%s)", company_id, kind)
            return {"ok": False, "queued": False, "reason": "agente_desligado"}

    if str(temperatura) == QUENTE:
        # Sem fila de cortesia e sem governador: a conversa em andamento É o
        # motivo de estar enviando. Adiar aqui seria deixar a pessoa no vácuo.
        return await _entregar(company_id, phone, text, kind, summary,
                               conexao, documento, ledger_ref, canario)

    # 1) Cortesia primeiro. Ela não consome slot do governador: uma mensagem
    #    que nem vai sair agora não pode gastar o espaçamento de quem vai.
    reason = await client_busy(company_id, phone)
    if reason:
        if not enfileirar:
            # ⚠️ Quem chamou tem retentador próprio (a próxima execução da
            # rotina). Guardar aqui só duplicaria o retentador e faria a
            # mensagem sair um dia, sozinha, sem ninguém esperando por ela.
            logger.info("[PLATFORM SEND] não enviado (%s) e NÃO enfileirado "
                        "company=%s", reason, company_id)
            return {"ok": False, "queued": False, "reason": "cliente_em_atendimento",
                    "motivo": reason}
        await _enfileirar(company_id, phone, text, kind, summary,
                          espera_s=_RETRY_MIN_S, tentativas=int(tentativas) + 1,
                          adiamentos=int(adiamentos), actor_user_id=actor_user_id,
                          work_run_id=work_run_id, integration_id=integration_id,
                          documento=documento, ledger_ref=ledger_ref, canario=canario)
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
    veredito = await governar_envio(company_id, temperatura=FRIA,
                                    para_numero_de_teste=bool(destino_interno))
    if not veredito.pode:
        if veredito.esperar_s <= 0:
            # Recusa estrutural (freio puxado). Enfileirar aqui faria tudo sair
            # junto quando o freio soltar — o defeito original, adiado.
            logger.warning(f"[GOVERNADOR] recusado company={company_id}: {veredito.motivo}")
            return {"ok": False, "queued": False, "reason": "governador",
                    "motivo": veredito.motivo}
        if not enfileirar:
            logger.info("[GOVERNADOR] não enviado e NÃO enfileirado company=%s: %s",
                        company_id, veredito.motivo)
            return {"ok": False, "queued": False, "reason": "governador",
                    "motivo": veredito.motivo, "esperar_s": veredito.esperar_s}
        enfileirou = await _enfileirar(company_id, phone, text, kind, summary,
                                       espera_s=veredito.esperar_s,
                                       tentativas=int(tentativas),
                                       adiamentos=int(adiamentos) + 1,
                                       actor_user_id=actor_user_id,
                                       work_run_id=work_run_id,
                                       integration_id=integration_id,
                                       documento=documento, ledger_ref=ledger_ref,
                                       canario=canario)
        logger.info(f"[GOVERNADOR] adiado {veredito.esperar_s}s company={company_id}: "
                    f"{veredito.motivo}")
        return {"ok": bool(enfileirou), "queued": bool(enfileirou), "reason": "governador",
                "motivo": veredito.motivo, "esperar_s": veredito.esperar_s}

    return await _entregar(company_id, phone, text, kind, summary,
                           conexao, documento, ledger_ref, canario)


async def _entregar(company_id: str, phone: str, text: str, kind: str, summary: str,
                    conexao: Optional[Dict[str, Any]], documento: Optional[Dict[str, Any]],
                    ledger_ref: Optional[Dict[str, Any]], canario: bool) -> Dict[str, Any]:
    """Chama `_entregar_agora` COMO HOJE quando nenhum kwarg novo foi usado.

    🔴 Default = comportamento de hoje, byte a byte — inclusive na ASSINATURA
    da chamada. 📊 07/09/2026: `test_098_builder_b_unit` substitui
    `_entregar_agora` por um dublê com a assinatura antiga (5 posicionais) e
    caía com `unexpected keyword argument 'integration'`. Um chamador antigo
    (e um dublê antigo) não pode saber que a porta ganhou parâmetros.
    """
    if conexao is None and documento is None and ledger_ref is None and not canario:
        return await _entregar_agora(company_id, phone, text, kind, summary)
    return await _entregar_agora(company_id, phone, text, kind, summary,
                                 integration=conexao, documento=documento,
                                 ledger_ref=ledger_ref, canario=canario)


async def _enfileirar(company_id: str, phone: str, text: str, kind: str, summary: str,
                      *, espera_s: int, tentativas: int = 0, adiamentos: int = 0,
                      actor_user_id: Optional[str] = None,
                      work_run_id: Optional[str] = None,
                      integration_id: Optional[str] = None,
                      documento: Optional[Dict[str, Any]] = None,
                      ledger_ref: Optional[Dict[str, Any]] = None,
                      canario: bool = False) -> bool:
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
        # 🔴 SPEC-098 R9 — O ATOR VIAJA NA ENTRADA DA FILA.
        #
        # ⚠️ **A chave só entra quando tem valor**, e isso é o que dá
        # COMPATIBILIDADE de graça: uma entrada gravada ANTES desta linha existir
        # não tem `actor_user_id`, o drenador lê `entry.get(...)` -> `None`, e ela
        # cai em "sem ator" — o comportamento de hoje, por construção. Nenhuma
        # mensagem já enfileirada é descartada por causa desta mudança.
        #
        # ⚠️ E é só o ID. ⛔ Nunca nome, telefone de corretor ou e-mail: a fila é
        # Redis, aparece em `MONITOR` e em dump, e CLAUDE.md §7 proíbe PII lá.
        if actor_user_id:
            entry["actor_user_id"] = str(actor_user_id)
        # ⚠️ Mesma regra para o run: so entra quando existe, e a entrada ANTIGA
        #    (sem a chave) cai em "sem run" — a recusa dela vai para a ficha.
        if work_run_id:
            entry["work_run_id"] = str(work_run_id)
        # ⚠️ SPEC-EXTRA-001 — mesma regra para as quatro chaves novas: elas só
        # entram quando existem, e a entrada gravada ANTES delas existirem cai
        # no comportamento de hoje (`entry.get(...)` → `None`/`False`). Nenhuma
        # mensagem já enfileirada muda de caminho por causa desta SPEC.
        # ⛔ O que viaja é referência, nunca conteúdo de segurado: id da conexão,
        #    caminho do arquivo no bucket, id da linha do ledger. A fila é Redis
        #    e aparece em `MONITOR` (CLAUDE.md §7).
        if integration_id:
            entry["integration_id"] = str(integration_id)
        if isinstance(documento, dict) and documento.get("path"):
            entry["documento"] = {"bucket": str(documento.get("bucket") or "portal-evidence"),
                                  "path": str(documento.get("path")),
                                  "filename": str(documento.get("filename") or "documento.pdf")}
        if isinstance(ledger_ref, dict) and ledger_ref.get("id"):
            entry["ledger_ref"] = {"table": str(ledger_ref.get("table") or "billing_sent_log"),
                                   "id": str(ledger_ref.get("id"))}
        if canario:
            entry["canario"] = True
        await r.rpush(_QUEUE_KEY.format(company_id=company_id),
                      json.dumps(entry, ensure_ascii=False))
        return True
    except Exception as e:  # noqa: BLE001
        logger.error(f"[PLATFORM SEND] fila falhou: {type(e).__name__}")
        return False


async def _entregar_agora(company_id: str, phone: str, text: str,
                          kind: str, summary: str, *,
                          integration: Optional[Dict[str, Any]] = None,
                          documento: Optional[Dict[str, Any]] = None,
                          ledger_ref: Optional[Dict[str, Any]] = None,
                          canario: bool = False) -> Dict[str, Any]:
    """O envio propriamente dito. Único ponto que chama o canal de WhatsApp.

    🔴 SPEC-EXTRA-001 — o que mudou, e o que **não** mudou:

    * `integration=None` → continua perguntando `get_platform_whatsapp_integration`,
      exatamente como sempre fez. É o CONTROLE.
    * `integration=<fixada>` → usa a conexão que a porta já revalidou. Escolher
      de novo aqui seria uma segunda decisão sobre o mesmo canal.
    * `documento` sai **depois** do texto, e só se o texto foi aceito — a
      mensagem anuncia o anexo; anexo sem anúncio é arquivo solto de origem
      desconhecida para quem recebe.
    * `text` vazio é legítimo: é o reparo de um `parcial`, em que só o PDF
      faltou. Reenviar o texto ali seria uma segunda abordagem ao mesmo cliente.
    """
    try:
        from app.services.integration_service import get_integration_service
        from app.services.whatsapp_service import get_whatsapp_service

        if integration is None:
            integration = get_integration_service().get_platform_whatsapp_integration(str(company_id))
        if not integration:
            # Nada saiu: aqui a falha de registro não muda desfecho nenhum.
            try:
                await _marcar_no_ledger(company_id, ledger_ref, status="falhou",
                                        last_error="sem canal de WhatsApp elegivel")
            except Exception:  # noqa: BLE001
                logger.error("[PLATFORM SEND] 'sem canal' não registrado no ledger de %s",
                             company_id)
            return {"ok": False, "queued": False, "reason": "sem_canal"}

        destino = _digits(phone)
        texto = str(text or "")
        if texto.strip():
            ok = await asyncio.to_thread(get_whatsapp_service().send_message,
                                         destino, texto, integration)
        else:
            # Nada a dizer nesta passagem: o texto já foi aceito antes.
            ok = True

        doc_ok: Optional[bool] = None
        if ok and isinstance(documento, dict) and documento.get("path"):
            url, nome = await _assinar_documento(documento)
            if not url:
                doc_ok = False
            else:
                doc_ok = bool(await asyncio.to_thread(
                    get_whatsapp_service().send_document, destino, url, nome, integration))

        if ok and texto.strip():
            await record_platform_send(company_id, phone, kind, summary or texto[:120])

        estado = _estado_do_envio(kind=kind, texto_ok=bool(ok),
                                  previa_doc=bool(isinstance(documento, dict)
                                                  and documento.get("path")),
                                  doc_ok=doc_ok)
        resposta: Dict[str, Any] = {
            "ok": bool(ok), "queued": False, "reason": None, "doc_ok": doc_ok,
            "integration_id": str(integration.get("id") or "") or None,
            "status": estado, "canario": bool(canario),
        }
        try:
            campos: Dict[str, Any] = {"status": estado,
                                      "updated_at": _agora().isoformat()}
            if texto.strip():
                campos["text_ok"] = bool(ok)
            if doc_ok is not None:
                campos["doc_ok"] = bool(doc_ok)
                campos["doc_sent"] = bool(doc_ok)   # espelho da coluna legada
            if ok:
                campos["sent_at"] = _agora().isoformat()
                campos["to_last4"] = destino[-4:]
            await _marcar_no_ledger(company_id, ledger_ref, **campos)
        except Exception as exc:  # noqa: BLE001
            # 🔴 A MENSAGEM JÁ SAIU. Levantar daqui faria o chamador achar que
            # nada aconteceu e tentar de novo — que é exatamente a segunda
            # cobrança que esta SPEC existe para impedir. O efeito é o fato; o
            # registro é o que falhou, e quem chamou grava `incerto`.
            logger.error("[PLATFORM SEND] envio feito mas NÃO registrado no "
                         "ledger de %s: %s", company_id, type(exc).__name__)
            resposta["ledger"] = "falhou"
        return resposta
    except Exception as e:  # noqa: BLE001
        logger.error(f"[PLATFORM SEND] envio falhou: {type(e).__name__}")
        # 🔴 `incerto`, NÃO `falhou`. A exceção estourou depois de o pedido ter
        # sido entregue ao provedor: o timeout clássico é exatamente "ele
        # aceitou e não respondeu". Chamar isso de `falhou` autorizaria a
        # próxima execução a reclamar a parcela e mandar a segunda cobrança
        # para o mesmo segurado — o defeito que esta SPEC existe para fechar.
        # Efeito POSSÍVEL não é efeito ausente (padrão outbox, AWS).
        try:
            await _marcar_no_ledger(company_id, ledger_ref, status="incerto",
                                    last_error=f"erro_envio:{type(e).__name__}")
        except Exception:  # noqa: BLE001
            logger.error("[PLATFORM SEND] falha de envio não registrada no ledger de %s",
                         company_id)
        return {"ok": False, "queued": False, "reason": "erro_envio",
                "status": "incerto"}


async def _marcar_no_ledger(company_id: str, ledger_ref: Optional[Dict[str, Any]],
                            **campos: Any) -> None:
    """Escreve o estado na linha do ledger. Sem `ledger_ref`, não faz nada.

    ⚠️ **Levanta de propósito** quando a escrita falha DEPOIS de um envio: quem
    chamou precisa saber a diferença entre "gravei" e "não sei se gravei". Os
    dois usos em que a falha é irrelevante (os caminhos que não enviaram nada)
    chamam dentro de `try` próprio.
    """
    if not isinstance(ledger_ref, dict) or not ledger_ref.get("id") or not campos:
        return
    campos.setdefault("updated_at", _agora().isoformat())
    await asyncio.to_thread(_marcar_no_ledger_sync, str(company_id),
                            ledger_ref, dict(campos))


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
                    # 🔴 SPEC-098 R9/E8 — o drenador RE-CHAMA a porta, e por
                    # isso não precisa (nem deve) revalidar sozinho: basta
                    # devolver o ator que a entrada carrega. Uma segunda
                    # revalidação aqui seria a segunda resposta para a mesma
                    # pergunta, e as duas divergiriam no primeiro conserto.
                    # ⚠️ `entry.get` devolve `None` para a entrada ANTIGA — que é
                    # exatamente "sem ator", o comportamento de hoje.
                    res = await send_to_client_guarded(
                        str(company_id), entry.get("phone") or "",
                        entry.get("text") or "", entry.get("kind") or "other",
                        entry.get("summary") or "",
                        tentativas=int(entry.get("attempts") or 0),
                        adiamentos=int(entry.get("adiamentos") or 0),
                        actor_user_id=entry.get("actor_user_id"),
                        work_run_id=entry.get("work_run_id"),
                        # ⚠️ As quatro chaves da EXTRA-001: a entrada ANTIGA não
                        # as tem, `entry.get` devolve None/False, e ela sai
                        # exatamente como saía antes desta SPEC.
                        integration_id=entry.get("integration_id"),
                        documento=entry.get("documento"),
                        ledger_ref=entry.get("ledger_ref"),
                        canario=bool(entry.get("canario")))
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
