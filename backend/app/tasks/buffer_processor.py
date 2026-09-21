"""
Buffer Processor - Periodic task to check and process WhatsApp message buffers.
ASYNC VERSION: Redis operations are non-blocking.
"""

import asyncio
import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.redis import get_async_redis_client
from app.services.message_buffer_service import get_message_buffer_service

logger = logging.getLogger(__name__)

logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("apscheduler.scheduler").setLevel(logging.WARNING)
logging.getLogger("apscheduler.executors").setLevel(logging.WARNING)
logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)

scheduler = AsyncIOScheduler()


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


# =============================================================================
# 🔴 A FILA QUE ERA UMA FILA DE VERDADE
# =============================================================================
#
# O laço processava as conversas prontas UMA DEPOIS DA OUTRA, com `await`
# dentro do `for`. A quarta pessoa da fila esperava as três da frente — e cada
# uma delas custa uma chamada de LLM mais um envio no WhatsApp. Numa manhã de
# piloto, isso é o segurado nº 4 olhando para o "digitando…" que não vem.
#
# ⛔ Paralelismo aqui NÃO é novidade arriscada: o caminho direto do webhook já
# dispara `process_whatsapp_message_background` por `background_tasks`, várias
# ao mesmo tempo, desde sempre. E `check_buffers` roda com `max_instances=10` —
# ou seja, dez varreduras podem se sobrepor. O serial era serial só DENTRO de
# uma varredura; nunca foi garantia de nada.
#
# 📊 O que foi conferido antes de mudar (leitura do código, 08/09/2026):
#   `get_and_clear_buffer`  é um pipeline Redis `get`+`delete` — ATÔMICO. Duas
#                           tarefas na mesma chave: uma leva o buffer, a outra
#                           leva `None` e desiste. É o que já protegia contra
#                           as varreduras sobrepostas.
#   estado por conversa     tudo que a tarefa usa nasce dentro dela (chave,
#                           buffer, payload). Nada é lido e escrito entre
#                           iterações.
#   singletons              `supabase`, `whatsapp_service`, `integration_service`
#                           já eram compartilhados pelo caminho concorrente do
#                           webhook. Nada novo os alcança aqui.
#
# Por isso o padrão é 6, e não 3.
#
# ⚠️ **Este nome e este valor são lidos de fora.** O guarda de paralelismo
# (`tests/test_midia_e_concorrencia_do_webhook.py:582`) afirma que ele é 6, e
# ele é a LINHA DE CONTROLE herdada da EXTRA-001.2. Continua sendo o teto do
# caminho SEM cota (o do serviço dublado).
_PARALELISMO_PADRAO = 6

# =============================================================================
# 🔴 SPEC-EXTRA-001.8 — UMA CORRETORA NÃO TRAVA A OUTRA
# =============================================================================
#
# 📊 O elo, lido no código em 21/09/2026:
#
#   ① o semáforo nasce DENTRO da varredura (linha 77 de antes) e o job roda a
#     cada 1 s com `max_instances=10`: o "teto de 6" real é até 60, e uma cota
#     criada dentro da função teria o MESMO furo — cota 4 viraria 40. Por isso
#     a ocupação mora em `_ADMISSAO`, no módulo: um estado por PROCESSO.
#   ② a lista é uma só, na ordem do SCAN — ordem de slot do Redis. 50 chaves de
#     uma corretora e 1 de outra: a de fora cai onde calhar. 📊 Medido no mesmo
#     dia, com 40+1 chaves: a conversa da outra corretora foi atendida em
#     **40º de 41**, 0,386 s depois do início da varredura
#     (`python tests/test_uma_corretora_nao_trava_a_outra.py --so FIO`).
#   ③ e quem espera EXPIRA: `add_message` grava com `setex(…, 60 s)`. Esperar a
#     vez por mais de um minuto é o Redis apagando a mensagem do segurado.
#
# ⛔ Nenhuma fila nova, nenhum scheduler novo, nenhum serviço novo (CLAUDE.md
# §5): a cota e o rodízio moram DENTRO deste varredor, e a forma é a mesma que
# `smith_worker.py:264-278` já roda em produção para Work Runs (dicionário por
# tenant, teto, liberação no fim).

#: 🔴 D-PILOTO-07: o PISO é 4 atendimentos simultâneos por corretora.
_COTA_PADRAO = 4

#: 📊 A conta: com cota 4, um teto global de 6 deixaria **uma corretora e meia**
#: trabalhar (6 ÷ 4 = 1,5) — o isolamento existiria no papel e a segunda
#: corretora esperaria assim mesmo. 24 = 6 corretoras × cota 4, que é a ordem de
#: grandeza do piloto com folga. ⚠️ O nome `_PARALELISMO_PADRAO` fica com o
#: valor 6 de propósito: é o do caminho legado, e é o que a linha de controle
#: herdada da 001.2 afirma. `WHATSAPP_BUFFER_PARALELISMO` continua mandando nos
#: dois.
_PARALELISMO_COM_COTA_PADRAO = 24

#: 📊 Medido em produção (21/09/2026): p95 do turno do chat = 107 s, máx 136 s,
#: n=41. 120 s cortaria turno legítimo; 180 s é ~1,3x o máximo medido.
_TURNO_TIMEOUT_PADRAO_S = 180

#: O vocabulário FECHADO de por que uma chave pronta não foi servida (§8.2).
#: ⚠️ `breaker` já existe aqui e ninguém o escreve ainda: o disjuntor por
#: provedor é de outra fatia, e o lugar dele na conta fica reservado para que a
#: conta não mude de forma quando ele chegar.
_MOTIVOS_DE_ESPERA = ("cota", "turno", "breaker", "sem_escopo")

