# -*- coding: utf-8 -*-
r"""O FIO · G1 · G2 · G3 · G4 · G5 · G7 · G10 — UMA CORRETORA NÃO TRAVA A OUTRA.
SPEC-EXTRA-001.8, FATIA 1 (medição · cota+rodízio · contrapressão · atraso de teste).

🔴 **O defeito, lido no código em 21/09/2026.** O varredor do buffer trata todas
as corretoras como uma só fila:

```
① o semáforo é GLOBAL e nasce DENTRO da varredura
   buffer_processor.py:77  semaforo = asyncio.Semaphore(limite)
   O job roda a cada 1 s com max_instances=10 -> o "teto de 6" real é até 60,
   e a conferência de prontidão (um GET, ~1 ms) espera atrás de turnos de LLM.
② a lista é uma só, na ordem arbitrária do SCAN: 50 chaves de uma corretora e
   1 de outra -> a de fora cai onde calhar.
③ e quem espera EXPIRA: `setex(chave, BUFFER_TTL_SECONDS=60, ...)`. Esperar a
   vez por mais de 60 s é o Redis apagando a mensagem do segurado, em silêncio.
```

O FIO que este arquivo atravessa — o mesmo caminho do produto, com dublê só nas
duas pontas (Redis em memória, e a borda onde estariam o LLM e o envio):

```
add_message (REAL)  ->  prontas/should_process (REAL)  ->  ordenar_em_rodizio (REAL)
   ->  cota por escopo + teto global (REAL)  ->  abrir_turno (REAL)
   ->  get_and_clear (REAL)  ->  [DUBLÊ: aqui estariam o modelo e o WhatsApp]
```

⛔ SEGURANÇA: zero rede, zero banco, zero Redis de verdade, zero LLM, zero
envio. Todo telefone e todo escopo deste arquivo são sintéticos, e nenhum nome
de corretora entra como constante (CLAUDE.md §13.9).

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_uma_corretora_nao_trava_a_outra.py
    ... --so G3   ·   ... --mutar   ·   ... --mutar M-18-1
    python -m pytest tests/test_uma_corretora_nao_trava_a_outra.py -q -p no:cacheprovider
"""
from __future__ import annotations

import ast
import asyncio
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from fnmatch import fnmatch

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

PASS = 0
FAIL = 0

#: ⛔ 100% SINTÉTICOS — nenhum nome, número ou id de corretora real (§13.9).
ESCOPO_A = "integ-corretora-a-0000-0000-0000"
ESCOPO_B = "integ-corretora-b-1111-1111-1111"
ESCOPO_C = "integ-corretora-c-2222-2222-2222"
TEL = "5511900000%03d"


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


# ===========================================================================
# O MOTOR — o serviço REAL importado, e o varredor RECORTADO DO FONTE
# ===========================================================================
#
# ⚠️ `import app.tasks.buffer_processor` arrasta `app.core.redis` e o APScheduler
# e 📊 custa ~97 s nesta máquina (medido em 21/09/2026:
# `python -c "import app.tasks.buffer_processor"`). O guarda vizinho
# (`test_midia_e_concorrencia_do_webhook.py:473`) já resolveu isso: recorta os
# nós reais da AST do MESMO arquivo em disco. Mutar o fonte muda o que este
# teste executa — é essa a garantia que importa (CLAUDE.md §9.4).
import app.services.message_buffer_service as M  # noqa: E402

NOMES_DO_VARREDOR = [
    "_PARALELISMO_PADRAO", "_PARALELISMO_COM_COTA_PADRAO", "_COTA_PADRAO",
    "_TURNO_TIMEOUT_PADRAO_S", "_MOTIVOS_DE_ESPERA", "_ADMISSAO", "_env_int",
    "_semaforo_global", "_tomar_cota", "_soltar_cota", "_colher_expiradas",
    "_adiar", "_renovar_vida", "ordenar_em_rodizio", "_atraso_de_teste_ms",
    "_fechar_a_conta", "processar_buffers_prontos",
    # 🔴 As pecas do CONSERTO UNICO (21/09/2026). Elas entram aqui e nao so no
    # guarda da costura porque sao alcancadas pelo caminho COMUM: o aviso de
    # consumo roda em toda conversa atendida, e a falha de teto roda em todo
    # turno cortado. Faltando no recorte, o defeito apareceria como `NameError`
    # dentro do teste — nunca dentro do produto, que e onde se descobriria tarde.
    "marcar_consumida", "_contar_timeout_no_breaker", "_sonda_do_meio_aberto",
    "_FOLGA_DE_INSTANCIAS",
]


class _LoggerMudo:
    def __getattr__(self, _nome):
        return lambda *a, **k: None


def carregar_varredor(nomes=None):
    """Os nós REAIS de `buffer_processor.py`, sem os imports de topo."""
    fonte = io.open(BUFFER_PY, encoding="utf-8").read()
    arvore = ast.parse(fonte)
    pedidos = list(nomes or NOMES_DO_VARREDOR)
    escolhidos = []
    achados = set()
    for no in arvore.body:
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and no.name in pedidos:
            escolhidos.append(no)
            achados.add(no.name)
        elif isinstance(no, (ast.Assign, ast.AnnAssign)):
            alvos = no.targets if isinstance(no, ast.Assign) else [no.target]
            for alvo in alvos:
                if isinstance(alvo, ast.Name) and alvo.id in pedidos:
                    escolhidos.append(no)
                    achados.add(alvo.id)
                    break
    faltando = sorted(set(pedidos) - achados)
    if faltando:
        raise AssertionError(
            "sumiram de buffer_processor.py: %s — se foram renomeados, "
            "o teste precisa saber" % faltando)
    modulo = ast.Module(body=escolhidos, type_ignores=[])
    ns = {"__name__": "buffer_processor_recortado",
          "asyncio": asyncio, "os": os, "logger": _LoggerMudo()}
    exec(compile(ast.fix_missing_locations(modulo), BUFFER_PY, "exec"), ns)  # noqa: S102
    return ns


# ===========================================================================
# O RELÓGIO DUBLADO — a espera real acontece em minutos; o teste, em ms
# ===========================================================================
RELOGIO = [datetime(2026, 9, 21, 9, 0, 0)]


class _DataHoraDublada:
    @staticmethod
    def now():
        return RELOGIO[0]

    @staticmethod
    def fromisoformat(texto):
        return datetime.fromisoformat(texto)


def _andar(segundos: float):
    RELOGIO[0] = RELOGIO[0] + timedelta(seconds=float(segundos))


# ===========================================================================
# O REDIS DUBLÊ — e ele HONRA TTL pelo relógio dublado.
# ⚠️ Sem TTL honrado, o guarda G7 não teria COMO ficar vermelho: `adiar` virando
#    `pass` não faria chave nenhuma sumir, e o guarda seria carimbo (§9.3).
# ===========================================================================
class _Pipe:
    def __init__(self, redis):
        self.redis = redis
        self.acoes = []

    def get(self, k):
        self.acoes.append(("get", k))

    def delete(self, k):
        self.acoes.append(("delete", k))

    async def execute(self):
        saida = []
        for acao, k in self.acoes:
            saida.append(await getattr(self.redis, acao)(k))
        return saida


