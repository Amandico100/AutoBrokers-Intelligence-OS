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
# ao mesmo tempo, desde sempre. E `check_buffers` roda com `max_instances` =
# teto global + folga (`start_buffer_scheduler`) — ou seja, dezenas de
# varreduras podem se sobrepor. O serial era serial só DENTRO de uma
# varredura; nunca foi garantia de nada.
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
#     cada 1 s com várias instâncias sobrepostas: o "teto de 6" real era até
#     60, e uma cota criada dentro da função teria o MESMO furo — cota 4
#     viraria 40. Por isso a ocupação mora em `_ADMISSAO`, no módulo: um
#     estado por PROCESSO.
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

#: 💭 A folga de instâncias da varredura sobre o teto global (`start_buffer_
#: scheduler`). Ela existe para as varreduras que só ADIAM: elas não ocupam
#: vaga do teto global, terminam em milissegundos, e ainda assim consomem uma
#: instância do agendador enquanto rodam.
_FOLGA_DE_INSTANCIAS = 16

#: 📊 Medido em produção (21/09/2026): p95 do turno do chat = 107 s, máx 136 s,
#: mediana 39 s, n=41. A query, ao lado do número (CLAUDE.md §12.1):
#:
#: ```sql
#: SELECT count(*),
#:        percentile_cont(0.5)  WITHIN GROUP (ORDER BY (payload->'turn'->>'total_ms')::bigint),
#:        percentile_cont(0.95) WITHIN GROUP (ORDER BY (payload->'turn'->>'total_ms')::bigint),
#:        max((payload->'turn'->>'total_ms')::bigint)
#:   FROM messages
#:  WHERE role = 'assistant'
#:    AND payload->'turn'->>'status' = 'complete';
#: ```
#:
#: 🔴 **E O TETO TEM DE SER MAIOR QUE O PIOR CASO DE UMA CHAMADA** — senão ele
#: corta ANTES de o modelo desistir, e quem corta com `CancelledError` não
#: dispara nenhum dos `except Exception` do caminho: o segurado fica em silêncio
#: DEFINITIVO. 📊 A conta, com os defaults de `relogio_do_modelo`:
#:
#:     LLM_TIMEOUT_SEGUNDOS (90 s) × (LLM_MAX_RETRIES (2) + 1 tentativa) = 270 s
#:     180 s  <  270 s   -> o teto cortava no meio da 2ª tentativa   (o defeito)
#:     300 s  >  270 s   -> o SDK desiste primeiro, com TimeoutError (o conserto)
#:
#: 300 s é 2,2× o turno mais lento já medido (136 s) e 40 s acima do pior caso
#: do SDK. ⚠️ Baixar o teto POR CHAMADA para 60 s resolveria a inequação e
#: cortaria chamada legítima: o p95 do turno inteiro é 107 s. A desigualdade é
#: guardada por `tests/test_a_costura_do_isolamento.py` (caso 6).
_TURNO_TIMEOUT_PADRAO_S = 300

#: O vocabulário FECHADO de por que uma chave pronta não foi servida (§8.2).
#: ⚠️ `breaker` é escrito por DOIS caminhos desde a FATIA 4: o disjuntor ABERTO
#: (retém a corretora inteira) e o MEIO-ABERTO (deixa passar a sonda e retém as
#: outras, §7.4).
_MOTIVOS_DE_ESPERA = ("cota", "turno", "breaker", "sem_escopo")

