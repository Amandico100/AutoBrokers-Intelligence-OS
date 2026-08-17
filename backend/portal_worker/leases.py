# -*- coding: utf-8 -*-
"""Lease distribuído por CONTA de portal — SPEC-075 Bloco N.

O que este módulo resolve
=========================
O portal-worker é globalmente serial. 📊 Medido em 16/08/2026 em
`backend/portal_worker/worker.py:747-760` (`run_once`): o loop faz
`.limit(1)`, roda a journey inteira e só então volta à fila — um job por vez,
para o produto inteiro. A única proteção contra dois workers é o UPDATE
condicional `.eq("id", job_id).eq("status", "queued")`, que impede o job
DUPLICADO mas não diz nada sobre a CONTA.

São dois problemas diferentes, e é por isso que o UPDATE condicional não basta
quando a concorrência sobe:

    job duplicado   → dois workers pegam o MESMO job        → UPDATE resolve
    conta duplicada → dois workers pegam jobs DIFERENTES    → UPDATE não vê
                      da mesma conta do mesmo portal

O segundo caso é o que quebra na prática: um portal de seguradora mantém UMA
sessão por login. Dois Chromium logados na mesma conta ao mesmo tempo derrubam
a sessão um do outro, e o sintoma que chega é "o portal deslogou sozinho no
meio do boleto" — que ninguém liga a paralelismo.

Por que Lease do Kubernetes e não `SETNX`
=========================================
`SETNX` guarda um cadeado anônimo: qualquer processo consegue abrir. O desenho
do Lease do Kubernetes guarda **identidade do dono + duração + renovação**, e é
a identidade que fecha o buraco abaixo:

    A adquire a lease (TTL 120s)
    A trava 130s dentro de um iframe da seguradora
    a lease vence, B adquire e começa a trabalhar
    A acorda, termina e "libera a lease"     🔴 A libera a lease de B

Com valor = identidade do dono, `liberar` de A vira no-op e a conta continua
protegida. Sem isso, o cadeado dá uma falsa sensação de exclusão mútua e o
estrago aparece exatamente na cauda longa (job lento), que é onde ele custa
mais caro.

`renovar` e `liberar` são Lua porque `GET` + comparar em Python + `EXPIRE` são
três viagens: a lease pode trocar de dono entre a primeira e a terceira. Lua no
Redis roda como uma unidade — o check e o set são o mesmo instante.

Redis fora do ar (SPEC-075 §23.5)
=================================
A tentação é fazer o lease "negar tudo" quando o Redis cai — parece o lado
seguro. Não é: negar tudo para o portal-worker inteiro, e uma renovação da CVA
que vence hoje não é enviada porque o cache está fora. Também não pode ser
"conceder tudo e seguir paralelo": aí sim duas sessões na mesma conta.

A saída é tratar as duas decisões como UMA:

    Redis fora  →  concorrência efetiva cai para 1  →  lease sempre concede

Com concorrência 1 existe um único job em voo por worker, então duas sessões na
mesma conta só podem vir de dois PROCESSOS — e contra isso o UPDATE condicional
do Supabase (`WHERE id=X AND status='queued'`) já é suficiente, porque com
serialidade global o job em voo é o único job em voo. O lease conceder nesse
regime não afrouxa nada: ele apenas deixa de ser o mecanismo de exclusão, que
volta a ser o banco — exatamente o desenho de hoje, que roda em produção.

🔴 A ordem importa e não é opcional: quem chamar `adquirir()` sem ter aplicado
`politica_com_redis_fora()` à concorrência transforma queda de Redis em
paralelismo sem trava. Rebaixar a concorrência é a metade que paga a outra.

Este módulo não faz I/O no import, não levanta exceção por causa de Redis e não
conhece Playwright, Supabase nem journey.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import socket
import time
import uuid
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Mesmos números do Work OS (`app/services/work/runs.py`) por decisão, não por
# coincidência: um operador que já sabe diagnosticar lease de Work Run não deve
# ter de aprender uma segunda escala de tempo para diagnosticar lease de portal.
LEASE_DURACAO_SEGUNDOS = 120
HEARTBEAT_INTERVALO_SEGUNDOS = 30

# 🔴 A lease é curta DE PROPÓSITO, mesmo com job que pode durar 1200s
# (`PORTAL_JOB_TIMEOUT_SECONDS`). Lease longa não protege melhor: ela só decide
# quanto tempo a conta fica refém de um worker que MORREU. Quem cobre job longo
# é a renovação, que só um processo vivo consegue fazer.
CONCORRENCIA_PADRAO = 1
TETO_CONCORRENCIA = 8

# Teto de 8 é memória, não gosto: cada slot é um Chromium com contexto próprio.
# Acima disso o container começa a ser morto por OOM no meio da journey, e job
# morto por OOM volta como "erro do portal" no diagnóstico — o pior tipo de
# falha, a que mente sobre a causa.

PREFIXO_CHAVE = "portal:lease"

# Portal público não tem conta, mas TEM corretora. Este discriminador entra no
# lugar do rótulo para manter a chave com a mesma forma; o `company_id` continua
# na chave, então duas corretoras seguem rodando em paralelo. 🔴 Usar uma chave
# global para portal público serializaria todos os tenants atrás de um cadeado
# só — o oposto do que o bloco quer.
CONTA_AUSENTE = "sem-conta"

# Janela do cache de disponibilidade. Sem ela, um `ping` por job — e num worker
# com concorrência 8 isso é ruído puro. Com ela, a queda é percebida em até 5s,
# que é uma ordem de grandeza menor que o poll de 30s do worker.
_JANELA_PING_SEGUNDOS = 5.0
_CLIENTE: Optional[Any] = None

_ultimo_ping_em: float = 0.0
_ultimo_ping_ok: bool = False


# --------------------------------------------------------------------------
# Lua — check-and-set atômico
# --------------------------------------------------------------------------

# Renova SÓ se o dono ainda for o mesmo. Chave ausente cai no `else`: uma lease
# vencida NÃO é ressuscitada por `renovar`. Isso é intencional — entre o
# vencimento e a renovação outro worker pode ter assumido, e ressuscitar seria
# roubar a conta de quem está com o browser aberto nela. Quem perdeu a lease
# tem de abortar o job e reconquistar via `adquirir`.
_LUA_RENOVAR = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('EXPIRE', KEYS[1], ARGV[2])
else
    return 0
end
"""

