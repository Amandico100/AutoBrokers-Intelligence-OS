# -*- coding: utf-8 -*-
"""SPEC-078 Bloco A — as duas portas que dependiam de sorte, agora trancadas.

O que este arquivo prova
------------------------
A.1  `platform_outbound.send_to_client_guarded` lê o interruptor de atendimento
     ANTES de qualquer outra coisa. Agente desligado → não sai nada.
A.2  `routine_engine._deliver` nunca entrega por um número `observer`, e o
     motivo da recusa chega inteiro em `routine_runs.error`.

Por que cada bloco tem uma linha de CONTROLE (CLAUDE.md §9.2)
-------------------------------------------------------------
Um guarda que recusa TUDO passa em qualquer teste que só verifique recusa. As
duas asserções marcadas 🔴 CONTROLE são as que dão direito à conclusão: elas
repetem o mesmo cenário com o único fator invertido (agente ligado / canal que
pode enviar) e exigem que o envio ACONTEÇA. Sem elas, um `return False` no topo
da função deixaria este arquivo verde.

Sem banco, sem rede, sem pytest — o mundo de fora é todo dublê. A ÚNICA peça
carregada de verdade além dos dois módulos sob teste é
`IntegrationService.pode_enviar`, porque ela é a autoridade que o Bloco A passou
a usar: reescrever a regra aqui provaria que sei copiar uma frozenset, não que o
motor consulta a autoridade certa.
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import types
from typing import Any, Dict, List

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PASS = FAIL = 0


def check(nome: str, cond: bool, extra: Any = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print("  [ok] " + nome)
    else:
        FAIL += 1
        print("  [FALHOU] " + nome + ("  " + str(extra)[:260] if extra else ""))


def rodar(coro):
    return asyncio.run(coro)


# ===========================================================================
# O mundo de fora, todo de mentira
# ===========================================================================

class _Resultado:
    def __init__(self, data=None):
        self.data = data or []


class _Tabela:
    def __init__(self, banco, nome):
        self.banco, self.nome = banco, nome
        self._modo = None
        self._payload = None
        self._eq: List = []

    def select(self, *_a, **_k):
        self._modo = "select"
        return self

    def insert(self, payload):
        self._modo = "insert"
        self._payload = payload
        return self

    def update(self, payload):
        self._modo = "update"
        self._payload = payload
        return self

    def eq(self, col, val):
        self._eq.append((col, val))
        return self

    def neq(self, *_a):
        return self

    def gte(self, *_a):
        return self

    def lte(self, *_a):
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a):
        return self

    def _linhas(self):
        linhas = list(self.banco.dados.get(self.nome, []))
        for col, val in self._eq:
            linhas = [r for r in linhas if str(r.get(col)) == str(val)]
        return linhas

    def execute(self):
        self.banco.dados.setdefault(self.nome, [])
        if self._modo == "insert":
            linha = dict(self._payload)
            linha.setdefault("id", f"{self.nome}-{len(self.banco.dados[self.nome]) + 1}")
            self.banco.dados[self.nome].append(linha)
            return _Resultado([linha])
        if self._modo == "update":
            achadas = self._linhas()
            for r in achadas:
                r.update(self._payload)
            return _Resultado(achadas)
        return _Resultado(self._linhas())


class _Banco:
    def __init__(self):
        self.dados: Dict[str, list] = {}
        self.client = self

    def table(self, nome):
        return _Tabela(self, nome)


class _Redis:
    def __init__(self):
        self.kv: Dict[str, Any] = {}
        self.listas: Dict[str, list] = {}
        self.expira: Dict[str, int] = {}

    async def get(self, k):
        return self.kv.get(k)

    async def set(self, k, v, ex=None, nx=False):
        if nx and k in self.kv:
            return None
        self.kv[k] = v
        if ex:
            self.expira[k] = int(ex)
        return True

    async def ttl(self, k):
        return self.expira.get(k, -1)

    async def delete(self, k):
        self.kv.pop(k, None)
        return 1

    async def rpush(self, k, v):
        self.listas.setdefault(k, []).append(v)
        return len(self.listas[k])

    async def lpop(self, k):
        lst = self.listas.get(k) or []
        return lst.pop(0) if lst else None

    async def llen(self, k):
        return len(self.listas.get(k) or [])

    async def hincrby(self, *_a):
        return 1


def _carregar(dotted: str, rel: str):
    caminho = os.path.join(BACKEND, *rel.split("/"))
    spec = importlib.util.spec_from_file_location(dotted, caminho)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = mod
    spec.loader.exec_module(mod)
    return mod


def _pacotes(*nomes):
    for n in nomes:
        m = sys.modules.setdefault(n, types.ModuleType(n))
        m.__path__ = []


def _integration_service_de_verdade():
    """Carrega o `integration_service` REAL — só ele, com o resto dublado.

    O módulo puxa `app.core.config.settings`, que puxa o SDK da OpenAI e não
    sobe numa máquina de teste. Dublar a CONFIGURAÇÃO é legítimo; dublar
    `pode_enviar` não seria, porque é justamente a autoridade que a SPEC-078 A.2
    mandou consultar.
    """
    _pacotes("app", "app.core", "app.services", "app.services.whatsapp")
    cfg = types.ModuleType("app.core.config")
    cfg.settings = types.SimpleNamespace(OPENAI_API_KEY="")
    sys.modules["app.core.config"] = cfg
    seg = types.ModuleType("app.services.whatsapp.integration_secrets")
    seg.prepare_integration_for_runtime = lambda i, **k: i
    sys.modules["app.services.whatsapp.integration_secrets"] = seg
    sup = types.ModuleType("supabase")
    sup.Client = object
    sys.modules.setdefault("supabase", sup)
    return _carregar("app.services.integration_service", "app/services/integration_service.py")


# ===========================================================================
print("\n[A.1] O INTERRUPTOR DO ATENDIMENTO, LIDO NA FUNÇÃO QUE ENVIA")
# ===========================================================================

def montar_outbound():
    banco, redis = _Banco(), _Redis()
    _pacotes("app", "app.core", "app.services", "app.services.atlas")

    db = types.ModuleType("app.core.database")
    db.get_supabase_client = lambda: banco
    sys.modules["app.core.database"] = db

    red = types.ModuleType("app.core.redis")

    async def _cliente():
        return redis

    red.get_async_redis_client = _cliente
    sys.modules["app.core.redis"] = red

    obs = types.ModuleType("app.services.atlas.observer_intake")
    obs._br_variants = lambda p: {"".join(c for c in str(p) if c.isdigit())}
    sys.modules["app.services.atlas.observer_intake"] = obs

    # O INTERRUPTOR. `interruptor["ligado"]` é o único fator que os dois
    # cenários abaixo variam — é ele que a linha de controle inverte.
    interruptor = {"ligado": False, "explode": False}
    cap = types.ModuleType("app.services.atlas.attendance_capture")

    async def _ativo(company_id):
        if interruptor["explode"]:
            raise RuntimeError("supabase fora do ar")
        return bool(interruptor["ligado"])

    cap.attendance_agent_active = _ativo
    sys.modules["app.services.atlas.attendance_capture"] = cap

    dr = types.ModuleType("app.services.dispatch_router")

    async def _sem_acionamento(_c):
        return []

    dr.list_active_dispatches = _sem_acionamento
    sys.modules["app.services.dispatch_router"] = dr

    act = types.ModuleType("app.services.activity_log")
    act.registrado = []

    async def _log(company_id, categoria, titulo, detalhe=""):
        act.registrado.append({"company_id": company_id, "titulo": titulo})

    act.log_activity = _log
    sys.modules["app.services.activity_log"] = act

    integ = types.ModuleType("app.services.integration_service")

    class _IS:
        def get_platform_whatsapp_integration(self, _c):
            return {"id": "canal-1", "purpose": "auxiliary"}

    integ.get_integration_service = lambda: _IS()
    sys.modules["app.services.integration_service"] = integ

    wa = types.ModuleType("app.services.whatsapp_service")
    wa.enviados = []

    class _WA:
        def send_message(self, numero, texto, _integ):
            wa.enviados.append({"para": numero, "texto": texto})
            return True

    wa.get_whatsapp_service = lambda: _WA()
    sys.modules["app.services.whatsapp_service"] = wa

    po = _carregar("app.services.platform_outbound", "app/services/platform_outbound.py")
    # Janela e espaçamento têm teste próprio (`test_governador_de_envio.py`) e
    # dependem do relógio da máquina. Neutralizo SÓ eles: um teste de guarda que
    # fica vermelho às 21:00 não informa nada sobre o guarda.
    po.avaliar_vazao = lambda **k: po.Veredito(True, "governador neutralizado neste teste", 0)
    return po, wa, banco, redis, interruptor


po, wa, banco, redis_po, interruptor = montar_outbound()

# ---- 1) agente DESLIGADO ---------------------------------------------------
interruptor["ligado"] = False
wa.enviados.clear()
res = rodar(po.send_to_client_guarded("amandus", "5547999112233",
                                      "Sua parcela vence amanhã", "billing",
                                      "cobrança da parcela 3"))
check("agente desligado: o envio é RECUSADO", res.get("ok") is False, res)
check("e o motivo é nomeado — 'agente_desligado', não um erro genérico",
      res.get("reason") == "agente_desligado", res)
check("nada saiu pelo canal de WhatsApp", not wa.enviados, wa.enviados)
check("e nada foi guardado na fila para sair depois — guardar enquanto o "
      "agente está desligado é a mesma rajada, só adiada",
      res.get("queued") is False and not any(redis_po.listas.values()),
      f"{res} / {redis_po.listas}")
check("nem virou linha em platform_sends", not banco.dados.get("platform_sends"),
      banco.dados.get("platform_sends"))

# ---- 2) 🔴 CONTROLE: o MESMO envio com o agente LIGADO ---------------------
# Esta é a asserção que dá direito à conclusão da anterior. Um guarda que
# recusasse tudo — `return {"ok": False}` no topo — passaria em [1] e morreria
# aqui.
interruptor["ligado"] = True
wa.enviados.clear()
res_on = rodar(po.send_to_client_guarded("amandus", "5547999112233",
                                         "Sua parcela vence amanhã", "billing",
                                         "cobrança da parcela 3"))
check("CONTROLE: agente LIGADO, mesmo envio — CHEGA no caminho de envio",
      res_on.get("ok") is True and len(wa.enviados) == 1, f"{res_on} / {wa.enviados}")
check("CONTROLE: e o texto que saiu é o mesmo que entrou",
      wa.enviados and wa.enviados[0]["texto"] == "Sua parcela vence amanhã", wa.enviados)
check("CONTROLE: o envio liberado fica registrado em platform_sends",
      len(banco.dados.get("platform_sends") or []) == 1,
      banco.dados.get("platform_sends"))

# ---- 3) o guarda vem ANTES do atalho quente -------------------------------
# `temperatura=QUENTE` pula fila de cortesia e governador. Se o interruptor
# ficasse depois dele, todo chamador quente furaria a trava.
interruptor["ligado"] = False
wa.enviados.clear()
quente = rodar(po.send_to_client_guarded("amandus", "5547999112233", "oi",
                                         "atendimento", temperatura=po.QUENTE))
check("o atalho QUENTE também respeita o interruptor",
      quente.get("reason") == "agente_desligado" and not wa.enviados,
      f"{quente} / {wa.enviados}")

# ---- 4) não conseguir LER o interruptor não é permissão -------------------
interruptor["ligado"] = True
interruptor["explode"] = True
wa.enviados.clear()
cego = rodar(po.send_to_client_guarded("amandus", "5547999112233", "oi", "billing"))
check("leitura do interruptor falhando -> FECHA (não sai)",
      cego.get("reason") == "agente_desligado" and not wa.enviados, f"{cego}")
interruptor["explode"] = False


# ===========================================================================
print("\n[A.2] O OBSERVER NUNCA É CANAL DE SAÍDA DE ROTINA")
# ===========================================================================

def montar_rotinas():
    banco = _Banco()
    _pacotes("app", "app.core", "app.services")

    db = types.ModuleType("app.core.database")
    db.get_supabase_client = lambda: banco
    sys.modules["app.core.database"] = db

    _integration_service_de_verdade()   # a autoridade, de verdade

    wa = types.ModuleType("app.services.whatsapp_service")
    wa.enviados = []

    class _WA:
        def send_message(self, numero, texto, integ):
            wa.enviados.append({"para": numero, "texto": texto,
                                "purpose": integ.get("purpose"), "id": integ.get("id")})
            return True

    wa.get_whatsapp_service = lambda: _WA()
    sys.modules["app.services.whatsapp_service"] = wa

    re_mod = _carregar("app.services.routine_engine", "app/services/routine_engine.py")
    return re_mod, banco, wa


RE, banco_r, wa_r = montar_rotinas()

ROTINA = {"id": "r-1", "company_id": "autofleet", "name": "Cobrança de boletos",
          "delivery": {"channel": "whatsapp", "number": "5547999110000"}}
RELATORIO = "Relatório da rotina — 3 boletos, CPF 123.456.789-01, tel 5547999112233"

# ---- 5) só `observer` ativo -----------------------------------------------
# 📊 Este é o estado medido de AutoFleet e AMANDUS em 17/08/2026.
banco_r.dados["integrations"] = [
    {"id": "i-obs", "company_id": "autofleet", "is_active": True, "purpose": "observer"},
    {"id": "i-off", "company_id": "autofleet", "is_active": False, "purpose": "auxiliary"},
]
wa_r.enviados.clear()
ok, motivo = rodar(RE._deliver(ROTINA, RELATORIO))
check("só observer ativo: a entrega é RECUSADA", ok is False, motivo)
check("e o relatório com CPF e telefone NÃO saiu pelo número calado",
      not wa_r.enviados, wa_r.enviados)
check("o motivo explica que é o observador — não manda o corretor caçar "
      "um defeito de conexão que não existe",
      "observ" in motivo.lower(), motivo)

# ---- 6) 🔴 CONTROLE: a MESMA corretora com um canal `auxiliary` ativo ------
# Sem esta linha, `_find_integration` podendo devolver None sempre passaria.
banco_r.dados["integrations"].append(
    {"id": "i-aux", "company_id": "autofleet", "is_active": True, "purpose": "auxiliary"})
wa_r.enviados.clear()
ok2, motivo2 = rodar(RE._deliver(ROTINA, RELATORIO))
check("CONTROLE: mesma corretora com canal `auxiliary` ativo — ENTREGA",
      ok2 is True and len(wa_r.enviados) == 1, f"{ok2} / {motivo2} / {wa_r.enviados}")
check("CONTROLE: e saiu pelo auxiliary, nunca pelo observer",
      wa_r.enviados and wa_r.enviados[0]["purpose"] == "auxiliary", wa_r.enviados)

# ---- 7) o rank continua valendo ENTRE as elegíveis -------------------------
banco_r.dados["integrations"] = [
    {"id": "i-att", "company_id": "autofleet", "is_active": True, "purpose": "attendance"},
    {"id": "i-aux", "company_id": "autofleet", "is_active": True, "purpose": "auxiliary"},
]
wa_r.enviados.clear()
ok3, _ = rodar(RE._deliver(ROTINA, RELATORIO))
check("auxiliary E attendance ativos: prefere o `auxiliary` (isola o outreach)",
      ok3 is True and wa_r.enviados and wa_r.enviados[0]["id"] == "i-aux", wa_r.enviados)

# 🔴 CONTROLE do rank: com observer + attendance, o escolhido tem de ser o
# attendance. Se o observer só tivesse ficado "por último" — o defeito de
# origem — esta ordem passaria e a de cima também.
banco_r.dados["integrations"] = [
    {"id": "i-obs", "company_id": "autofleet", "is_active": True, "purpose": "observer"},
    {"id": "i-att", "company_id": "autofleet", "is_active": True, "purpose": "attendance"},
]
wa_r.enviados.clear()
ok4, _ = rodar(RE._deliver(ROTINA, RELATORIO))
check("CONTROLE: observer + attendance -> sai pelo attendance, "
      "o observer é EXCLUÍDO e não apenas desempatado",
      ok4 is True and wa_r.enviados and wa_r.enviados[0]["id"] == "i-att", wa_r.enviados)

# ---- 8) a autoridade é uma só ---------------------------------------------
IS = sys.modules["app.services.integration_service"].IntegrationService
check("quem decide é `IntegrationService.pode_enviar` (SPEC-063 D), "
      "não uma segunda lista dentro do motor de rotinas",
      IS.pode_enviar({"purpose": "observer"}) is False
      and IS.pode_enviar({"purpose": "auxiliary"}) is True)
fonte = open(os.path.join(BACKEND, "app", "services", "routine_engine.py"),
             encoding="utf-8").read()
check("e o motor de rotinas não recria a lista de propósitos proibidos",
      "pode_enviar" in fonte and "PROPOSITOS_QUE_NUNCA_ENVIAM" not in fonte)


# ===========================================================================
print("\n[A.2b] O MOTIVO CHEGA EM routine_runs.error — não é engolido")
# ===========================================================================
# Uma recusa que só aparece no log do contêiner é, para o corretor, um relatório
# que sumiu. `_execute_routine` é quem transforma o motivo em linha de banco.

bc = types.ModuleType("app.services.billing_collection")
bc.is_billing_routine = lambda r: True


async def _executa(_supa, _rot):
    return RELATORIO


bc.execute_billing_collection_routine = _executa
sys.modules["app.services.billing_collection"] = bc

act2 = types.ModuleType("app.services.activity_log")


async def _log2(*_a, **_k):
    return None


act2.log_activity = _log2
sys.modules["app.services.activity_log"] = act2

banco_r.dados["integrations"] = [
    {"id": "i-obs", "company_id": "autofleet", "is_active": True, "purpose": "observer"},
]
banco_r.dados["routines"] = [dict(ROTINA, consecutive_failures=0)]
banco_r.dados["routine_runs"] = []
wa_r.enviados.clear()
rodar(RE._execute_routine(banco_r, dict(ROTINA)))
runs = banco_r.dados.get("routine_runs") or []
erro = (runs[0].get("error") or "") if runs else ""
check("a execução vira uma linha em routine_runs", len(runs) == 1, runs)
check("com status de erro", runs and runs[0].get("status") == "error", runs)
check("e o motivo da recusa está ESCRITO lá, legível",
      "entrega falhou" in erro and "observ" in erro.lower(), erro)
check("nada saiu pelo observer nem por acidente", not wa_r.enviados, wa_r.enviados)

# 🔴 CONTROLE: a mesma execução com canal que pode enviar termina `ok` e sem
# erro. Sem isto, um `_execute_routine` que gravasse "error" sempre passaria.
banco_r.dados["integrations"] = [
    {"id": "i-aux", "company_id": "autofleet", "is_active": True, "purpose": "auxiliary"},
]
banco_r.dados["routine_runs"] = []
wa_r.enviados.clear()
rodar(RE._execute_routine(banco_r, dict(ROTINA)))
runs_ok = banco_r.dados.get("routine_runs") or []
check("CONTROLE: com canal `auxiliary`, a mesma rotina termina ok e sem erro",
      len(runs_ok) == 1 and runs_ok[0].get("status") == "ok"
      and not runs_ok[0].get("error") and len(wa_r.enviados) == 1,
      f"{runs_ok} / {wa_r.enviados}")


# ===========================================================================
print("\n[A.4] `agent_enabled` parou de apontar para um leitor que não existe")
# ===========================================================================
RAIZ = os.path.dirname(BACKEND)
nodes = open(os.path.join(BACKEND, "app", "agents", "nodes.py"), encoding="utf-8").read()
check("MEDIDO 17/08: o runtime continua sem ler `agent_enabled` "
      "(grep em backend/app/agents/nodes.py -> zero)",
      "agent_enabled" not in nodes)
portao = open(os.path.join(BACKEND, "app", "services", "portao_do_prompt.py"),
              encoding="utf-8").read()
check("o portão escreve o fato: a coluna é legada e não tem leitor no runtime",
      "sem leitor no runtime" in portao.lower(), portao[7000:7400])
# A frase antiga continua no arquivo — de propósito, entre aspas, como a
# afirmação que foi DESMENTIDA. O que não pode é ela voltar a valer como
# instrução. Por isso a prova é de ORDEM: o `nodes.py` só aparece depois do
# aviso de correção. (CLAUDE.md §9.3 — a lição migra, não morre.)
i_corr = portao.find("CORRIGIDO EM 17/08/2026")
i_nodes = portao.find("nodes.py")
check("e `nodes.py` só é citado DEPOIS do aviso de correção — como afirmação "
      "desmentida, nunca como onde conferir o interruptor",
      i_corr >= 0 and i_nodes > i_corr, f"corr={i_corr} nodes={i_nodes}")
check("ele agora nomeia o interruptor de verdade (`agents.is_active`/attendance)",
      "is_active" in portao and "attendance_agent_active" in portao)

for rel in ("app/api/admin/sandbox/bootstrap-tenant/route.ts",
            "lib/admin/blueprint-studio-store.ts",
            "components/admin/AgentConfigModal.tsx"):
    src = open(os.path.join(RAIZ, *rel.split("/")), encoding="utf-8").read()
    trechos = src.split("agent_enabled: true")
    check(f"{rel}: TODO `agent_enabled: true` do nascimento avisa que não liga nada",
          len(trechos) > 1 and all("não liga" in t[-400:].lower() for t in trechos[:-1]),
          f"{len(trechos) - 1} ocorrência(s)")

print("\n" + "=" * 70)
print(f"  {PASS} asserções verdes · {FAIL} vermelhas")
print("=" * 70)
sys.exit(1 if FAIL else 0)