# 🔴 O ESTADO DE ADMISSÃO É DO PROCESSO, NUNCA DA VARREDURA.
#
# Varreduras se SOBREPÕEM (`max_instances=10`). Ocupação que nasce dentro da
# chamada é ocupação que cada varredura conta sozinha — e N varreduras em voo
# multiplicam qualquer teto por N. É o defeito ① acima, e ele não se conserta
# com um número maior; conserta-se com um estado só.
_ADMISSAO = {
    "em_voo_por_escopo": {},   # escopo -> turnos deste escopo em voo AGORA
    "em_voo_global": 0,        # turnos em voo no processo inteiro
    "aguardando": {},          # chave -> escopo, adiadas na varredura anterior
    "servidas": {},            # chave -> True, processadas desde a última colheita
    "semaforos": {},           # (id(loop), limite) -> asyncio.Semaphore
    "pico_por_escopo": {},     # só para os guardas: maior ocupação já vista
    "pico_global": 0,
}


def _semaforo_global(limite: int):
    """O teto do PROCESSO, compartilhado entre varreduras sobrepostas.

    ⚠️ Um `asyncio.Semaphore` só vale dentro do event loop em que foi usado, e
    o repositório roda testes com vários `asyncio.run`. Por isso o registro é
    por (loop, limite) — e as entradas de loops já fechados são varridas, senão
    o dicionário do isolamento vira vazamento de memória com nome bonito.
    """
    loop = asyncio.get_running_loop()
    registro = _ADMISSAO["semaforos"]
    for chave_velha, (loop_velho, _sem) in list(registro.items()):
        if loop_velho is not loop and loop_velho.is_closed():
            registro.pop(chave_velha, None)
    chave = (id(loop), int(limite))
    atual = registro.get(chave)
    if atual is None:
        atual = (loop, asyncio.Semaphore(int(limite)))
        registro[chave] = atual
    return atual[1]


def _tomar_cota(estado: dict, escopo: str, cota: int) -> bool:
    """ADMISSÃO NÃO-BLOQUEANTE: ou tem vaga agora, ou a chave é adiada.

    🔴 **Por que não é um semáforo por corretora.** Uma corrotina parada
    esperando semáforo segura a varredura: `check_buffers` roda a cada 1 s com
    `max_instances=10`, e varredura que demora minutos esgota as instâncias —
    as novas são PULADAS pelo APScheduler, ninguém renova o TTL do buffer e a
    mensagem do segurado some. Com admissão não-bloqueante a varredura termina
    rápido, o buffer fica no Redis com a vida renovada, e a varredura de 1 s
    depois o reencontra. É a diferença entre esperar e desaparecer.

    ⛔ E os registros nascem sob demanda: um dicionário por corretora que só
    cresce é vazamento de memória com nome de isolamento (`_soltar_cota`).
    """
    em_voo = estado["em_voo_por_escopo"]
    atual = em_voo.get(escopo, 0)
    if cota > 0 and atual >= cota:
        return False
    em_voo[escopo] = atual + 1
    picos = estado["pico_por_escopo"]
    if em_voo[escopo] > picos.get(escopo, 0):
        picos[escopo] = em_voo[escopo]
    return True


def _soltar_cota(estado: dict, escopo: str) -> None:
    """Devolve a vaga — e APAGA o registro quando a corretora zera (D7)."""
    em_voo = estado["em_voo_por_escopo"]
    resta = em_voo.get(escopo, 1) - 1
    if resta <= 0:
        em_voo.pop(escopo, None)
    else:
        em_voo[escopo] = resta


def _colher_expiradas(estado: dict, recebidas) -> int:
    """Quantas chaves que esperavam SUMIRAM sem ninguém as processar.

    🔴 É o único número desta SPEC que não admite "quase": uma chave que estava
    pronta numa varredura, foi adiada, e não existe na varredura seguinte sem
    ter sido processada, é **uma mensagem de segurado perdida**.

    ⚠️ O que foi processado por QUALQUER varredura (inclusive uma sobreposta)
    sai da conta antes — senão o sucesso de uma viraria a perda da outra.
    """
    aguardando = estado["aguardando"]
    servidas = estado["servidas"]
    if not aguardando:
        servidas.clear()
        return 0
    presentes = set(str(c) for c in (recebidas or []))
    sumiram = 0
    for chave in list(aguardando):
        if chave in presentes:
            continue
        if chave in servidas:
            aguardando.pop(chave, None)
            continue
        aguardando.pop(chave, None)
        sumiram += 1
    servidas.clear()
    return sumiram


async def _renovar_vida(buffer_service, chave: str) -> None:
    """Renova SÓ o TTL da chave — antes de qualquer espera (§8.1)."""
    fn = getattr(buffer_service, "renovar_vida", None)
    if fn is None:
        return
    try:
        await fn(chave)
    except Exception as erro:  # noqa: BLE001
        logger.warning("[ISOLAMENTO] vida não renovada (%s)", type(erro).__name__)


async def _adiar(buffer_service, chave: str, motivo: str) -> None:
    """A chave pronta que não foi servida AGORA continua existindo."""
    fn = getattr(buffer_service, "adiar", None)
    if fn is None:
        return
    try:
        await fn(chave, motivo=motivo)
    except Exception as erro:  # noqa: BLE001
        # ⚠️ SEM PII: a chave TERMINA no telefone. Só o motivo e o tipo do erro.
        logger.warning("[ISOLAMENTO] adiamento por %s falhou (%s)",
                       motivo, type(erro).__name__)


def ordenar_em_rodizio(chaves, escopo_de=None):
    """Agrupa por corretora e INTERCALA: A1 B1 C1 · A2 B2 C2 · A3 …

    🔴 Determinística por construção: dentro do escopo preserva a ordem
    RECEBIDA (que `prontas()` já entrega da mais antiga para a mais nova), e
    entre escopos preserva a ordem de primeira aparição. ⛔ Nada de aleatório e
    nada por tamanho de fila — sem determinismo o guarda não consegue afirmar
    nada, e um rodízio que muda de resultado a cada execução é um rodízio que
    ninguém consegue depurar às 9 da manhã.

    📊 O que isto muda: na ordem do SCAN, 50 chaves de uma corretora vêm todas
    antes da única chave da outra. Intercalado, a outra é a SEGUNDA da fila.
    """
    if escopo_de is None:
        # ⚠️ Import LOCAL, pelo mesmo motivo do import da trava logo abaixo:
        # o motor é recortado do fonte por AST nos guardas.
        from app.services.message_buffer_service import escopo_da_chave as escopo_de

    from itertools import zip_longest

    por_escopo = {}
    for chave in chaves or []:
        por_escopo.setdefault(escopo_de(chave), []).append(chave)
    return [chave for grupo in zip_longest(*por_escopo.values())
            for chave in grupo if chave is not None]