# Libera SÓ se for o dono — o bug clássico descrito no cabeçalho.
_LUA_LIBERAR = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
else
    return 0
end
"""


# --------------------------------------------------------------------------
# Cliente
# --------------------------------------------------------------------------


def _cliente() -> Optional[Any]:
    """Cliente Redis, ou `None`. Nunca levanta.

    🔴 Este módulo mora em `portal_worker/`, e NÃO em `app/services/portals/`,
    por uma razão de contêiner: o `Dockerfile` do portal-worker faz
    `COPY backend/portal_worker /app/portal_worker` e mais nada. Um lease que
    importasse `app.core.redis` seria um lease que **não existe no processo que
    precisa dele** — o worker. A primeira versão deste arquivo nasceu em `app/`
    e teria falhado exatamente assim, em produção, com todos os testes verdes:
    a falha da CLAUDE.md §9.1 outra vez.

    Pelo mesmo motivo o cliente é criado aqui a partir de `REDIS_URL`, e não
    reusado de `app.core.redis`. Não é um segundo pool contra o mesmo Redis no
    mesmo processo — é o único pool DESTE processo, que é outro serviço.

    O import de `redis` é tardio e tolerante: se a biblioteca não estiver na
    imagem, o resultado é "Redis fora" — decisão segura e registrada — em vez de
    derrubar o boot do worker por causa de um recurso opcional.
    """
    global _CLIENTE
    if _CLIENTE is not None:
        return _CLIENTE
    url = str(os.getenv("REDIS_URL") or "").strip()
    if not url:
        return None
    try:
        import redis as _redis  # noqa: PLC0415

        _CLIENTE = _redis.from_url(
            url, decode_responses=True,
            socket_connect_timeout=3, socket_timeout=3,
            health_check_interval=30)
        return _CLIENTE
    except Exception as exc:  # noqa: BLE001
        logger.warning("[PortalLease] Redis indisponível: %s", type(exc).__name__)
        return None


def redis_disponivel(forcar: bool = False) -> bool:
    """`True` se o Redis responde `ping`. Resultado vale por 5s.

    `forcar=True` ignora o cache — para o teste e para o diagnóstico, que
    precisam da resposta de agora, não da de cinco segundos atrás.
    """
    global _ultimo_ping_em, _ultimo_ping_ok

    agora = time.monotonic()
    if not forcar and (agora - _ultimo_ping_em) < _JANELA_PING_SEGUNDOS:
        return _ultimo_ping_ok

    cliente = _cliente()
    ok = False
    if cliente is not None:
        try:
            ok = bool(cliente.ping())
        except Exception as exc:  # noqa: BLE001
            logger.warning("[PortalLease] ping falhou: %s", type(exc).__name__)
            ok = False

    _ultimo_ping_em, _ultimo_ping_ok = agora, ok
    return ok


def _resetar_cache_de_ping() -> None:
    """Zera o cache de disponibilidade. Existe para o teste não esperar 5s."""
    global _ultimo_ping_em, _ultimo_ping_ok
    _ultimo_ping_em, _ultimo_ping_ok = 0.0, False


# --------------------------------------------------------------------------
# Identidade e chave
# --------------------------------------------------------------------------


def identidade_do_worker() -> str:
    """Quem é o dono da lease. Mesmo formato de `work/runs.py:worker_id()`.

    Host + sufixo aleatório: o host diz em QUAL máquina olhar quando uma conta
    fica travada, e o sufixo distingue dois processos no mesmo host — que é o
    caso normal quando a concorrência sobe.
    """
    return f"{socket.gethostname()}:{uuid.uuid4().hex[:8]}"


def _fatia(valor: Any, padrao: str = "") -> str:
    texto = str(valor or "").strip().lower()
    if not texto:
        return padrao

    limpo = re.sub(r"[^a-z0-9_-]+", "-", texto).strip("-")
    if not limpo:
        limpo = "x"

    # Rótulo com acento, espaço ou barra vira outra coisa depois da limpeza, e
    # duas contas distintas poderiam colidir na mesma chave. Colisão só CAUSA
    # serialização a mais (lado seguro), mas atrapalha o diagnóstico: duas
    # contas somem atrás de uma chave só. O sufixo do hash separa as duas sem
    # perder a parte legível no `redis-cli`.
    if limpo != texto:
        limpo = f"{limpo}-{hashlib.sha1(texto.encode('utf-8')).hexdigest()[:6]}"
    return limpo


def chave_de_conta(company_id: Any, portal_key: Any, account_label: Any = "") -> str:
    """Chave que serializa a MESMA conta — e só ela.

        portal:lease:{company_id}:{portal_key}:{account_label}

    Duas contas diferentes do mesmo portal PODEM rodar em paralelo (dois logins,
    duas sessões, nenhum conflito). A mesma conta, não: o portal mantém uma
    sessão por login e a segunda derruba a primeira.

    `company_id` está na chave por isolamento, não por enfeite: sem ele, a conta
    "default" da corretora A e a "default" da B disputariam o mesmo cadeado —
    vazamento de disponibilidade entre tenants, do tipo que só aparece sob carga.

    Portal público (sem conta) usa `CONTA_AUSENTE`, mantendo `company_id` na
    chave para preservar o paralelismo entre corretoras.

    Levanta `ValueError` sem `company_id` ou `portal_key`. 🔴 Aqui a exceção é
    correta e a tolerância é que seria perigosa: cair para um valor genérico
    fabricaria uma chave compartilhada entre tenants. Isso é erro de chamada, não
    é indisponibilidade de infraestrutura — a regra de "nunca levantar" vale para
    o Redis, não para argumento faltando.
    """
    empresa = _fatia(company_id)
    portal = _fatia(portal_key)
    if not empresa or not portal:
        raise ValueError(
            "chave_de_conta exige company_id e portal_key — "
            f"recebi company_id={company_id!r} portal_key={portal_key!r}"
        )
    conta = _fatia(account_label, padrao=CONTA_AUSENTE)
    return f"{PREFIXO_CHAVE}:{empresa}:{portal}:{conta}"


# --------------------------------------------------------------------------
# Concorrência
# --------------------------------------------------------------------------


def concorrencia_configurada() -> int:
    """Quantos jobs em voo o worker pode ter. `PORTAL_WORKER_CONCURRENCY`.

    Default 1: quem faz deploy sem tocar em nada continua com o comportamento
    serial de hoje, que é o comportamento auditado. Aumentar concorrência é uma
    decisão, nunca um efeito colateral de subir a versão.

    Lixo (vazio, texto, `0`, negativo) vira 1 e acima do teto vira o teto — sem
    exceção. Variável de ambiente malformada não pode derrubar o worker no boot:
    o modo degradado é serial, e serial funciona.
    """
    bruto = os.getenv("PORTAL_WORKER_CONCURRENCY", "")
    try:
        valor = int(str(bruto).strip())
    except (TypeError, ValueError):
        if str(bruto).strip():
            logger.warning(
                "[PortalLease] PORTAL_WORKER_CONCURRENCY=%r inválido — usando %d",
                bruto, CONCORRENCIA_PADRAO,
            )
        return CONCORRENCIA_PADRAO

    if valor < 1:
        logger.warning("[PortalLease] PORTAL_WORKER_CONCURRENCY=%d < 1 — usando %d",
                       valor, CONCORRENCIA_PADRAO)
        return CONCORRENCIA_PADRAO
    if valor > TETO_CONCORRENCIA:
        logger.warning("[PortalLease] PORTAL_WORKER_CONCURRENCY=%d acima do teto — usando %d",
                       valor, TETO_CONCORRENCIA)
        return TETO_CONCORRENCIA
    return valor


def politica_com_redis_fora(concorrencia_pedida: int) -> Tuple[int, str]:
    """Concorrência efetiva + motivo, considerando o estado do Redis.

    Chame isto ANTES de abrir slots, a cada volta do poll — não uma vez no boot.
    O Redis cai no meio da tarde, não no `startup`, e uma decisão tomada no boot
    deixaria o worker paralelo sem trava até alguém reiniciar o serviço.

    Devolve sempre um par legível, porque o motivo vai para log e para a tela de
    diagnóstico: "por que só um job está rodando" precisa ter resposta escrita.
    """
    try:
        pedida = int(concorrencia_pedida)
    except (TypeError, ValueError):
        pedida = CONCORRENCIA_PADRAO

    pedida = max(CONCORRENCIA_PADRAO, min(pedida, TETO_CONCORRENCIA))

    if pedida <= 1:
        return 1, "concorrência 1 configurada — exclusão pelo UPDATE condicional do Supabase"

    if redis_disponivel():
        return pedida, f"Redis disponível — concorrência {pedida} com lease por conta"

    # 🔴 Este é o ponto exato onde queda de Redis vira ou não vira incidente.
    return 1, (
        f"Redis indisponível — concorrência rebaixada de {pedida} para 1; "
        "sem lease, a exclusão volta a ser o UPDATE condicional do Supabase, "
        "que só é suficiente em regime serial"
    )


# --------------------------------------------------------------------------
# Lease
# --------------------------------------------------------------------------


class LeaseDePortal:
    """Lease por conta de portal: identidade do dono, duração e renovação.

    Aceita `cliente` injetado — para teste com fake e para quem já tem o cliente
    em mãos. Sem injeção, resolve pelo caminho da casa (`app.core.redis`) na
    primeira chamada, nunca no import.

    Contrato de falha: **nada aqui levanta por causa de Redis.** Redis fora faz
    todo método conceder (`True`), porque a política de rebaixar a concorrência
    para 1 é quem restaura a segurança — ver `politica_com_redis_fora`. Método
    que levantasse obrigaria cada chamador a inventar sua própria política, e
    seriam políticas diferentes em cada ponto de chamada.
    """

    def __init__(self, cliente: Optional[Any] = None) -> None:
        self._cliente = cliente
        self._resolvido = cliente is not None

    # -- infraestrutura ------------------------------------------------

    def _redis(self) -> Optional[Any]:
        if not self._resolvido:
            self._cliente = _cliente()
            self._resolvido = True
        return self._cliente

    @staticmethod
    def _ttl(duracao_s: Optional[int]) -> int:
        """TTL sempre ≥ 1s. TTL 0 ou negativo no `SET ... EX` é erro no Redis, e
        um erro aqui viraria "lease concedida" — trava que não trava."""
        try:
            valor = int(duracao_s) if duracao_s is not None else LEASE_DURACAO_SEGUNDOS
        except (TypeError, ValueError):
            valor = LEASE_DURACAO_SEGUNDOS
        return max(1, valor)

    # -- operações -----------------------------------------------------

    def adquirir(self, chave: str, dono: str, duracao_s: int = LEASE_DURACAO_SEGUNDOS) -> bool:
        """`SET chave dono NX EX ttl`. `True` = a conta é sua até o TTL vencer.

        O VALOR é a identidade do dono, e é isso que torna `renovar` e `liberar`
        verificáveis depois. Um cadeado sem valor só responde "está travado";
        este responde "travado por quem", que é a pergunta que o operador faz.

        `dono` vazio é recusado: uma lease anônima poderia ser liberada por
        qualquer um que também passasse vazio.
        """
        if not dono:
            logger.error("[PortalLease] adquirir sem dono — recusado (chave=%s)", chave)
            return False

        cliente = self._redis()
        if cliente is None:
            logger.warning("[PortalLease] Redis fora — concedendo %s (exige concorrência 1)", chave)
            return True

        try:
            return bool(cliente.set(chave, dono, nx=True, ex=self._ttl(duracao_s)))
        except Exception as exc:  # noqa: BLE001
            logger.warning("[PortalLease] adquirir falhou (%s) em %s — concedendo",
                           type(exc).__name__, chave)
            return True

    def renovar(self, chave: str, dono: str, duracao_s: int = LEASE_DURACAO_SEGUNDOS) -> bool:
        """Estende a lease SÓ se `dono` ainda for o dono. Lua, atômico.

        `False` significa "você perdeu a conta" — a lease venceu ou outro worker
        assumiu. 🔴 O chamador tem de ABORTAR o job nesse caso, não continuar
        clicando: quem está com o browser aberto na conta agora é outro, e
        seguir é exatamente a colisão de sessão que este módulo existe para
        impedir.
        """
        if not dono:
            return False

        cliente = self._redis()
        if cliente is None:
            return True

        try:
            return bool(cliente.eval(_LUA_RENOVAR, 1, chave, dono, self._ttl(duracao_s)))
        except Exception as exc:  # noqa: BLE001
            # Falha de rede não é perda de lease: o TTL no servidor continua
            # correndo. Conceder aqui só mantém o job vivo até a próxima
            # renovação; negar mataria job bom por soluço de rede.
            logger.warning("[PortalLease] renovar falhou (%s) em %s — mantendo",
                           type(exc).__name__, chave)
            return True

    def liberar(self, chave: str, dono: str) -> bool:
        """Devolve a conta SÓ se `dono` for o dono. Lua, atômico.

        🔴 O bug clássico que este `if` no Lua impede: A expira, B adquire, A
        acorda e libera — e a conta de B fica aberta para um terceiro enquanto B
        ainda está dentro do portal. `DEL` cego é o erro; `DEL` condicionado à
        identidade é a correção.

        `False` = não era seu, nada foi apagado. Não é erro: é o caso normal de
        quem perdeu a lease por timeout e só está limpando a própria bagunça.
        """
        if not dono:
            return False

        cliente = self._redis()
        if cliente is None:
            return True

        try:
            return bool(cliente.eval(_LUA_LIBERAR, 1, chave, dono))
        except Exception as exc:  # noqa: BLE001
            # Sem liberar, a lease morre sozinha no TTL. Prejuízo máximo é a
            # conta esperar até 120s — muito menor que liberar às cegas.
            logger.warning("[PortalLease] liberar falhou (%s) em %s — TTL cuidará",
                           type(exc).__name__, chave)
            return False

    def dono_atual(self, chave: str) -> Optional[str]:
        """Quem segura a lease agora, ou `None` (livre / Redis fora).

        Só diagnóstico. 🔴 Não use para decidir se pode trabalhar: entre o `GET`
        e o clique a lease pode trocar de dono. Quem decide é `adquirir`.
        """
        cliente = self._redis()
        if cliente is None:
            return None

        try:
            valor = cliente.get(chave)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[PortalLease] dono_atual falhou (%s) em %s",
                           type(exc).__name__, chave)
            return None

        if valor is None:
            return None
        # O cliente da casa usa `decode_responses=True`, então isto já vem str.
        # O `bytes` é cinto de segurança para cliente injetado em teste.
        return valor.decode("utf-8") if isinstance(valor, bytes) else str(valor)
