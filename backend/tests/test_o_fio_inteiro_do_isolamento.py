# -*- coding: utf-8 -*-
r"""O FIO INTEIRO — a saída REAL de cada fatia é entrada válida da seguinte.
SPEC-EXTRA-001.8, FATIA 6 (a costura final).

🔴 **A classe de defeito que este arquivo existe para pegar.** Na SPEC anterior,
o que TODO gate de unidade deixou passar foram as SETE quebras de COSTURA: cada
peça certa sozinha, e o encaixe entre elas errado — um nome de campo que não
casa, um kwarg que o outro lado não aceita, um número somado no lugar errado.
Um guarda por fatia não tem COMO ver isso: ele dubla exatamente a fronteira onde
o defeito mora.

O QUE ESTE ARQUIVO ATRAVESSA, com o MOTOR REAL dos dois lados de cada fronteira
e dublê só nas BORDAS (Redis em memória, PostgREST em memória que FILTRA, envio
que CONTA):

```
add_message (REAL)
   -> prontas / rodízio / cota / disjuntor (REAL, buffer_processor)
   -> registrar_ocupacao (REAL, message_buffer_service)
   -> [BORDA] o `processar`, com os MESMOS kwargs de
      process_whatsapp_message_background
   -> montar_turno_do_atendimento (REAL, webhook) com o relógio REAL da fila
   -> _contadores_por_escopo + montar_atendimento_por_corretora (REAIS, Central)
   -> avisar_os_donos_da_fila -> avisar_pelos_escopos (REAIS) -> [BORDA] o envio
```

AS FRONTEIRAS CONFERIDAS (cada asserção é uma costura, não uma unidade):

```
F1->F5       o relógio que o processador PRODUZ tem as chaves que o webhook LÊ
F1->F5       a assinatura REAL do webhook ACEITA todo kwarg que o processador passa
F1->Central  os campos que `registrar_ocupacao` ESCREVE são os que a Central LÊ
F4->Central  o disjuntor que retém a conversa é o MESMO que a Central mostra
F1->aviso    a fila que o dono recebe é a DELE, uma vez, e desligada por padrão
A CONTA      entrada = processadas + adiadas · zero expiradas · uma resposta só
```

⛔ SEGURANÇA: zero rede, zero banco, zero Redis de verdade, zero LLM, zero
envio. Todo id, telefone e escopo é sintético; nenhum nome de corretora ou de
pessoa entra como constante (CLAUDE.md §13.9).

⚠️ **Por AST, e não por `import`.** 📊 Medido em 21/09/2026 nesta máquina:
`import app.api.webhook` custa 13,1 s e sobe serviços de verdade no caminho
(`WhatsApp service initialized`). Os nós REAIS são recortados do MESMO arquivo
em disco — mutar o fonte muda o que este teste executa, que é a garantia que
importa (CLAUDE.md §9.4).

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_o_fio_inteiro_do_isolamento.py
    ... --so F1   ·   ... --mutar   ·   ... --mutar M-FIO-1
    python -m pytest tests/test_o_fio_inteiro_do_isolamento.py -q -p no:cacheprovider
"""
from __future__ import annotations

import ast
import asyncio
import io
import os
import shutil
import subprocess
import sys
import time
import types

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)                        # .../backend
for caminho in (RAIZ, AQUI):
    if caminho not in sys.path:
        sys.path.insert(0, caminho)
os.environ["SEM_REDE"] = "1"

ESTE = os.path.abspath(__file__)
BUFFER_PY = os.path.join(RAIZ, "app", "tasks", "buffer_processor.py")
WEBHOOK_PY = os.path.join(RAIZ, "app", "api", "webhook.py")
MBS_PY = os.path.join(RAIZ, "app", "services", "message_buffer_service.py")

# ⚠️ Os dois guardas vizinhos são REAPROVEITADOS: o Redis dublê que honra TTL, o
# relógio controlável, o recorte por AST e o dublê do breaker já existem e já
# são a linha de base desta SPEC. Um segundo motor de teste é como dois guardas
# passam a discordar sobre o mesmo fato (CLAUDE.md §5).
import test_uma_corretora_nao_trava_a_outra as V     # noqa: E402
import test_a_costura_do_isolamento as C             # noqa: E402
import test_a_atendente_fala_e_o_robo_cala as H      # noqa: E402

PASS = 0
FAIL = 0

#: ⛔ 100% SINTÉTICOS (§13.9).
CORRETORA_A = "corretora-sintetica-a"
CORRETORA_B = "corretora-sintetica-b"
ESCOPO_A = V.ESCOPO_A
ESCOPO_B = V.ESCOPO_B


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
        _p("  [FALHOU] %s" % nome
           + ("\n         %s" % str(detalhe)[:900] if detalhe else ""))
    return bool(cond)


# ===========================================================================
# OS MOTORES REAIS, RECORTADOS DO FONTE
# ===========================================================================
NOMES_DA_FATIA_6 = list(V.NOMES_DO_VARREDOR) + [
    "provedores_barrados", "provedor_do_escopo", "_provedor_da_chave",
    "_PROVEDOR_POR_ESCOPO", "_PROVEDOR_CACHE_PADRAO_S", "_LANGCHAIN_PARA_RESOLVER",
    "check_buffers", "avisar_os_donos_da_fila", "_corretora_do_escopo",
    "_CORRETORA_POR_ESCOPO", "_CORRETORA_CACHE_PADRAO_S", "_ESCOPOS_ESPERANDO",
    # A segunda pergunta da varredura, do conserto unico de 21/09/2026: o
    # meio-aberto deixa passar UMA sonda (SPEC §7.4). `check_buffers` a passa
    # para o processador, entao ela tem de existir no recorte.
    "provedores_em_meio_aberto",
]