class _RedisDuble:
    """Só o que o serviço REAL usa: get/set/setex/delete/mget/expire/ttl/scan/
    pipeline/eval/hset/hincrby. Nada mais — um dublê que aceita tudo esconde
    exatamente a chamada que faltava."""

    def __init__(self):
        self.dados = {}          # chave -> (valor, expira_em|None)
        self.hashes = {}         # chave -> {campo: valor}
        self.hash_expira = {}    # chave de HASH -> quando morre
        self.expires = 0         # quantos EXPIRE foram pedidos

    def _vivo(self, k):
        item = self.dados.get(k)
        if item is None:
            return None
        valor, expira = item
        if expira is not None and RELOGIO[0] >= expira:
            self.dados.pop(k, None)
            return None
        return valor

    async def get(self, k):
        return self._vivo(k)

    async def mget(self, chaves):
        return [self._vivo(k) for k in chaves]

    async def set(self, k, v, nx=False, ex=None):
        if nx and self._vivo(k) is not None:
            return None
        self.dados[k] = (v, RELOGIO[0] + timedelta(seconds=int(ex)) if ex else None)
        return True

    async def setex(self, k, ttl, v):
        self.dados[k] = (v, RELOGIO[0] + timedelta(seconds=int(ttl)))
        return True

    async def expire(self, k, ttl):
        # ⚠️ No Redis de verdade o EXPIRE vale para QUALQUER tipo de chave —
        # inclusive HASH. Um dublê que só soubesse expirar string deixaria o
        # contador sem prazo passar despercebido.
        self.expires += 1
        if k in self.hashes:
            self.hash_expira[k] = RELOGIO[0] + timedelta(seconds=int(ttl))
            return 1
        valor = self._vivo(k)
        if valor is None:
            return 0
        self.dados[k] = (valor, RELOGIO[0] + timedelta(seconds=int(ttl)))
        return 1

    async def ttl(self, k):
        if k in self.hashes:
            fim = self.hash_expira.get(k)
            return -1 if fim is None else int((fim - RELOGIO[0]).total_seconds())
        item = self.dados.get(k)
        if item is None or item[1] is None:
            return -2 if item is None else -1
        return int((item[1] - RELOGIO[0]).total_seconds())

    async def delete(self, k):
        return 1 if self.dados.pop(k, None) is not None else 0

    async def scan(self, cursor=0, match="*", count=100):
        vivas = [k for k in list(self.dados) if self._vivo(k) is not None]
        return 0, [k for k in vivas if fnmatch(k, match or "*")]

    async def hset(self, chave, mapping=None, **kw):
        alvo = self.hashes.setdefault(chave, {})
        alvo.update({str(a): str(b) for a, b in (mapping or {}).items()})
        return len(mapping or {})

    async def hincrby(self, chave, campo, quanto=1):
        alvo = self.hashes.setdefault(chave, {})
        novo = int(alvo.get(campo, 0)) + int(quanto)
        alvo[campo] = str(novo)
        return novo

    async def eval(self, script, numkeys, *args):
        chave, token = args[0], args[1]
        atual = self._vivo(chave)
        if script == M.LUA_LIBERA_SE_FOR_MEU:
            if atual == token:
                self.dados.pop(chave, None)
                return 1
            return 0
        if script == M.LUA_RENOVA_SE_FOR_MEU:
            if atual == token:
                valor, _ = self.dados[chave]
                self.dados[chave] = (valor,
                                     RELOGIO[0] + timedelta(seconds=int(args[2])))
                return 1
            return 0
        raise AssertionError("script Lua desconhecido no dublê: %r" % script[:80])

    def pipeline(self):
        return _Pipe(self)


def servico_novo():
    M.datetime = _DataHoraDublada
    return M.MessageBufferService(_RedisDuble())


async def _semear(s, escopo, quantas, texto="bateu meu carro", inicio=0):
    """`add_message` REAL — é o mesmo caminho que o webhook usa."""
    chaves = []
    for n in range(inicio, inicio + quantas):
        tel = TEL % n
        await s.add_message(tel, texto, "pending", "pending", {},
                            {"_integration_id": escopo}, escopo=escopo)
        chaves.append(s.chave(escopo, tel))
    return chaves


def escopo_do_turno(payload_dict=None, **extras):
    """De quem é a conversa que chegou à BORDA. ⚠️ Sai do `_integration_id` que
    o `add_message` REAL gravou no payload — e não de um campo que o teste
    inventa, que é o que o dublê do guarda vizinho faz (`_chave`)."""
    return str((payload_dict or {}).get("_integration_id") or "")


def _zerar_admissao(bp):
    """O estado de admissão é DO PROCESSO (D1) — entre cenários ele volta a zero."""
    est = bp["_ADMISSAO"]
    est["em_voo_por_escopo"].clear()
    est["aguardando"].clear()
    # ⚠️ `servidas` FOI APOSENTADO no conserto unico de 21/09/2026 (era ele que
    # transformava conversa respondida em "mensagem perdida"); a chamada fica
    # tolerante para que scripts externos que ainda a citem continuem rodando.
    est.get("servidas", {}).clear()
    est["motivo_da_chave"].clear()
    est["esperando_desde"].clear()
    est["semaforos"].clear()
    est["em_voo_global"] = 0
    est["pico_por_escopo"].clear()
    est["pico_global"] = 0


# ===========================================================================
# O TESTE DO FIO — a corretora sadia não espera atrás da doente,
#                  e o buffer de quem espera NÃO expira
# ===========================================================================
def fio():
    _p("\n[FIO] add_message REAL -> varredura REAL -> dublê só na borda do envio")
    bp = carregar_varredor()
    _zerar_admissao(bp)
    RELOGIO[0] = datetime(2026, 9, 21, 9, 0, 0)

    entregues = []

    async def cenario():
        s = servico_novo()
        # A corretora DOENTE despeja uma rajada; a SADIA tem uma conversa só.
        await _semear(s, ESCOPO_A, 40)
        await _semear(s, ESCOPO_B, 1, inicio=900)
        _andar(30)                      # todas passaram do teto de 25 s: prontas

        marco = [0.0]

        async def borda(payload_dict=None, combined_message=None,
                        buffered_messages=None, **extras):
            # ⛔ É AQUI que estariam o LLM e o `send_message`. Nada sai.
            escopo = escopo_do_turno(payload_dict, **extras)
            entregues.append((escopo, time.perf_counter() - marco[0]))
            await asyncio.sleep(0.05 if escopo == ESCOPO_A else 0.0)

        _cursor, chaves = await s.redis.scan(match="whatsapp_buffer:*")
        marco[0] = time.perf_counter()
        resumo = await bp["processar_buffers_prontos"](
            chaves, s, borda, paralelismo=6, cota_por_corretora=4)
        primeira_varredura = list(entregues)

        # ... e agora o relógio anda 90 s — MAIS que o TTL de 60 s do buffer —
        # com a varredura de 1 s acontecendo no meio, como acontece de verdade.
        for _volta in range(3):
            _andar(30)
            _cursor, ainda = await s.redis.scan(match="whatsapp_buffer:*")
            await bp["processar_buffers_prontos"](
                ainda, s, borda, paralelismo=6, cota_por_corretora=4)
        _cursor, sobraram = await s.redis.scan(match="whatsapp_buffer:*")
        contadores = dict(s.redis.hashes)
        ttls = {k: await s.redis.ttl(k) for k in contadores}
        return resumo, sobraram, primeira_varredura, contadores, ttls

    resumo, sobraram, primeira, contadores, ttls = asyncio.run(cenario())

    da_sadia = [t for e, t in primeira if e == ESCOPO_B]
    da_doente = [t for e, t in primeira if e == ESCOPO_A]
    espera_sadia = da_sadia[0] if da_sadia else float("inf")
    _p("      📊 a conversa da SADIA foi atendida em %.4f s do início da varredura"
       % espera_sadia)

    check("a conversa da corretora SADIA foi atendida nesta varredura",
          len(da_sadia) == 1,
          "entregues=%d, da sadia=%d" % (len(primeira), len(da_sadia)))
    check("🔴 e foi atendida na PRIMEIRA leva (< 0,05 s), não atrás da rajada",
          espera_sadia < 0.05,
          "esperou %.4f s — hoje a lista é uma só, na ordem do SCAN: a chave "
          "da outra corretora cai onde calhar, atrás de até 6 turnos de LLM"
          % espera_sadia)
    check("a corretora DOENTE não levou mais que a cota (4) nesta varredura",
          len(da_doente) <= 4, "levou %d de 40" % len(da_doente))
    check("o resumo traz a conta inteira (vistas/prontas/adiadas/expiradas)",
          all(k in resumo for k in ("vistas", "prontas", "processadas",
                                    "adiadas", "falhas", "timeouts", "expiradas")),
          repr(resumo))
    check("e as que esperaram foram ADIADAS, não perdidas",
          isinstance(resumo.get("adiadas"), dict)
          and resumo["adiadas"].get("cota", 0) >= 30, repr(resumo))
    check("🔴 90 s de relógio depois, o buffer de quem esperou CONTINUA no Redis",
          len(sobraram) >= 20,
          "sobraram %d — sem `adiar`, o `setex` de 60 s apaga a rajada do "
          "segurado e ninguém fica sabendo" % len(sobraram))

    # ------------------------------------------------------------------ #
    # O CONTRATO QUE A CENTRAL DE AGENTES VAI LER (§10) — outra fatia consome
    # ------------------------------------------------------------------ #
    chave_a = M.MessageBufferService.chave_dos_contadores(ESCOPO_A)
    hash_a = contadores.get(chave_a, {})
    check("existe um contador por corretora, no padrão `isolamento_escopo:{id}`",
          chave_a in contadores,
          "chaves gravadas: %s" % sorted(contadores)[:3])
    check("e ele traz os campos do contrato",
          all(campo in hash_a for campo in
              ("em_execucao", "em_espera", "ultimo_motivo",
               "ultimo_motivo_em", "atualizado_em")),
          "veio %s" % sorted(hash_a))
    check("o último motivo de espera é uma palavra do vocabulário fechado",
          hash_a.get("ultimo_motivo") in ("cota", "turno", "breaker",
                                          "sem_escopo"),
          "veio %r" % hash_a.get("ultimo_motivo"))
    check("e o contador tem TTL — contador sem prazo vira lixo no Redis",
          0 < ttls.get(chave_a, -1) <= 24 * 3600,
          "ttl = %r" % ttls.get(chave_a))
    check("⛔ e nenhum telefone entrou no contador (a chave é do ESCOPO)",
          all("5511" not in k for k in contadores),
          "%s" % sorted(contadores)[:2])


