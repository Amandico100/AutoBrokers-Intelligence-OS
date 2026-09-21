# -*- coding: utf-8 -*-
r"""G8 + EXECUTOR — SÓ UM AGENDADOR MANDA, E O POÇO DE THREADS TEM TAMANHO.
SPEC-EXTRA-001.8, FATIA 4 (lock de líder · classificação dos 25 jobs · poço).

🔴 **O defeito, lido no código em 21/09/2026.** `start_buffer_scheduler()`
registra 25 jobs periódicos (📊 `grep -c "scheduler.add_job"
app/tasks/buffer_processor.py` → 25) e é chamado no `lifespan` de CADA processo
que sobe. Hoje só existe uma réplica do `smith-api` — isso é uma configuração
do painel, não uma trava do código. Duas réplicas = dois `handoff_watchdog`
varrendo os mesmos handoffs parados e mandando DUAS mensagens ao mesmo grupo de
suporte, no mesmo minuto.

E o segundo defeito, na mesma camada: 📊 `grep -rn "asyncio.to_thread" app
--include=*.py | wc -l` → **319** pontos dividindo UM executor default que
ninguém dimensionou — `min(32, cpu+4)`, que num contêiner de 1 vCPU é **cinco
threads** para o envio ao WhatsApp de todas as corretoras.

O QUE ESTE ARQUIVO PROVA, com o MÓDULO REAL sobre um Redis dublê que honra
`NX` e TTL pelo relógio controlado:

```
(a) dois "processos", tokens diferentes  ->  UM só é líder
(b) o líder morre (TTL vence)            ->  o seguidor assume
(c) soltura confere o token              ->  B NÃO solta o cadeado de A
(d) Redis fora                           ->  nenhum job de ENVIO roda; os que
                                             só leem, sim (decisão POR JOB)
(e) todo job registrado está na tabela   ->  job novo sem linha = VERMELHO
(f) SCHEDULER_ENABLED=false              ->  zero job registrado
(g) 1 processo, Redis ok                 ->  os 25 jobs (LINHA DE CONTROLE)
(h) o poço de threads tem o tamanho pedido, e `main.py` o instala ANTES
```

⛔ SEGURANÇA: zero rede, zero banco, zero Redis de verdade, zero LLM, zero
envio. Nenhum nome de corretora, pessoa ou telefone (CLAUDE.md §13.9).

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_so_um_agendador_manda.py
    ... --so d          ·   ... --mutar   ·   ... --mutar M-E-2
    python -m pytest tests/test_so_um_agendador_manda.py -q -p no:cacheprovider
"""
from __future__ import annotations

import ast
import asyncio
import io
import os
import shutil
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../backend
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ["SEM_REDE"] = "1"

BUFFER_PY = os.path.join(RAIZ, "app", "tasks", "buffer_processor.py")
LIDER_PY = os.path.join(RAIZ, "app", "core", "lider_do_agendador.py")
MAIN_PY = os.path.join(RAIZ, "app", "main.py")
ESTE = os.path.abspath(__file__)

PASS = 0
FAIL = 0


def _p(texto):
    try:
        print(texto)
    except UnicodeEncodeError:
        cod = getattr(sys.stdout, "encoding", None) or "ascii"
        print(str(texto).encode(cod, "replace").decode(cod, "replace"))