def _recortar(arquivo, nomes, extras=None):
    """Os nós REAIS de um arquivo do produto, sem os imports de topo."""
    fonte = io.open(arquivo, encoding="utf-8").read()
    arvore = ast.parse(fonte)
    pedidos, escolhidos, achados = list(nomes), [], set()
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
        raise AssertionError("sumiram de %s: %s — se foram renomeados, o guarda "
                             "da costura precisa saber" % (arquivo, faltando))
    ns = dict(extras or {})
    ns.setdefault("__name__", "recortado_" + os.path.basename(arquivo)[:-3])
    exec(compile(ast.fix_missing_locations(ast.Module(body=escolhidos, type_ignores=[])),
                 arquivo, "exec"), ns)  # noqa: S102
    return ns


def _no_do_fonte(arquivo, nome):
    """O nó de AST de uma função, para LER a declaração dela (assinatura)."""
    arvore = ast.parse(io.open(arquivo, encoding="utf-8").read())
    for no in ast.walk(arvore):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and no.name == nome:
            return no
    raise AssertionError("%s não existe mais em %s" % (nome, arquivo))


def assinatura_do_webhook():
    """Os nomes que `process_whatsapp_message_background` ACEITA — do fonte.

    🔴 Por AST e não por `inspect.signature`: importar `app.api.webhook` custa
    📊 13,1 s e sobe serviços de verdade (medido em 21/09/2026). O alvo é o
    mesmo — a declaração REAL no arquivo que o produto roda.
    """
    no = _no_do_fonte(WEBHOOK_PY, "process_whatsapp_message_background")
    a = no.args
    nomes = {x.arg for x in list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs)}
    return nomes, bool(a.kwarg)


def chaves_lidas_pelo_webhook():
    """As chaves do `relogio_da_fila` que o CONSUMIDOR de fato lê.

    ⚠️ Lidas do lado de quem CONSOME (`da_fila.get("...")` dentro de
    `montar_turno_do_atendimento`), nunca escritas de memória: o contrato é o que
    o código do outro lado procura, não o que a SPEC lembrava.
    """
    no = _no_do_fonte(WEBHOOK_PY, "montar_turno_do_atendimento")
    chaves = set()
    for filho in ast.walk(no):
        if (isinstance(filho, ast.Call) and isinstance(filho.func, ast.Attribute)
                and filho.func.attr == "get"
                and isinstance(filho.func.value, ast.Name)
                and filho.func.value.id == "da_fila"
                and filho.args and isinstance(filho.args[0], ast.Constant)):
            chaves.add(str(filho.args[0].value))
    return chaves


def webhook_real():
    """`montar_turno_do_atendimento` REAL — a função que o caminho do WhatsApp
    chama depois do envio, recortada do fonte."""
    from typing import Any, Dict, List, Optional  # noqa: F401

    return _recortar(
        WEBHOOK_PY,
        ["_ms_medido", "ETAPAS_DO_ATENDIMENTO", "montar_turno_do_atendimento"],
        extras={"Any": Any, "Dict": Dict, "List": List, "Optional": Optional},
    )


# ===========================================================================
# AS BORDAS — Redis em memória (com TTL e relógio), PostgREST que FILTRA,
#             envio que CONTA
# ===========================================================================
class Duble(C.Duble):
    """O dublê do vizinho + o que a CENTRAL usa para ler os contadores.

    ⚠️ `scan_iter` e `hgetall` entram porque é por eles que
    `_contadores_por_escopo` lê o HASH — e é essa leitura REAL que prova que os
    nomes dos campos casam dos dois lados. Um dublê que aceitasse qualquer
    chamada esconderia exatamente o comando que faltasse.
    """

    async def hgetall(self, chave):
        return dict(self.hashes.get(chave) or {})

    async def scan_iter(self, match="*", count=100):
        from fnmatch import fnmatch

        for chave in list(self.hashes):
            if fnmatch(chave, match or "*"):
                yield chave


class Envio:
    """A BORDA do WhatsApp: ninguém fala com ninguém, mas alguém CONTA."""

    def __init__(self):
        self.avisos = []

    async def __call__(self, _db, **kw):
        self.avisos.append({"company_id": kw.get("company_id"),
                            "texto": str(kw.get("texto") or "")})
        return {"enviado": True, "calado": False}


def banco_das_duas():
    """Duas corretoras, duas integrações — o mundo mínimo do produto."""
    b = H.BancoFalso()
    b.semear("companies", [
        {"id": CORRETORA_A, "company_name": "Corretora sintetica A"},
        {"id": CORRETORA_B, "company_name": "Corretora sintetica B"},
    ])
    b.semear("integrations", [
        {"id": ESCOPO_A, "company_id": CORRETORA_A, "is_active": True},
        {"id": ESCOPO_B, "company_id": CORRETORA_B, "is_active": True},
    ])
    b.semear("conversations", [])
    b.semear("messages", [])
    return b


#: ⚠️ A cota é regulada por variável de ambiente, e variável de ambiente é
#: estado do PROCESSO: deixá-la ligada depois do último caso mudaria o teto de
#: quem rodar em seguida no mesmo `pytest`.
_COTA_ORIGINAL: dict = {}


def preparar(*, cota=2):
    """Um cenário limpo: dublê, serviço REAL, varredor REAL, duas corretoras."""
    V.RELOGIO[0] = V.datetime(2026, 9, 21, 9, 0, 0)
    duble = Duble()
    C._relogio_do_modelo(duble)
    V.M.datetime = V._DataHoraDublada
    servico = V.M.MessageBufferService(duble)
    bp = _recortar(BUFFER_PY, NOMES_DA_FATIA_6,
                   extras={"asyncio": asyncio, "os": os, "logger": V._LoggerMudo()})
    V._zerar_admissao(bp)
    for nome in ("motivo_da_chave", "esperando_desde"):
        bp["_ADMISSAO"].setdefault(nome, {}).clear()
    bp["_PROVEDOR_POR_ESCOPO"].clear()
    bp["_CORRETORA_POR_ESCOPO"].clear()
    bp["_ESCOPOS_ESPERANDO"].clear()
    _COTA_ORIGINAL.setdefault("valor", os.environ.get("WHATSAPP_COTA_POR_CORRETORA"))
    os.environ["WHATSAPP_COTA_POR_CORRETORA"] = str(cota)
    return duble, servico, bp