# ===========================================================================
# G1 — `prontas()` e `should_process()` são a MESMA régua
# ===========================================================================
def g1():
    _p("\n[G1] A régua de prontidão é UMA: `prontas()` == `should_process()`")

    async def cenario():
        s = servico_novo()
        chaves = []
        # 24 buffers variados: v2 (itens) e v1 (messages), cada tipo de janela,
        # ociosidades dos dois lados de cada fronteira (3 s, 8 s, 18 s, teto 25 s).
        combos = [
            ("sim", 1.0), ("sim", 4.0),                       # dado curto: 3 s
            ("ABC1D23", 2.0), ("ABC1D23", 3.5),
            ("bateu meu carro", 5.0), ("bateu meu carro", 9.0),   # completa: 8 s
            ("SOCORRO", 7.9), ("SOCORRO", 8.1),
            ("o carro parou na", 9.0), ("o carro parou na", 19.0),  # conectivo: 18 s
            ("eu estava indo e", 17.0), ("eu estava indo e", 18.5),
            ("preciso de ajuda com o carro.", 0.0),
            ("preciso de ajuda com o carro.", 30.0),
        ]
        for pos, (texto, ocioso) in enumerate(combos):
            escopo = ESCOPO_A if pos % 2 else ESCOPO_B
            tel = TEL % (100 + pos)
            await s.add_message(tel, texto, "pending", "pending", {},
                                {"_integration_id": escopo}, escopo=escopo)
            chave = s.chave(escopo, tel)
            await _envelhecer(s, chave, ocioso_s=ocioso, idade_s=ocioso + 1.0)
            chaves.append(chave)

        # buffers no formato V1 (`messages`) — ainda existem no Redis por até
        # 60 s depois de um deploy, e a régua tem de valer para eles também.
        for pos, ocioso in enumerate((1.0, 9.0, 4.0, 20.0, 26.0)):
            tel = TEL % (200 + pos)
            chave = s.chave(ESCOPO_C, tel)
            agora = RELOGIO[0]
            await s.redis.setex(chave, 60, json.dumps({
                "messages": ["bateu meu carro"],
                "first_at": (agora - timedelta(seconds=ocioso + 1.0)).isoformat(),
                "last_at": (agora - timedelta(seconds=ocioso)).isoformat(),
                "company_id": "pending", "user_id": "pending",
                "integration": {}, "payload": {"_integration_id": ESCOPO_C},
            }))
            chaves.append(chave)

        # e um buffer que atravessa o TETO de 25 s desde a primeira mensagem
        for pos, (ocioso, idade) in enumerate(((1.0, 26.0), (2.0, 40.0),
                                               (1.0, 10.0), (0.5, 24.0),
                                               (6.0, 6.5))):
            tel = TEL % (300 + pos)
            await s.add_message(tel, "e depois", "pending", "pending", {},
                                {"_integration_id": ESCOPO_A}, escopo=ESCOPO_A)
            chave = s.chave(ESCOPO_A, tel)
            await _envelhecer(s, chave, ocioso_s=ocioso, idade_s=idade)
            chaves.append(chave)

        em_lote = await s.prontas(chaves)
        uma_a_uma = []
        for c in chaves:
            if await s.should_process(c):
                uma_a_uma.append(c)
        idades = {}
        for c in chaves:
            bruto = await s.redis.get(c)
            if bruto:
                idades[c] = json.loads(bruto)["first_at"]
        return chaves, em_lote, uma_a_uma, idades

    chaves, em_lote, uma_a_uma, idades = asyncio.run(cenario())
    check("são pelo menos 20 buffers variados (v1 e v2)", len(chaves) >= 20,
          "%d" % len(chaves))
    check("e as duas medidas CONSEGUEM ser diferentes (nem tudo está pronto)",
          0 < len(uma_a_uma) < len(chaves),
          "prontas=%d de %d — se fossem todas, o guarda não guardaria nada"
          % (len(uma_a_uma), len(chaves)))
    check("🔴 `prontas()` devolve EXATAMENTE o mesmo conjunto que `should_process()`",
          set(em_lote) == set(uma_a_uma),
          "só no lote: %s | só uma a uma: %s"
          % (sorted(set(em_lote) - set(uma_a_uma))[:3],
             sorted(set(uma_a_uma) - set(em_lote))[:3]))
    saida = [idades[c] for c in em_lote if c in idades]
    check("e devolve da mais ANTIGA para a mais nova (FIFO dentro do escopo)",
          saida == sorted(saida),
          "sem ordem, a ordem é a do SCAN — ordem de slot — e uma conversa "
          "velha da mesma corretora pode passar fome")
    entrada = [idades[c] for c in chaves if c in idades and c in set(em_lote)]
    check("CONTROLE: a ordem de ENTRADA não estava ordenada por idade",
          entrada != sorted(entrada),
          "se já entrasse ordenada, a asserção acima não conseguiria falhar")