def check(nome, cond, detalhe=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        _p("  [ok] %s" % nome)
    else:
        FAIL += 1
        _p("  [FALHOU] %s" % nome + ("\n         %s" % str(detalhe)[:900] if detalhe else ""))
    return bool(cond)


import app.core.lider_do_agendador as L  # noqa: E402


# ===========================================================================
# O REDIS DUBLÊ — honra NX e TTL, e o relógio é nosso
# ===========================================================================
RELOGIO = [1_000.0]


def _andar(segundos: float):
    RELOGIO[0] += float(segundos)


class RedisDuble:
    """Só o que o líder usa: `set(nx=, ex=)`, `get`, `eval`, `delete`.

    ⚠️ O `eval` é um mini-intérprete de propósito: ele OBEDECE ao script que
    receber. É isso que torna a mutação honesta — trocar o Lua por um `DEL`
    cego não vira erro de dublê, vira um cadeado apagado de verdade.
    """

    def __init__(self):
        self.dados = {}     # chave -> (valor, vence_em|None)
        self.chamadas = []

    def _vivo(self, k):
        item = self.dados.get(k)
        if item is None:
            return None
        valor, vence = item
        if vence is not None and RELOGIO[0] >= vence:
            self.dados.pop(k, None)
            return None
        return valor

    async def get(self, k):
        return self._vivo(k)

    async def set(self, k, v, nx=False, ex=None):
        self.chamadas.append(("set", k, bool(nx), ex))
        if nx and self._vivo(k) is not None:
            return None
        self.dados[k] = (str(v), RELOGIO[0] + float(ex) if ex else None)
        return True

    async def delete(self, *chaves):
        return sum(1 for k in chaves if self.dados.pop(k, None) is not None)

    async def eval(self, script, numkeys, *args):
        self.chamadas.append(("eval", script))
        chave = args[0]
        token = args[1] if len(args) > 1 else None
        atual = self._vivo(chave)
        # O script CONFERE o dono? (é a diferença entre cadeado e `DEL` cego)
        confere = "ARGV[1]" in script and ("GET" in script.upper())
        apaga = "del" in script.lower()
        renova = "expire" in script.lower()
        if confere and atual != token:
            return 0
        if apaga:
            existia = self.dados.pop(chave, None) is not None
            return 1 if existia else 0
        if renova:
            if atual is None:
                return 0
            self.dados[chave] = (atual, RELOGIO[0] + float(args[2]))
            return 1
        raise AssertionError("script Lua desconhecido no duble: %r" % script[:80])


class RedisFora:
    """Todo comando levanta — é o Redis caído, não um Redis vazio."""

    async def get(self, *a, **k):
        raise ConnectionError("redis fora")

    async def set(self, *a, **k):
        raise ConnectionError("redis fora")

    async def eval(self, *a, **k):
        raise ConnectionError("redis fora")

    async def delete(self, *a, **k):
        raise ConnectionError("redis fora")


def _lider(cliente, token=None):
    return L.LiderDoAgendador(cliente=cliente, token=token)


# ===========================================================================
# (a) DOIS PROCESSOS, UM CADEADO
# ===========================================================================
def cenario_a():
    _p("\n=== (a) dois processos, tokens diferentes -> UM so e lider ===")

    async def corpo():
        redis = RedisDuble()
        a, b = _lider(redis), _lider(redis)
        check("os tokens sao diferentes (um por processo)", a.token != b.token)
        ganhou_a = await a.tentar_assumir()
        ganhou_b = await b.tentar_assumir()
        check("A assumiu", ganhou_a is True, "A=%s" % a.estado)
        check("B NAO assumiu", ganhou_b is False, "B=%s" % b.estado)
        check("A se diz lider e B se diz seguidor",
              (a.estado, b.estado) == (L.LIDER, L.SEGUIDOR),
              "A=%s B=%s" % (a.estado, b.estado))
        check("o cadeado guarda o token de A, nao o de B",
              redis.dados[L.CHAVE_DO_LIDER][0] == a.token)
        check("o SET foi NX com EX (nunca um SET cru)",
              ("set", L.CHAVE_DO_LIDER, True, L.TTL_SEGUNDOS) in redis.chamadas,
              redis.chamadas)
        # LINHA DE CONTROLE: o proprio lider renovando segue lider.
        check("CONTROLE: A tenta de novo e continua lider",
              await a.tentar_assumir() is True and a.estado == L.LIDER)
        # E o que o produto pergunta: B nao roda job de envio nenhum.
        check("B (seguidor, Redis ok) nao roda o vigia de handoff",
              b.deve_rodar("handoff_watchdog_check") is False)
        check("B (seguidor) nao roda nem o backup — quem manda e o lider",
              b.deve_rodar("minio_backup") is False)
        check("B (seguidor) CONTINUA respondendo ao segurado",
              b.deve_rodar("whatsapp_buffer_check") is True)

    asyncio.run(corpo())


# ===========================================================================
# (b) O LÍDER MORRE — o seguidor assume em <= TTL
# ===========================================================================
def cenario_b():
    _p("\n=== (b) o lider morre (TTL vence) -> o seguidor assume ===")

    async def corpo():
        redis = RedisDuble()
        a, b = _lider(redis), _lider(redis)
        await a.tentar_assumir()
        await b.tentar_assumir()

        _andar(L.TTL_SEGUNDOS - 1)
        check("antes do TTL vencer, B ainda nao assume",
              await b.tentar_assumir() is False)

        # 🔴 A morreu: ninguem renova. O cadeado vence sozinho.
        _andar(2)
        check("passado o TTL, B ASSUME", await b.tentar_assumir() is True)
        check("B agora e o lider e roda o vigia de handoff",
              b.estado == L.LIDER and b.deve_rodar("handoff_watchdog_check"))
        check("o cadeado agora guarda o token de B",
              redis.dados[L.CHAVE_DO_LIDER][0] == b.token)

        # E o zumbi descobre na renovacao: outro token esta la.
        check("A (zumbi) tenta renovar e DESCOBRE que perdeu",
              await a.renovar() is False)
        check("A voltou a seguidor e PARA de rodar o que envia",
              a.estado == L.SEGUIDOR
              and a.deve_rodar("handoff_watchdog_check") is False)
        check("o cadeado de B sobreviveu a renovacao de A",
              redis.dados[L.CHAVE_DO_LIDER][0] == b.token)

    asyncio.run(corpo())


# ===========================================================================
# (c) A SOLTURA CONFERE O TOKEN — ⛔ nunca `DEL` cego
# ===========================================================================
def cenario_c():
    _p("\n=== (c) soltura so com o token certo ===")
    literal = ('if redis.call("get",KEYS[1]) == ARGV[1] then return '
               'redis.call("del",KEYS[1]) else return 0 end')
    check("o script de soltura e o LITERAL da doc do Redis (E3)",
          " ".join(L.LUA_LIBERAR.split()) == literal,
          repr(L.LUA_LIBERAR))

    async def corpo():
        redis = RedisDuble()
        a, b = _lider(redis), _lider(redis)
        await a.tentar_assumir()
        await b.tentar_assumir()

        # B acha que e lider (estado velho) e tenta soltar o cadeado de A.
        b.estado = L.LIDER
        soltou = await b.soltar()
        check("B NAO consegue soltar o cadeado de A", soltou is False)
        check("🔴 o cadeado de A CONTINUA la depois da tentativa de B",
              redis.dados.get(L.CHAVE_DO_LIDER, (None,))[0] == a.token,
              redis.dados)
        check("A continua lider de fato (renova sem susto)",
              await a.renovar() is True)

        check("A solta o proprio cadeado", await a.soltar() is True)
        check("e o cadeado sumiu", L.CHAVE_DO_LIDER not in redis.dados)
        check("solto o cadeado, o outro processo assume NA HORA",
              await b.tentar_assumir() is True)

    asyncio.run(corpo())


# ===========================================================================
# (d) REDIS FORA — a decisão é POR JOB
# ===========================================================================
def cenario_d():
    _p("\n=== (d) Redis fora -> quem ENVIA para; quem so le, segue ===")

    async def corpo():
        lider = _lider(RedisFora())
        check("sem Redis ninguem vira lider", await lider.tentar_assumir() is False)
        check("e o processo SABE que esta sem Redis", lider.redis_fora is True)

        enviam = [i for i, j in L.JOBS.items() if j.envia and j.exige_lider]
        so_leem = [i for i, j in L.JOBS.items()
                   if not j.envia and j.exige_lider and j.sem_redis_roda]
        abertos = [i for i, j in L.JOBS.items() if not j.exige_lider]

        rodando_envia = [i for i in enviam if lider.deve_rodar(i)]
        parados_le = [i for i in so_leem if not lider.deve_rodar(i)]
        check("🔴 NENHUM job de envio roda sem prova de lideranca (%d jobs)"
              % len(enviam), rodando_envia == [], rodando_envia)
        check("os que so leem/higienizam/fazem backup SEGUEM (%d jobs)"
              % len(so_leem), parados_le == [], parados_le)
        check("o vigia de handoff (o dano medido da 001.3) esta PARADO",
              lider.deve_rodar("handoff_watchdog_check") is False)
        check("o backup do MinIO segue — backup duplicado nao machuca",
              lider.deve_rodar("minio_backup") is True)
        check("a varredura que responde ao segurado NUNCA para (%s)"
              % ", ".join(abertos),
              all(lider.deve_rodar(i) for i in abertos))
        check("job desconhecido e tratado como ENVIA (fail-closed)",
              lider.deve_rodar("job_que_alguem_esqueceu_de_classificar") is False)

        # CONTROLE: o MESMO lider, com Redis de pe e cadeado na mao, roda TUDO.
        redis = RedisDuble()
        chefe = _lider(redis)
        await chefe.tentar_assumir()
        faltando = [i for i in L.JOBS if not chefe.deve_rodar(i)]
        check("CONTROLE: lider com Redis de pe roda os %d jobs" % len(L.JOBS),
              faltando == [], faltando)

    asyncio.run(corpo())


# ===========================================================================
# (e) TODO JOB REGISTRADO ESTÁ CLASSIFICADO
# ===========================================================================
def _ids_registrados():
    """Os `id=` de cada `scheduler.add_job` no fonte REAL — nunca uma lista à mão."""
    fonte = io.open(BUFFER_PY, encoding="utf-8").read()
    ids = []
    for no in ast.walk(ast.parse(fonte)):
        if not isinstance(no, ast.Call):
            continue
        nome = no.func.attr if isinstance(no.func, ast.Attribute) else None
        if nome != "add_job":
            continue
        for kw in no.keywords:
            if kw.arg == "id" and isinstance(kw.value, ast.Constant):
                ids.append(str(kw.value.value))
    return ids


def cenario_e():
    _p("\n=== (e) todo job registrado tem linha na tabela ===")
    registrados = _ids_registrados()
    check("o fonte registra 25 jobs (o numero medido)", len(registrados) == 25,
          "%d: %s" % (len(registrados), registrados))
    check("nenhum id registrado duas vezes",
          len(set(registrados)) == len(registrados))
    orfaos = sorted(L.sem_classificacao(registrados))
    check("🔴 ZERO job registrado sem classificacao", orfaos == [], orfaos)
    fantasmas = sorted(set(L.JOBS) - set(registrados))
    check("e ZERO classificacao para job que nao existe mais", fantasmas == [],
          fantasmas)
    sem_porque = [i for i, j in L.JOBS.items() if not str(j.porque).strip()]
    check("cada linha diz POR QUE (uma frase)", sem_porque == [], sem_porque)


# ===========================================================================
# (f) SCHEDULER_ENABLED=false — nem registra
# ===========================================================================
def cenario_f():
    _p("\n=== (f) SCHEDULER_ENABLED=false -> nenhum job registrado ===")
    antes = os.environ.get("SCHEDULER_ENABLED")
    try:
        for valor, esperado in (("false", False), ("0", False), ("no", False),
                                ("true", True), ("", True)):
            os.environ["SCHEDULER_ENABLED"] = valor
            check("SCHEDULER_ENABLED=%r -> ligado=%s" % (valor, esperado),
                  L.agendador_ligado() is esperado)
        os.environ.pop("SCHEDULER_ENABLED", None)
        check("sem a variavel, o default e LIGADO (nada muda para quem sobe hoje)",
              L.agendador_ligado() is True)
    finally:
        if antes is None:
            os.environ.pop("SCHEDULER_ENABLED", None)
        else:
            os.environ["SCHEDULER_ENABLED"] = antes

    # 🔴 E o comportamento de verdade, no modulo REAL, num processo separado:
    # com a flag desligada ele nem chega nos imports dos 25 jobs.
    saida = _num_subprocesso(
        "import app.tasks.buffer_processor as bp\n"
        "bp.start_buffer_scheduler()\n"
        "print('RESULTADO', bp.scheduler.running, len(bp.scheduler.get_jobs()))\n",
        env={"SCHEDULER_ENABLED": "false"})
    check("o agendador REAL nao subiu e registrou ZERO jobs",
          "RESULTADO False 0" in saida, saida[-400:])


# ===========================================================================
# (g) LINHA DE CONTROLE — um processo, Redis de pé: os 25 jobs
# ===========================================================================
_CONTROLE = r"""
import app.tasks.buffer_processor as bp
import app.core.lider_do_agendador as L

class _JobFalso:
    def __init__(self, id): self.id, self.next_run_time = id, object()
class _AgendadorFalso:
    def __init__(self): self.jobs, self.running, self.iniciou = [], False, 0
    def add_job(self, fn, *a, **kw): self.jobs.append(_JobFalso(kw.get("id")))
    def get_jobs(self): return list(self.jobs)
    def get_job(self, id): return next(j for j in self.jobs if j.id == id)
    def start(self): self.iniciou += 1; self.running = True
    def pause_job(self, id): self.get_job(id).next_run_time = None
    def resume_job(self, id): self.get_job(id).next_run_time = object()

falso = _AgendadorFalso()
bp.scheduler = falso
bp.start_buffer_scheduler()
ids = [j.id for j in falso.get_jobs()]
parados = [j.id for j in falso.get_jobs() if j.next_run_time is None]
print("RESULTADO", len(ids), falso.iniciou, len(parados))
print("IDS", ",".join(sorted(ids)))
print("PARADOS", ",".join(sorted(parados)))
"""


def cenario_g():
    _p("\n=== (g) CONTROLE: 1 processo -> os 25 jobs registrados ===")
    saida = _num_subprocesso(_CONTROLE, env={"SCHEDULER_ENABLED": "true"})
    linha = [l for l in saida.splitlines() if l.startswith("RESULTADO")]
    ids = [l for l in saida.splitlines() if l.startswith("IDS")]
    parados = [l for l in saida.splitlines() if l.startswith("PARADOS")]
    check("o agendador REAL registrou os jobs e ligou",
          bool(linha) and linha[0].split()[1] == "25" and linha[0].split()[2] == "1",
          saida[-600:])
    if ids:
        registrados = set(ids[0][4:].split(","))
        check("os ids registrados sao EXATAMENTE os classificados",
              registrados == L.ids_classificados(),
              sorted(registrados ^ L.ids_classificados()))
    if parados:
        nomes = set(x for x in parados[0][8:].split(",") if x)
        esperados = {i for i, j in L.JOBS.items() if j.exige_lider}
        check("🔴 no boot, sem cadeado na mao, o que exige lideranca nasce PARADO",
              nomes == esperados, sorted(nomes ^ esperados))
        check("e a varredura do segurado nasce RODANDO",
              "whatsapp_buffer_check" not in nomes)

    async def corpo():
        redis = RedisDuble()
        chefe = _lider(redis)
        await chefe.tentar_assumir()
        check("CONTROLE: com o cadeado na mao, os %d jobs rodam" % len(L.JOBS),
              chefe.jobs_permitidos() == L.ids_classificados())

    asyncio.run(corpo())


# ===========================================================================
# (h) O POÇO DE THREADS
# ===========================================================================
def cenario_h():
    _p("\n=== (h) o poco de threads tem tamanho, e e instalado no loop ===")
    antes = os.environ.get("EXECUTOR_THREADS")
    try:
        os.environ.pop("EXECUTOR_THREADS", None)
        padrao = max(32, (os.cpu_count() or 1) + 4)
        check("sem a variavel, o default e EXPLICITO (max(32, cpu+4) = %d)" % padrao,
              L.tamanho_do_poco() == padrao, L.tamanho_do_poco())
        check("e ele nunca e os 5 do contentor de 1 vCPU",
              L.tamanho_do_poco() >= 32)
        os.environ["EXECUTOR_THREADS"] = "7"
        check("EXECUTOR_THREADS manda", L.tamanho_do_poco() == 7)
        os.environ["EXECUTOR_THREADS"] = "0"
        check("0 = ausente (cai no default)", L.tamanho_do_poco() == padrao)
        os.environ["EXECUTOR_THREADS"] = "lixo"
        check("lixo na variavel nao derruba o boot", L.tamanho_do_poco() == padrao)

        os.environ["EXECUTOR_THREADS"] = "9"

        async def corpo():
            laco = asyncio.get_running_loop()
            L.instalar_poco(laco)
            instalado = getattr(laco, "_default_executor", None)
            check("o executor DEFAULT do loop foi trocado", instalado is not None)
            check("e ele tem o tamanho pedido",
                  getattr(instalado, "_max_workers", None) == 9,
                  getattr(instalado, "_max_workers", None))
            check("/health consegue publicar o numero",
                  L.tamanho_instalado() == 9)
            # E ele funciona: `to_thread` passa por ele.
            check("uma tarefa em thread roda nesse poco",
                  (await asyncio.to_thread(lambda: 2 + 2)) == 4)
            L.fechar_poco(esperar=False)
            check("no shutdown o poco e fechado", L.tamanho_instalado() is None)

        asyncio.run(corpo())
    finally:
        if antes is None:
            os.environ.pop("EXECUTOR_THREADS", None)
        else:
            os.environ["EXECUTOR_THREADS"] = antes

    # 🔴 E o lifespan o instala ANTES do agendador — senão o primeiro
    # `check_buffers` (1 s depois do start) já pegaria o poço antigo.
    fonte = io.open(MAIN_PY, encoding="utf-8").read()
    arvore = ast.parse(fonte)
    lifespan = [n for n in ast.walk(arvore)
                if isinstance(n, ast.AsyncFunctionDef) and n.name == "lifespan"]
    check("main.py tem o lifespan", bool(lifespan))
    if lifespan:
        chamadas = []
        for no in ast.walk(lifespan[0]):
            if isinstance(no, ast.Call):
                nome = (no.func.id if isinstance(no.func, ast.Name)
                        else getattr(no.func, "attr", ""))
                if nome in ("instalar_poco", "start_buffer_scheduler"):
                    chamadas.append((no.lineno, nome))
        chamadas.sort()
        ordem = [n for _l, n in chamadas]
        check("o lifespan instala o poco", "instalar_poco" in ordem, ordem)
        check("🔴 e o instala ANTES de start_buffer_scheduler",
              ordem[:2] == ["instalar_poco", "start_buffer_scheduler"], ordem)


# ===========================================================================
# (i) A COSTURA ESTÁ LIGADA — o disjuntor é perguntado por alguém
# ===========================================================================
def cenario_i():
    _p("\n=== (i) check_buffers pergunta ao disjuntor (O ELO) ===")
    fonte = io.open(BUFFER_PY, encoding="utf-8").read()
    arvore = ast.parse(fonte)
    alvo = [n for n in ast.walk(arvore)
            if isinstance(n, ast.AsyncFunctionDef) and n.name == "check_buffers"]
    check("check_buffers existe", bool(alvo))
    if not alvo:
        return
    kwargs = []
    for no in ast.walk(alvo[0]):
        if isinstance(no, ast.Call) and getattr(no.func, "id", "") == \
                "processar_buffers_prontos":
            kwargs = [kw.arg for kw in no.keywords]
    check("🔴 a varredura do produto passa `barrados` (senao o breaker "
          "existiria sem chamador)", "barrados" in kwargs, kwargs)
    check("e passa `provedor_de` (senao ninguem sabe de QUEM e a conversa)",
          "provedor_de" in kwargs, kwargs)


# ===========================================================================
# INFRAESTRUTURA — subprocesso e mutações
# ===========================================================================
def _num_subprocesso(codigo: str, env=None) -> str:
    ambiente = dict(os.environ)
    ambiente.update(env or {})
    ambiente["PYTHONIOENCODING"] = "utf-8"
    ambiente["SEM_REDE"] = "1"
    proc = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=ambiente, timeout=600)
    return (proc.stdout or "") + "\n" + (proc.stderr or "")