def _ligar_check_buffers(bp, duble, servico, processar):
    """Dá a `check_buffers` REAL as três peças que ele importa do `app`.

    🔴 Devolve o DESFAZER, e ele não é opcional. 📊 O comentário do guarda
    vizinho (`test_midia_e_concorrencia_do_webhook.py:473`) documenta o preço de
    esquecer: um `app` sintético deixado em `sys.modules` por um teste fez o
    seguinte quebrar no import de um módulo que existe — "um teste que fica
    vermelho por causa do vizinho mede a ordem de coleta, não o produto".
    """
    async def _redis():
        return duble

    async def _servico():
        return servico

    antes = sys.modules.get("app.api.webhook")
    falso = types.ModuleType("app.api.webhook")
    falso.process_whatsapp_message_background = processar
    sys.modules["app.api.webhook"] = falso
    bp["get_async_redis_client"] = _redis
    bp["get_message_buffer_service"] = _servico

    def desligar():
        if antes is None:
            sys.modules.pop("app.api.webhook", None)
        else:
            sys.modules["app.api.webhook"] = antes

    return desligar


class Atendimento:
    """A BORDA do atendimento — o mais perto do real que dá sem chamar o modelo.

    🔴 Ela recebe os MESMOS kwargs que `process_whatsapp_message_background`
    recebe do varredor e entrega o `relogio_da_fila` REAL para o
    `montar_turno_do_atendimento` REAL. É aqui que a fronteira F1->F5 é
    atravessada de verdade, em vez de conferida de memória.
    """

    def __init__(self, webhook, demora_s=0.0):
        self.webhook = webhook
        self.demora_s = float(demora_s)
        self.kwargs_vistos = []
        self.relogios = []        # o `relogio_da_fila` REAL, como chegou
        self.turnos = []          # (escopo, telefone, turn)
        self.respostas = []       # uma por rajada respondida

    async def __call__(self, payload_dict=None, combined_message=None,
                       buffered_messages=None, **extras):
        self.kwargs_vistos.append(set(extras))
        if isinstance(extras.get("relogio_da_fila"), dict):
            self.relogios.append(dict(extras["relogio_da_fila"]))
        if self.demora_s:
            await asyncio.sleep(self.demora_s)
        escopo = str((payload_dict or {}).get("_integration_id") or "")
        telefone = str((payload_dict or {}).get("phone") or "")
        turno = self.webhook["montar_turno_do_atendimento"](
            status="complete", total_ms=1234,
            relogio_da_fila=extras.get("relogio_da_fila"),
            grafo_ms=900, envio_ms=120)
        self.turnos.append((escopo, telefone, turno))
        self.respostas.append((escopo, telefone))
        return True


async def semear(servico, escopo, quantas, inicio=0):
    """`add_message` REAL — o MESMO caminho do webhook."""
    for n in range(inicio, inicio + quantas):
        tel = V.TEL % n
        await servico.add_message(tel, "bateu meu carro", "pending", "pending", {},
                                  {"_integration_id": escopo, "phone": tel},
                                  escopo=escopo)


async def varrer(bp, servico, duble, processar, **kw):
    _cursor, chaves = await duble.scan(0, match="whatsapp_buffer:*")
    return await bp["processar_buffers_prontos"](chaves, servico, processar, **kw)


def central():
    import app.core.central_de_agentes as Central

    return Central


async def bloco_da_central(duble, banco, breaker=None):
    """O bloco da Central com os contadores REAIS lidos do dublê de Redis."""
    import app.core.database as _database
    import app.core.redis as _redis_mod

    Central = central()
    antes_db, antes_redis = _database.get_supabase_client, _redis_mod.get_async_redis_client

    async def _cliente():
        return duble

    _database.get_supabase_client = lambda: banco
    _redis_mod.get_async_redis_client = _cliente
    try:
        contadores = await Central._contadores_por_escopo()
        bruto = await asyncio.to_thread(Central._ler_atendimento_sincrono)
        breakers = breaker if breaker is not None else await Central._estado_dos_breakers()
    finally:
        _database.get_supabase_client = antes_db
        _redis_mod.get_async_redis_client = antes_redis
    linhas = Central.montar_atendimento_por_corretora(
        bruto=bruto, contadores=contadores, breaker=breakers, cota=4)
    return {str(l.get("company_id") or "__sem__"): l for l in linhas}, contadores