async def _envelhecer(s, chave, *, ocioso_s, idade_s):
    """Reescreve SÓ os carimbos do buffer no dublê. ⚠️ É DADO, não motor: quem
    decide continua sendo `_esta_pronta`."""
    bruto = await s.redis.get(chave)
    dados = json.loads(bruto)
    agora = RELOGIO[0]
    dados["last_at"] = (agora - timedelta(seconds=float(ocioso_s))).isoformat()
    dados["first_at"] = (agora - timedelta(seconds=float(idade_s))).isoformat()
    await s.redis.setex(chave, 60, json.dumps(dados))


# ===========================================================================
# G2 — o rodízio intercala, e é o MESMO em toda execução
# ===========================================================================
def g2():
    _p("\n[G2] `ordenar_em_rodizio` intercala as corretoras e é determinística")
    bp = carregar_varredor()
    ordenar = bp["ordenar_em_rodizio"]

    chaves = ([M.MessageBufferService.chave(ESCOPO_A, TEL % n) for n in range(5)]
              + [M.MessageBufferService.chave(ESCOPO_B, TEL % (10 + n)) for n in range(3)]
              + [M.MessageBufferService.chave(ESCOPO_C, TEL % (20 + n)) for n in range(2)])

    saida = ordenar(list(chaves))
    escopos = [M.escopo_da_chave(c) for c in saida]

    check("nada se perde e nada se duplica no rodízio",
          sorted(saida) == sorted(chaves),
          "entrou %d, saiu %d" % (len(chaves), len(saida)))
    check("🔴 as três primeiras são de TRÊS corretoras diferentes",
          len(set(escopos[:3])) == 3,
          "veio %s — na ordem do SCAN, 5 chaves de uma corretora vêm antes "
          "de qualquer outra" % escopos[:3])
    check("e a intercalação continua: as 6 primeiras são 2 de cada",
          sorted(escopos[:6]) == sorted([ESCOPO_A, ESCOPO_B, ESCOPO_C] * 2),
          "%s" % escopos[:6])

    dentro_a = [c for c in saida if M.escopo_da_chave(c) == ESCOPO_A]
    check("dentro da corretora, a ordem RECEBIDA é preservada (FIFO)",
          dentro_a == [c for c in chaves if M.escopo_da_chave(c) == ESCOPO_A],
          "%s" % dentro_a[:3])
    check("e o rodízio é DETERMINÍSTICO: 5 execuções, 1 resultado",
          len({tuple(ordenar(list(chaves))) for _ in range(5)}) == 1,
          "sem determinismo este guarda não consegue afirmar nada")

    # CONTROLE: a ordem de ENTRADA (a do SCAN) NÃO é intercalada. Sem esta
    # linha, um `return chaves` cru passaria nas asserções acima por acaso.
    escopos_crus = [M.escopo_da_chave(c) for c in chaves]
    check("CONTROLE: a ordem do SCAN não intercala (as 3 primeiras são a MESMA)",
          len(set(escopos_crus[:3])) == 1,
          "as duas medidas precisam CONSEGUIR ser diferentes (CLAUDE.md §9.2)")


# ===========================================================================
# G3 — 🔴 O OUTCOME: a corretora doente não muda a latência da sadia
# ===========================================================================
#
# 🔴 **O PISO DO X SAIU DE MEDIÇÃO, NÃO DE PALPITE.**
#
# 📊 21/09/2026, nesta máquina, com o comando abaixo:
#   · p95 da sadia SOZINHA (lote A) .............. 0,0010 s
#   · p95 da sadia SOZINHA (lote B, controle) .... 0,0010 s   -> ruído: 0,0000 s
#   · p95 da sadia COM a doente .................. 0,0298 s
#   · p95 da sadia COM a doente e SEM cota ....... 2,4752 s
#
# ⚠️ Os 29 ms que sobram no cenário COM cota **não são fila**: é o custo de a
# varredura OLHAR 54 chaves em vez de 4 (o `MGET`, o rodízio e os 46
# adiamentos). O que o outcome proíbe é a sadia ESPERAR o turno da doente — e
# um turno da doente custa 300 ms neste cenário, 10x o piso. Com a cota
# desligada a mesma medida vai a 2,47 s: o guarda tem 80x de margem para
# distinguir as duas coisas.
#
# 🔴 **E O PISO FOI RECALIBRADO EM 21/09/2026, POR MEDIÇÃO — NÃO AFROUXADO.**
#
# 📊 O guarda PISCAVA no relógio do Windows: numa bateria completa deu VERMELHO
# com `0,0529 <= 0,0511` (p95 com a doente = 0,0529 s contra um X de 0,050 s),
# e isolado deu 5/5 verde entre 0,022 e 0,040 s. Um gate que pisca custa uma
# triagem por SPEC e ensina a ignorá-lo (CLAUDE.md §9.3).
#
# A CONTA do piso novo, com os três números medidos:
#
#     custo de OLHAR 54 chaves (o que sobra com a cota) .. 0,024 a 0,053 s
#     piso do X ........................................ 0,120 s   (2,3x o pior)
#     um TURNO da corretora doente ..................... 0,600 s   (5x o piso)
#     a MESMA rodada com a cota DESLIGADA (controle) ... ~5 s      (40x o piso)
#
# ⛔ O piso subiu e o turno da doente subiu JUNTO, para a razão
# `piso x 4 <= turno` continuar valendo: calibrar ruído de relógio é mexer no
# piso do ruído, nunca na distância entre "olhar" e "esperar". A linha de
# controle (cota desligada) continua tendo de ficar VERMELHA.
PISO_DO_X_S = 0.120
_TURNO_DA_DOENTE_S = 0.60


def _p95(amostras):
    ordenado = sorted(amostras)
    if not ordenado:
        return 0.0
    # rank mais próximo, como a §5.4 pede: nada de interpolação escondida
    pos = int(round(0.95 * (len(ordenado) - 1)))
    return ordenado[pos]


async def _uma_rodada_g3(bp, *, com_doente, cota, paralelismo,
                         lento_s=0.60, rapido_s=0.002):
    """A varredura 1 satura (ou não) com a corretora DOENTE e FICA EM VOO; o que
    se mede é quanto o SEGURADO da corretora sadia espera até o motor chegar
    nele — atravessando quantas varreduras forem precisas, que é como o
    agendador de 1 s com `max_instances=10` realmente se comporta."""
    _zerar_admissao(bp)
    RELOGIO[0] = datetime(2026, 9, 21, 9, 0, 0)
    s = servico_novo()
    marco = [0.0]
    esperas = []

    async def borda(payload_dict=None, combined_message=None,
                    buffered_messages=None, **extras):
        escopo = escopo_do_turno(payload_dict, **extras)
        if escopo == ESCOPO_B:
            esperas.append(time.perf_counter() - marco[0])
            await asyncio.sleep(rapido_s)
            return
        await asyncio.sleep(lento_s)

    if com_doente:
        await _semear(s, ESCOPO_A, 50)
        _andar(30)
        _cursor, primeiras = await s.redis.scan(match="whatsapp_buffer:*")
        tarefa1 = asyncio.create_task(bp["processar_buffers_prontos"](
            primeiras, s, borda, paralelismo=paralelismo,
            cota_por_corretora=cota))
        await asyncio.sleep(0.015)      # a varredura 1 já tomou os slots dela
    else:
        tarefa1 = None

    # ... e SÓ AGORA o segurado da outra corretora manda mensagem.
    await _semear(s, ESCOPO_B, 4, inicio=900)
    _andar(30)

    marco[0] = time.perf_counter()
    # o agendador de 1 s, em escala de teste: varre até a sadia ser atendida
    for _volta in range(60):
        _cursor, agora = await s.redis.scan(match="whatsapp_buffer:*")
        resumo = await bp["processar_buffers_prontos"](
            agora, s, borda, paralelismo=paralelismo, cota_por_corretora=cota)
        if len(esperas) >= 4:
            break
        await asyncio.sleep(0.01)
    gasto = max(esperas) if len(esperas) >= 4 else float("inf")
    if tarefa1 is not None:
        await tarefa1
    return gasto, resumo