def _atraso_de_teste_ms(company_id_ou_escopo: str) -> int:
    """💭 O ÚNICO mecanismo desta SPEC que degrada de propósito — e ele nasce
    desligado.

    🔴 FAIL-CLOSED por construção, no desenho de `JANELA_SILENCIO_EXCECOES`:
    lista vazia = NINGUÉM. Sem `ISOLAMENTO_ATRASO_ALLOWLIST` contendo o id
    EXATO, devolve 0 e não dorme. Em produção a variável fica vazia.
    """
    alvo = str(company_id_ou_escopo or "").strip()
    permitidas = {c.strip() for c in
                  os.getenv("ISOLAMENTO_ATRASO_ALLOWLIST", "").split(",")
                  if c.strip()}
    if not permitidas or alvo not in permitidas:
        return 0
    return _env_int("ISOLAMENTO_ATRASO_MS", 0, minimum=0)


async def processar_buffers_prontos(chaves, buffer_service, processar,
                                    paralelismo: int = 0,
                                    cota_por_corretora: int = 0,
                                    timeout_s: float = 0) -> dict:
    """Processa as conversas prontas EM PARALELO, com teto — e com COTA.

    Recebe as peças por parâmetro (chaves, serviço, função de processamento)
    porque é assim que o teste exercita ESTE motor com dublês, em vez de
    reimplementar o laço e provar outra coisa (CLAUDE.md §9.4).

    ⛔ `return_exceptions=True` é a regra inteira: uma conversa que estoura não
    pode levar as outras junto. Antes, com `await` no `for`, a primeira exceção
    caía no `except` de fora e as conversas seguintes da varredura **nunca eram
    processadas** — o defeito de uma pessoa virava silêncio para todas.

    🔴 **Os parâmetros novos têm default 0 = "leia do ambiente"**, e a
    assinatura antiga continua válida: o guarda de paralelismo chama com
    `paralelismo=6` e `paralelismo=1` e TEM de continuar verde sem ser editado.

    ⚠️ **Os dois caminhos, e por que existem.** Quando o serviço de buffer
    expõe `escopo_da_chave` (o serviço REAL), vale a cota por corretora, o
    rodízio, o adiamento e o teto de tempo. Quando não expõe (o dublê do guarda
    de paralelismo), o motor se comporta exatamente como antes — é o mesmo
    `getattr` que já governa a trava de turno logo abaixo, pelo mesmo motivo:
    o guarda recorta do fonte APENAS `_PARALELISMO_PADRAO`, `_env_int` e esta
    função, e um nome novo tocado no caminho dele viraria `NameError` dentro do
    teste, não dentro do produto — que é onde se descobriria tarde.
    """
    recebidas = [str(c) for c in (chaves or []) if c]
    escopo_de = getattr(buffer_service, "escopo_da_chave", None)
    com_cota = escopo_de is not None

    if com_cota:
        estado = _ADMISSAO
        limite = paralelismo or _env_int("WHATSAPP_BUFFER_PARALELISMO",
                                         _PARALELISMO_COM_COTA_PADRAO)
        cota = cota_por_corretora or _env_int("WHATSAPP_COTA_POR_CORRETORA",
                                              _COTA_PADRAO)
        teto_turno = float(timeout_s or _env_int("WHATSAPP_TURNO_TIMEOUT_S",
                                                 _TURNO_TIMEOUT_PADRAO_S))
        semaforo = _semaforo_global(limite)
        expiradas = _colher_expiradas(estado, recebidas)
        adiadas = {motivo: 0 for motivo in _MOTIVOS_DE_ESPERA}
    else:
        estado = None
        limite = paralelismo or _env_int("WHATSAPP_BUFFER_PARALELISMO",
                                         _PARALELISMO_PADRAO)
        cota = 0
        teto_turno = 0.0
        semaforo = asyncio.Semaphore(limite)
        expiradas = 0
        adiadas = {"cota": 0, "turno": 0, "breaker": 0, "sem_escopo": 0}

    # 🔴 A CONFERÊNCIA DE PRONTIDÃO SAI DE DENTRO DO SEMÁFORO (§5.2).
    # Ela custa um GET de ~1 ms e estava atrás de até 6 turnos de LLM: a
    # conversa da outra corretora não ficava atrás na fila, ela NEM ERA OLHADA.
    _prontas = getattr(buffer_service, "prontas", None)
    if _prontas is not None:
        fila = list(await _prontas(recebidas))
    else:
        # Legado: `should_process` continua sendo perguntado dentro de `_uma`.
        fila = list(recebidas)

    if com_cota:
        fila = ordenar_em_rodizio(fila, escopo_de)

    timeouts = 0
    sumidas = 0

    async def _uma(chave: str) -> bool:
        nonlocal timeouts, sumidas
        escopo = escopo_de(chave) if com_cota else ""

        if com_cota:
            # ⛔ FAIL-CLOSED: sem corretora identificada não se processa às
            # cegas. 📊 Hoje esta chave já não é respondida (`abrir_turno` a
            # recusa, 001.2 §5.3); o que muda é ela aparecer na conta.
            if not escopo:
                adiadas["sem_escopo"] += 1
                await _adiar(buffer_service, chave, "sem_escopo")
                return False
            # ============================================================
            # ① A COTA DA CORRETORA VEM PRIMEIRO. SEMPRE.
            # ============================================================
            # Se o teto global viesse antes, uma conversa esperando a cota da
            # própria corretora estaria SEGURANDO um slot global — a corretora
            # saturada passaria a consumir os slots do processo inteiro só para
            # esperar. É a inversão que transforma a proteção no defeito.
            if com_cota and not _tomar_cota(estado, escopo, cota):
                adiadas["cota"] += 1
                await _adiar(buffer_service, chave, "cota")
                return False

        try:
            if com_cota:
                # 🔴 Renova a VIDA antes de esperar o teto global: quem espera
                # não pode morrer de TTL enquanto espera (§8.1).
                await _renovar_vida(buffer_service, chave)
            async with semaforo:        # ② o teto do PROCESSO, depois
                if com_cota:
                    estado["em_voo_global"] += 1
                    if estado["em_voo_global"] > estado["pico_global"]:
                        estado["pico_global"] = estado["em_voo_global"]
                try:
                    if _prontas is None and not await buffer_service.should_process(chave):
                        return False

                    # =====================================================
                    # 🔴 A TRAVA DE TURNO VEM ANTES DO `get_and_clear`
                    # =====================================================
                    #
                    # A ORDEM É A REGRA INTEIRA. Se a trava viesse depois,
                    # perder a trava custaria o BUFFER — as cinco mensagens do
                    # segurado sumiriam do Redis e ninguém as responderia.
                    # Perder a trava ANTES custa 1 segundo: o buffer fica, e a
                    # varredura tenta de novo na volta seguinte.
                    #
                    # ⚠️ `getattr` e não chamada direta: o motor continua
                    # aceitando um serviço de buffer sem trava (é o dublê do
                    # guarda de paralelismo, a LINHA DE CONTROLE desta SPEC).
                    # Quem garante que o serviço REAL tem a trava é
                    # `test_uma_rajada_um_turno.py`.
                    _abrir = getattr(buffer_service, "abrir_turno", None)
                    turno = None
                    if _abrir is not None:
                        # ⚠️ Import LOCAL, e é de propósito: o motor é
                        # recortado do fonte por AST no guarda de paralelismo,
                        # e um import de topo que ele não pede vira `NameError`
                        # dentro do teste — não dentro do produto, que é onde
                        # se descobriria tarde.
                        from app.services.message_buffer_service import (
                            Turno, partes_da_chave,
                        )

                        escopo_do_turno, phone = partes_da_chave(chave)
                        token = await _abrir(escopo_do_turno, phone)
                        if token is None:
                            # 🔴 O buffer FICA. Ninguém o tocou.
                            if com_cota:
                                adiadas["turno"] += 1
                                await _adiar(buffer_service, chave, "turno")
                            return False
                        turno = Turno(escopo_do_turno, phone, token)

                    try:
                        buffer = await buffer_service.get_and_clear_buffer(chave)
                        if not buffer:
                            # A chave sumiu entre a conferência e o consumo, e
                            # a trava de turno garante que não foi outra
                            # varredura: foi o TTL. É perda, e é contada.
                            if com_cota:
                                sumidas += 1
                            return False
                        combined_msg = buffer_service.get_combined_message(buffer)
                        # Leitura de campo, não regra: v2 traz `itens`; o v1 que
                        # ainda estiver no Redis (<= 60 s de TTL) traz `messages`.
                        itens = [i for i in (buffer.get("itens") or [])
                                 if isinstance(i, dict)]
                        if not itens:
                            itens = [{"tipo": "text", "texto": str(m or "")}
                                     for m in (buffer.get("messages") or [])]
                        msg_count = len(itens)
                        logger.info("[BUFFER] Processing buffer: %d itens", msg_count)
                        extras = {}
                        if turno is not None:
                            extras["turno"] = turno
                            extras["chave_do_buffer"] = chave
                            extras["buffered_items"] = itens

                        if com_cota:
                            atraso = _atraso_de_teste_ms(escopo)
                            if atraso > 0:
                                logger.warning(
                                    "[ISOLAMENTO] atraso de TESTE de %d ms neste "
                                    "escopo — allowlist ligada", atraso)
                                await asyncio.sleep(atraso / 1000.0)

                        chamada = processar(
                            payload_dict=buffer["payload"],
                            combined_message=combined_msg,
                            buffered_messages=[
                                str(i.get("texto") or i.get("legenda") or "")
                                for i in itens],
                            **extras,
                        )
                        if teto_turno > 0:
                            # 🔴 TETO POR TURNO. ⚠️ A ESSA ALTURA O BUFFER JÁ
                            # FOI CONSUMIDO, e a decisão é declarada: a rajada
                            # NÃO volta ao buffer. Não há como saber daqui se o
                            # envio ao segurado já saiu, e devolver criaria a
                            # chance de DUAS respostas para a mesma pergunta —
                            # que é pior do que uma resposta atrasada. O turno
                            # cortado entra em `timeouts` e no contador da
                            # corretora, que é onde ele tem de aparecer.
                            try:
                                await asyncio.wait_for(chamada, timeout=teto_turno)
                            except asyncio.TimeoutError:
                                timeouts += 1
                                logger.error(
                                    "[ISOLAMENTO] turno cortado pelo teto de %.0f s "
                                    "— nada foi dito ao segurado por este caminho",
                                    teto_turno)
                                return False
                        else:
                            await chamada
                        logger.info("[BUFFER] ✅ Processed: combined %d itens",
                                    msg_count)
                        if com_cota:
                            estado["servidas"][chave] = True
                            estado["aguardando"].pop(chave, None)
                        return True
                    finally:
                        if turno is not None:
                            await buffer_service.fechar_turno(
                                turno.escopo, turno.phone, turno.token)
                finally:
                    if com_cota:
                        estado["em_voo_global"] -= 1
        finally:
            if com_cota and escopo:
                _soltar_cota(estado, escopo)

    resultados = await asyncio.gather(*(_uma(c) for c in fila),
                                      return_exceptions=True)

    processadas = 0
    falhas = 0
    for r in resultados:
        if isinstance(r, BaseException):
            falhas += 1
            # ⚠️ SEM PII: nem telefone, nem chave (a chave TERMINA no telefone).
            # Só o tipo do erro — que é o que diz o que consertar.
            logger.error("[BUFFER] ❌ uma conversa falhou (%s) — as outras seguiram",
                         type(r).__name__)
        elif r:
            processadas += 1

    if com_cota:
        await _fechar_a_conta(buffer_service, estado, escopo_de, fila,
                              adiadas, expiradas + sumidas, timeouts)

    return {"vistas": len(recebidas), "prontas": len(fila),
            "processadas": processadas, "adiadas": adiadas,
            "falhas": falhas, "timeouts": timeouts,
            "expiradas": expiradas + sumidas}