# ===========================================================================
# F1 — O RELÓGIO DA FILA ATRAVESSA O FIO INTEIRO
# ===========================================================================
def caso_F1():
    _p("\n=== F1. o relogio que o PROCESSADOR produz e o que o WEBHOOK le ===")

    async def corpo():
        duble, servico, bp = preparar(cota=2)
        webhook = webhook_real()
        # 5 conversas de uma corretora com cota 2: três são ADIADAS e voltam na
        # varredura seguinte — é o caso em que a espera pela cota EXISTE.
        await semear(servico, ESCOPO_A, 5)
        await semear(servico, ESCOPO_B, 1, inicio=900)
        V._andar(30)                      # a rajada fecha pelo teto de 25 s

        # ⚠️ A borda DEMORA de propósito: sem uma espera de verdade as tarefas
        # do `gather` correm até o fim uma a uma (nenhuma cede o laço) e a cota
        # nunca chega a ser disputada — o cenário pareceria saudável por
        # ausência de concorrência, que é como um guarda de fila vira carimbo.
        borda = Atendimento(webhook, demora_s=0.03)
        primeira = await varrer(bp, servico, duble, borda)
        check("a cota de 2 segurou parte da fila da corretora A",
              primeira["adiadas"]["cota"] >= 1, primeira)

        # 🔴 A espera pela cota é REAL: 120 ms de relógio de parede entre as
        # varreduras, que é o que a conversa adiada de fato esperou. O produto
        # varre a cada 1 s; aqui cada volta é uma varredura, até a fila drenar.
        voltas = []
        for _ in range(6):
            time.sleep(0.12)
            voltas.append(await varrer(bp, servico, duble, borda))
            if len(borda.respostas) == 6:
                break
        segunda = voltas[0]

        # ---- F1 -> F5 · as CHAVES -----------------------------------------
        check("🔴 toda conversa atendida chegou ao webhook COM relogio_da_fila",
              all("relogio_da_fila" in kw for kw in borda.kwargs_vistos),
              borda.kwargs_vistos)

        # As chaves que o processador PRODUZ, lidas do dado real que ele passou.
        produzidas = set()
        for relogio in borda.relogios:
            produzidas |= set(relogio)
        lidas = chaves_lidas_pelo_webhook()
        check("🔴 as chaves do relogio sao EXATAMENTE as que o webhook le "
              "(lidas do lado consumidor): %s" % sorted(lidas),
              produzidas == lidas, "produzidas=%s lidas=%s" % (sorted(produzidas),
                                                               sorted(lidas)))

        # ---- F1 -> F5 · o TURNO montado ------------------------------------
        etapas = [t[2]["stage_ms"] for t in borda.turnos]
        check("`buffer_espera` sai INT em todo turno (nunca None: o carimbo "
              "existe)", all(isinstance(e["buffer_espera"], int) for e in etapas),
              etapas[:3])
        check("`fila_cota` sai INT em todo turno",
              all(isinstance(e["fila_cota"], int) for e in etapas), etapas[:3])
        check("e o tempo de rajada medido bate com os 30 s do relogio dublado",
              all(29_000 <= e["buffer_espera"] <= 95_000 for e in etapas),
              [e["buffer_espera"] for e in etapas])

        # 🔴 A ESPERA PELA COTA É A REAL, NÃO A DA ÚLTIMA TENTATIVA.
        esperou = [e["fila_cota"] for e in etapas if e["fila_cota"] >= 100]
        check("🔴 quem foi adiado por cota carrega a espera REAL (>= 100 ms), "
              "e nao os ~0 ms da ultima tentativa",
              len(esperou) >= 1, [e["fila_cota"] for e in etapas])
        servidas_na_hora = [e["fila_cota"] for e in etapas if e["fila_cota"] < 100]
        check("CONTROLE: quem foi servido de primeira marca ~0 ms — as duas "
              "medidas CONSEGUEM ser diferentes",
              len(servidas_na_hora) >= 1, [e["fila_cota"] for e in etapas])

        # ---- F1 -> F5 · a ASSINATURA ---------------------------------------
        aceitos, tem_kwargs = assinatura_do_webhook()
        passados = set().union(*borda.kwargs_vistos) if borda.kwargs_vistos else set()
        check("🔴 a assinatura REAL de process_whatsapp_message_background "
              "ACEITA todos os kwargs que o processador passa",
              tem_kwargs or passados <= aceitos,
              "passados=%s aceitos=%s" % (sorted(passados), sorted(aceitos)))

        # ---- A CONTA FECHA --------------------------------------------------
        for nome, resumo in (("1a", primeira), ("2a", segunda)):
            check("conta da %s varredura: entrada = processadas + adiadas" % nome,
                  resumo["prontas"] == resumo["processadas"]
                  + sum(resumo["adiadas"].values()), resumo)
            check("e ninguem expirou na %s varredura" % nome,
                  resumo["expiradas"] == 0, resumo)
        check("🔴 as 6 conversas foram respondidas UMA vez cada — nenhuma "
              "perdida, nenhuma duplicada (%d volta(s) de fila)" % (len(voltas) + 1),
              sorted(borda.respostas) == sorted(set(borda.respostas))
              and len(borda.respostas) == 6,
              "%d respostas, %d distintas" % (len(borda.respostas),
                                              len(set(borda.respostas))))
        check("e nenhuma expirou em nenhuma das voltas",
              all(r["expiradas"] == 0 for r in voltas), voltas)

    asyncio.run(corpo())


# ===========================================================================
# F2 — OS CAMPOS QUE O PROCESSADOR ESCREVE SÃO OS QUE A CENTRAL LÊ
# ===========================================================================
def caso_F2():
    _p("\n=== F2. o contador que o varredor ESCREVE e o que a Central LE ===")

    async def corpo():
        duble, servico, bp = preparar(cota=2)
        webhook = webhook_real()
        banco = banco_das_duas()
        await semear(servico, ESCOPO_A, 6)
        await semear(servico, ESCOPO_B, 1, inicio=900)
        V._andar(30)

        borda = Atendimento(webhook, demora_s=0.03)
        resumo = await varrer(bp, servico, duble, borda)
        adiadas_a = sum((resumo["adiadas_por_escopo"].get(ESCOPO_A) or {}).values())
        check("a corretora A ficou com fila (cota 2, 6 conversas)",
              adiadas_a >= 3, resumo["adiadas_por_escopo"])
        check("e o mapa por escopo NAO carrega chave sem dono",
              "" not in resumo["adiadas_por_escopo"],
              list(resumo["adiadas_por_escopo"]))

        linhas, contadores = await bloco_da_central(duble, banco)
        check("🔴 a Central LEU o HASH que `registrar_ocupacao` escreveu "
              "(os nomes dos campos casam dos dois lados)",
              bool(contadores) and ESCOPO_A in contadores, contadores)
        a = linhas.get(CORRETORA_A) or {}
        b = linhas.get(CORRETORA_B) or {}
        check("🔴 o `em_espera` da corretora A na tela e o numero REAL da fila "
              "dela (%d)" % adiadas_a, a.get("em_espera") == adiadas_a, a)
        check("o motivo que a tela mostra e o que o varredor registrou",
              a.get("ultimo_motivo_de_espera") == "cota", a)
        # ⚠️ A corretora B pode nem ter LINHA: sem fila e sem turno gravado, não
        # há contador dela no Redis. O que não pode existir é número da A
        # aparecendo em qualquer outra linha.
        fora_da_a = sum(int(l.get("em_espera") or 0)
                        for e, l in linhas.items() if e != CORRETORA_A)
        check("🔴 e NENHUM dos %d em_espera da corretora A vazou para outra "
              "linha da tela" % adiadas_a,
              fora_da_a == 0 and int((b or {}).get("em_espera") or 0) == 0,
              {"fora_da_a": fora_da_a, "b": b})
        check("ninguem expirou nem estourou o teto de tempo",
              a.get("expiradas_acumuladas") == 0
              and a.get("timeouts_acumulados") == 0, a)

    asyncio.run(corpo())