def _lote_g3(bp, *, com_doente, cota, paralelismo, n=15):
    amostras = []
    for _ in range(n):
        gasto, resumo = asyncio.run(_uma_rodada_g3(
            bp, com_doente=com_doente, cota=cota, paralelismo=paralelismo))
        amostras.append(gasto)
    return amostras


def g3():
    _p("\n[G3] 50 chaves da corretora DOENTE + 4 da SADIA: as 4 não esperam")
    bp = carregar_varredor()
    cota = 4
    paralelismo = 6

    sozinha_a = _lote_g3(bp, com_doente=False, cota=cota, paralelismo=paralelismo)
    sozinha_b = _lote_g3(bp, com_doente=False, cota=cota, paralelismo=paralelismo)
    com_doente = _lote_g3(bp, com_doente=True, cota=cota, paralelismo=paralelismo)

    p95_sozinha = _p95(sozinha_a)
    p95_controle_b = _p95(sozinha_b)
    p95_com = _p95(com_doente)
    ruido = abs(p95_sozinha - p95_controle_b)
    x = max(PISO_DO_X_S, p95_sozinha * 0.25)

    _p("      📊 p95 sadia SOZINHA .......... %.4f s  (lote A, n=%d)"
       % (p95_sozinha, len(sozinha_a)))
    _p("      📊 p95 sadia SOZINHA (lote B).. %.4f s   <- LINHA DE CONTROLE"
       % p95_controle_b)
    _p("      📊 ruído entre os dois lotes .. %.4f s  (piso do X: %.4f s)"
       % (ruido, PISO_DO_X_S))
    _p("      📊 p95 sadia COM a doente ..... %.4f s" % p95_com)
    _p("      📊 X = max(piso, p95_sozinha x 0,25) = %.4f s" % x)
    _p("      comando: PYTHONIOENCODING=utf-8 python tests/"
       "test_uma_corretora_nao_trava_a_outra.py --so G3")

    check("a LINHA DE CONTROLE é estável (o ruído cabe no piso do X)",
          ruido <= PISO_DO_X_S,
          "ruído %.4f s > piso %.4f s — a máquina está barulhenta demais para "
          "esta medida valer" % (ruido, PISO_DO_X_S))
    check("o piso do X fica MUITO abaixo de um turno da doente (%.3f << %.3f)"
          % (PISO_DO_X_S, _TURNO_DA_DOENTE_S),
          PISO_DO_X_S * 4 <= _TURNO_DA_DOENTE_S,
          "um piso da ordem do turno da doente deixaria a espera passar "
          "despercebida — o guarda viraria carimbo")
    check("🔴 p95 da SADIA com a doente <= p95 sozinha + X (%.4f <= %.4f)"
          % (p95_com, p95_sozinha + x),
          p95_com <= p95_sozinha + x,
          "a corretora sadia está esperando atrás da doente")

    # E o cenário TEM de conseguir ficar vermelho: sem cota, a doente ocupa os
    # 6 slots globais e a sadia espera um turno inteiro dela.
    sem_cota = _lote_g3(bp, com_doente=True, cota=10_000, paralelismo=paralelismo, n=5)
    p95_sem_cota = _p95(sem_cota)
    _p("      📊 CONTROLE (cota=10.000) ..... %.4f s" % p95_sem_cota)
    check("CONTROLE: com a cota desligada a MESMA rodada estoura o X",
          p95_sem_cota > p95_sozinha + x,
          "deu %.4f s — se não estourasse, a cota não seria o mérito "
          "(CLAUDE.md §9.2)" % p95_sem_cota)


# ===========================================================================
# G4 — a COTA é tomada ANTES do teto global
# ===========================================================================
def g4():
    _p("\n[G4] A cota da corretora vem ANTES do teto do processo")
    bp = carregar_varredor()

    async def cenario():
        _zerar_admissao(bp)
        RELOGIO[0] = datetime(2026, 9, 21, 9, 0, 0)
        s = servico_novo()
        chaves = await _semear(s, ESCOPO_A, 6)
        _andar(30)

        async def borda(**kw):
            await asyncio.sleep(0.02)

        resumo = await bp["processar_buffers_prontos"](
            chaves, s, borda, paralelismo=1, cota_por_corretora=4)
        est = bp["_ADMISSAO"]
        return resumo, est["pico_por_escopo"].get(ESCOPO_A, 0), est["pico_global"]

    resumo, pico_escopo, pico_global = asyncio.run(cenario())

    check("o teto global de 1 foi respeitado (contador de ocupação GLOBAL)",
          pico_global == 1, "pico global = %d" % pico_global)
    check("🔴 e a cota já estava TOMADA por 4 enquanto só 1 rodava",
          pico_escopo == 4,
          "pico do escopo = %d — se a ordem estivesse invertida, ninguém "
          "seguraria cota enquanto espera o teto global" % pico_escopo)
    check("as duas conseguem ser diferentes (4 != 1)", pico_escopo != pico_global)
    check("🔴 e 2 chaves foram ADIADAS POR COTA, não processadas",
          resumo["adiadas"]["cota"] == 2,
          "adiadas=%r — com a ordem INVERTIDA o teto global de 1 serializa "
          "tudo e a cota nunca enche: adiadas['cota'] cai para 0"
          % (resumo["adiadas"],))
    check("e as 4 admitidas foram processadas", resumo["processadas"] == 4,
          repr(resumo))


# ===========================================================================
# D1 — duas varreduras SOBREPOSTAS somam no MESMO estado
# ===========================================================================
def d1():
    _p("\n[D1] Duas varreduras sobrepostas: a soma em voo do escopo respeita a cota")
    bp = carregar_varredor()
    em_voo = {"agora": 0, "pico": 0}

    async def cenario():
        _zerar_admissao(bp)
        RELOGIO[0] = datetime(2026, 9, 21, 9, 0, 0)
        s = servico_novo()
        await _semear(s, ESCOPO_A, 20)
        _andar(30)

        async def borda(**kw):
            em_voo["agora"] += 1
            em_voo["pico"] = max(em_voo["pico"], em_voo["agora"])
            await asyncio.sleep(0.05)
            em_voo["agora"] -= 1

        _c, chaves = await s.redis.scan(match="whatsapp_buffer:*")
        t1 = asyncio.create_task(bp["processar_buffers_prontos"](
            chaves, s, borda, paralelismo=24, cota_por_corretora=4))
        await asyncio.sleep(0.005)
        _c, chaves2 = await s.redis.scan(match="whatsapp_buffer:*")
        t2 = asyncio.create_task(bp["processar_buffers_prontos"](
            chaves2, s, borda, paralelismo=24, cota_por_corretora=4))
        r1, r2 = await asyncio.gather(t1, t2)
        return r1, r2

    r1, r2 = asyncio.run(cenario())
    check("🔴 a soma EM VOO da corretora nunca passou da cota (4)",
          em_voo["pico"] <= 4,
          "pico = %d — cada varredura criando o próprio estado transforma "
          "cota 4 em cota 4xN (hoje o `Semaphore(6)` vira até 60)"
          % em_voo["pico"])
    check("e o cenário conseguiu sobrepor as duas varreduras (pico > 1)",
          em_voo["pico"] > 1,
          "pico=%d — sem sobreposição real o guarda não guarda nada"
          % em_voo["pico"])
    check("as duas varreduras devolveram a conta", "adiadas" in r1 and "adiadas" in r2)