async def _fechar_a_conta(buffer_service, estado, escopo_de, fila,
                          adiadas, expiradas, timeouts) -> None:
    """Grava o que a Central de Agentes vai LER — UMA escrita por corretora.

    ⛔ Uma escrita por CHAVE seriam 200 idas ao Redis numa varredura de rajada,
    para um número que ninguém lê 200 vezes por segundo.
    """
    pendentes = {}
    for chave in fila:
        escopo = escopo_de(chave)
        if escopo and chave not in estado["servidas"]:
            pendentes[chave] = escopo
    estado["aguardando"].update(pendentes)

    por_escopo = {}
    for escopo in pendentes.values():
        por_escopo[escopo] = por_escopo.get(escopo, 0) + 1
    for escopo in estado["em_voo_por_escopo"]:
        por_escopo.setdefault(escopo, 0)

    motivo = ""
    for nome in _MOTIVOS_DE_ESPERA:
        if adiadas.get(nome):
            motivo = nome
            break

    registrar = getattr(buffer_service, "registrar_ocupacao", None)
    if registrar is None:
        return
    for escopo, em_espera in por_escopo.items():
        try:
            await registrar(
                escopo,
                em_execucao=estado["em_voo_por_escopo"].get(escopo, 0),
                em_espera=em_espera, motivo=motivo,
                expiradas=expiradas, timeouts=timeouts)
        except Exception as erro:  # noqa: BLE001
            # ⛔ Contador nunca derruba atendimento.
            logger.warning("[ISOLAMENTO] contador não gravado (%s)",
                           type(erro).__name__)