# ===========================================================================
# F4 — O DISJUNTOR QUE RETÉM É O MESMO QUE A CENTRAL MOSTRA
# ===========================================================================
def caso_F4():
    _p("\n=== F4. o disjuntor do processador e o da Central sao o MESMO ===")

    async def corpo():
        duble, servico, bp = preparar(cota=4)
        webhook = webhook_real()
        banco = banco_das_duas()
        import app.core.relogio_do_modelo as RM

        await semear(servico, ESCOPO_A, 3)
        await semear(servico, ESCOPO_B, 3, inicio=900)
        V._andar(30)
        await C._abrir_o_disjuntor(RM, C.PROVEDOR_A)

        async def resolver(escopo):
            return {ESCOPO_A: C.PROVEDOR_A, ESCOPO_B: C.PROVEDOR_B}.get(escopo)

        borda = Atendimento(webhook)
        resumo = await varrer(bp, servico, duble, borda,
                              barrados=bp["provedores_barrados"],
                              provedor_de=resolver)
        check("as 3 conversas da corretora A foram retidas pelo disjuntor",
              resumo["adiadas"]["breaker"] == 3, resumo)
        check("🔴 e a corretora B foi ATENDIDA na MESMA varredura",
              [e for e, _t in borda.respostas].count(ESCOPO_B) == 3,
              borda.respostas)

        linhas, _c = await bloco_da_central(duble, banco)
        a = linhas.get(CORRETORA_A) or {}
        b = linhas.get(CORRETORA_B) or {}
        check("🔴 a Central mostra o provedor da A como ABERTO — o mesmo estado "
              "que reteve a conversa",
              (a.get("breaker") or {}).get(C.PROVEDOR_A) == "aberto",
              a.get("breaker"))
        check("o provedor da B continua fechado na mesma tela",
              (a.get("breaker") or {}).get(C.PROVEDOR_B) == "fechado",
              a.get("breaker"))
        check("🔴 e o motivo da espera da corretora A e 'breaker'",
              a.get("ultimo_motivo_de_espera") == "breaker", a)
        fora_da_a = sum(int(l.get("em_espera") or 0)
                        for e, l in linhas.items() if e != CORRETORA_A)
        check("🔴 os numeros da corretora B seguem intactos: fila zero e nenhum "
              "'breaker' na conta dela",
              fora_da_a == 0
              and int((b or {}).get("em_espera") or 0) == 0
              and (b or {}).get("ultimo_motivo_de_espera") != "breaker",
              {"fora_da_a": fora_da_a, "b": b})
        check("e a fila retida INTEIRA (3) esta na linha da corretora A",
              int(a.get("em_espera") or 0) == 3, a)

    asyncio.run(corpo())


# ===========================================================================
# F5 — O AVISO AO DONO: um, para a corretora certa, e desligado por padrão
# ===========================================================================
def _com_o_aviso(duble, banco, envio, *, ligado: bool):
    """Aponta o módulo de aviso para os dublês e CONTA quem ele consultou."""
    import app.core.database as _database
    import app.services.aviso_de_fila_longa as A

    contagem = {"redis": 0, "banco": 0}
    antes = (A._redis, A._enviar_ao_grupo, _database.get_supabase_client,
             os.environ.get("ISOLAMENTO_AVISO_AO_DONO"))

    async def _redis_contado():
        contagem["redis"] += 1
        return duble

    def _banco_contado():
        contagem["banco"] += 1
        return banco

    A._redis = _redis_contado
    A._enviar_ao_grupo = envio
    _database.get_supabase_client = _banco_contado
    if ligado:
        os.environ["ISOLAMENTO_AVISO_AO_DONO"] = "1"
    else:
        os.environ.pop("ISOLAMENTO_AVISO_AO_DONO", None)

    def desfazer():
        A._redis, A._enviar_ao_grupo = antes[0], antes[1]
        _database.get_supabase_client = antes[2]
        if antes[3] is None:
            os.environ.pop("ISOLAMENTO_AVISO_AO_DONO", None)
        else:
            os.environ["ISOLAMENTO_AVISO_AO_DONO"] = antes[3]

    return contagem, desfazer


def _envelhecer_a_espera(duble, escopo, segundos):
    """O relógio da espera, CONTROLADO: esta corretora já espera há N segundos.

    ⚠️ `marcar_espera` é `SET NX` — o primeiro a chegar manda. Semear a chave com
    um instante antigo é o mesmo que ter visto a fila há N segundos, sem esperar
    N segundos de verdade.
    """
    import app.services.aviso_de_fila_longa as A

    duble.dados[A.CHAVE_DA_ESPERA.format(escopo=escopo)] = (
        str(int(time.time()) - int(segundos)), None)


