# -*- coding: utf-8 -*-
"""O LÍDER DO AGENDADOR — uma réplica manda nos jobs; as outras só atendem.

SPEC-EXTRA-001.8 · BLOCO E (§9). **Uma corretora não trava a outra.**

🔴 O DEFEITO QUE ESTE ARQUIVO FECHA. `start_buffer_scheduler()` registra 25 jobs
periódicos (📊 21/09/2026, `grep -c "scheduler.add_job" app/tasks/buffer_processor.py`
→ 25) e é chamado no `lifespan` de CADA processo que sobe. Hoje isso funciona
porque o EasyPanel roda **uma** réplica do `smith-api` — uma configuração, não
uma trava. Subir a segunda réplica (ou um `--workers 2` distraído) faria dois
processos varrerem os mesmos handoffs parados e mandarem **duas** mensagens ao
mesmo grupo de suporte, no mesmo segundo. É o ruído que a EXTRA-001.3 existe
para matar, multiplicado por réplica.

⛔ NENHUM AGENDADOR NOVO, NENHUM EXECUTOR NOVO (CLAUDE.md §5). Este módulo não
roda job nenhum: ele só responde **"este processo pode rodar este job agora?"**.
Quem roda continua sendo o `AsyncIOScheduler` único de `app/tasks/buffer_processor.py`.

O PADRÃO É O QUE O REPOSITÓRIO JÁ RODA EM PRODUÇÃO
--------------------------------------------------
`SET chave token NX EX 60`, renovação a cada 20 s por script Lua que só renova
se o valor ainda for o token, e soltura pelo script **literal** da doc do Redis
(§17 E3 da SPEC — https://redis.io/docs/latest/commands/set/). É a mesma forma
de `portal_worker/leases.py:124-146`; a FORMA é copiada, o arquivo não — aquele
é lease de conta de portal e vive noutro contêiner (`Dockerfile` do
portal-worker copia só `backend/portal_worker`).

⛔ **NUNCA `DEL` cego.** Um `DEL` sem conferir o dono apaga o cadeado de quem
está trabalhando: o processo A perde a liderança sem saber, o B assume, e por
um instante os DOIS acham que mandam. O guarda `test_so_um_agendador_manda.py`
fica vermelho se a soltura deixar de conferir o token.

🔴 REDIS FORA: A DECISÃO É POR JOB, NUNCA GLOBAL
------------------------------------------------
Sem Redis não há como provar liderança. Parar tudo seria transformar uma queda
de cache em parada de produto; rodar tudo seria arriscar mensagem duplicada.
Então cada job responde por si:

```
ENVIA algo para fora (segurado, grupo, equipe, seguradora, cobrança)
    → FAIL-CLOSED. Sem prova de liderança, não roda. Duas réplicas avisando o
      mesmo grupo é o dano; um aviso atrasado, não.
só LÊ, higieniza, espelha ou faz backup
    → FAIL-OPEN. Rodar duas vezes custa CPU e não machuca ninguém — é o que
      `minio_backup.py` já faz hoje quando o Redis falta, e está certo lá.
```

⚠️ **O `whatsapp_buffer_check` é a exceção declarada, e ela tem nota.** Ele
RESPONDE ao segurado — pela régua acima seria fail-closed. Mas (a) a entrega
única dele já é garantida por outro mecanismo: `get_and_clear_buffer` é um
pipeline `get`+`delete` atômico e a trava de turno da 001.2 (`abrir_turno`)
recusa a segunda réplica; e (b) 📊 **sem Redis o buffer nem existe** —
`message_buffer_service.add_message` grava com `setex` no MESMO Redis
(`app/services/message_buffer_service.py:568`), e `check_buffers` começa por
`await get_async_redis_client()` (`app/tasks/buffer_processor.py`), que
**levanta** quando não conecta. Com o Redis fora não há o que duplicar: não há
buffer. Prendê-lo ao lock só criaria um segundo jeito de o produto calar.
Nota da decisão: **92** (roda sempre) contra **38** (exigir liderança).
"""
from __future__ import annotations

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional, Set
from uuid import uuid4