# 🔴 O ESTADO DE ADMISSÃO É DO PROCESSO, NUNCA DA VARREDURA.
#
# Varreduras se SOBREPÕEM (`max_instances` = teto global + folga). Ocupação que nasce dentro da
# chamada é ocupação que cada varredura conta sozinha — e N varreduras em voo
# multiplicam qualquer teto por N. É o defeito ① acima, e ele não se conserta
# com um número maior; conserta-se com um estado só.
_ADMISSAO = {
    "em_voo_por_escopo": {},   # escopo -> turnos deste escopo em voo AGORA
    "em_voo_global": 0,        # turnos em voo no processo inteiro
    "aguardando": {},          # chave -> escopo, ADIADAS e ainda esperando a vez
    "semaforos": {},           # (id(loop), limite) -> asyncio.Semaphore
    "pico_por_escopo": {},     # só para os guardas: maior ocupação já vista
    "pico_global": 0,
    # 🔴 FATIA 6 — os dois mapas que a COSTURA precisa, e por que eles moram
    # aqui e não dentro da varredura:
    #
    #   `motivo_da_chave`   por que esta chave NÃO foi servida da última vez.
    #                       É o que transforma a conta global da varredura
    #                       (`adiadas`) numa conta POR CORRETORA — e sem conta
    #                       por corretora o aviso ao dono avisaria a corretora
    #                       errada, com o número da fila da outra.
    #   `esperando_desde`   o instante do PRIMEIRO adiamento por COTA daquela
    #                       chave. ⚠️ A admissão é NÃO-bloqueante: a conversa
    #                       adiada sai da varredura e volta numa POSTERIOR, e um
    #                       marco criado dentro da varredura mediria só a última
    #                       tentativa (~0 ms) — escondendo justamente a espera
    #                       que esta SPEC existe para medir.
    #
    # ⛔ Os dois são PODADOS em `_fechar_a_conta` para o conjunto de quem ainda
    # espera: dicionário que só cresce é vazamento de memória com nome bonito
    # (a mesma regra de `_soltar_cota` e do cache de provedor).
    "motivo_da_chave": {},     # chave -> "cota" | "turno" | "breaker" | "sem_escopo"
    "esperando_desde": {},     # chave -> monotonic() do 1º adiamento por cota
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
    várias instâncias sobrepostas, e varredura que demora minutos esgota as
    instâncias do agendador —
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


def marcar_consumida(chave) -> None:
    """A rajada desta chave SAIU do Redis porque alguém deste processo a pegou.

    🔴 **QUEM CONSOME AVISA, NO INSTANTE EM QUE CONSOME.** É a linha inteira
    que separa "mensagem respondida" de "mensagem perdida" na tela do Founder:
    a varredura seguinte não acha a chave no SCAN, e sem este aviso ela conta
    a conversa RESPONDIDA como sumida.

    ⚠️ Vale para os DOIS consumidores: o varredor (`get_and_clear_buffer`) e o
    re-planejamento do turno (`webhook.mesclar_o_que_chegou`), que absorve na
    MESMA resposta a mensagem que chegou no meio do turno.
    """
    alvo = str(chave or "")
    if not alvo:
        return
    _ADMISSAO["aguardando"].pop(alvo, None)
    _ADMISSAO["motivo_da_chave"].pop(alvo, None)
    _ADMISSAO["esperando_desde"].pop(alvo, None)


def _colher_expiradas(estado: dict, recebidas) -> dict:
    """`{escopo: quantas}` — as chaves que ESPERAVAM e sumiram do Redis.

    🔴 É o único número desta SPEC que não admite "quase": uma chave que foi
    ADIADA numa varredura e não existe na varredura seguinte, sem que ninguém
    deste processo a tenha consumido, é **uma mensagem de segurado perdida**.

    ⛔ **E ELE TEM DONO.** 📊 21/09/2026 o número era GLOBAL e era gravado no
    hash de TODO escopo ativo: a perda da corretora A aparecia na tela da B
    (`atk1b`: `corretora-B | expiradas_acumuladas = 1`, com ZERO perdas). Por
    isso a colheita devolve um mapa por escopo, e `_fechar_a_conta` grava cada
    número SÓ no hash do dono.

    ⚠️ **Não existe mais um mapa `servidas`.** Ele era limpo por QUALQUER
    varredura sobreposta e lido pela varredura dona só no fim dela — e era
    assim que uma conversa respondida virava "expirada" duas varreduras depois
    (red team B1a, juiz B3). Agora o pertencimento a `aguardando` é a única
    régua: quem foi ADIADO entra, quem foi CONSUMIDO sai na hora
    (`marcar_consumida`).
    """
    aguardando = estado["aguardando"]
    if not aguardando:
        return {}
    presentes = set(str(c) for c in (recebidas or []))
    sumiram: dict = {}
    for chave, escopo in list(aguardando.items()):
        if chave in presentes:
            continue
        aguardando.pop(chave, None)
        estado["motivo_da_chave"].pop(chave, None)
        estado["esperando_desde"].pop(chave, None)
        sumiram[escopo] = sumiram.get(escopo, 0) + 1
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


async def _adiar(buffer_service, chave: str, motivo: str):
    """A chave pronta que não foi servida AGORA continua existindo.

    🔴 **FATIA 6 — é aqui que a espera passa a ter DONO e RELÓGIO.** Todo
    adiamento do varredor passa por esta função, com a chave e o motivo em mãos;
    anotar aqui é o que evita repetir a contagem em quatro lugares (e é o que
    mantém a conta por corretora e a conta global falando do mesmo fato).

    ⚠️ O registro é no `_ADMISSAO` do MÓDULO — o mesmo estado por PROCESSO de
    que `processar_buffers_prontos` se serve —, porque uma conversa adiada volta
    numa varredura POSTERIOR e o relógio dela não pode nascer de novo a cada
    volta.
    """
    from time import monotonic

    alvo = str(chave)
    _ADMISSAO["motivo_da_chave"][alvo] = str(motivo)
    if motivo == "cota":
        # `setdefault`: quem manda no relógio é o PRIMEIRO adiamento. Reescrever
        # a cada volta zeraria a espera e ela nunca passaria de um segundo.
        _ADMISSAO["esperando_desde"].setdefault(alvo, monotonic())

    fn = getattr(buffer_service, "adiar", None)
    if fn is None:
        return None
    try:
        # Devolve o que o serviço disse: True (vida renovada) · False (a chave
        # NÃO EXISTE mais) · None (não deu para saber). Quem decide é `_guardar`.
        return await fn(chave, motivo=motivo)
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


# ===========================================================================
# 🔴 A COSTURA — o disjuntor pergunta ANTES de consumir o buffer (§7.4, §8)
# ===========================================================================
#
# O RELÓGIO DO MODELO (`app/core/relogio_do_modelo.py`) abre um breaker por
# PROVEDOR quando ele cai. Sem esta costura, o breaker aberto viraria SILÊNCIO:
# o varredor consumiria o buffer (`get_and_clear` apaga a rajada do Redis), a
# chamada ao modelo falharia na hora, e as cinco mensagens do segurado teriam
# sumido — respondidas por ninguém. 🔴 §7.4: *"breaker aberto não vira
# silêncio"*. Quem PERGUNTA é quem RETÉM.
#
# ⚠️ O PROBLEMA REAL, medido antes de desenhar (21/09/2026): o varredor só tem a
# CHAVE (`whatsapp_buffer:{escopo}:{telefone}`, escopo = id da INTEGRAÇÃO), e
# `provedor_configurado(company_config, agent_data)` precisa da configuração do
# agente — que só é resolvida DENTRO de `process_whatsapp_message_background`
# (`webhook.py:811-822` → `langchain_service.process_message(...,
# required_role="attendance")`). Resolver isso por chave, a cada varredura de
# 1 s, com 200 chaves adiadas, seriam 200 consultas por segundo ao banco.
#
# AS OPÇÕES, COM NOTA:
#   (i)   resolver escopo→provedor com cache de 60 s, sempre           78
#   (ii)  perguntar primeiro "ALGUM provedor está barrado?" e SÓ então
#         resolver os escopos                                          **90**
#   (iii) adiar só quando TODOS os provedores estão abertos            35
#
# (ii) vence porque o caso normal — nenhum breaker aberto — custa 📊 **8 idas ao
# Redis** por varredura COM FILA (4 provedores x 1 GET + 1 EXISTS, medido em
# 21/09/2026 com `redteam/atk5_custo_por_varredura.py`; a proposta escreveu
# "quatro GETs" de memória) e ZERO consulta ao banco, independentemente de
# haver 1 ou 200 chaves — e ZERO em varredura VAZIA, que é o caso da maioria
# dos segundos do dia. E porque (iii) é o defeito com outro nome: com o provedor de uma
# corretora fora e o da outra de pé, (iii) não reteria ninguém, e a rajada da
# primeira morreria na chamada.
#
# ⛔ AS REGRAS QUE NÃO SE NEGOCIAM:
#   · Redis fora, breaker indisponível ou erro ao resolver → **NÃO adia**. Na
#     dúvida, atende: um silêncio por engano custa a conversa inteira.
#   · nenhuma PII em log — nem chave, nem telefone, nem nome de corretora.
#   · o provedor sai da MESMA função que a fábrica usa (`provedor_configurado`)
#     e o agente, da MESMA função do atendimento (`_get_raw_agent`, com
#     `required_role="attendance"`). Reescrever a escolha de modelo aqui seria o
#     motor paralelo do CLAUDE.md §5 — e a costura perguntaria pelo breaker de
#     um provedor enquanto a chamada sairia por outro.

#: escopo -> (provedor|None, quando_vence). ⚠️ O negativo TAMBÉM é guardado: sem
#: isso, um escopo que não resolve viraria uma consulta por chave por varredura.
_PROVEDOR_POR_ESCOPO: dict = {}
_PROVEDOR_CACHE_PADRAO_S = 60
_LANGCHAIN_PARA_RESOLVER: list = [None]


async def provedores_barrados() -> set:
    """Quais provedores estão com o disjuntor ABERTO agora. ⛔ Nunca levanta.

    ⚠️ Usa `estado_do_breaker` (LEITURA) e **não** `provedor_disponivel`: este
    consome a sonda do meio-aberto (`SET NX`), e a sonda é de quem vai CHAMAR o
    modelo — uma conversa de cada vez, dentro de `_uma`. Gastar a sonda aqui, no
    nível da varredura, deixaria as conversas retidas sem ninguém para testar se
    o provedor voltou.

    Esta função responde só pelo estado **aberto**. O meio-aberto é a pergunta
    de `provedores_em_meio_aberto`, e ele não barra: deixa passar UMA sonda.
    """
    try:
        from app.core.relogio_do_modelo import PROVEDORES, estado_do_breaker
    except Exception:  # noqa: BLE001
        return set()
    barrados = set()
    for provedor in PROVEDORES:
        try:
            estado = await estado_do_breaker(provedor)
        except Exception as erro:  # noqa: BLE001
            # ⛔ FAIL-OPEN: breaker indisponível nunca retém ninguém.
            logger.debug("[ISOLAMENTO] breaker indisponivel (%s)",
                         type(erro).__name__)
            continue
        if (estado or {}).get("estado") == "aberto":
            barrados.add(provedor)
    return barrados


async def provedores_em_meio_aberto() -> set:
    """Quais provedores estão em MEIO-ABERTO agora. ⛔ Nunca levanta.

    🔴 É a outra metade da pergunta da varredura, e ela existe porque o §7.4
    promete que o meio-aberto *"deixa passar UMA chamada"*. 📊 21/09/2026 a
    promessa não tinha chamador: `provedor_disponivel` (a sonda atômica) não era
    chamada por ninguém no produto, e o varredor soltava TODAS as retidas de uma
    vez contra um provedor que acabara de cair (`juiz/medir.py` M3:
    `consumidas em meio-aberto = 8 | adiadas.breaker = 0`).

    ⚠️ Aqui ainda é LEITURA (`estado_do_breaker`): a sonda é gasta por quem vai
    CHAMAR o modelo, uma conversa de cada vez, dentro de `_uma`.
    """
    try:
        from app.core.relogio_do_modelo import PROVEDORES, estado_do_breaker
    except Exception:  # noqa: BLE001
        return set()
    meio = set()
    for provedor in PROVEDORES:
        try:
            estado = await estado_do_breaker(provedor)
        except Exception as erro:  # noqa: BLE001
            # ⛔ FAIL-OPEN: breaker indisponível nunca retém ninguém.
            logger.debug("[ISOLAMENTO] breaker indisponivel (%s)",
                         type(erro).__name__)
            continue
        if (estado or {}).get("estado") == "meio_aberto":
            meio.add(provedor)
    return meio


async def _sonda_do_meio_aberto(provedor: str) -> bool:
    """Esta conversa é A sonda? `SET NX` atômico. ⛔ Nunca levanta.

    ⛔ Fail-open na dúvida: erro ao sondar devolve `True` e a conversa é
    atendida. Um silêncio por engano custa a conversa inteira.
    """
    try:
        from app.core.relogio_do_modelo import provedor_disponivel

        return bool(await provedor_disponivel(provedor))
    except Exception as erro:  # noqa: BLE001
        logger.debug("[ISOLAMENTO] sonda nao consultada (%s) — atendendo",
                     type(erro).__name__)
        return True


async def _contar_timeout_no_breaker(provedor_de, escopo: str,
                                     teto_turno: float) -> None:
    """O turno foi cortado pelo teto: o PROVEDOR pendurado tem de contar falha.

    🔴 **É o elo que faltava para o disjuntor abrir no caso que lhe dá nome.**
    `asyncio.wait_for` corta com `CancelledError`, e `e_transitorio(
    CancelledError)` é `False` (📊 `juiz/medir.py` M4) — então o callback do
    modelo NUNCA alimentava o breaker com um provedor pendurado, e cada conversa
    seguinte era consumida, pendurava e sumia, uma a uma. Quem sabe que o turno
    estourou é ESTE lado, e é daqui que a falha entra na conta.

    ⛔ Nunca levanta, e nunca PII: só o nome do provedor.
    """
    if provedor_de is None or not escopo:
        return
    try:
        from app.core.relogio_do_modelo import registrar_falha

        provedor = await _provedor_da_chave(provedor_de, escopo)
        if not provedor:
            return
        await registrar_falha(provedor, TimeoutError(
            "turno cortado pelo teto de %.0f s" % teto_turno))
        logger.warning("[ISOLAMENTO] teto de turno contado como falha do "
                       "provedor %s (o disjuntor decide se abre)", provedor)
    except Exception as erro:  # noqa: BLE001
        logger.debug("[ISOLAMENTO] falha de teto nao contada (%s)",
                     type(erro).__name__)


async def provedor_do_escopo(escopo: str):
    """`escopo` (id da integração) -> o provedor que o atendimento VAI usar.

    `None` quando não dá para saber — e `None` significa ATENDER, nunca reter.
    """
    from app.core.config import settings
    from app.core.database import get_supabase_client
    from app.core.relogio_do_modelo import provedor_configurado
    from app.services.integration_service import get_integration_service

    supabase = get_supabase_client()
    integracao = await asyncio.to_thread(
        get_integration_service(supabase.client).get_integration_by_id, escopo)
    if not integracao:
        return None
    company_id = integracao.get("company_id")
    if not company_id:
        return None

    servico = _LANGCHAIN_PARA_RESOLVER[0]
    if servico is None:
        from app.services.langchain_service import LangChainService
        servico = LangChainService(settings.OPENAI_API_KEY, supabase)
        _LANGCHAIN_PARA_RESOLVER[0] = servico

    # ⛔ A MESMA função do atendimento, com o MESMO papel (`webhook.py:1617`).
    agente = await servico._get_raw_agent(  # noqa: SLF001
        str(company_id), integracao.get("agent_id"), required_role="attendance")
    if not agente:
        return None
    return provedor_configurado(agente, agente)


async def _provedor_da_chave(provedor_de, escopo: str):
    """O provedor do escopo, com cache curto em memória. ⛔ Nunca levanta."""
    import time as _time

    agora = _time.monotonic()
    guardado = _PROVEDOR_POR_ESCOPO.get(escopo)
    if guardado is not None and guardado[1] > agora:
        return guardado[0]
    # Limpeza preguiçosa: cache sem poda é vazamento de memória com nome bonito.
    if len(_PROVEDOR_POR_ESCOPO) > 500:
        for chave_velha, (_p, vence) in list(_PROVEDOR_POR_ESCOPO.items()):
            if vence <= agora:
                _PROVEDOR_POR_ESCOPO.pop(chave_velha, None)
    try:
        provedor = await provedor_de(escopo)
    except Exception as erro:  # noqa: BLE001
        provedor = None
        logger.warning("[ISOLAMENTO] provedor nao resolvido (%s) — atendendo",
                       type(erro).__name__)
    vida = _env_int("ISOLAMENTO_PROVEDOR_CACHE_S", _PROVEDOR_CACHE_PADRAO_S)
    _PROVEDOR_POR_ESCOPO[escopo] = (provedor, agora + vida)
    return provedor


async def processar_buffers_prontos(chaves, buffer_service, processar,
                                    paralelismo: int = 0,
                                    cota_por_corretora: int = 0,
                                    timeout_s: float = 0,
                                    barrados=None,
                                    provedor_de=None,
                                    meio_abertos=None) -> dict:
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
    from time import monotonic

    recebidas = [str(c) for c in (chaves or []) if c]
    escopo_de = getattr(buffer_service, "escopo_da_chave", None)
    com_cota = escopo_de is not None
    adiadas_por_escopo: dict = {}

    def _relogio_da_fila(buffer, desde: float) -> dict:
        """Quanto tempo esta conversa esperou — o contrato do §5.1 com o webhook.

        ```
        buffer_espera_ms   desde a PRIMEIRA mensagem da rajada (o `first_at` que
                           `add_message` gravou) até agora
        fila_cota_ms       desde o 1º adiamento por COTA desta conversa (ou,
                           quando ela nunca foi adiada, desde a disputa de agora)
        ```

        🔴 **`None` nunca vira 0.** Zero é medição ("não esperou"); `None` é
        "não sei" (buffer sem carimbo ou carimbo ilegível). Um p95 calculado
        sobre zeros inventados mente para quem decide (CLAUDE.md §12.1).

        ⚠️ O `datetime` sai do MÓDULO QUE ESCREVEU o `first_at`
        (`message_buffer_service`, `datetime.now().isoformat()` — hora local,
        SEM fuso) e não de um `datetime` importado aqui: medir com uma
        ferramenta e gravar com outra é como se inventa um fuso que ninguém
        escreveu (CLAUDE.md §9.4).

        ⛔ **Medir nunca atrasa nem impede o atendimento**: qualquer erro aqui
        devolve `{}` e a conversa segue sem relógio.
        """
        try:
            from app.services.message_buffer_service import datetime as _quando

            espera_ms = None
            carimbo = str((buffer or {}).get("first_at") or "")
            if carimbo:
                try:
                    espera_ms = max(0, int(
                        (_quando.now() - _quando.fromisoformat(carimbo)
                         ).total_seconds() * 1000))
                except (TypeError, ValueError):
                    espera_ms = None
            return {"buffer_espera_ms": espera_ms,
                    "fila_cota_ms": max(0, int((monotonic() - desde) * 1000))}
        except Exception as erro:  # noqa: BLE001
            logger.debug("[ISOLAMENTO] relogio da fila nao montado (%s)",
                         type(erro).__name__)
            return {}

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
        expiradas = {}
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

    # 🔴 UMA pergunta por VARREDURA, não uma por chave: o custo é o mesmo com 1
    # ou com 200 chaves na fila. Conjunto vazio = nada muda para ninguém.
    #
    # 📊 O CUSTO, MEDIDO (21/09/2026, contando as chamadas no dublê:
    # `python %TEMP%\laudos-0018\redteam\atk5_custo_por_varredura.py`): cada
    # `estado_do_breaker` custa 1 GET + 1 EXISTS, e são 4 provedores — a
    # pergunta inteira custa **8 idas ao Redis**, não "quatro GETs" como o
    # comentário antigo dizia. Com a segunda pergunta (meio-aberto) seriam 16
    # **por varredura vazia**, 16 por segundo por processo, para descobrir que
    # não há nada a fazer.
    #
    # ⛔ Por isso as duas perguntas só saem quando há FILA. 📊 Medido de novo com
    # o mesmo comando, depois do corte:
    #
    #     varredura VAZIA ............ breaker = 0 idas  (era 8)
    #     1 chave ainda em debounce .. breaker = 0 idas  (era 8)
    #     1 chave pronta e atendida .. breaker = 8 idas por pergunta
    #
    # A colheita de `expiradas` acontece ACIMA e continua rodando em varredura
    # vazia — foi um defeito de produto desta SPEC (M-18-7): com todo mundo
    # expirando de uma vez, a perda TOTAL era justamente a que ninguém veria.
    provedores_fora = set()
    em_meio_aberto = set()
    if com_cota and fila:
        if barrados is not None:
            try:
                provedores_fora = set(await barrados())
            except Exception as erro:  # noqa: BLE001
                # ⛔ FAIL-OPEN, e é a regra que não se negocia: na dúvida, atende.
                provedores_fora = set()
                logger.warning("[ISOLAMENTO] breaker nao consultado (%s) — atendendo",
                               type(erro).__name__)
        if meio_abertos is not None:
            try:
                em_meio_aberto = set(await meio_abertos()) - provedores_fora
            except Exception as erro:  # noqa: BLE001
                em_meio_aberto = set()
                logger.warning("[ISOLAMENTO] meio-aberto nao consultado (%s) — "
                               "atendendo", type(erro).__name__)
    if provedores_fora:
        logger.warning("[ISOLAMENTO] %d provedor(es) com disjuntor ABERTO — as "
                       "conversas deles ficam guardadas", len(provedores_fora))
    if em_meio_aberto:
        logger.info("[ISOLAMENTO] %d provedor(es) em meio-aberto — passa UMA "
                    "sonda por provedor, as outras conversas ficam guardadas",
                    len(em_meio_aberto))

    timeouts_por_escopo: dict = {}
    sumidas: dict = {}
    #: chave -> escopo das que foram ADIADAS NESTA volta. 🔴 É ela, e não "quem
    #: estava na fila e não foi servido", que diz quem continua esperando: uma
    #: varredura sobreposta pode ter atendido a conversa no meio do caminho.
    pendentes_da_volta: dict = {}

    async def _guardar(chave: str, escopo: str, motivo: str) -> bool:
        """Adia a chave E anota o DONO da espera — nunca um sem o outro.

        ⛔ Os quatro pontos de adiamento passam por aqui de propósito: contar o
        motivo num lugar e o dono em outro é como os dois números começam a
        discordar (o aviso ao dono e a tela da Central leem a MESMA conta).
        """
        adiadas[motivo] += 1
        if com_cota and escopo:
            pendentes_da_volta[str(chave)] = escopo
            # 🔴 A ESPERA COMEÇA A VALER AGORA, não no fim da varredura. 📊 Uma
            # varredura que só fecha a conta lá no fim (quando o turno mais
            # lento dela termina, minutos depois) reinscreveria como "esperando"
            # uma conversa que uma varredura SOBREPOSTA já respondeu — e a
            # varredura seguinte a contaria como mensagem perdida.
            estado["aguardando"][str(chave)] = escopo
        existe = await _adiar(buffer_service, chave, motivo)
        if existe is False and motivo != "sem_escopo":
            # 🔴 A chave JÁ NÃO EXISTE: uma varredura SOBREPOSTA a consumiu entre
            # a nossa leitura e este adiamento (📊 21/09/2026, confirmação:
            # `m1_corrida_sobreposta.py` → controle 0 · corrida `expiradas = 1`
            # para uma conversa ATENDIDA, com o teto global cheio). Reinscrevê-la
            # como "esperando" faria a volta seguinte contá-la como mensagem
            # perdida. ⚠️ Só `False`: `None` é "o Redis não respondeu" — na dúvida
            # a espera FICA anotada (perda de verdade tem de continuar contando).
            marcar_consumida(chave)
            pendentes_da_volta.pop(str(chave), None)
        return False

    async def _uma(chave: str) -> bool:
        escopo = escopo_de(chave) if com_cota else ""
        # O instante em que ESTA tentativa entrou na disputa pela cota. Vale
        # como começo da espera só para a conversa que nunca foi adiada — para
        # as outras, quem manda é `esperando_desde` (o 1º adiamento por cota).
        entrou_na_disputa = monotonic()

        if com_cota:
            # ⛔ FAIL-CLOSED: sem corretora identificada não se processa às
            # cegas. 📊 Hoje esta chave já não é respondida (`abrir_turno` a
            # recusa, 001.2 §5.3); o que muda é ela aparecer na conta.
            if not escopo:
                return await _guardar(chave, escopo, "sem_escopo")
            # ============================================================
            # ① A COTA DA CORRETORA VEM PRIMEIRO. SEMPRE.
            # ============================================================
            # Se o teto global viesse antes, uma conversa esperando a cota da
            # própria corretora estaria SEGURANDO um slot global — a corretora
            # saturada passaria a consumir os slots do processo inteiro só para
            # esperar. É a inversão que transforma a proteção no defeito.
            if com_cota and not _tomar_cota(estado, escopo, cota):
                return await _guardar(chave, escopo, "cota")

        try:
            # ================================================================
            # 🔴 O DISJUNTOR PERGUNTA **ANTES** DE CONSUMIR O BUFFER
            # ================================================================
            #
            # A ORDEM É A REGRA INTEIRA, pelo mesmo motivo da trava de turno
            # logo abaixo: depois do `get_and_clear` a rajada já saiu do Redis,
            # e descobrir ali que o provedor está fora custaria as mensagens do
            # segurado. Aqui custa um segundo — o buffer fica, com a vida
            # renovada por `adiar`, e a próxima varredura o reencontra.
            #
            # ⚠️ Dentro do `try`, e não antes dele, de propósito: é o `finally`
            # lá embaixo que devolve a VAGA DE COTA desta corretora. Sair por
            # cima do `try` deixaria a vaga presa até o processo reiniciar.
            if com_cota and provedores_fora and provedor_de is not None:
                provedor = await _provedor_da_chave(provedor_de, escopo)
                if provedor and provedor in provedores_fora:
                    # ⚠️ Sem PII: nem chave, nem telefone, nem corretora.
                    logger.info("[ISOLAMENTO] conversa guardada: disjuntor "
                                "aberto no provedor %s", provedor)
                    return await _guardar(chave, escopo, "breaker")

            # ================================================================
            # 🔴 MEIO-ABERTO: PASSA **UMA**, E SÓ UMA (§7.4)
            # ================================================================
            #
            # O aberto barra todo mundo; o meio-aberto é o contrário — é o
            # instante em que UMA conversa precisa passar para descobrir se o
            # provedor voltou. Sem a sonda, o varredor solta as até 24 retidas
            # de uma vez contra um provedor que acabou de cair, e cada uma delas
            # custa a rajada de um segurado (📊 `juiz/medir.py` M3: 8 de 8
            # consumidas em meio-aberto, 0 adiadas).
            #
            # ⛔ A sonda é ATÔMICA (`SET NX` em `provedor_disponivel`) e é
            # gasta AQUI, antes do `get_and_clear` — quem pergunta é quem retém.
            # Na dúvida (erro), `_sonda_do_meio_aberto` devolve True: atende.
            if com_cota and em_meio_aberto and provedor_de is not None:
                provedor = await _provedor_da_chave(provedor_de, escopo)
                if provedor and provedor in em_meio_aberto:
                    if not await _sonda_do_meio_aberto(provedor):
                        logger.info("[ISOLAMENTO] conversa guardada: a sonda do "
                                    "meio-aberto e de outra conversa (%s)",
                                    provedor)
                        return await _guardar(chave, escopo, "breaker")

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
                                return await _guardar(chave, escopo, "turno")
                            return False
                        turno = Turno(escopo_do_turno, phone, token)

                    try:
                        buffer = await buffer_service.get_and_clear_buffer(chave)
                        if not buffer:
                            # A chave sumiu entre a conferência e o consumo.
                            #
                            # ⚠️ O comentário antigo dizia que a trava de turno
                            # provava ter sido o TTL. 📊 Era falso: a varredura
                            # que consumiu já tinha TERMINADO e soltado a trava
                            # (red team B1c), e a conta inventava uma perda.
                            #
                            # 🔴 A régua certa: só é perda se a chave ainda
                            # ESTAVA ESPERANDO. Quem consome tira a chave de
                            # `aguardando` no mesmo instante — se ela continua
                            # lá, ninguém deste processo a pegou.
                            if com_cota and estado["aguardando"].pop(
                                    chave, None) is not None:
                                sumidas[escopo] = sumidas.get(escopo, 0) + 1
                            return False
                        # 🔴 CONSUMIDA: a rajada saiu do Redis AGORA, e a
                        # contabilidade fica sabendo AGORA — não no fim do
                        # turno, que pode demorar minutos e atravessar dez
                        # varreduras (red team B1a).
                        desde_a_espera = entrou_na_disputa
                        if com_cota:
                            desde_a_espera = estado["esperando_desde"].get(
                                chave, entrou_na_disputa)
                            marcar_consumida(chave)
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
                            # 🔴 O MESMO critério dos três extras acima, e é de
                            # propósito: eles só viajam quando o serviço de
                            # buffer é o REAL (é o `abrir_turno` que produz o
                            # `turno`). O dublê do guarda de paralelismo tem um
                            # `processar` SEM `**kwargs` — um kwarg novo com
                            # outro critério o quebraria, e o guarda é a LINHA
                            # DE CONTROLE herdada da 001.2. Quem recebe do lado
                            # real é `process_whatsapp_message_background`, que
                            # já declara `relogio_da_fila` keyword-only.
                            relogio = _relogio_da_fila(buffer, desde_a_espera)
                            if relogio:
                                extras["relogio_da_fila"] = relogio

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
                            #
                            # ⚠️ QUEM FALA COM O SEGURADO É O WEBHOOK. O corte
                            # é um `CancelledError` lá dentro, e é lá que o
                            # aviso honesto de falha sai quando o envio ainda
                            # não começou (`webhook.py`, o `except
                            # asyncio.CancelledError`). Daqui não se sabe, e por
                            # isso o log não afirma mais que nada foi dito.
                            try:
                                await asyncio.wait_for(chamada, timeout=teto_turno)
                            except asyncio.TimeoutError:
                                timeouts_por_escopo[escopo] = \
                                    timeouts_por_escopo.get(escopo, 0) + 1
                                logger.error(
                                    "[ISOLAMENTO] turno cortado pelo teto de %.0f s "
                                    "— o webhook decide o que o segurado ouve",
                                    teto_turno)
                                # 🔴 O PROVEDOR PENDURADO TEM DE ABRIR O
                                # DISJUNTOR: sem esta linha, cada conversa
                                # seguinte era consumida, pendurava e sumia.
                                await _contar_timeout_no_breaker(
                                    provedor_de, escopo, teto_turno)
                                return False
                        else:
                            await chamada
                        logger.info("[BUFFER] ✅ Processed: combined %d itens",
                                    msg_count)
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

    # 🔴 A PERDA É POR DONO, E É A SOMA DAS DUAS FONTES: a chave que sumiu do
    # SCAN esperando (`_colher_expiradas`) e a que sumiu entre a conferência e o
    # consumo (`sumidas`).
    perdidas_por_escopo: dict = dict(expiradas)
    for escopo_perdido, quantas in sumidas.items():
        if escopo_perdido:
            perdidas_por_escopo[escopo_perdido] = \
                perdidas_por_escopo.get(escopo_perdido, 0) + quantas

    if com_cota:
        adiadas_por_escopo = await _fechar_a_conta(
            buffer_service, estado, pendentes_da_volta,
            adiadas, perdidas_por_escopo, timeouts_por_escopo) or {}

    return {"vistas": len(recebidas), "prontas": len(fila),
            "processadas": processadas, "adiadas": adiadas,
            # 🔴 A MESMA conta de `adiadas`, agora com DONO — {escopo: {motivo:
            # quantas}}. ⚠️ Chave sem escopo não tem dono a avisar e fica de
            # fora; ela continua contada em `adiadas["sem_escopo"]`.
            "adiadas_por_escopo": adiadas_por_escopo,
            "falhas": falhas,
            "timeouts": sum(timeouts_por_escopo.values()),
            "timeouts_por_escopo": dict(timeouts_por_escopo),
            "expiradas": sum(perdidas_por_escopo.values()),
            # ⛔ A perda com DONO, para quem precisa saber DE QUEM era a
            # mensagem — o resumo global continua sendo a soma.
            "expiradas_por_escopo": dict(perdidas_por_escopo)}


async def _fechar_a_conta(buffer_service, estado, pendentes,
                          adiadas, expiradas_por_escopo,
                          timeouts_por_escopo) -> dict:
    """Grava o que a Central de Agentes vai LER — UMA escrita por corretora.

    ⛔ Uma escrita por CHAVE seriam 200 idas ao Redis numa varredura de rajada,
    para um número que ninguém lê 200 vezes por segundo.

    Devolve `{escopo: {motivo: quantas}}` — a MESMA fila que vira `em_espera`
    nos contadores, repartida pelo motivo do último adiamento. 🔴 Vem daqui, e
    não de contadores espalhados pelos quatro pontos de adiamento, para que o
    número que o dono da corretora recebe no aviso e o número que a Central
    mostra na tela sejam, por construção, o mesmo número.

    🔴 **`pendentes` é quem foi ADIADO NESTA volta** (`{chave: escopo}`), e não
    "quem estava na fila e não foi servido". 📊 A segunda régua contava como
    espera a conversa que uma varredura SOBREPOSTA acabara de responder — e
    duas varreduras depois ela virava "mensagem perdida" (red team B1a).

    ⛔ **`expiradas` e `timeouts` são POR ESCOPO, e cada um vai SÓ no hash do
    dono.** 📊 Antes eram totais globais gravados com `HINCRBY` no hash de todo
    escopo ativo: a perda de A aparecia na tela de B, e a perda total sem outra
    corretora ativa não era gravada em lugar nenhum (juiz B3, red team B1b).
    """
    # ⛔ `aguardando` NÃO é escrito aqui. Quem adia já o escreveu, no instante do
    # adiamento (`_guardar`): reescrevê-lo no FIM da varredura reinscreveria
    # como "esperando" a conversa que outra varredura respondeu no meio do
    # caminho — e a varredura seguinte a chamaria de mensagem perdida.
    por_escopo = {}
    por_motivo: dict = {}
    for chave, escopo in pendentes.items():
        por_escopo[escopo] = por_escopo.get(escopo, 0) + 1
        motivo_da_chave = estado["motivo_da_chave"].get(chave)
        if not motivo_da_chave:
            # Sem motivo registrado não foi adiamento: foi falha ou teto de
            # tempo, e esses têm contadores próprios (`falhas`, `timeouts`).
            continue
        dela = por_motivo.setdefault(escopo, {m: 0 for m in _MOTIVOS_DE_ESPERA})
        dela[motivo_da_chave] = dela.get(motivo_da_chave, 0) + 1
    for escopo in estado["em_voo_por_escopo"]:
        por_escopo.setdefault(escopo, 0)
    # 🔴 O DONO DA PERDA APARECE MESMO SEM FILA E SEM TURNO EM VOO. 📊 Era o
    # caso `M1a` do juiz: a corretora perdeu a mensagem, não tinha mais nada na
    # fila, e o número não era gravado em lugar NENHUM.
    for escopo in list(expiradas_por_escopo) + list(timeouts_por_escopo):
        if escopo:
            por_escopo.setdefault(escopo, 0)

    # ⛔ A PODA. Os dois mapas do `_ADMISSAO` ficam com quem AINDA espera —
    # exatamente o conjunto de `aguardando`. Sem isto, dois dicionários
    # cresceriam para sempre, uma entrada por conversa já respondida.
    vivas = set(estado["aguardando"])
    for mapa in (estado["motivo_da_chave"], estado["esperando_desde"]):
        for velha in [c for c in mapa if c not in vivas]:
            mapa.pop(velha, None)

    motivo = ""
    for nome in _MOTIVOS_DE_ESPERA:
        if adiadas.get(nome):
            motivo = nome
            break

    # 🔴 PERDA SEMPRE APARECE NO LOG, com ou sem contador de pé. 📊 Era o outro
    # meio do achado M1a: além de não ser gravada, a perda total não deixava uma
    # linha sequer (`grep expiradas` no log → zero). ⛔ Sem PII: quantas e em
    # quantas corretoras — nunca a chave, o telefone ou o nome da corretora.
    if expiradas_por_escopo:
        logger.error(
            "[ISOLAMENTO] 🔴 %d mensagem(ns) de segurado SUMIRAM do Redis "
            "esperando a vez, em %d corretora(s) — este número não admite quase",
            sum(expiradas_por_escopo.values()), len(expiradas_por_escopo))

    registrar = getattr(buffer_service, "registrar_ocupacao", None)
    if registrar is None:
        return por_motivo
    for escopo, em_espera in por_escopo.items():
        try:
            await registrar(
                escopo,
                em_execucao=estado["em_voo_por_escopo"].get(escopo, 0),
                em_espera=em_espera, motivo=motivo,
                expiradas=int(expiradas_por_escopo.get(escopo, 0)),
                timeouts=int(timeouts_por_escopo.get(escopo, 0)))
        except Exception as erro:  # noqa: BLE001
            # ⛔ Contador nunca derruba atendimento.
            logger.warning("[ISOLAMENTO] contador não gravado (%s)",
                           type(erro).__name__)
    return por_motivo


# ===========================================================================
# 🔴 A COSTURA COM O AVISO AO DONO (FATIA 6) — a fila tem dono, e ele fica
# sabendo UMA vez
# ===========================================================================
#
# ⛔ **O aviso nasce DESLIGADO** (`ISOLAMENTO_AVISO_AO_DONO` ausente = não
# avisa) e a flag é o PRIMEIRO teste desta função, antes de qualquer ida ao
# Redis ou ao banco: `check_buffers` roda a cada 1 s, e um custo por varredura
# "só para descobrir que está desligado" seria um custo permanente cobrado de
# quem nunca ligou nada.
#
# ⚠️ **Só `cota` e `breaker` contam como fila.** `turno` é o normal e rápido (a
# trava de uma rajada que já está sendo respondida, medida em ms); avisar por
# ele seria avisar do funcionamento — e 📊 é assim que o grupo da corretora
# virou ruído (DIAGNÓSTICO §1.5).

#: escopo -> (company_id|None, quando_vence). ⚠️ O negativo TAMBÉM é guardado,
#: pelo mesmo motivo do cache de provedor: um escopo que não resolve viraria uma
#: consulta ao banco por varredura, para sempre.
_CORRETORA_POR_ESCOPO: dict = {}
_CORRETORA_CACHE_PADRAO_S = 300

#: Quem estava esperando na varredura anterior. É o que permite ZERAR o relógio
#: da espera quando a fila de uma corretora esvazia — sem isso o "esperando há"
#: nunca voltaria a zero e o aviso seguinte sairia no primeiro segundo de fila.
_ESCOPOS_ESPERANDO: set = set()


async def _corretora_do_escopo(escopo: str):
    """`escopo` (id da integração) -> `company_id`. ⛔ Nunca levanta.

    A fonte é a MESMA da Central (a tabela `integrations`, pelo serviço que já
    existe) — reescrever a resolução aqui seria o motor paralelo do CLAUDE.md
    §5, e as duas telas passariam a discordar sobre de quem é a fila.
    """
    import time as _time

    agora = _time.monotonic()
    guardado = _CORRETORA_POR_ESCOPO.get(escopo)
    if guardado is not None and guardado[1] > agora:
        return guardado[0]
    if len(_CORRETORA_POR_ESCOPO) > 500:
        for velha, (_c, vence) in list(_CORRETORA_POR_ESCOPO.items()):
            if vence <= agora:
                _CORRETORA_POR_ESCOPO.pop(velha, None)
    empresa = None
    try:
        from app.core.database import get_supabase_client
        from app.services.integration_service import get_integration_service

        supabase = get_supabase_client()
        integracao = await asyncio.to_thread(
            get_integration_service(supabase.client).get_integration_by_id, escopo)
        empresa = str((integracao or {}).get("company_id") or "") or None
    except Exception as erro:  # noqa: BLE001
        logger.warning("[ISOLAMENTO] corretora do escopo nao resolvida (%s)",
                       type(erro).__name__)
    vida = _env_int("ISOLAMENTO_CORRETORA_CACHE_S", _CORRETORA_CACHE_PADRAO_S)
    _CORRETORA_POR_ESCOPO[escopo] = (empresa, agora + vida)
    return empresa


async def avisar_os_donos_da_fila(resumo) -> int:
    """Avisa o dono de cada corretora cuja fila está longa. ⛔ Nunca levanta.

    Devolve quantos avisos saíram. As portas, nesta ordem — e a primeira não
    custa nada:

    ```
    ① a flag                  ausente -> volta na hora, ZERO Redis, ZERO banco
    ② quem está na fila       só `cota` e `breaker`, por ESCOPO
    ③ há quanto tempo         `SET NX` no Redis: o 1º a ver manda no relógio
    ④ de quem é a fila        `integrations`, com cache (nunca 1 SELECT/escopo/s)
    ⑤ um por janela           a trava do módulo de aviso, que é de REDIS
    ```
    """
    from app.services import aviso_de_fila_longa as aviso

    # ① 🔴 A FLAG É O PRIMEIRO TESTE. Desligada, esta função custa uma leitura
    # de variável de ambiente por varredura e mais nada.
    if not aviso.aviso_ligado():
        return 0

    import time as _time

    agora_s = _time.time()
    limiar = aviso.limiar_de_espera_s()
    alvos: dict = {}
    esperando_agora = set()
    for escopo, motivos in dict((resumo or {}).get("adiadas_por_escopo") or {}).items():
        # ② `turno` fica de fora de propósito: ele não é fila, é a rajada sendo
        # respondida agora.
        na_fila = int((motivos or {}).get("cota") or 0) + \
            int((motivos or {}).get("breaker") or 0)
        if na_fila <= 0:
            continue
        esperando_agora.add(escopo)
        # ③
        await aviso.marcar_espera(escopo, agora_s=agora_s)
        ha = await aviso.esperando_ha(escopo, agora_s=agora_s)
        if ha is None or ha < limiar:
            continue
        # ④
        empresa = await _corretora_do_escopo(escopo)
        if not empresa:
            continue
        alvos[escopo] = (empresa, na_fila, ha)

    # A fila desta corretora esvaziou: o relógio dela zera para a próxima vez.
    for escopo in list(_ESCOPOS_ESPERANDO - esperando_agora):
        await aviso.esquecer_espera(escopo)
        _ESCOPOS_ESPERANDO.discard(escopo)
    _ESCOPOS_ESPERANDO.update(esperando_agora)

    if not alvos:
        return 0
    from app.core.database import get_supabase_client

    # ⑤ A trava "um por janela" mora dentro de `avisar_dono_se_fila_longa`, e é
    # de Redis: duas varreduras sobrepostas ou duas réplicas
    # avisariam duas vezes sobre a mesma fila.
    return await aviso.avisar_pelos_escopos(
        get_supabase_client().client, resumo, alvos)


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
        # 🔴 É AQUI QUE A COSTURA LIGA. Sem estas duas linhas o disjuntor por
        # provedor existiria e não seria perguntado por ninguém — código vivo
        # sem chamador, que é a forma mais cara de não ter feito nada
        # (protocolo §0.3, O ELO). O guarda confere que elas estão aqui.
        resumo = await processar_buffers_prontos(
            chaves, buffer_service, process_whatsapp_message_background,
            barrados=provedores_barrados, provedor_de=provedor_do_escopo,
            meio_abertos=provedores_em_meio_aberto)

        # 🔴 O AVISO VEM DEPOIS, E NO TRY DELE. Ele é EFEITO da varredura, nunca
        # condição: um aviso que estoura não pode derrubar o job de 1 s que
        # responde ao segurado — nem atrasar a varredura seguinte.
        try:
            await avisar_os_donos_da_fila(resumo)
        except Exception as erro:  # noqa: BLE001
            logger.warning("[ISOLAMENTO] aviso ao dono nao saiu (%s)",
                           type(erro).__name__)

        # A conta da varredura volta para quem chamar. ⚠️ É por ela que o guarda
        # do FIO prova que o aviso não engoliu a varredura: com o aviso
        # explodindo FORA do try acima, esta linha nunca seria alcançada.
        return resumo

    except Exception as e:
        logger.error(f"[BUFFER] ❌ Error in check_buffers: {e}", exc_info=True)


# ===========================================================================
# 🔴 QUEM MANDA NOS JOBS — o lock de líder (BLOCO E, §9.2)
# ===========================================================================
#
# ⛔ NENHUM AGENDADOR NOVO. O `scheduler` continua sendo o único; o líder só
# decide QUAIS jobs dele rodam NESTE processo.
#
# ⚖️ PAUSAR OU DESLIGAR, quando a liderança é perdida:
#   `scheduler.pause_job(id)` / `resume_job(id)`   **93**
#       📊 Medido em 21/09/2026 (apscheduler 3.11.3, Python 3.14): pausado, o
#       job continua LISTADO em `get_jobs()` com `next_run_time=None`, e
#       `resume_job` devolve um `next_run_time` novo. É o que permite ao guarda
#       comparar a tabela de classificação com os jobs REALMENTE registrados —
#       e é por job, que é o que a regra "decisão por JOB" exige.
#   `scheduler.shutdown()` + `start()`             **22**
#       📊 Medido no mesmo dia: `AsyncIOScheduler.shutdown` é decorado com
#       `@run_in_event_loop` — ele NÃO para na hora, e `s.state` continua
#       RUNNING logo depois; um `start()` em seguida levanta
#       `SchedulerAlreadyRunningError`. Reiniciar o agendador para retomar a
#       liderança seria, na melhor hipótese, uma corrida.
#   `scheduler.pause()` (o agendador inteiro)      **40** — pararia também o
#       `whatsapp_buffer_check`, e o produto calaria para TODAS as corretoras.
_LIDER: list = [None]
_TAREFA_DE_LIDERANCA: list = [None]


def lider_do_agendador():
    """O líder deste processo, ou `None` quando o agendador está desligado."""
    return _LIDER[0]


def estado_do_agendador() -> str:
    """`"desligado"` · `"lider"` · `"seguidor"` — é o que o `/health` publica."""
    from app.core.lider_do_agendador import DESLIGADO

    lider = _LIDER[0]
    if lider is None:
        return DESLIGADO
    return lider.estado


def _aplicar_lideranca(lider) -> dict:
    """Pausa o que este processo não pode rodar, retoma o que pode."""
    rodando, parados = [], []
    for job in list(scheduler.get_jobs()):
        try:
            if lider.deve_rodar(job.id):
                if getattr(job, "next_run_time", None) is None:
                    scheduler.resume_job(job.id)
                rodando.append(job.id)
            else:
                if getattr(job, "next_run_time", None) is not None:
                    scheduler.pause_job(job.id)
                parados.append(job.id)
        except Exception as erro:  # noqa: BLE001
            logger.warning("[AGENDADOR] job %s nao mudou de estado (%s)",
                           job.id, type(erro).__name__)
    logger.info("[AGENDADOR] %s: %d job(s) rodando, %d parado(s)",
                lider.estado, len(rodando), len(parados))
    return {"rodando": rodando, "parados": parados}


async def parar_lideranca() -> None:
    """Solta o cadeado no shutdown — pelo script literal, nunca `DEL` cego."""
    tarefa = _TAREFA_DE_LIDERANCA[0]
    _TAREFA_DE_LIDERANCA[0] = None
    if tarefa is not None:
        tarefa.cancel()
        try:
            await tarefa
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
    lider = _LIDER[0]
    if lider is not None:
        await lider.soltar()


def start_buffer_scheduler():
    """Start the APScheduler for buffer processing."""
    from app.core.lider_do_agendador import LiderDoAgendador, agendador_ligado

    # 🔴 `SCHEDULER_ENABLED=false` → este processo NÃO registra job NENHUM. É o
    # que permite, amanhã, um serviço `smith-jobs` separado com a MESMA imagem
    # (§9.4): a API sobe só atendendo requisição.
    if not agendador_ligado():
        logger.warning("[BUFFER SCHEDULER] DESLIGADO por SCHEDULER_ENABLED — "
                       "nenhum job periodico neste processo")
        return

    if not scheduler.running:
        # ===================================================================
        # 🔴 O 5º RECURSO COMPARTILHADO: `max_instances` É UM TETO TAMBÉM
        # ===================================================================
        #
        # 📊 Medido em 21/09/2026 (`check_buffers` REAL + APScheduler REAL +
        # Redis dublê, 1 s do produto = 0,2 s;
        # `python %TEMP%\laudos-0018\juiz\medir_instancias.py 10`):
        #
        #     max_instances=10  -> a 4ª corretora esperou 3,24 s (= 16 s do produto)
        #     max_instances=100 -> a 4ª corretora esperou 0,08 s   (CONTROLE)
        #
        # A varredura só termina quando os TURNOS dela terminam (`gather`).
        # Com 10 turnos em voo, 10 instâncias ficam presas e o APScheduler PULA
        # as varreduras seguintes: ninguém novo é atendido **e ninguém renova o
        # TTL de 60 s de quem espera**. O teto real era 10, não o teto global.
        #
        # ⛔ Por isso o número NÃO é um literal: ele sai da MESMA fonte do teto
        # global, senão os dois envelhecem separados e o menor volta a mandar.
        # A folga cobre as instâncias que estão só ADIANDO (elas terminam em
        # milissegundos e não ocupam vaga nenhuma do teto global).
        _teto_global = _env_int("WHATSAPP_BUFFER_PARALELISMO",
                                _PARALELISMO_COM_COTA_PADRAO)
        scheduler.add_job(
            check_buffers,
            "interval",
            seconds=1,
            id="whatsapp_buffer_check",
            max_instances=_teto_global + _FOLGA_DE_INSTANCIAS,
            # 📊 Os dois já eram os defaults do APScheduler 3.11.3 (medido em
            # 21/09/2026: `job_defaults = {'coalesce': True,
            # 'misfire_grace_time': 1, 'max_instances': 1}`). Escritos porque
            # são eles que impedem a avalanche: varredura atrasada além de 1 s
            # é PULADA, e as puladas COLAPSAM numa só quando destrava.
            coalesce=True,
            misfire_grace_time=1,
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

        # 🔴 A LIDERANÇA COMEÇA FECHADA. O processo nasce SEGUIDOR: tudo que
        # ENVIA fica pausado até o cadeado provar que este processo manda. A
        # janela entre `start()` e a primeira aquisição é de milissegundos — e
        # se fosse o contrário, seria a janela em que duas réplicas avisariam o
        # mesmo grupo de suporte.
        lider = LiderDoAgendador()
        _LIDER[0] = lider
        _aplicar_lideranca(lider)

        # ⚠️ O BOOT NUNCA ESPERA O REDIS. A aquisição vive numa tarefa: o
        # `lifespan` segue, o `/health` responde, e a liderança chega quando
        # chegar (teto de 2 s por ida ao Redis, nova tentativa a cada 20 s).
        try:
            laco = asyncio.get_running_loop()
            _TAREFA_DE_LIDERANCA[0] = laco.create_task(
                lider.laco(_aplicar_lideranca))
        except RuntimeError:
            # Sem event loop (script, teste): fica seguidor, e os jobs que
            # ENVIAM ficam parados. Nunca é o caso do produto — `main.py` chama
            # isto de dentro do `lifespan`, que é assíncrono.
            logger.warning("[AGENDADOR] sem event loop — este processo fica "
                           "SEGUIDOR e nao roda job de envio")

        logger.info("✅ [BUFFER SCHEDULER] Started (interval: 1s, max_instances: 10)")
    else:
        logger.warning("[BUFFER SCHEDULER] Already running")


def shutdown_buffer_scheduler():
    """Shutdown the APScheduler gracefully.

    ⚠️ Quem solta o cadeado de líder é `parar_lideranca()` (assíncrona), e
    `main.py` a chama ANTES desta — soltar exige `await`, e um cadeado não
    solto simplesmente vence em <= 60 s.
    """
    _LIDER[0] = None
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("🛑 [BUFFER SCHEDULER] Stopped")
    else:
        logger.warning("[BUFFER SCHEDULER] Not running")