def caso_F5():
    _p("\n=== F5. o aviso vai ao dono da fila — um, e so o dele ===")

    async def corpo():
        duble, servico, bp = preparar(cota=2)
        webhook = webhook_real()
        banco = banco_das_duas()
        envio = Envio()
        borda = Atendimento(webhook, demora_s=0.03)
        desligar = _ligar_check_buffers(bp, duble, servico, borda)

        # A corretora A satura; a B tem uma conversa só (fila curta).
        await semear(servico, ESCOPO_A, 8)
        await semear(servico, ESCOPO_B, 4, inicio=900)
        V._andar(30)
        _envelhecer_a_espera(duble, ESCOPO_A, 600)   # A espera há 10 min
        # ⚠️ A corretora B TAMBÉM tem fila, mas nova: ela existe para que um
        # aviso com o TOTAL da varredura (em vez do número por corretora) tenha
        # como ficar vermelho.

        contagem, desfazer = _com_o_aviso(duble, banco, envio, ligado=True)
        try:
            # 🔴 DEZ VARREDURAS SOBREPOSTAS — é o `max_instances=10` do produto.
            resumos = await asyncio.gather(*[bp["check_buffers"]() for _ in range(10)])
        finally:
            desfazer()

        fila_a = sum((r or {}).get("adiadas_por_escopo", {}).get(ESCOPO_A, {}).get("cota", 0)
                     for r in resumos)
        check("🔴 dez varreduras sobrepostas -> UM aviso (a trava e de Redis)",
              len(envio.avisos) == 1, envio.avisos)
        if envio.avisos:
            check("🔴 e ele foi para a corretora A, a dona da fila",
                  envio.avisos[0]["company_id"] == CORRETORA_A, envio.avisos[0])
            numeros = [int(n) for n in
                       __import__("re").findall(r"\d+", envio.avisos[0]["texto"])]
            por_escopo = max(
                ((r or {}).get("adiadas_por_escopo", {}).get(ESCOPO_A, {}) or {}).get("cota", 0)
                for r in resumos)
            total_da_varredura = max((r or {}).get("adiadas", {}).get("cota", 0)
                                     for r in resumos)
            check("🔴 o numero no aviso e o da fila DELA (%d), nunca o total da "
                  "varredura (%d)" % (por_escopo, total_da_varredura),
                  por_escopo in numeros and (
                      total_da_varredura == por_escopo
                      or total_da_varredura not in numeros),
                  "%s | texto=%r" % (numeros, envio.avisos[0]["texto"][:90]))
        check("a corretora B, com fila nova, NAO foi avisada",
              all(a["company_id"] != CORRETORA_B for a in envio.avisos),
              envio.avisos)
        check("e as varreduras seguiram atendendo (a conta voltou inteira)",
              all(r is not None for r in resumos)
              and sum(r["processadas"] for r in resumos) >= 4,
              [r and r["processadas"] for r in resumos])
        check("nenhuma mensagem expirou durante as dez varreduras",
              all(r["expiradas"] == 0 for r in resumos),
              [r and r["expiradas"] for r in resumos])

        # ---- A FILA ZERA -> O RELÓGIO DA ESPERA ZERA -----------------------
        import app.services.aviso_de_fila_longa as A

        chave_da_espera = A.CHAVE_DA_ESPERA.format(escopo=ESCOPO_A)
        check("enquanto ha fila, o relogio da espera da A existe",
              duble.dados.get(chave_da_espera) is not None)
        envio2 = Envio()
        contagem2, desfazer2 = _com_o_aviso(duble, banco, envio2, ligado=True)
        try:
            # Sem chave nenhuma no Redis: a fila de todo mundo zerou.
            for chave in [k for k in list(duble.dados) if k.startswith("whatsapp_buffer:")]:
                duble.dados.pop(chave, None)
            await bp["check_buffers"]()
        finally:
            desfazer2()
        check("🔴 a fila zerou -> `esquecer_espera` apagou o relogio (senao o "
              "'esperando ha' nunca voltaria a zero)",
              duble.dados.get(chave_da_espera) is None,
              duble.dados.get(chave_da_espera))
        desligar()

    asyncio.run(corpo())


def caso_F6():
    _p("\n=== F6. com a flag AUSENTE o aviso custa ZERO — nem Redis, nem banco ===")

    async def corpo():
        duble, servico, bp = preparar(cota=2)
        webhook = webhook_real()
        banco = banco_das_duas()
        envio = Envio()
        borda = Atendimento(webhook, demora_s=0.03)
        desligar = _ligar_check_buffers(bp, duble, servico, borda)
        await semear(servico, ESCOPO_A, 8)
        V._andar(30)
        _envelhecer_a_espera(duble, ESCOPO_A, 600)

        contagem, desfazer = _com_o_aviso(duble, banco, envio, ligado=False)
        try:
            resumo = await bp["check_buffers"]()
        finally:
            desfazer()
        check("flag ausente -> ZERO avisos", not envio.avisos, envio.avisos)
        check("🔴 flag ausente -> ZERO consultas do modulo de aviso ao Redis "
              "(a flag e o PRIMEIRO teste, nao o ultimo)",
              contagem["redis"] == 0, contagem)
        check("🔴 flag ausente -> ZERO consultas ao banco",
              contagem["banco"] == 0, contagem)
        check("e a varredura atendeu normalmente assim mesmo",
              (resumo or {}).get("processadas", 0) >= 2, resumo)

        # CONTROLE: o MESMO cenário com a flag ligada avisa. Sem esta linha, o
        # zero acima poderia ser mérito de qualquer coisa (CLAUDE.md §9.2).
        envio2 = Envio()
        contagem2, desfazer2 = _com_o_aviso(duble, banco, envio2, ligado=True)
        try:
            await bp["check_buffers"]()
        finally:
            desfazer2()
        check("CONTROLE: com a flag LIGADA, o mesmo cenario avisa UMA vez",
              len(envio2.avisos) == 1, envio2.avisos)
        desligar()

    asyncio.run(corpo())