async def check_buffers():
    """
    Periodic job - scans Redis for ready buffers (async, non-blocking).
    """
    redis = await get_async_redis_client()
    buffer_service = await get_message_buffer_service()

    from app.api.webhook import process_whatsapp_message_background

    try:
        cursor = 0
        chaves = []

        while True:
            cursor, keys = await redis.scan(
                cursor=cursor, match="whatsapp_buffer:*", count=100
            )

            for key in keys:
                # SPEC-063 Bloco H — a chave agora tem tenant
                # (`whatsapp_buffer:{integracao}:{telefone}`) e o varredor passa
                # a chave INTEIRA. Extrair o telefone e remontar a chave era o
                # que prendia o buffer ao formato antigo de uma parte só.
                chaves.append(
                    key.decode() if isinstance(key, (bytes, bytearray)) else str(key)
                )

            if cursor == 0:
                break

        # 🔴 SEM `if chaves:` — e o motivo foi uma MUTACAO que ficou verde
        # (21/09/2026, M-18-7). Com `adiar` desligado, TODAS as chaves da fila
        # expiravam de uma vez; o SCAN voltava vazio, a varredura era pulada, e
        # a colheita de `expiradas` nunca rodava. A perda total de mensagens era
        # justamente o caso em que ninguém ficava sabendo. Varredura vazia custa
        # um `gather` de nada — e é ela que fecha a conta do que sumiu.
        await processar_buffers_prontos(
            chaves, buffer_service, process_whatsapp_message_background)

    except Exception as e:
        logger.error(f"[BUFFER] ❌ Error in check_buffers: {e}", exc_info=True)