# ===========================================================================
# (j) O AGENDADOR DE VERDADE OBEDECE — pausa e retoma job a job
# ===========================================================================
_REAL = r"""
import asyncio
import app.tasks.buffer_processor as bp
import app.core.lider_do_agendador as L
from apscheduler.schedulers.asyncio import AsyncIOScheduler

async def main():
    agendador = AsyncIOScheduler()
    bp.scheduler = agendador
    contagem = {"envia": 0, "responde": 0}
    async def _envia(): contagem["envia"] += 1
    async def _responde(): contagem["responde"] += 1
    agendador.add_job(_envia, "interval", seconds=0.05, id="handoff_watchdog_check")
    agendador.add_job(_responde, "interval", seconds=0.05, id="whatsapp_buffer_check")
    agendador.start()

    lider = L.LiderDoAgendador(cliente=None)
    lider.redis_fora = True                      # sem prova de lideranca
    bp._aplicar_lideranca(lider)
    await asyncio.sleep(0.4)
    print("SEM_CADEADO", contagem["envia"], contagem["responde"] > 0)

    lider.redis_fora = False
    lider.estado = L.LIDER                       # cadeado na mao
    bp._aplicar_lideranca(lider)
    await asyncio.sleep(0.4)
    print("COM_CADEADO", contagem["envia"] > 0)
    agendador.shutdown(wait=False)

asyncio.run(main())
"""