def caso_F7():
    _p("\n=== F7. o aviso que EXPLODE nao derruba a varredura de 1 s ===")

    async def corpo():
        duble, servico, bp = preparar(cota=4)
        webhook = webhook_real()
        borda = Atendimento(webhook)
        desligar = _ligar_check_buffers(bp, duble, servico, borda)
        await semear(servico, ESCOPO_A, 2)
        await semear(servico, ESCOPO_B, 2, inicio=900)
        V._andar(30)

        async def aviso_que_explode(_resumo):
            raise RuntimeError("o grupo da corretora recusou a mensagem")

        bp["avisar_os_donos_da_fila"] = aviso_que_explode
        resumo = await bp["check_buffers"]()
        check("🔴 a varredura devolveu a conta mesmo com o aviso explodindo",
              resumo is not None, resumo)
        check("🔴 e as 4 conversas foram respondidas assim mesmo",
              len(borda.respostas) == 4, borda.respostas)
        desligar()

    asyncio.run(corpo())


# ===========================================================================
# INFRAESTRUTURA
# ===========================================================================
# ===========================================================================
# F8 — 🔴 QUEM CONSOME AVISA: o re-planejamento do turno também
# ===========================================================================
#
# 📊 O defeito, medido em 21/09/2026 (`juiz/medir2.py`, M5b):
#
#     M5b r2.adiadas.turno=1 | r3.expiradas=1
#         (a mensagem foi RESPONDIDA no mesmo turno — não se perdeu)
#
# A mensagem que chega no meio do turno é absorvida pela MESMA resposta
# (`webhook.py`, `mesclar_o_que_chegou` — §6.3). Ela sai do Redis pela mão do
# webhook, não do varredor. A varredura seguinte não a acha no SCAN e, sem
# aviso, chama de "mensagem de segurado perdida" uma mensagem que foi
# respondida — na tela que o Founder olha todo dia.
#
# ⛔ O elo tem DOIS lados, e os dois são provados aqui:
#   ① o webhook REAL chama `marcar_consumida` no laço do re-planejamento (AST)
#   ② com o aviso, a conta fecha; SEM o aviso (linha de controle), ela mente
def caso_F8():
    _p("\n=== F8. a mensagem absorvida pelo re-planejamento NAO e' perda ===")

    # ---------------------------------------------------------------- ①
    fonte = io.open(WEBHOOK_PY, encoding="utf-8").read()
    arvore = ast.parse(fonte)
    alvo = [n for n in ast.walk(arvore)
            if isinstance(n, ast.AsyncFunctionDef)
            and n.name == "process_whatsapp_message_background"]
    check("o caminho real do atendimento existe", bool(alvo))
    chamou = False
    perto_do_mesclar = False
    if alvo:
        for no in ast.walk(alvo[0]):
            if isinstance(no, ast.Call) and getattr(no.func, "id", "") == \
                    "marcar_consumida":
                chamou = True
        # ...e a chamada mora no MESMO laço do `mesclar_o_que_chegou`: e' de la'
        # que a mensagem sai do Redis.
        for no in ast.walk(alvo[0]):
            if not isinstance(no, ast.For):
                continue
            texto = ast.unparse(no)
            if "mesclar_o_que_chegou" in texto and "marcar_consumida" in texto:
                perto_do_mesclar = True
    check("🔴 o webhook REAL avisa o consumo (`marcar_consumida`)", chamou,
          "sem chamador, a anotacao existiria e ninguem a escreveria")
    check("e o aviso esta DENTRO do laco do re-planejamento", perto_do_mesclar)

    # ---------------------------------------------------------------- ②
    async def corpo(avisa):
        duble, servico, bp = preparar(cota=2)
        chave = V.M.MessageBufferService.chave(servico, ESCOPO_A, V.TEL % 0) \
            if False else None
        await semear(servico, ESCOPO_A, 1)
        V._andar(30)
        _c, chaves = await duble.scan(0, match="whatsapp_buffer:*")
        chave = list(chaves)[0]

        p1 = asyncio.Event(); f1 = asyncio.Event()
        p2 = asyncio.Event(); f2 = asyncio.Event()

        async def borda(payload_dict=None, chave_do_buffer="", **kw):
            p1.set()
            await f1.wait()
            novos = await servico.mesclar_o_que_chegou(chave_do_buffer)
            if novos and avisa:
                # E' a linha que o webhook REAL executa (conferida em ① acima).
                bp["marcar_consumida"](chave_do_buffer)
            p2.set()
            await f2.wait()

        v1 = asyncio.create_task(bp["processar_buffers_prontos"](
            [chave], servico, borda))
        await p1.wait()
        # ...uma mensagem nova do MESMO segurado chega no meio do turno.
        await semear(servico, ESCOPO_A, 1)
        await V._envelhecer(servico, chave, ocioso_s=30, idade_s=30)
        # A varredura seguinte encontra a trava de turno e ADIA por `turno`.
        r2 = await bp["processar_buffers_prontos"]([chave], servico, borda)
        f1.set()
        await p2.wait()          # o turno absorveu a mensagem nova
        # E agora a varredura seguinte: a chave nao esta mais no Redis.
        r3 = await bp["processar_buffers_prontos"]([], servico, borda)
        f2.set()
        await v1
        return r2, r3

    r2, r3 = asyncio.run(corpo(True))
    _p("      📊 COM o aviso: adiadas.turno=%d -> expiradas=%d"
       % (r2["adiadas"]["turno"], r3["expiradas"]))
    check("a mensagem nova foi mesmo ADIADA por `turno` (o cenario aconteceu)",
          r2["adiadas"]["turno"] == 1, r2)
    check("🔴 e ela NAO virou 'mensagem perdida' — foi respondida no mesmo turno",
          r3["expiradas"] == 0, r3)

    # 🔴 LINHA DE CONTROLE: sem o aviso, o MESMO cenario conta uma perda falsa.
    r2b, r3b = asyncio.run(corpo(False))
    _p("      📊 CONTROLE (sem o aviso): expiradas=%d" % r3b["expiradas"])
    check("CONTROLE: sem `marcar_consumida` a MESMA rajada vira perda falsa",
          r3b["expiradas"] == 1,
          "deu %d — se nao contasse, o merito do aviso iria para o lugar errado "
          "(CLAUDE.md §9.2)" % r3b["expiradas"])