# ===========================================================================
# G7 — 🔴 `expiradas == 0` e a conta fecha
# ===========================================================================
def g7():
    _p("\n[G7] 200 chaves, cota 4, turnos de 2 s: nenhuma mensagem se perde")
    bp = carregar_varredor()

    async def cenario():
        _zerar_admissao(bp)
        RELOGIO[0] = datetime(2026, 9, 21, 9, 0, 0)
        s = servico_novo()
        await _semear(s, ESCOPO_A, 200)
        _andar(30)

        async def borda(**kw):
            await asyncio.sleep(0)      # o custo REAL está no relógio dublado

        total = {"processadas": 0, "expiradas": 0, "adiadas": 0, "desbalanceadas": 0}
        for _rodada in range(70):
            _c, chaves = await s.redis.scan(match="whatsapp_buffer:*")
            # ⛔ NÃO parar quando o SCAN volta vazio: foi assim que a mutação
            # M-18-7 ficou VERDE na primeira tentativa. Com `adiar` desligado a
            # fila inteira expira de uma vez, o SCAN volta vazio, a varredura é
            # pulada e a colheita de `expiradas` nunca roda — a perda TOTAL era
            # a única que ninguém veria. O produto tinha o mesmo `if chaves:`
            # em `check_buffers`, e ele saiu de lá pelo mesmo motivo.
            r = await bp["processar_buffers_prontos"](
                chaves, s, borda, paralelismo=24, cota_por_corretora=4)
            total["processadas"] += r["processadas"]
            total["expiradas"] += r["expiradas"]
            total["adiadas"] += sum(r["adiadas"].values())
            saida = (r["processadas"] + r["falhas"] + r["timeouts"]
                     + sum(r["adiadas"].values()) + r["expiradas"])
            if saida != r["prontas"]:
                total["desbalanceadas"] += 1
            # 📊 O turno do chat custa p95 107 s em produção (medido 21/09); aqui
            # 2 s por rodada de relógio DUBLADO basta para atravessar o TTL de
            # 60 s do buffer — é o que o guarda precisa poder ver.
            _andar(2.0)
        return total, s

    total, _s = asyncio.run(cenario())
    check("🔴 `expiradas` == 0 — nenhuma mensagem de segurado sumiu",
          total["expiradas"] == 0,
          "%d chave(s) sumiram esperando a vez. Sem `adiar`, o TTL de 60 s "
          "apaga quem está na fila há mais de um minuto" % total["expiradas"])
    check("as 200 conversas foram processadas", total["processadas"] == 200,
          "processadas=%d" % total["processadas"])
    check("e a conta FECHA em toda varredura (entrada = saída + retidas)",
          total["desbalanceadas"] == 0,
          "%d varredura(s) não fecharam" % total["desbalanceadas"])
    check("e houve espera de verdade (senão não haveria o que perder)",
          total["adiadas"] > 1000, "adiadas=%d" % total["adiadas"])


# ===========================================================================
# G10 — o atraso de teste é ZERO por padrão, para QUALQUER id
# ===========================================================================
def g10():
    _p("\n[G10] O atraso injetado nasce DESLIGADO — fail-closed")
    bp = carregar_varredor()
    atraso = bp["_atraso_de_teste_ms"]

    guardados = {k: os.environ.get(k)
                 for k in ("ISOLAMENTO_ATRASO_ALLOWLIST", "ISOLAMENTO_ATRASO_MS")}
    try:
        os.environ.pop("ISOLAMENTO_ATRASO_ALLOWLIST", None)
        os.environ["ISOLAMENTO_ATRASO_MS"] = "5000"
        for alvo in (ESCOPO_A, ESCOPO_B, "", "qualquer-coisa", "*", "all"):
            check("sem allowlist, `%s` não dorme" % (alvo or "<vazio>"),
                  atraso(alvo) == 0,
                  "devolveu %d ms — em produção a variável fica vazia e ESTE "
                  "é o guarda que impede o mecanismo de virar defeito"
                  % atraso(alvo))

        os.environ["ISOLAMENTO_ATRASO_ALLOWLIST"] = "  , %s ,  " % ESCOPO_A
        check("com o id EXATO na allowlist, o atraso vale",
              atraso(ESCOPO_A) == 5000, "deu %d" % atraso(ESCOPO_A))
        check("e só para ele — o vizinho continua em zero",
              atraso(ESCOPO_B) == 0, "deu %d" % atraso(ESCOPO_B))
        check("prefixo não conta: a lista é de ids EXATOS",
              atraso(ESCOPO_A[:10]) == 0 and atraso(ESCOPO_A + "x") == 0)
        check("e o vazio nunca entra, nem com vírgulas soltas na lista",
              atraso("") == 0)
    finally:
        for k, v in guardados.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v



# ===========================================================================
# G11 — 🔴 A CONTA DE `expiradas` TEM DONO, E SÓ CONTA PERDA DE VERDADE
# ===========================================================================
#
# 📊 O DEFEITO, reproduzido em 21/09/2026 com o motor REAL
# (`python %TEMP%\laudos-0018\redteam\atk1b_cai_na_tela_da_outra.py`):
#
#     conversas respondidas: 3 de 3 (A,A,B) — NENHUMA perdida
#     expiradas por varredura: [0, 0, 0, 1]
#     TELA Central -> corretora-A | expiradas_acumuladas = 0
#     TELA Central -> corretora-B | expiradas_acumuladas = 1   <- a perda FALSA
#                                                                 de A, na tela de B
#
# Três defeitos na MESMA conta, e nenhum deles precisa de carga anormal — basta
# uma varredura com duas conversas de durações DIFERENTES, que é o regime normal
# (varredura de 1 s, turno de 10 a 100 s):
#
#   (a) `servidas` era limpo por QUALQUER varredura sobreposta e lido pela dona
#       só no fim: conversa RESPONDIDA virava "expirada" duas varreduras depois;
#   (b) `expiradas`/`timeouts` eram totais GLOBAIS gravados no hash de TODO
#       escopo ativo: a perda de uma corretora aparecia na tela da outra;
#   (c) turno cortado/falho era contado DUAS vezes (timeout e, depois, expirada).
#
# ⛔ E O GUARDA PRECISA DO CASO POSITIVO. Sem ele, um contador que nunca mais
# contasse nada ficaria verde — e o número que o Founder olha todo dia teria
# virado um zero permanente. Carimbo, não guarda (CLAUDE.md §9.3).
class _LoggerQueAnota:
    """Um logger que GUARDA o que foi dito — sem PII, é só texto de log."""

    def __init__(self):
        self.linhas = []

    def _anota(self, nivel):
        def _fn(msg, *args, **kw):
            try:
                self.linhas.append((nivel, str(msg) % args if args else str(msg)))
            except Exception:  # noqa: BLE001
                self.linhas.append((nivel, str(msg)))
        return _fn

    def __getattr__(self, nome):
        return self._anota(nome)


def _hash_de(s, escopo):
    return dict(s.redis.hashes.get(
        M.MessageBufferService.chave_dos_contadores(escopo)) or {})