def cenario_j():
    _p("\n=== (j) o AsyncIOScheduler real obedece: pausa e retoma job a job ===")
    saida = _num_subprocesso(_REAL, env={"SCHEDULER_ENABLED": "true"})
    sem = [l for l in saida.splitlines() if l.startswith("SEM_CADEADO")]
    com = [l for l in saida.splitlines() if l.startswith("COM_CADEADO")]
    check("sem cadeado, o vigia que ENVIA nao disparou NENHUMA vez",
          bool(sem) and sem[0].split()[1] == "0", saida[-500:])
    check("e a varredura que responde ao segurado disparou assim mesmo",
          bool(sem) and sem[0].split()[2] == "True", saida[-500:])
    check("🔴 com o cadeado na mao, o vigia volta a disparar",
          bool(com) and com[0].split()[1] == "True", saida[-500:])


CENARIOS = {
    "a": cenario_a, "b": cenario_b, "c": cenario_c, "d": cenario_d,
    "e": cenario_e, "f": cenario_f, "g": cenario_g, "h": cenario_h,
    "i": cenario_i, "j": cenario_j,
}

#: Cada mutação: (arquivo, texto original, texto mutado, cenários que TÊM de
#: ficar vermelhos). ⛔ Restaura por CÓPIA, nunca `git checkout` (protocolo §10).
MUTACOES = {
    "M-E-1": (LIDER_PY,
              'LUA_LIBERAR = (\n    \'if redis.call("get",KEYS[1]) == ARGV[1] then return redis.call("del",KEYS[1]) \'\n    \'else return 0 end\'\n)',
              'LUA_LIBERAR = \'return redis.call("del",KEYS[1])\'',
              ["c"], "DEL cego na soltura"),
    "M-E-2": (LIDER_PY,
              '    _j("handoff_watchdog_check", True,',
              '    _j("handoff_watchdog_check", False,',
              ["d"], "fail-open no handoff_watchdog_check"),
    "M-E-3": (LIDER_PY,
              '    _j("minio_backup", False,',
              '    _j("minio_backup_REMOVIDO", False,',
              ["e"], "um id sai da tabela de classificacao"),
    "M-E-4": (MAIN_PY,
              "    app.state.executor = instalar_poco(_asyncio.get_running_loop())",
              "    app.state.executor = None",
              ["h"], "o lifespan deixa de instalar o poco"),
    "M-E-5": (BUFFER_PY,
              "    if not agendador_ligado():",
              "    if False:",
              ["f"], "start_buffer_scheduler ignora SCHEDULER_ENABLED"),
    "M-E-6": (BUFFER_PY,
              "            barrados=provedores_barrados, provedor_de=provedor_do_escopo)",
              "            )",
              ["i"], "a costura deixa de ser ligada em check_buffers"),
    "M-E-7": (BUFFER_PY,
              "                if getattr(job, \"next_run_time\", None) is not None:\n                    scheduler.pause_job(job.id)",
              "                pass",
              ["j"], "o agendador deixa de PAUSAR o que nao pode rodar"),
}