CASOS = {"F1": caso_F1, "F2": caso_F2, "F4": caso_F4, "F5": caso_F5,
         "F6": caso_F6, "F7": caso_F7, "F8": caso_F8}

_TRY_DO_AVISO = """        try:
            await avisar_os_donos_da_fila(resumo)
        except Exception as erro:  # noqa: BLE001
            logger.warning("[ISOLAMENTO] aviso ao dono nao saiu (%s)",
                           type(erro).__name__)
"""

#: (descrição, [(arquivo, velho, novo)], casos que TÊM de ficar VERMELHOS)
MUTACOES = {
    "M-FIO-1": ("o processador renomeia o kwarg do relogio (o webhook nao aceita)",
                [(BUFFER_PY, 'extras["relogio_da_fila"] = relogio',
                  'extras["relogio_da_fila_novo"] = relogio')],
                ["F1"]),
    "M-FIO-2": ("o contador muda de nome de um lado so (em_espera)",
                [(MBS_PY, '"em_espera": str(max(0, int(em_espera))),',
                  '"em_espera_agora": str(max(0, int(em_espera))),')],
                ["F2"]),
    # ANCORA ATUALIZADA em 21/09/2026 (conserto unico): a expressao virou a
    # variavel `desde_a_espera`, lida no INSTANTE DO CONSUMO — porque e' ali que
    # a chave sai de `aguardando`. A mutacao continua sendo a MESMA ideia.
    "M-FIO-3": ("a espera pela cota volta a ser a da ULTIMA tentativa",
                [(BUFFER_PY,
                  """                            desde_a_espera = estado["esperando_desde"].get(
                                chave, entrou_na_disputa)""",
                  "                            desde_a_espera = entrou_na_disputa  # MUTACAO")],
                ["F1"]),
    "M-FIO-4": ("o aviso leva o TOTAL da varredura, e nao a fila da corretora",
                [(BUFFER_PY,
                  """        na_fila = int((motivos or {}).get("cota") or 0) + \\
            int((motivos or {}).get("breaker") or 0)""",
                  '        na_fila = int((resumo or {}).get("adiadas", {}).get("cota") or 0)')],
                ["F5"]),
    "M-FIO-5": ("o aviso sai de DENTRO do try da varredura",
                [(BUFFER_PY, _TRY_DO_AVISO,
                  "        await avisar_os_donos_da_fila(resumo)\n")],
                ["F7"]),
    "M-FIO-6": ("a flag deixa de ser o primeiro teste do aviso",
                [(BUFFER_PY,
                  "    if not aviso.aviso_ligado():\n        return 0",
                  "    if False:\n        return 0")],
                ["F6"]),
    # O elo do conserto unico: o webhook deixa de avisar que consumiu a
    # mensagem absorvida pelo re-planejamento -> a varredura seguinte chama de
    # "mensagem perdida" uma mensagem que foi RESPONDIDA.
    "M-FIO-7": ("o re-planejamento deixa de avisar o consumo",
                [(WEBHOOK_PY,
                  "                        marcar_consumida(chave_do_buffer)",
                  "                        pass  # MUTACAO")],
                ["F8"]),
}


def _mutar(nome):
    descricao, trocas, casos = MUTACOES[nome]
    backups = []
    try:
        for arquivo, velho, novo in trocas:
            fonte = io.open(arquivo, encoding="utf-8").read()
            if velho not in fonte:
                _p("[%s] ALVO NAO ENCONTRADO — a mutacao precisa ser atualizada:\n%s"
                   % (nome, velho[:160]))
                return 1
            if arquivo not in [b[0] for b in backups]:
                backup = arquivo + ".backup_mutacao_fio"
                shutil.copyfile(arquivo, backup)      # 🔴 por CÓPIA
                backups.append((arquivo, backup))
            io.open(arquivo, "w", encoding="utf-8", newline="\n").write(
                fonte.replace(velho, novo, 1))
        ruim = 0
        for caso in casos:
            proc = subprocess.run([sys.executable, ESTE, "--so", caso], cwd=RAIZ,
                                  capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=900,
                                  env={**os.environ, "PYTHONIOENCODING": "utf-8",
                                       "PYTHONDONTWRITEBYTECODE": "1"})
            vermelho = proc.returncode != 0
            falhas = [l.strip() for l in (proc.stdout or "").splitlines()
                      if "[FALHOU]" in l]
            _p("[%s] %s -> caso %s: %s" % (
                nome, descricao, caso,
                ("VERMELHO ✅ | " + (falhas[0][:170] if falhas else ""))
                if vermelho else "VERDE ❌ (o guarda e carimbo)"))
            if not vermelho:
                ruim = 1
                _p((proc.stdout or proc.stderr)[-1200:])
        return ruim
    finally:
        for arquivo, backup in backups:
            shutil.copyfile(backup, arquivo)
            os.remove(backup)


def principal(argv):
    if "--mutar" in argv:
        pos = argv.index("--mutar")
        nomes = ([argv[pos + 1]] if len(argv) > pos + 1
                 and not argv[pos + 1].startswith("--") else sorted(MUTACOES))
        return 1 if sum(_mutar(n) for n in nomes) else 0

    escolhidos = [argv[argv.index("--so") + 1]] if "--so" in argv else list(CASOS)
    for nome in escolhidos:
        try:
            CASOS[nome]()
        except Exception as exc:  # noqa: BLE001
            import traceback
            check("o caso %s EXPLODIU" % nome, False,
                  "%s: %s\n%s" % (type(exc).__name__, exc,
                                  traceback.format_exc()[-1500:]))
    _p("\n%s\nRESUMO DO FIO: %d ok, %d falhas\n%s" % ("=" * 64, PASS, FAIL, "=" * 64))
    return 1 if FAIL else 0


def test_o_fio_inteiro_do_isolamento():
    """Ponte para o pytest — o mesmo caminho do script."""
    assert principal([]) == 0, "%d assercoes falharam" % FAIL


if __name__ == "__main__":
    sys.exit(principal(sys.argv[1:]))