def g11():
    _p("\n[G11] A conta de perdas: duracoes DESIGUAIS, varreduras SOBREPOSTAS, "
       "duas corretoras")
    bp = carregar_varredor()

    # ------------------------------------------------------------------ #
    # (a)+(b) A CORRIDA — e a segunda corretora em voo
    # ------------------------------------------------------------------ #
    async def corrida():
        _zerar_admissao(bp)
        RELOGIO[0] = datetime(2026, 9, 21, 9, 0, 0)
        s = servico_novo()
        await _semear(s, ESCOPO_A, 2)
        await _semear(s, ESCOPO_B, 1, inicio=70)
        _andar(30)
        entregues = []

        async def borda(payload_dict=None, **kw):
            escopo = escopo_do_turno(payload_dict)
            i = len(entregues)
            entregues.append(escopo)
            # 🔴 DURACOES DESIGUAIS, e a corretora B com o turno mais LONGO de
            # todos: e' ela que continua em voo na terceira varredura, e e' por
            # isso que a perda FALSA da corretora A caia na tela DELA.
            if escopo == ESCOPO_B:
                await asyncio.sleep(0.6)
            else:
                await asyncio.sleep(0.10 if i == 0 else 0.05)

        async def varrer(atraso):
            await asyncio.sleep(atraso)
            _c, chaves = await s.redis.scan(match="whatsapp_buffer:*")
            # ⚠️ COTA 1: e' o que faz a segunda conversa da corretora A ser
            # ADIADA na primeira varredura e SERVIDA por uma varredura
            # SOBREPOSTA depois — a corrida exata do defeito.
            return await bp["processar_buffers_prontos"](
                list(chaves), s, borda, cota_por_corretora=1)

        resumos = await asyncio.gather(varrer(0), varrer(0.2), varrer(0.35),
                                       varrer(0.5))
        contas = [r["expiradas"] for r in resumos if isinstance(r, dict)]
        return entregues, contas, _hash_de(s, ESCOPO_A), _hash_de(s, ESCOPO_B)

    entregues, contas, hash_a, hash_b = asyncio.run(corrida())
    _p("      📊 conversas respondidas: %d de 3 | expiradas por varredura: %s"
       % (len(entregues), contas))
    check("as 3 conversas foram RESPONDIDAS (nenhuma se perdeu de verdade)",
          len(entregues) == 3, entregues)
    check("🔴 `expiradas == 0` em TODA varredura — conversa respondida nao e' "
          "perda", all(n == 0 for n in contas), contas)
    check("e nenhuma perda falsa entrou no hash de NENHUMA das duas",
          hash_a.get("expiradas") in (None, "0")
          and hash_b.get("expiradas") in (None, "0"),
          "A=%s B=%s" % (hash_a.get("expiradas"), hash_b.get("expiradas")))

    # ------------------------------------------------------------------ #
    # (b) O TIMEOUT DE UMA NAO MANCHA A OUTRA
    # ------------------------------------------------------------------ #
    async def timeout_com_vizinha():
        _zerar_admissao(bp)
        RELOGIO[0] = datetime(2026, 9, 21, 9, 0, 0)
        s = servico_novo()
        await _semear(s, ESCOPO_A, 1)
        # A corretora B tem 5 conversas e cota 4: uma sobra na fila, e e' por
        # isso que ela aparece em `por_escopo` — o cenario em que o numero
        # global caia no hash dela.
        await _semear(s, ESCOPO_B, 5, inicio=50)
        _andar(30)

        async def borda(payload_dict=None, **kw):
            await asyncio.sleep(5 if escopo_do_turno(payload_dict) == ESCOPO_A
                                else 0.01)

        _c, chaves = await s.redis.scan(match="whatsapp_buffer:*")
        r = await bp["processar_buffers_prontos"](
            list(chaves), s, borda, timeout_s=0.2)
        return r, _hash_de(s, ESCOPO_A), _hash_de(s, ESCOPO_B)

    r, hash_a, hash_b = asyncio.run(timeout_com_vizinha())
    check("🔴 o `timeouts` da corretora A foi gravado no hash DELA",
          hash_a.get("timeouts") == "1", "A=%s" % hash_a.get("timeouts"))
    check("🔴 e o hash da corretora B ficou INTACTO (nada de timeout dela)",
          hash_b.get("timeouts") in (None, "0"),
          "B=%s — o numero de uma corretora na tela da outra"
          % hash_b.get("timeouts"))
    check("e o turno cortado NAO virou tambem uma 'expirada'",
          r["expiradas"] == 0, r)

    # ------------------------------------------------------------------ #
    # (c) O CASO POSITIVO — uma chave EXPIRA DE VERDADE
    # ------------------------------------------------------------------ #
    #
    # ⛔ Sem este cenario o guarda acima ficaria verde com um contador que
    # nunca mais contasse nada — e o numero que existe para dizer "perdi
    # mensagem de segurado" seria um zero permanente.
    async def perda_de_verdade():
        _zerar_admissao(bp)
        RELOGIO[0] = datetime(2026, 9, 21, 9, 0, 0)
        s = servico_novo()
        await _semear(s, ESCOPO_A, 2)
        # A corretora B esta ATIVA na mesma varredura: e' ela quem prova que o
        # numero vai para o DONO, e nao para todo mundo.
        await _semear(s, ESCOPO_B, 1, inicio=70)
        _andar(30)

        async def borda(**kw):
            await asyncio.sleep(0)

        # Cota 1: uma conversa de A e' atendida, a outra e' ADIADA.
        _c, chaves = await s.redis.scan(match="whatsapp_buffer:*")
        r1 = await bp["processar_buffers_prontos"](
            list(chaves), s, borda, cota_por_corretora=1)
        # ...e agora NINGUEM varre por 90 s: o `setex` de 60 s do Redis apaga a
        # rajada de quem estava na fila. E' a perda que o numero existe para ver.
        _andar(90)
        # A corretora B volta a falar com DUAS conversas e cota 1: uma e'
        # atendida e a outra fica na FILA dela. E' isso que poe a corretora B na
        # conta da mesma varredura que colhe a perda de A — e e' so' assim que
        # se prova que o numero foi para o DONO, e nao para todo escopo ativo.
        await _semear(s, ESCOPO_B, 2, inicio=80)
        _andar(30)
        anotador = _LoggerQueAnota()
        guardado = bp["logger"]
        bp["logger"] = anotador
        try:
            _c, chaves = await s.redis.scan(match="whatsapp_buffer:*")
            r2 = await bp["processar_buffers_prontos"](
                list(chaves), s, borda, cota_por_corretora=1)
        finally:
            bp["logger"] = guardado
        return r1, r2, _hash_de(s, ESCOPO_A), _hash_de(s, ESCOPO_B), anotador.linhas

    r1, r2, hash_a, hash_b, linhas = asyncio.run(perda_de_verdade())
    _p("      📊 CASO POSITIVO: adiadas=%s -> expiradas=%s (hash A=%s, B=%s)"
       % (sum(r1["adiadas"].values()), r2["expiradas"],
          hash_a.get("expiradas"), hash_b.get("expiradas")))
    check("a conversa foi mesmo ADIADA antes (senao nao havia o que perder)",
          r1["adiadas"]["cota"] >= 1, r1)
    check("🔴 POSITIVO: a chave que sumiu do Redis esperando conta 1 perda",
          r2["expiradas"] == 1, r2)
    check("🔴 POSITIVO: e ela foi gravada no hash do DONO (corretora A)",
          hash_a.get("expiradas") == "1", "A=%s" % hash_a.get("expiradas"))
    check("🔴 POSITIVO: o hash da corretora B nao recebeu nada",
          hash_b.get("expiradas") in (None, "0"), "B=%s" % hash_b.get("expiradas"))
    perdas = [t for n, t in linhas if "SUMIRAM" in t]
    check("🔴 POSITIVO: a perda deixou LINHA DE LOG (antes nao deixava nenhuma)",
          len(perdas) == 1, [t[:80] for _n, t in linhas][:4])
    check("e a linha de log nao carrega telefone nem chave (sem PII)",
          all("5511" not in t and "whatsapp_buffer" not in t for t in perdas),
          perdas)