def start_buffer_scheduler():
    """Start the APScheduler for buffer processing."""
    if not scheduler.running:
        scheduler.add_job(
            check_buffers,
            "interval",
            seconds=1,
            id="whatsapp_buffer_check",
            max_instances=10,
        )
        # Follow-up pós-acionamento (SPEC-031 Faixa 6): "o guincho chegou?" e
        # encerramento carinhoso — varre sessões monitoring a cada 60s.
        from app.tasks.dispatch_followup import check_dispatch_followups

        scheduler.add_job(
            check_dispatch_followups,
            "interval",
            seconds=60,
            id="dispatch_followup_check",
            max_instances=1,
        )
        # VIGIA + SENTINELA (SPEC-034 Onda 1): vigilância de desfecho e
        # recuperação de travas nos acionamentos — varredura a cada 20s.
        from app.tasks.dispatch_watchdog import check_dispatch_watchdog

        scheduler.add_job(
            check_dispatch_watchdog,
            "interval",
            seconds=20,
            id="dispatch_watchdog_check",
            max_instances=1,
        )
        # VIGIA DO PORTAL (SPEC-065): a SEGUNDA varredura do MESMO vigia.
        #
        # 📊 Medido em 04/08/2026: `dispatch_watchdog` e `handoff_watchdog` têm
        # zero menções a "portal". Eles cuidam do corredor de WhatsApp com a
        # seguradora; o portal de vidros é outro caminho (`portal_jobs`) e não
        # tinha ninguém olhando.
        #
        # O ponto cego era estreito e fatal: a `portal_action` espera o worker
        # por 150s e conta ao segurado o que aconteceu. Depois disso, ninguém.
        # O job chega em `needs_human` mais tarde e a conversa nunca fica
        # sabendo — o segurado ouviu "um minutinho" e o minutinho não acaba.
        #
        # 60s (e não 20s): job de portal leva minutos, não segundos. Varrer mais
        # rápido só gastaria banco para reencontrar o mesmo job.
        from app.tasks.vigia_do_portal import varrer_portal

        scheduler.add_job(
            varrer_portal,
            "interval",
            seconds=60,
            id="vigia_do_portal",
            max_instances=1,
        )
        # GARIMPO (SPEC-034 Onda 3): minera desejos/dores dos corretores 1x/dia
        # (marcador em Redis; captura determinística, custo zero de LLM).
        from app.services.broker_insights import check_garimpo

        scheduler.add_job(
            check_garimpo,
            "interval",
            seconds=3600,
            id="garimpo_check",
            max_instances=1,
        )
        # AUDITOR + overlays do ALFAIATE (SPEC-034 Onda 4): scorecards 1x/dia
        # (marcador Redis) e cache de overlays atualizado a cada varredura.
        from app.services.conversation_auditor import check_auditor

        scheduler.add_job(
            check_auditor,
            "interval",
            seconds=1800,
            id="auditor_check",
            max_instances=1,
        )
        # IA DE SUGESTÕES (SPEC-034 Onda 5): auxiliar global ON por padrão —
        # 1 msg/semana por corretora (segunda, horário comercial, marcador Redis).
        from app.services.proactive_suggestions import check_suggestions

        scheduler.add_job(
            check_suggestions,
            "interval",
            seconds=1800,
            id="sugestoes_check",
            max_instances=1,
        )
        # RELATÓRIO DE SÁBADO (SPEC-036): resumo semanal das Atividades por
        # corretora ("olha quanta coisa fizemos") — sábado de manhã, 1x/semana.
        from app.services.weekly_report import check_weekly_report

        scheduler.add_job(
            check_weekly_report,
            "interval",
            seconds=1800,
            id="relatorio_semanal_check",
            max_instances=1,
        )
        # 🔴 SPEC-EXTRA-001.3 BLOCO D.4 — O RESUMO DAS 19h.
        #
        # ⛔ NENHUM SCHEDULER NOVO: entra como mais um job DESTE agendador, no
        # padrão do relatório de sábado logo acima — intervalo curto + checagem
        # interna de "já é hora / já saiu hoje". As 19h são LOCAIS da corretora.
        from app.tasks.o_resumo_das_19h import check_resumo_das_19h

        scheduler.add_job(
            check_resumo_das_19h,
            "interval",
            seconds=1800,
            id="resumo_das_19h",
            max_instances=1,
        )
        # SENTINELA DE ROTAS (SPEC-038/039 F1): tece TODAS as seguradoras e
        # detecta mudança de menu — 1x/dia (marcador Redis). Dá vida própria ao
        # Atlas: os mapas se atualizam sozinhos e o drift é detectado.
        from app.services.atlas.route_sentinel import check_atlas_sentinela

        scheduler.add_job(
            check_atlas_sentinela,
            "interval",
            minutes=_env_int("ATLAS_INCREMENTAL_INTERVAL_MINUTES", 15),
            id="atlas_sentinela_check",
            max_instances=1,
        )

        # SPEC-063 — HIGIENE E PROMOÇÃO DO MAPA DE URA.
        #
        # 📊 07/08/2026: zero mapas `active`, e por isso a Sentinela acima saía
        # na terceira linha, `route_drift` = 0, `playbook_overlays` = 0 e o
        # alerta de mudança de menu nunca chegou ao Founder. Três subsistemas
        # prontos e inalcançáveis por um `status`.
        #
        # Promover à mão resolveria — e teria publicado 115 nomes de segurado e
        # 24 marcas de corretora no acervo global. Por isso limpar é
        # pré-condição de promover, e as duas coisas rodam juntas aqui em vez de
        # depender de alguém lembrar a ordem.
        #
        # De hora em hora: é idempotente e não chama modelo nenhum (regex e
        # escrita). Custo por rodada sem trabalho: uma consulta.
        from app.services.ura_map_service import higienizar_e_promover

        scheduler.add_job(
            higienizar_e_promover,
            "interval",
            seconds=_env_int("URA_HIGIENE_SECONDS", 3600),
            id="ura_higiene_e_promocao",
            max_instances=1,
        )

        # SPEC-051: mídias do Observador nunca bloqueiam o webhook. Um lote
        # pequeno é enriquecido separadamente e armazenado apenas em cofre.
        from app.services.atlas.observer_media import observer_media_check

        scheduler.add_job(
            observer_media_check,
            "interval",
            seconds=_env_int("OBSERVER_MEDIA_INTERVAL_SECONDS", 10, minimum=5),
            id="observer_media_check",
            max_instances=1,
        )

        # SPEC-062 §30.3 — BACKUP DO STORAGE, de hora em hora.
        #
        # O Supabase faz backup do Postgres pelo plano. O MinIO nao tinha
        # rotina nenhuma — e e ele que guarda a UNICA copia de cada documento
        # que a corretora enviou. O Postgres guarda o ponteiro, nao o arquivo.
        #
        # A rotina e incremental (so copia o que falta) e NUNCA apaga no
        # destino: um espelho que replica exclusao e inutil justamente no caso
        # que mais importa — alguem apaga por engano e o backup apaga junto.
        from app.services.backup.minio_backup import rodar_periodicamente as _backup

        scheduler.add_job(
            _backup,
            "interval",
            minutes=_env_int("MINIO_BACKUP_INTERVAL_MINUTES", 60),
            id="minio_backup",
            max_instances=1,
        )

        # SPEC-040 Onda 1: retenção do Espelho de Atendimento — o transcript
        # cru (com PII) expira; purge 1x/dia (marcador Redis, gate na task).
        from app.services.atlas.attendance_capture import check_attendance_purge

        scheduler.add_job(
            check_attendance_purge,
            "interval",
            seconds=3600,
            id="attendance_purge_check",
            max_instances=1,
        )

        # SPEC-040 Onda 2: seed do conhecimento global (idempotente por hash) —
        # 1ª rodada ~2min após o boot, depois checagem horária (custo zero se
        # nada mudou). É o que popula a coleção autobrokers_global sozinho.
        from datetime import datetime as _dt, timedelta as _td, timezone as _tz

        from app.services.global_knowledge_seed import check_global_seed

        scheduler.add_job(
            check_global_seed,
            "interval",
            seconds=3600,
            id="global_seed_check",
            max_instances=1,
            next_run_time=_dt.now(_tz.utc) + _td(seconds=120),
        )

        # SPEC-040 Onda 3: Destilador do Espelho de Atendimento — 1x/dia na
        # madrugada (janela + marcador dentro da task). Sonnet no braçal,
        # modelo forte na síntese de playbook. Zero LLM sem sessão nova.
        from app.services.attendance_distiller import check_attendance_distiller

        scheduler.add_job(
            check_attendance_distiller,
            "interval",
            # A cada 30 min. No regime normal a task sai em milissegundos (fora
            # da janela da madrugada ou marcador do dia ja gravado); o intervalo
            # curto so importa no MODO DE RECUPERACAO, depois de um pareamento.
            seconds=_env_int("DISTILLER_CHECK_SECONDS", 1800),
            id="attendance_distiller_check",
            max_instances=1,
        )

        # SPEC-040 Onda 4: Sentinela de Regressão — nota média 24h vs 7 dias,
        # por corretora; queda relevante = alerta ANTES do cliente sentir.
        # Determinístico, zero LLM, 1x/dia (marcador na task).
        from app.services.regression_sentinel import check_regression

        scheduler.add_job(
            check_regression,
            "interval",
            seconds=3600,
            id="regression_sentinel_check",
            max_instances=1,
        )

        # SPEC-040 Onda 5: memória por agente — blocos reescritos 1x/dia a
        # partir dos dados reais (determinístico, zero LLM). A Central mostra
        # "o que cada agente sabe".
        from app.services.agent_memory import check_agent_memories

        scheduler.add_job(
            check_agent_memories,
            "interval",
            hours=_env_int("AGENT_MEMORY_INTERVAL_HOURS", 6),
            id="agent_memory_check",
            max_instances=1,
        )

        # SPEC-042: Lapidador — otimização reflexiva SEMANAL dos playbooks
        # ativos com feedback novo (padrão GEPA); draft passa pelo gate.
        from app.services.prompt_optimizer import check_lapidador

        scheduler.add_job(
            check_lapidador,
            "interval",
            seconds=3600,
            id="lapidador_check",
            max_instances=1,
        )

        # SPEC-045: fila de cortesia — envios de plataforma adiados (cliente
        # estava em atendimento) são re-tentados a cada 10 min.
        from app.services.platform_outbound import check_platform_queue

        scheduler.add_job(
            check_platform_queue,
            "interval",
            seconds=600,
            id="platform_queue_check",
            max_instances=1,
        )

        # SPEC-063 Bloco E / P-34 — VARREDURA DE ACIONAMENTO ÓRFÃO, periódica.
        #
        # A varredura existia e era boa; o GATILHO é que era frágil.
        # `_agendar_reconciliacao_uma_vez()` dispara no primeiro cache-miss do
        # processo, uma vez só. Isso tem duas falhas, e a segunda é a que dói:
        #
        #   1. uma vez por processo — depois disso, um Redis esvaziado às 3h da
        #      manhã só é notado no próximo deploy;
        #   2. e ela depende de TRÁFEGO. Se o cache cair e nenhuma mensagem
        #      chegar, `load_active_dispatch` nunca é chamado, o cache-miss
        #      nunca acontece, e o segurado com o guincho a caminho fica órfão
        #      **em silêncio** — exatamente o caso que a varredura existe para
        #      cobrir. O único sintoma é uma conversa que não anda.
        #
        # 5 minutos é folgado contra a janela real: a sessão vive 6h no Redis
        # (24h em `monitoring`). O que muda é o piso — o atraso máximo para
        # perceber um órfão deixa de ser "até alguém mandar uma mensagem" e
        # passa a ser um número.
        #
        # A varredura é idempotente por construção (órfão já sinalizado não
        # vira alarme de novo) e limitada a 50 runs em voo por passada.
        from app.services.dispatch_router import reconciliar_acionamentos_orfaos

        scheduler.add_job(
            reconciliar_acionamentos_orfaos,
            "interval",
            minutes=_env_int("DISPATCH_RECONCILE_INTERVAL_MINUTES", 5),
            id="dispatch_reconcile_check",
            max_instances=1,
            # Depois de um deploy, o cache está vazio e a verdade durável não.
            # Este é o momento de maior chance de órfão no dia inteiro.
            next_run_time=_dt.now(_tz.utc) + _td(seconds=60),
        )

        # SPEC-063 Bloco V — HEARTBEAT DO CANAL: o vigia que desmente.
        #
        # 📊 03/08/2026, banco de produção: três integrações ATIVAS afirmando
        # `connected`/`connecting` com `last_seen_at` congelado em 28-29/07 —
        # quatro e cinco dias de estado que ninguém confirmava. A causa era que
        # NADA renovava a coluna: ela só é escrita quando chega um
        # `connection.update`, e evento de transição não chega em canal parado.
        #
        # O heartbeat pergunta ao provedor e grava a resposta. Confirmou →
        # renova `last_seen_at` (é o que faz a idade da coluna significar algo).
        # Não confirmou por mais de 15 min → o estado vira `unknown` e a tela
        # para de prometer atendimento. A lógica inteira mora em
        # `channel_state.py`, o dono declarado do estado do canal; aqui só se
        # registra o job no agendador que já existe.
        # ESPELHO NO CHAT — a rede que pega o que a ponte ao vivo perdeu.
        #
        # A ponte (`observer_intake` → `espelho_chat`) age quando a mensagem
        # chega. Este job varre o acervo e leva ao chat o que ainda não foi.
        #
        # 📊 Ele existe por duas medições do mesmo dia, 06/08/2026:
        #   · a ponte subiu 22 min depois da última mensagem, e o chat abriu
        #     vazio sobre 32.128 mensagens já capturadas;
        #   · a Amandus pareou e trouxe 13.200 mensagens de histórico de uma
        #     vez — HISTORY_SYNC não passa pela ponte ao vivo.
        #
        # E por uma frase do Founder: *"eu só quero as coisas funcionando"*. Um
        # produto que precisa de alguém abrir terminal para mostrar as conversas
        # do dia não está pronto. Nenhum motor novo: entra no agendador que já
        # existe, ao lado do heartbeat.
        #
        # 🔴 AQUI DIZIA "barato porque é incremental — a dedup faz a segunda
        # passada não escrever nada". A frase estava certa sobre ESCRITAS e
        # errada sobre LEITURAS, e a diferença derrubou o produto.
        #
        # 📊 13/08/2026: a implementação relia a janela de 7 dias do acervo a
        # cada ciclo (4.008 linhas) e chamava `espelhar_no_chat` para cada uma.
        # `pg_stat_statements`: **771.313 leituras de `messages` para 5.681
        # mensagens escritas** — 136 leituras por escrita. Da ordem dos 6,98 GB
        # que restringiram a organização no Supabase Free; PostgREST, Storage e
        # Auth passaram a responder 402 e o portal-worker parou de enxergar
        # `portal_jobs`.
        #
        # Deduplicar DEPOIS de ler não torna a leitura barata. Agora ele é
        # incremental de verdade — cursor durável por corretora, no relógio de
        # ingestão (migration 20260813_01).
        #
        # ⚠️ E NASCE DESLIGADO. `ESPELHO_SYNC_ENABLED` precisa dizer que sim.
        # O job continua registrado de propósito: ele sai na primeira linha
        # quando está OFF, e ligar passa a ser mudar uma variável — não fazer
        # deploy. O primeiro boot depois do Upgrade para Pro é o instante mais
        # perigoso do plano, e é justamente nele que este job não pode subir
        # trabalhando.
        from app.services.atlas.espelho_chat import sincronizar_chats, sync_ligado

        logger.info("[ESPELHO] recovery periódico: %s",
                    "LIGADO" if sync_ligado() else "desligado (ESPELHO_SYNC_ENABLED)")

        scheduler.add_job(
            sincronizar_chats,
            "interval",
            minutes=_env_int("ESPELHO_SYNC_INTERVAL_MINUTES", 10),
            id="espelho_chat_sync",
            max_instances=1,
            # Logo após o boot: depois de um deploy, as conversas do dia
            # aparecem em ~2 min, não no fim do primeiro intervalo.
            next_run_time=_dt.now(_tz.utc) + _td(seconds=120),
        )

        from app.services.whatsapp.channel_state import verificar_canais

        scheduler.add_job(
            verificar_canais,
            "interval",
            minutes=_env_int("CHANNEL_HEARTBEAT_INTERVAL_MINUTES", 5),
            id="channel_heartbeat_check",
            max_instances=1,
            # Primeira passada logo após o boot: depois de um deploy a verdade
            # é restaurada em ~90s, não no fim do primeiro intervalo.
            next_run_time=_dt.now(_tz.utc) + _td(seconds=90),
        )
        # SPEC-063 — VIGIA DO HANDOFF HUMANO: `HUMAN_REQUESTED` deixa de ser
        # estado sem saída.
        #
        # 📊 03/08/2026, banco de produção: UMA conversa presa em
        # `HUMAN_REQUESTED` há ~730 horas. Trinta dias. A causa não foi a
        # marcação — foi que NENHUM job olhava `conversations.status`. O aviso
        # ao suporte saía uma vez, no instante do pedido; se ninguém viu aquela
        # mensagem, ninguém veria nunca mais.
        #
        # É a MESMA fragilidade do gatilho de reconciliação de acionamento
        # órfão, logo acima: um estado que só é observado quando nasce não é
        # observado. Este job dá a ele um piso — o atraso máximo para alguém
        # ser lembrado deixa de ser "para sempre" e passa a ser um número.
        #
        # A lógica mora em `app/tasks/handoff_watchdog.py`, ao lado dos outros
        # vigias, e o import da FERRAMENTA de handoff (que arrasta `langgraph`)
        # acontece dentro da função, por execução. `main.py` chama
        # `start_buffer_scheduler()` sem `try`: um ImportError aqui derrubaria a
        # aplicação inteira, não só este job (CLAUDE.md §9.1).
        from app.tasks.handoff_watchdog import varrer_handoffs_parados

        scheduler.add_job(
            varrer_handoffs_parados,
            "interval",
            minutes=_env_int("HANDOFF_WATCHDOG_INTERVAL_MINUTES", 10),
            id="handoff_watchdog_check",
            max_instances=1,
            # Depois de um deploy, quem já estava esperando continua esperando.
            next_run_time=_dt.now(_tz.utc) + _td(seconds=120),
        )

        # 🔴 SPEC-086 BLOCO C — a espera vencida acorda alguém.
        #
        # ⚠️ **Mesmo módulo, mesmo agendador, mesmo `_avisar_suporte`.** A SPEC
        # manda estender o vigia que já existe, e não criar outro: um
        # escalonamento novo seria motor paralelo (§5), e um scheduler novo
        # seria a fila que a §5 também proíbe.
        #
        # ⚠️ O intervalo é o MESMO do handoff de propósito — quem ajustar um
        # ajusta os dois, e duas cadências diferentes para o mesmo grupo de
        # WhatsApp é como se ensina uma equipe a ignorar alarme.
        #
        # ⚠️ E o `next_run_time` sai 30 s DEPOIS do outro: as duas varreduras
        # avisam o mesmo destino, e sobrepô-las mandaria duas mensagens no mesmo
        # segundo — que a corretora lê como defeito, não como dois assuntos.
        from app.tasks.handoff_watchdog import varrer_esperas_vencidas

        scheduler.add_job(
            varrer_esperas_vencidas,
            "interval",
            minutes=_env_int("HANDOFF_WATCHDOG_INTERVAL_MINUTES", 10),
            id="espera_watchdog_check",
            max_instances=1,
            next_run_time=_dt.now(_tz.utc) + _td(seconds=150),
        )

        scheduler.start()
        logger.info("✅ [BUFFER SCHEDULER] Started (interval: 1s, max_instances: 10)")
    else:
        logger.warning("[BUFFER SCHEDULER] Already running")


def shutdown_buffer_scheduler():
    """Shutdown the APScheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("🛑 [BUFFER SCHEDULER] Stopped")
    else:
        logger.warning("[BUFFER SCHEDULER] Not running")