def _mutar(nome):
    arquivo, velho, novo, cenarios, descricao = MUTACOES[nome]
    backup = arquivo + ".backup_mutacao"
    fonte = io.open(arquivo, encoding="utf-8").read()
    if velho not in fonte:
        _p("[%s] ALVO NAO ENCONTRADO em %s — a mutacao precisa ser atualizada"
           % (nome, os.path.basename(arquivo)))
        return 1
    shutil.copyfile(arquivo, backup)
    try:
        io.open(arquivo, "w", encoding="utf-8").write(fonte.replace(velho, novo, 1))
        vermelhos = []
        for cen in cenarios:
            proc = subprocess.run([sys.executable, ESTE, "--so", cen], cwd=RAIZ,
                                  capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=900)
            vermelho = proc.returncode != 0
            vermelhos.append(vermelho)
            _p("[%s] %s -> cenario (%s): %s" % (
                nome, descricao, cen, "VERMELHO ✅" if vermelho else "VERDE ❌ (o guarda e carimbo)"))
            if not vermelho:
                _p((proc.stdout or "")[-1500:])
        return 0 if all(vermelhos) else 1
    finally:
        shutil.copyfile(backup, arquivo)     # 🔴 restaura por CÓPIA
        os.remove(backup)


def principal(argv):
    if "--mutar" in argv:
        pos = argv.index("--mutar")
        nomes = [argv[pos + 1]] if len(argv) > pos + 1 and not argv[pos + 1].startswith("--") \
            else sorted(MUTACOES)
        ruim = 0
        for nome in nomes:
            ruim += _mutar(nome)
        return 1 if ruim else 0

    escolhidos = list(CENARIOS)
    if "--so" in argv:
        escolhidos = [argv[argv.index("--so") + 1]]
    for nome in escolhidos:
        CENARIOS[nome]()
    _p("\n%s\nRESUMO: %d ok, %d falhas\n%s" % ("=" * 60, PASS, FAIL, "=" * 60))
    return 1 if FAIL else 0


def test_so_um_agendador_manda():
    """Ponte para o pytest — o mesmo caminho do script."""
    assert principal([]) == 0, "%d assercoes falharam" % FAIL


if __name__ == "__main__":
    sys.exit(principal(sys.argv[1:]))