# ===========================================================================
# G5 — A LINHA DE CONTROLE HERDADA: os guardas vizinhos continuam verdes
# ===========================================================================
def g5():
    _p("\n[G5] Os guardas vizinhos continuam verdes — SEM uma linha editada")
    for arquivo in ("test_midia_e_concorrencia_do_webhook.py",
                    "test_uma_rajada_um_turno.py"):
        r = subprocess.run(
            [sys.executable, os.path.join("tests", arquivo)],
            cwd=RAIZ, capture_output=True, text=True, timeout=1800,
            encoding="utf-8", errors="replace",
            env={**os.environ, "PYTHONIOENCODING": "utf-8",
                 "PYTHONDONTWRITEBYTECODE": "1"})
        falhas = [l.strip() for l in (r.stdout or "").splitlines()
                  if "[FALHOU]" in l]
        check("%s continua verde" % arquivo,
              r.returncode == 0 and not falhas,
              "rc=%s | %s" % (r.returncode, (falhas or [(r.stderr or "")[-400:]])[0]))


GATES = {"FIO": fio, "G1": g1, "G2": g2, "G3": g3, "G4": g4, "D1": d1,
         "G7": g7, "G10": g10, "G11": g11, "G5": g5}


# ===========================================================================
# AS MUTAÇÕES — por CÓPIA, em SUBPROCESSO. A árvore precisa estar parada.
# ===========================================================================
BP = "app/tasks/buffer_processor.py"
MBS = "app/services/message_buffer_service.py"

MUTACOES = [
    # G1 — `prontas` com régua própria, em vez de `_esta_pronta`
    ("M-18-1", MBS,
     "            motivo = _esta_pronta(dados, agora)",
     "            motivo = \"janela\" if (agora - datetime.fromisoformat(\n"
     "                dados[\"last_at\"])).total_seconds() >= 5 else \"\"  # MUTACAO",
     "G1"),
    # G2 — devolver a ordem recebida (a do SCAN) em vez de intercalar
    ("M-18-2", BP,
     "    return [chave for grupo in zip_longest(*por_escopo.values())\n"
     "            for chave in grupo if chave is not None]",
     "    return list(chaves)  # MUTACAO",
     "G2"),
    # G3 — cota altíssima: a corretora doente volta a ocupar tudo
    ("M-18-3", BP,
     '        cota = cota_por_corretora or _env_int("WHATSAPP_COTA_POR_CORRETORA",\n'
     "                                              _COTA_PADRAO)",
     "        cota = 10_000  # MUTACAO",
     "G3"),
    # G4 — inverter a ordem: a cota passa a medir o teto GLOBAL, que é o que
    #      aconteceria se ela fosse tomada DEPOIS do semáforo do processo
    ("M-18-4", BP,
     "    atual = em_voo.get(escopo, 0)",
     '    atual = estado["em_voo_global"]  # MUTACAO',
     "G4"),
    # G5 — a chave da cota sem o escopo: todas as corretoras no mesmo balde
    ("M-18-5", BP,
     "        escopo = escopo_de(chave) if com_cota else \"\"",
     "        escopo = \"balde-unico\" if com_cota else \"\"  # MUTACAO",
     "G3"),
    # G7 — `adiar` vira `pass`: quem espera passa dos 60 s e some
    ("M-18-7", MBS,
     "        return await self.renovar_vida(chave)",
     "        return False  # MUTACAO",
     "G7"),
    # G10 — o default vira "todos"
    ("M-18-10", BP,
     "    if not permitidas or alvo not in permitidas:",
     "    if False:  # MUTACAO",
     "G10"),
    # G11 — quem CONSOME deixa de avisar: a conversa respondida continua em
    #       `aguardando` e vira "mensagem perdida" duas varreduras depois.
    #       É o defeito (a) do red team B1, com outro nome.
    ("M-18-11", BP,
     "                            marcar_consumida(chave)",
     "                            pass  # MUTACAO",
     "G11"),
    # G11 — o número da perda volta a ser GLOBAL e cai no hash de TODO escopo
    #       ativo: a perda de uma corretora aparece na tela da outra.
    ("M-18-12", BP,
     "                expiradas=int(expiradas_por_escopo.get(escopo, 0)),",
     "                expiradas=sum(expiradas_por_escopo.values()),  # MUTACAO",
     "G11"),
    # D1 — o estado de admissão volta a ser LOCAL da varredura
    ("M-18-D1", BP,
     "        estado = _ADMISSAO",
     "        estado = {k: (type(v)() if hasattr(v, 'clear') else 0)\n"
     "                  for k, v in _ADMISSAO.items()}  # MUTACAO",
     "D1"),
]


def _rodar(gate):
    return subprocess.run(
        [sys.executable, os.path.abspath(__file__), "--so", gate],
        cwd=RAIZ, capture_output=True, text=True, timeout=2400,
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8",
             "PYTHONDONTWRITEBYTECODE": "1"})


def rodar_mutacoes(filtro=None):
    _p("\n[MUT] MUTACOES POR COPIA -- cada uma em SUBPROCESSO. A arvore precisa estar parada.")
    vermelhas = verdes = 0
    for mid, relativo, de, para, gate in MUTACOES:
        if filtro and mid != filtro:
            continue
        caminho = os.path.normpath(os.path.join(RAIZ, relativo))
        original = io.open(caminho, encoding="utf-8").read()
        if de not in original:
            _p("  [FALHOU] %s: a ancora nao existe em %s -- mutacao NAO aplicada "
               "NAO e mutacao passada" % (mid, relativo))
            verdes += 1
            continue
        base = _rodar(gate)
        backup = tempfile.NamedTemporaryFile(delete=False, suffix=".bak-018").name
        shutil.copyfile(caminho, backup)
        try:
            io.open(caminho, "w", encoding="utf-8", newline="\n").write(
                original.replace(de, para, 1))
            r = _rodar(gate)
            falhas = [l.strip() for l in (r.stdout or "").splitlines() if "[FALHOU]" in l]
            if base.returncode == 0 and r.returncode != 0 and falhas:
                vermelhas += 1
                _p("  [ok] %s deixa %s VERMELHO: %s" % (mid, gate, falhas[0][:200]))
            else:
                verdes += 1
                _p("  [FALHOU] %s NAO deixou %s vermelho (base rc=%s, mutado rc=%s)\n%s"
                   % (mid, gate, base.returncode, r.returncode,
                      (r.stdout or r.stderr)[-900:]))
        finally:
            shutil.copyfile(backup, caminho)
            os.unlink(backup)
            assert io.open(caminho, encoding="utf-8").read() == original, \
                "restauracao falhou em " + relativo
    _p("\n  PLACAR DAS MUTACOES: %d vermelhas - %d verdes" % (vermelhas, verdes))
    return verdes == 0


def main():
    args = sys.argv[1:]
    if "--mutar" in args:
        i = args.index("--mutar")
        filtro = args[i + 1] if len(args) > i + 1 and args[i + 1].startswith("M-") else None
        return 0 if rodar_mutacoes(filtro) else 1

    so = args[args.index("--so") + 1] if "--so" in args else None
    if not so:
        _p("=" * 78)
        _p("  O FIO · G1-G5 · G7 · G10 -- UMA CORRETORA NAO TRAVA A OUTRA")
        _p("  (SPEC-EXTRA-001.8, FATIA 1)")
        _p("=" * 78)
    for gid, fn in GATES.items():
        if so and gid != so:
            continue
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            import traceback
            check("%s EXPLODIU (defeito do guarda ou do produto)" % gid, False,
                  "%s: %s\n%s" % (type(exc).__name__, exc,
                                  traceback.format_exc()[-1200:]))
    if not so:
        _p("\n" + "=" * 78)
        _p("  %d assercoes verdes - %d vermelhas" % (PASS, FAIL))
        _p("=" * 78)
    return 1 if FAIL else 0


def test_uma_corretora_nao_trava_a_outra():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