logger = logging.getLogger(__name__)

# ===========================================================================
# O CONTRATO DO CADEADO
# ===========================================================================
CHAVE_DO_LIDER = "autobrokers:scheduler:lider"

#: TTL do cadeado. Se o líder morrer, este é o atraso MÁXIMO até outro assumir.
TTL_SEGUNDOS = 60
#: Renovação com folga de 3× o TTL — duas renovações podem falhar sem perder o
#: cadeado por timing. Renovar no limite é como não renovar.
RENOVACAO_SEGUNDOS = 20
#: ⚠️ O boot NUNCA espera o Redis. Se ele demorar mais que isto, o processo sobe
#: como seguidor e tenta de novo em 20 s — a aplicação no ar vale mais que a
#: liderança imediata (CLAUDE.md §9.1).
TIMEOUT_REDIS_S = 2.0

# Renova SÓ se o dono ainda for o mesmo (a forma de `leases.py:129-135`).
LUA_RENOVAR = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('EXPIRE', KEYS[1], ARGV[2])
else
    return 0
end
"""

#: 🔴 O SCRIPT **LITERAL** DA DOCUMENTAÇÃO DO REDIS (§17 E3). Está escrito numa
#: linha, com aspas duplas, exatamente como a página "Patterns" de
#: https://redis.io/docs/latest/commands/set/ o publica — para que o juiz possa
#: comparar caractere a caractere sem traduzir formatação.
LUA_LIBERAR = (
    'if redis.call("get",KEYS[1]) == ARGV[1] then return redis.call("del",KEYS[1]) '
    'else return 0 end'
)

DESLIGADO = "desligado"
LIDER = "lider"
SEGUIDOR = "seguidor"

_VERDADEIRO = ("1", "true", "yes", "on", "sim", "t")


def agendador_ligado() -> bool:
    """`SCHEDULER_ENABLED` — default LIGADO.

    🔴 Desligar é o que permite, amanhã, um serviço `smith-jobs` separado com a
    MESMA imagem: a API sobe com `SCHEDULER_ENABLED=false` e não registra job
    nenhum. Sem isto, separar os jobs exigiria código novo (§9.4 da SPEC).
    """
    bruto = str(os.getenv("SCHEDULER_ENABLED", "true")).strip().lower()
    if not bruto:
        return True
    return bruto in _VERDADEIRO


# ===========================================================================
# 🔴 A TABELA DOS 25 JOBS — a lista que o guarda impede de envelhecer
# ===========================================================================
#
# ⚠️ Ela é uma ESTRUTURA DE DADOS, e não um comentário, por um motivo só: o
# guarda `tests/test_so_um_agendador_manda.py` compara esta tabela com os jobs
# REALMENTE registrados por `start_buffer_scheduler()`. Job novo sem linha aqui
# = teste VERMELHO. Uma lista em prosa envelheceria na primeira SPEC seguinte, e
# o primeiro sintoma seria uma mensagem duplicada em produção.
#
# `envia`          este job faz alguma coisa SAIR (mensagem ao segurado, aviso
#                  ao grupo da corretora, chamado à seguradora, cobrança).
# `exige_lider`    com o Redis de pé, só o líder o roda. É VERDADE para todos
#                  menos o `whatsapp_buffer_check` (a exceção com nota, acima):
#                  duas réplicas rodando o mesmo vigia é trabalho dobrado mesmo
#                  quando não machuca.
# `sem_redis_roda` 🔴 a decisão do caso "não dá para provar liderança". Default
#                  = o contrário de `envia`: quem envia, para; quem só lê,
#                  segue. Alguns jobs que não enviam também param, e a linha
#                  diz por quê (gasto de LLM em lote).
class Job:
    __slots__ = ("id", "envia", "exige_lider", "sem_redis_roda", "porque")

    def __init__(self, id: str, envia: bool, exige_lider: bool,
                 sem_redis_roda: bool, porque: str):
        self.id = id
        self.envia = envia
        self.exige_lider = exige_lider
        self.sem_redis_roda = sem_redis_roda
        self.porque = porque

    @property
    def fail_closed(self) -> bool:
        """Sem prova de liderança, este job NÃO roda de jeito nenhum."""
        return self.exige_lider and not self.sem_redis_roda

    def __repr__(self) -> str:  # pragma: no cover - diagnóstico
        return "Job(%s, envia=%s, fail_closed=%s)" % (
            self.id, self.envia, self.fail_closed)


def _j(id: str, envia: bool, porque: str, exige_lider: bool = True,
       sem_redis_roda: Optional[bool] = None) -> Job:
    return Job(id, envia, exige_lider,
               (not envia) if sem_redis_roda is None else sem_redis_roda,
               porque)


JOBS: Dict[str, Job] = {j.id: j for j in (
    # ------------------------------------------------- o que RESPONDE/ENVIA
    _j("whatsapp_buffer_check", True,
       "responde ao segurado — mas a entrega unica ja e do Redis (get+delete "
       "atomico + trava de turno da 001.2), e sem Redis nao existe buffer para "
       "duplicar. Roda em toda replica com SCHEDULER_ENABLED (decisao 92x38)",
       exige_lider=False),
    _j("dispatch_followup_check", True,
       "pergunta ao segurado 'o guincho chegou?' e encerra o caso"),
    _j("dispatch_watchdog_check", True,
       "vigia de desfecho: fala com o segurado e com a equipe"),
    _j("vigia_do_portal", True,
       "leva ao segurado o desfecho do job de portal — na duvida, ENVIA"),
    _j("sugestoes_check", True,
       "1 mensagem por semana para o dono da corretora"),
    _j("relatorio_semanal_check", True,
       "o resumo de sabado sai no WhatsApp da corretora"),
    _j("resumo_das_19h", True,
       "o resumo do dia sai no WhatsApp da corretora"),
    _j("atlas_sentinela_check", True,
       "alerta de mudanca de menu vai por WhatsApp (route_sentinel.py:498)"),
    _j("regression_sentinel_check", True,
       "alerta de queda de nota no canal de suporte da corretora"),
    _j("platform_queue_check", True,
       "fila de cortesia: re-tenta ENVIOS adiados"),
    _j("dispatch_reconcile_check", True,
       "acionamento orfao vira alarme para a equipe (dispatch_router.py)"),
    _j("handoff_watchdog_check", True,
       "avisa o grupo de suporte sobre handoff parado — 🔴 dois avisos ao mesmo "
       "grupo e exatamente o ruido que a 001.3 existe para matar"),
    _j("espera_watchdog_check", True,
       "mesma varredura, mesmo grupo, espera vencida"),
    # ------------------------------------------------- o que so LE/HIGIENIZA
    _j("garimpo_check", False,
       "minera desejos/dores do acervo; escreve sinal, nao fala com ninguem"),
    _j("auditor_check", False,
       "scorecards e overlays — leitura e escrita interna"),
    _j("ura_higiene_e_promocao", False,
       "higiene e promocao de mapa de URA; idempotente por construcao"),
    _j("observer_media_check", False,
       "enriquece midia do Observador em cofre; nao envia nada"),
    _j("minio_backup", False,
       "backup incremental que nunca apaga no destino — backup duplicado nao "
       "machuca (e o que minio_backup.py:295-297 ja assume)"),
    _j("attendance_purge_check", False,
       "retencao do espelho: apaga transcript vencido, idempotente"),
    _j("global_seed_check", False,
       "seed do conhecimento global, idempotente por hash"),
    _j("attendance_distiller_check", False,
       "destila o espelho em playbook: nao envia, mas gasta LLM em lote — duas "
       "replicas dobrariam a conta, entao NAO roda sem prova de lideranca",
       sem_redis_roda=False),
    _j("agent_memory_check", False,
       "reescreve blocos de memoria por agente; deterministico, zero LLM"),
    _j("lapidador_check", False,
       "otimizacao reflexiva semanal: gera DRAFT que passa por gate humano; "
       "gasta LLM, entao NAO roda sem prova de lideranca",
       sem_redis_roda=False),
    _j("espelho_chat_sync", False,
       "espelha o acervo no chat da corretora; cursor duravel, sem envio"),
    _j("channel_heartbeat_check", False,
       "pergunta ao provedor se o canal vive e grava a resposta; duas perguntas "
       "nao machucam ninguem"),
)}


def ids_classificados() -> Set[str]:
    return set(JOBS)


def sem_classificacao(ids) -> Set[str]:
    """Quais dos jobs REGISTRADOS não têm linha na tabela. Vazio = tabela em dia."""
    return {str(i) for i in (ids or [])} - ids_classificados()


# ===========================================================================
# O LÍDER
# ===========================================================================
class LiderDoAgendador:
    """O estado de liderança DESTE processo. Um por processo.

    ⛔ Nunca levanta e nunca bloqueia o boot: toda ida ao Redis tem teto de
    `TIMEOUT_REDIS_S` e toda falha vira `redis_fora=True`, que é uma decisão
    tomada job a job (`deve_rodar`) — nunca uma parada global.
    """

    def __init__(self, chave: str = CHAVE_DO_LIDER, ttl_s: int = TTL_SEGUNDOS,
                 token: Optional[str] = None, cliente=None):
        self.chave = chave
        self.ttl_s = int(ttl_s)
        #: 🔴 "a non-guessable large random string" (§17 E3). É do PROCESSO: duas
        #: instâncias no mesmo processo (o guarda) têm tokens diferentes, que é
        #: o que torna o teste de dois donos honesto.
        self.token = str(token or uuid4().hex)
        self.estado = SEGUIDOR
        self.redis_fora = False
        self._cliente_fixo = cliente
        self._tarefa: Optional[asyncio.Task] = None

    # -- o cliente ---------------------------------------------------------
    async def _cliente(self):
        if self._cliente_fixo is not None:
            return self._cliente_fixo
        from app.core.redis import get_async_redis_client
        return await asyncio.wait_for(get_async_redis_client(),
                                      timeout=TIMEOUT_REDIS_S)

    # -- as três operações -------------------------------------------------
    async def tentar_assumir(self) -> bool:
        """`SET chave token NX EX ttl`. `True` = este processo manda agora."""
        try:
            cliente = await self._cliente()
            ganhou = await asyncio.wait_for(
                cliente.set(self.chave, self.token, nx=True, ex=self.ttl_s),
                timeout=TIMEOUT_REDIS_S)
            self.redis_fora = False
        except Exception as erro:  # noqa: BLE001
            self._sem_redis(erro)
            return False
        if ganhou:
            if self.estado != LIDER:
                logger.warning("[AGENDADOR] este processo assumiu a LIDERANCA")
            self.estado = LIDER
            return True
        # ⚠️ Ninguém perde nada aqui: se o dono for ESTE token (reinício de laço
        # depois de um susto), a renovação logo abaixo confirma.
        if self.estado == LIDER:
            return await self.renovar()
        self.estado = SEGUIDOR
        return False

    async def renovar(self) -> bool:
        """Lua: estende SÓ se o valor ainda for o token. `False` = PERDI."""
        try:
            cliente = await self._cliente()
            ok = await asyncio.wait_for(
                cliente.eval(LUA_RENOVAR, 1, self.chave, self.token, str(self.ttl_s)),
                timeout=TIMEOUT_REDIS_S)
            self.redis_fora = False
        except Exception as erro:  # noqa: BLE001
            self._sem_redis(erro)
            return False
        if int(ok or 0) > 0:
            self.estado = LIDER
            return True
        # 🔴 Perdeu: outro token está lá, ou a chave venceu e outro pegou.
        if self.estado == LIDER:
            logger.error("[AGENDADOR] LIDERANCA PERDIDA — os jobs deste processo "
                         "param e ele volta a seguidor")
        self.estado = SEGUIDOR
        return False

    async def soltar(self) -> bool:
        """Solta o cadeado pelo script literal — ⛔ nunca `DEL` cego."""
        era_lider = self.estado == LIDER
        self.estado = SEGUIDOR
        if not era_lider:
            return False
        try:
            cliente = await self._cliente()
            saiu = await asyncio.wait_for(
                cliente.eval(LUA_LIBERAR, 1, self.chave, self.token),
                timeout=TIMEOUT_REDIS_S)
            return bool(int(saiu or 0))
        except Exception as erro:  # noqa: BLE001
            # Não solta: o cadeado vence sozinho em <= TTL. Melhor esperar um
            # minuto do que arriscar apagar o cadeado de outro.
            logger.warning("[AGENDADOR] cadeado nao solto (%s) — vence em %ss",
                           type(erro).__name__, self.ttl_s)
            return False

    def _sem_redis(self, erro: BaseException) -> None:
        if not self.redis_fora:
            logger.warning("[AGENDADOR] sem Redis (%s) — jobs que ENVIAM ficam "
                           "parados; os que so leem seguem", type(erro).__name__)
        self.redis_fora = True
        self.estado = SEGUIDOR

    # -- a pergunta que o agendador faz ------------------------------------
    def deve_rodar(self, job_id: str) -> bool:
        """Este processo pode rodar este job AGORA?

        ⛔ Job desconhecido é tratado como ENVIA (fail-closed). Na dúvida, o
        silencioso é reversível; a mensagem duplicada, não.
        """
        job = JOBS.get(str(job_id))
        if job is None:
            return self.estado == LIDER
        if not job.exige_lider:
            return True
        if self.estado == LIDER:
            return True
        if self.redis_fora:
            # 🔴 A decisão é POR JOB, e é aqui que ela mora.
            return job.sem_redis_roda
        return False

    def jobs_permitidos(self) -> Set[str]:
        return {i for i in JOBS if self.deve_rodar(i)}

    # -- o laço ------------------------------------------------------------
    async def um_passo(self) -> bool:
        """Uma volta: renova se for líder, tenta assumir se não for."""
        if self.estado == LIDER:
            if await self.renovar():
                return True
        return await self.tentar_assumir()

    async def laco(self, aplicar=None, intervalo_s: float = RENOVACAO_SEGUNDOS,
                   voltas: int = 0) -> None:
        """Renova/assume a cada `intervalo_s`. ⛔ Nunca deixa uma exceção subir.

        `aplicar` é chamado DEPOIS de cada passo com o próprio líder — é ele que
        pausa e solta os jobs no agendador que já existe.
        """
        dadas = 0
        while True:
            try:
                await self.um_passo()
            except asyncio.CancelledError:
                raise
            except Exception as erro:  # noqa: BLE001
                logger.warning("[AGENDADOR] passo de lideranca falhou (%s)",
                               type(erro).__name__)
            if aplicar is not None:
                try:
                    resultado = aplicar(self)
                    if asyncio.iscoroutine(resultado):
                        await resultado
                except Exception as erro:  # noqa: BLE001
                    logger.warning("[AGENDADOR] nao consegui aplicar a lideranca "
                                   "(%s)", type(erro).__name__)
            dadas += 1
            if voltas and dadas >= voltas:
                return
            await asyncio.sleep(intervalo_s)


# ===========================================================================
# O POÇO DE THREADS — deixa de ser implícito (§9.3)
# ===========================================================================
#
# 📊 21/09/2026: `grep -rn "asyncio.to_thread" app --include=*.py | wc -l` → 319
# pontos. Todos eles compartilham UM executor default, e o default do Python é
# `min(32, cpu_count + 4)`: num contêiner de 1 vCPU são **5 threads** para os
# 319 pontos — incluindo o envio ao WhatsApp, que é `requests.post` SÍNCRONO com
# timeout de 30 s, de TODAS as corretoras.
#
# 🔴 Com cota 4 por corretora e teto global 24 (esta SPEC), 5 threads é o
# gargalo que reintroduz "uma trava a outra" UMA CAMADA ABAIXO da cota: a cota
# admitiria 24 turnos e eles fariam fila no poço, invisíveis.
#
# A DECISÃO, com nota:
#   max(32, cpu+4)         **91** — as threads aqui ESPERAM REDE (Supabase,
#                          WhatsApp, MinIO), não queimam CPU; 32 esperas
#                          simultâneas num contêiner de 1 vCPU é correto, e é o
#                          mesmo teto que o Python já usa numa máquina de 28
#                          núcleos. Custo: cada thread reserva pilha (8 MB
#                          VIRTUAIS no Linux, alguns dezenas de KB residentes) e
#                          só nasce quando há trabalho — o pool é preguiçoso.
#                          📊 32 threads ociosas ≈ 2-3 MB residentes.
#   cpu*8                  74 — depende do vCPU do plano, que muda sem aviso.
#   deixar o default       31 — é o número que ninguém conhece (BLOCO 0 item 9).
_POCO_PADRAO = 32
_POCO_INSTALADO: list = [None]


def tamanho_do_poco() -> int:
    """`EXECUTOR_THREADS`, ou o default EXPLÍCITO. Nunca zero, nunca implícito."""
    try:
        pedido = int(str(os.getenv("EXECUTOR_THREADS", "0")).strip() or 0)
    except (TypeError, ValueError):
        pedido = 0
    if pedido > 0:
        return pedido
    return max(_POCO_PADRAO, (os.cpu_count() or 1) + 4)


def instalar_poco(loop=None) -> Any:
    """Instala o executor default do loop — e é o LOOP que passa a mandar.

    ⛔ Não cria concorrência nova: `asyncio.to_thread` já usava um poço: um que
    ninguém dimensionou. O que muda é o número virar variável com nome.
    """
    alvo = loop or asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=tamanho_do_poco(),
                                  thread_name_prefix="to_thread")
    alvo.set_default_executor(executor)
    _POCO_INSTALADO[0] = executor
    logger.info("[POCO] executor default com %d threads (EXECUTOR_THREADS)",
                tamanho_do_poco())
    return executor


def poco_instalado() -> Any:
    return _POCO_INSTALADO[0]


def tamanho_instalado() -> Optional[int]:
    """Quantas threads o executor instalado aceita — para o `/health`."""
    executor = _POCO_INSTALADO[0]
    if executor is None:
        return None
    return getattr(executor, "_max_workers", None)


def fechar_poco(esperar: bool = False) -> None:
    executor = _POCO_INSTALADO[0]
    _POCO_INSTALADO[0] = None
    if executor is not None:
        try:
            executor.shutdown(wait=esperar)
        except Exception as erro:  # noqa: BLE001
            logger.warning("[POCO] executor nao fechou (%s)", type(erro).__name__)


__all__ = [
    "CHAVE_DO_LIDER", "TTL_SEGUNDOS", "RENOVACAO_SEGUNDOS", "TIMEOUT_REDIS_S",
    "LUA_RENOVAR", "LUA_LIBERAR", "DESLIGADO", "LIDER", "SEGUIDOR",
    "agendador_ligado", "JOBS", "Job", "ids_classificados", "sem_classificacao",
    "LiderDoAgendador",
    "tamanho_do_poco", "instalar_poco", "poco_instalado", "tamanho_instalado",
    "fechar_poco",
]
