# -*- coding: utf-8 -*-
"""SPEC-121 · CONSERTO ÚNICO · B1 do red team — o pedido do CARRO RESERVA não é
"🚨 NOVO SINISTRO", e o dossiê leva o que o segurado contou (P3).

O DEFEITO, MEDIDO
=================
📊 29/09/2026 (red team, `scratchpad/julgamento/rt2_dossie.py`, dublê no envio):

    yelum  sem nº do sinistro   -> carro_reserva_sem_sinistro | tipo = sinistro | 🚨 *NOVO SINISTRO*
    zurich com nº               -> carro_reserva_por_desenho  | tipo = sinistro | 🚨 *NOVO SINISTRO*
    zurich pane mecânica        -> carro_reserva_por_desenho  | tipo = sinistro | 🚨 *NOVO SINISTRO*

A COSTURA: `corridor_playbooks.antes_de_acionar` escreve o motivo em PROSA (com a
palavra "sinistro"), o agente a copia para `request_human_agent`, e
`human_handoff._avisar_suporte` passava a prosa por `claims_shadow.detectar_sinistro`.
Nenhum teste da SPEC atravessava as duas fatias.

O QUE ESTE ARQUIVO PROVA — o FIO real, dublê só na borda (banco, Redis, WhatsApp,
destino do grupo, relógio da seguradora)
=================================================================================
  ① para CADA motivo que `antes_de_acionar` devolve (o MOTOR real, como a ferramenta
    de acionamento o chama), a ficha é gravada pelo escritor REAL
    (`nodes._gravar_ficha_do_turno`), o agente chama `request_human_agent` com a
    PROSA do motivo (`HumanHandoffTool._arun` real) e a porta real do grupo decide:
      · tipo ao grupo = `pedido_de_ajuda` e 1ª linha ≠ NOVO SINISTRO
      · `claims.handoff_pedido` com `motivo_enum='outro'`
      · 🔴 CONTROLE D10: raio que queimou equipamento → `sinistro` e 🚨 NOVO SINISTRO
  ② o dossiê do carro reserva leva quem retira, cidade, data/hora, CNH+cartão e a
    linha das diárias (P3) — e o título é 🚙 CARRO RESERVA
  ③ a marca DECLARADA (`codigo`) vale sozinha, mesmo com a ficha velha
  ④ CONTROLES do lado oposto: sinistro que o segurado CONTA (sem acionamento) →
    NOVO SINISTRO; e uma ficha de carro reserva VELHA não rebaixa um sinistro novo
  ⑤ o guarda da tabela: todo `codigo` que o motor declara tem tipo conhecido e caso
    aqui (código novo sem caso → VERMELHO)

🔴 MUTAÇÕES (rodadas em cópia, `git worktree`): `tipo_do_pedido` ignorando a marca ·
`pedido_antes_de_acionar` sem o motor (só o declarado) · sem o frescor da ficha ·
sem a seção *O PEDIDO* — cada uma fica VERMELHA aqui.

⛔ Nenhum dado pessoal: nomes, CPF e telefones inventados (faixa de teste).
Roda com `python tests/test_spec121_costura_carro_reserva_grupo.py` (exit ≠ 0 em
falha) E com `pytest`.
"""
from __future__ import annotations

import asyncio
import inspect
import os
import re
import sys
import types
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _pkg in ("app", "app.agents", "app.agents.tools", "app.core", "app.services",
             "app.services.atlas", "app.tasks"):
    if _pkg not in sys.modules:
        _m = types.ModuleType(_pkg)
        _m.__path__ = [os.path.join(_RAIZ, *_pkg.split("."))]
        sys.modules[_pkg] = _m

OK = 0
FAIL = 0


def certo(condicao, frase, detalhe=""):
    global OK, FAIL
    if condicao:
        OK += 1
        print("  ✅", frase)
    else:
        FAIL += 1
        print("  ❌", frase + (("\n       " + str(detalhe)[:600]) if detalhe else ""))


def rodar(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


# =============================================================================
# DUBLÊS — só a borda
# =============================================================================
class _Resp:
    def __init__(self, data):
        self.data = data


class _Consulta:
    """PostgREST de mentira que honra filtro, ordem, limite e o teto de 1000."""

    def __init__(self, banco, tabela):
        self.b, self.t = banco, tabela
        self.filtros, self.ordem, self.teto = [], None, None
        self.acao, self.carga = "select", None

    def select(self, *_a, **_k):
        return self

    def eq(self, c, v):
        self.filtros.append(("eq", c, v))
        return self

    def neq(self, c, v):
        self.filtros.append(("neq", c, v))
        return self

    def is_(self, c, v):
        self.filtros.append(("is", c, str(v)))
        return self

    def in_(self, c, vals):
        self.filtros.append(("in", c, [str(x) for x in vals]))
        return self

    def gte(self, c, v):
        self.filtros.append(("gte", c, v))
        return self

    def lt(self, c, v):
        self.filtros.append(("lt", c, v))
        return self

    def lte(self, c, v):
        self.filtros.append(("lte", c, v))
        return self

    def order(self, c, desc=False):
        self.ordem = (c, desc)
        return self

    def limit(self, n):
        self.teto = int(n)
        return self

    def update(self, campos):
        self.acao, self.carga = "update", dict(campos)
        return self

    def insert(self, linha):
        self.acao, self.carga = "insert", linha
        return self

    def _casa(self, linha):
        for op, c, v in self.filtros:
            x = linha.get(c)
            if op == "eq" and str(x) != str(v):
                return False
            if op == "neq" and str(x) == str(v):
                return False
            if op == "is" and ((x is None) != (v == "null")):
                return False
            if op == "in" and str(x) not in v:
                return False
            if op == "gte" and not (x is not None and str(x) >= str(v)):
                return False
            if op == "lt" and not (x is not None and str(x) < str(v)):
                return False
            if op == "lte" and not (x is not None and str(x) <= str(v)):
                return False
        return True

    def execute(self):
        fonte = self.b.tabelas.setdefault(self.t, [])
        if self.acao == "insert":
            linhas = self.carga if isinstance(self.carga, list) else [self.carga]
            fonte.extend(dict(l) for l in linhas)
            return _Resp([dict(l) for l in linhas])
        achadas = [l for l in fonte if self._casa(l)]
        if self.acao == "update":
            for l in achadas:
                l.update(self.carga)
            return _Resp([dict(l) for l in achadas])
        if self.ordem:
            c, desc = self.ordem
            achadas = sorted(achadas, key=lambda l: str(l.get(c) or ""), reverse=desc)
        teto = min(self.teto or 1000, 1000)
        return _Resp([dict(l) for l in achadas[:teto]])


class Banco:
    def __init__(self, **tabelas):
        self.tabelas = {k: list(v) for k, v in tabelas.items()}

    def table(self, nome):
        return _Consulta(self, nome)

    def eventos(self, prefixo=""):
        return [e for e in self.tabelas.get("work_events", [])
                if str(e.get("event_type") or "").startswith(prefixo)]


class _Embrulho:
    def __init__(self, banco):
        self.client = banco


class RedisFake:
    def __init__(self):
        self.chaves = {}

    async def set(self, chave, valor, ex=None, nx=False):
        if nx and chave in self.chaves:
            return None
        self.chaves[chave] = valor
        return True

    async def get(self, chave):
        return self.chaves.get(chave)

    async def delete(self, chave):
        self.chaves.pop(chave, None)

    async def incr(self, chave):
        self.chaves[chave] = int(self.chaves.get(chave) or 0) + 1
        return self.chaves[chave]

    async def expire(self, *_a, **_k):
        return True


ENVIOS: list = []
GESTOS: list = []
REDIS = RedisFake()
BANCO = {"b": None}
_ANTES = {}
FUSO_BR = timezone(timedelta(hours=-3))
#: 🕐 O relógio da SEGURADORA (CR5), fixo: terça 11h de Brasília.
RELOGIO = {"agora": datetime(2026, 10, 6, 11, 0, tzinfo=FUSO_BR)}


def _instalar(nome, modulo):
    if nome not in _ANTES:
        _ANTES[nome] = sys.modules.get(nome)
    sys.modules[nome] = modulo


def _instalar_dubles():
    red = types.ModuleType("app.core.redis")

    async def _redis():
        return REDIS
    red.get_async_redis_client = _redis
    _instalar("app.core.redis", red)

    zap = types.ModuleType("app.services.whatsapp_service")

    class _Zap:
        def send_message(self, alvo, texto, integ, bloco_unico=False):
            ENVIOS.append((alvo, texto))
            return True
    zap.get_whatsapp_service = lambda: _Zap()
    _instalar("app.services.whatsapp_service", zap)

    integ = types.ModuleType("app.services.integration_service")

    class _Integ:
        def get_whatsapp_integration(self, _empresa):
            return {"canal": "teste"}
    integ.get_integration_service = lambda _bruto=None: _Integ()
    _instalar("app.services.integration_service", integ)

    rot = types.ModuleType("app.services.dispatch_router")

    async def _destino(_empresa):
        return {"destino": "grupo-de-teste@g.us", "fonte": "teste", "recusa": ""}
    rot.resolver_destino_de_suporte = _destino
    _instalar("app.services.dispatch_router", rot)

    plat = types.ModuleType("app.services.platform_outbound")

    async def _conta(*_a, **_k):
        return None
    plat.record_platform_send = _conta
    plat.fuso_da_corretora = lambda *_a, **_k: FUSO_BR
    _instalar("app.services.platform_outbound", plat)

    feed = types.ModuleType("app.services.activity_log")

    async def _feed(*_a, **_k):
        return None
    feed.log_activity = _feed
    _instalar("app.services.activity_log", feed)

    obs = types.ModuleType("app.services.observability")
    obs.sli = types.SimpleNamespace(HANDOFF_ESPERA="x", registrar=lambda *a, **k: None)
    _instalar("app.services.observability", obs)
    _instalar("app.services.observability.sli", obs.sli)

    import app.core.database as dbreal
    _ANTES.setdefault("__get_supabase_client", dbreal.get_supabase_client)
    dbreal.get_supabase_client = lambda: _Embrulho(BANCO["b"])

    # 🕐 o relógio da seguradora (borda: o tempo), o MESMO para a ferramenta e o handoff
    import app.services.corridor_playbooks as CP
    _ANTES.setdefault("__agora_brasilia", CP._agora_brasilia)
    CP._agora_brasilia = lambda agora=None: agora if agora is not None else RELOGIO["agora"]

    # a escrita do gesto da sombra vai para o banco pela sombra (que exige work_run);
    # o dublê só GUARDA o que seria gravado — a decisão (`motivo_enum`) é do _arun.
    import app.services.claims_shadow as CS
    _ANTES.setdefault("__registrar_gesto", CS.registrar_gesto)

    async def _gesto(_db, **kw):
        GESTOS.append(kw)
        return True
    CS.registrar_gesto = _gesto


def _restaurar():
    import app.core.database as dbreal
    import app.services.claims_shadow as CS
    import app.services.corridor_playbooks as CP

    if "__get_supabase_client" in _ANTES:
        dbreal.get_supabase_client = _ANTES.pop("__get_supabase_client")
    if "__agora_brasilia" in _ANTES:
        CP._agora_brasilia = _ANTES.pop("__agora_brasilia")
    if "__registrar_gesto" in _ANTES:
        CS.registrar_gesto = _ANTES.pop("__registrar_gesto")
    for nome, antigo in list(_ANTES.items()):
        if antigo is None:
            sys.modules.pop(nome, None)
        else:
            sys.modules[nome] = antigo
    _ANTES.clear()


# =============================================================================
# O CENÁRIO — a corretora X com o agente LIGADO; o segurado acabou de escrever
# =============================================================================
X = "11111111-1111-4111-8111-111111111111"
_ENV_CANAL = "INSURER_CONTACT_YELUM_CARRO_RESERVA"


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")


def _banco(cid):
    ja = datetime.now(timezone.utc)
    conversa = {"id": cid, "company_id": X, "session_id": "ses-" + cid,
                "user_name": "Pessoa de Teste", "user_phone": "5547900000000",
                "status": "open", "claimed_by": None, "claimed_by_name": None,
                "claimed_at": None, "human_handoff_reason": None, "resolvido_em": None,
                "ficha_atendimento": None, "last_message_preview": "preciso de ajuda",
                "last_message_at": iso(ja - timedelta(seconds=30)),
                "created_at": iso(ja - timedelta(hours=1))}
    msgs = [{"conversation_id": cid, "role": "user", "content": "preciso de ajuda",
             "created_at": iso(ja - timedelta(minutes=3)), "type": "text", "payload": {}},
            {"conversation_id": cid, "role": "assistant", "content": "me conte o que houve",
             "created_at": iso(ja - timedelta(minutes=2)), "type": "text", "payload": {}},
            {"conversation_id": cid, "role": "user", "content": "é isso aí",
             "created_at": iso(ja - timedelta(seconds=30)), "type": "text", "payload": {}}]
    b = Banco(conversations=[conversa], messages=msgs,
              agents=[{"id": "ag-x", "company_id": X, "agent_role": "attendance",
                       "is_active": True, "name": "Assistente"}],
              work_events=[], company_internal_numbers=[], company_members=[],
              users_v2=[], work_waits=[], agent_activities=[])
    BANCO["b"] = b
    return b


#: O que o segurado contou para o carro reserva (inventado, faixa de teste).
DADOS_CR = {
    "titular_cpf": "00000000191", "telefone_contato": "47900000000",
    "problema_descricao": "bati o carro e ele está na oficina",
    "veiculo_placa": "TST1A23", "apolice_numero": "1234567",
    "carro_reserva_condutor_nome": "Pessoa Que Retira",
    "carro_reserva_condutor_cpf": "00000000272",
    "carro_reserva_cidade": "Cidade de Teste",
    "carro_reserva_data_hora": "08/10 às 15h",
    "carro_reserva_telefone": "47900000001",
}


def _acionar_e_pedir(cid, cia, linha, sub, slots, *, codigo_declarado=None,
                     envelhecer_ficha=False, motivo_do_agente=None, sem_acionamento=False):
    """O FIO: a ferramenta consulta o motor → a ficha é gravada pelo escritor real →
    o agente pede gente com a PROSA do motivo → a porta real do grupo decide."""
    import app.agents.nodes as N
    import app.services.corridor_playbooks as CP
    from app.agents.tools.human_handoff import HumanHandoffTool

    b = _banco(cid)
    ref = CP.resolve_playbook_ref(cia, linha)
    r = None
    if not sem_acionamento:
        # ⚠️ exatamente como `insurer_dispatch_tool` chama (sem `agora`, sem `env`)
        r = CP.antes_de_acionar(ref, sub, slots)
        tool_args = {"insurer_key": cia, "line_kind": linha, "subservice": sub, **slots}
        rodar(N._gravar_ficha_do_turno({"company_id": X, "session_id": "ses-" + cid},
                                       "insurer_dispatch", tool_args,
                                       {"status": "pessoa_antes_de_acionar",
                                        "codigo": (r or {}).get("codigo")}))
    if envelhecer_ficha:
        linha_db = b.tabelas["conversations"][0]
        ficha = dict(linha_db.get("ficha_atendimento") or {})
        ficha["atualizada_em"] = iso(datetime.now(timezone.utc) - timedelta(days=2))
        # ⚠️ e a marca do pedido de ANTEONTEM, como o `_arun` de então a gravou
        ficha["pedido_antes_de_acionar"] = {
            "codigo": "carro_reserva_por_desenho",
            "em": iso(datetime.now(timezone.utc) - timedelta(days=2))}
        linha_db["ficha_atendimento"] = ficha
    motivo = motivo_do_agente if motivo_do_agente is not None else (r or {}).get("motivo", "")
    antes_envios, antes_gestos = len(ENVIOS), len(GESTOS)
    tool = HumanHandoffTool(supabase_client=b)
    resposta = rodar(tool._arun(reason=motivo, session_id="ses-" + cid, company_id=X,
                                codigo=codigo_declarado))
    enviados = b.eventos("grupo.enviado")
    tipo = str(((enviados[-1] if enviados else {}).get("payload_redacted") or {}).get("tipo") or "")
    texto = ENVIOS[-1][1] if len(ENVIOS) > antes_envios else ""
    gesto = GESTOS[-1] if len(GESTOS) > antes_gestos else {}
    return {"codigo": (r or {}).get("codigo", ""), "motivo": motivo, "tipo": tipo,
            "texto": texto, "primeira": (texto.splitlines() or [""])[0],
            "motivo_enum": str((gesto.get("payload") or {}).get("motivo_enum") or ""),
            "resposta": resposta, "banco": b}


def rodar_tudo():
    global OK, FAIL
    OK = FAIL = 0
    ENVIOS.clear()
    GESTOS.clear()
    REDIS.chaves.clear()
    env_antes = os.environ.pop(_ENV_CANAL, None)
    _instalar_dubles()
    try:
        _casos()
    finally:
        _restaurar()
        if env_antes is not None:
            os.environ[_ENV_CANAL] = env_antes
        else:
            os.environ.pop(_ENV_CANAL, None)
    print()
    print("=" * 74)
    print("  %d asserções verdes · %d vermelhas" % (OK, FAIL))
    print("=" * 74)
    return OK, FAIL


#: os dois nomes do "falta o número" (antes e depois da fatia do motor)
SEM_NUMERO = frozenset({"carro_reserva_sem_sinistro", "carro_reserva_sem_numero_do_processo"})


def _casos():
    import app.agents.tools.human_handoff as H
    import app.services.corridor_playbooks as CP
    import app.services.o_grupo_so_o_que_importa as G

    # ------------------------------------------------------------------ ①
    print("\n" + "=" * 74 + "\n  ① cada motivo do motor, pelo fio inteiro, até o grupo\n" + "=" * 74)
    sinistro_sim = {"carro_reserva_motivo": "sinistro", "sinistro_numero": "12345678",
                    "carro_reserva_cnh_e_cartao": "sim"}
    CASOS = [
        # (rótulo, seguradora, linha, serviço, slots, env do canal, relógio, código esperado)
        # ⚠️ o código do "sem número" mudou de nome na fatia do motor (conserto único):
        #    os dois nomes valem, e o guarda ⑤ cobra que a tabela conheça o de hoje.
        ("Yelum sem nº do sinistro", "yelum", "auto", "carro_reserva",
         {**DADOS_CR, "carro_reserva_motivo": "sinistro", "sinistro_numero": "não tenho"},
         "5547900000009", None, SEM_NUMERO),
        ("Yelum por pane", "yelum", "auto", "carro_reserva",
         {**DADOS_CR, "carro_reserva_motivo": "pane mecânica"},
         "5547900000009", None, "carro_reserva_motivo"),
        ("Yelum sem CNH/cartão", "yelum", "auto", "carro_reserva",
         {**DADOS_CR, **sinistro_sim, "carro_reserva_cnh_e_cartao": "não"},
         "5547900000009", None, "carro_reserva_sem_cartao"),
        ("Yelum fora do horário (sábado)", "yelum", "auto", "carro_reserva",
         {**DADOS_CR, **sinistro_sim}, "5547900000009",
         datetime(2026, 10, 10, 11, 0, tzinfo=FUSO_BR), "carro_reserva_fora_do_horario"),
        ("Yelum com o canal desligado", "yelum", "auto", "carro_reserva",
         {**DADOS_CR, **sinistro_sim}, "", None, "carro_reserva_canal_desligado"),
        ("Zurich com nº", "zurich", "auto", "carro_reserva",
         {**DADOS_CR, **sinistro_sim}, "", None, "carro_reserva_por_desenho"),
        ("Zurich por pane", "zurich", "auto", "carro_reserva",
         {**DADOS_CR, "carro_reserva_motivo": "pane mecânica"}, "", None,
         "carro_reserva_por_desenho"),
    ] + [("%s (por desenho)" % cia.title(), cia, "auto", "carro_reserva",
          {**DADOS_CR, **sinistro_sim}, "", None, "carro_reserva_por_desenho")
         for cia in ("allianz", "hdi", "porto", "bradesco", "mapfre")] + [
        ("portão eletrônico (D10)", "yelum", "residencial", "eletricista",
         {"problema_descricao": "o motor do portão eletrônico parou de abrir"},
         "", None, "portao_nao_e_eletricista"),
        ("falta de energia na rua", "yelum", "residencial", "eletricista",
         {"problema_descricao": "sem luz", "eletricista_tipo_opcao": "falta de energia na rua"},
         "", None, "falta_de_energia_na_rua"),
        ("🔴 CONTROLE D10: raio queimou a geladeira", "yelum", "residencial", "eletricista",
         {"problema_descricao": "caiu um raio e queimou a geladeira"},
         "", None, "sinistro_danos_eletricos"),
    ]
    vistos = set()
    carro_reserva_yelum = None
    for i, (rot, cia, linha, sub, slots, canal, relogio, esperado) in enumerate(CASOS):
        if canal:
            os.environ[_ENV_CANAL] = canal
        else:
            os.environ.pop(_ENV_CANAL, None)
        RELOGIO["agora"] = relogio or datetime(2026, 10, 6, 11, 0, tzinfo=FUSO_BR)
        REDIS.chaves.clear()
        s = _acionar_e_pedir("cr-%02d" % i, cia, linha, sub, slots)
        vistos.add(s["codigo"])
        e_sinistro = H._codigos_do_motor().get(s["codigo"]) == "sinistro"
        esperados = esperado if isinstance(esperado, (set, frozenset)) else {esperado}
        certo(s["codigo"] in esperados, "%s → o motor devolve `%s`" % (rot, s["codigo"]),
              (s["codigo"], sorted(esperados)))
        if e_sinistro:
            certo(s["tipo"] == G.TIPO_SINISTRO and s["primeira"] == "🚨 *NOVO SINISTRO*"
                  and s["motivo_enum"] == "sinistro",
                  "   continua SINISTRO: tipo `sinistro`, 🚨 NOVO SINISTRO, sombra 'sinistro'",
                  (s["tipo"], s["primeira"], s["motivo_enum"]))
        else:
            certo(s["tipo"] == G.TIPO_PEDIDO_DE_AJUDA and "NOVO SINISTRO" not in s["texto"]
                  and "SINISTRO*" not in s["primeira"] and s["motivo_enum"] == "outro",
                  "   ao grupo: `pedido_de_ajuda`, 1ª linha %r, sombra 'outro'" % s["primeira"],
                  (s["tipo"], s["primeira"], s["motivo_enum"], s["texto"][:300]))
        certo(s["resposta"] == H.SUCESSO_DO_HANDOFF and s["texto"],
              "   e o aviso SAIU (1 balão) — o conserto não cala o pedido", s["resposta"])
        if sub == "carro_reserva":
            certo(s["primeira"] == "🚙 *CARRO RESERVA*" and "abra o aviso" not in s["texto"],
                  "   título 🚙 CARRO RESERVA e nenhuma ordem de abrir aviso de sinistro",
                  s["texto"][:300])
            if s["codigo"] in SEM_NUMERO and cia == "yelum":
                carro_reserva_yelum = s
        if "sinistro" in s["motivo"].lower() and not e_sinistro:
            print("     (a prosa diz 'sinistro' e mesmo assim: %s)" % s["tipo"])

    # ------------------------------------------------------------------ ②
    print("\n" + "=" * 74 + "\n  ② P3 — o dossiê leva o que o segurado contou\n" + "=" * 74)
    t = (carro_reserva_yelum or {}).get("texto", "")
    for pedaco in ("*O PEDIDO*", "Quem retira: Pessoa Que Retira",
                   "CPF de quem retira: 00000000272", "Celular de quem retira: 47900000001",
                   "Cidade da retirada: Cidade de Teste",
                   "Data e hora da retirada: 08/10 às 15h", "Nº do sinistro: não tenho",
                   "Diárias: o limite do plano — sem ele, 15"):
        certo(pedaco in t, "o dossiê traz %r" % pedaco, t)
    ficha = carro_reserva_yelum["banco"].tabelas["conversations"][0]["ficha_atendimento"] \
        if carro_reserva_yelum else {}
    certo((ficha.get(H.CHAVE_DO_PEDIDO) or {}).get("codigo") in SEM_NUMERO,
          "a MARCA fica gravada na ficha (é ela que o aviso tardio do vigia lê)",
          ficha.get(H.CHAVE_DO_PEDIDO))
    certo(H._o_pedido_do_carro_reserva({"ficha_atendimento": {"confirmados": {}}})[0]
          .startswith("⚠️ o agente não chegou a anotar"),
          "🔴 CONTROLE: sem nada anotado, o dossiê DIZ que falta (não inventa)")

    # ------------------------------------------------------------------ ③
    print("\n" + "=" * 74 + "\n  ③ a marca DECLARADA vale sozinha\n" + "=" * 74)
    os.environ[_ENV_CANAL] = "5547900000009"
    RELOGIO["agora"] = datetime(2026, 10, 6, 11, 0, tzinfo=FUSO_BR)
    REDIS.chaves.clear()
    s = _acionar_e_pedir("cr-decl", "yelum", "auto", "carro_reserva",
                         {**DADOS_CR, "carro_reserva_motivo": "sinistro",
                          "sinistro_numero": "não tenho"},
                         envelhecer_ficha=True, codigo_declarado=sorted(
                             SEM_NUMERO & set(H._codigos_do_motor()))[0])
    certo(s["tipo"] == G.TIPO_PEDIDO_DE_AJUDA and s["primeira"] == "🚙 *CARRO RESERVA*",
          "ficha VELHA + `codigo` declarado pelo agente → pedido de ajuda 🚙", (s["tipo"], s["primeira"]))
    REDIS.chaves.clear()
    s = _acionar_e_pedir("cr-decl-lixo", "yelum", "auto", "carro_reserva",
                         {**DADOS_CR, "carro_reserva_motivo": "sinistro",
                          "sinistro_numero": "não tenho"},
                         envelhecer_ficha=True, codigo_declarado="qualquer_coisa",
                         motivo_do_agente="pedido de carro reserva — falta o número do "
                                          "sinistro")
    certo(s["tipo"] == G.TIPO_SINISTRO,
          "🔴 CONTROLE: código INVENTADO + ficha velha → nenhuma marca, vale o detector de "
          "sempre (a prosa diz sinistro → sinistro)", s["tipo"])

    # ------------------------------------------------------------------ ①b
    print("\n" + "=" * 74 + "\n  ①b a marca NO TEXTO, como a ferramenta manda copiar\n" + "=" * 74)
    if callable(getattr(CP, "motivo_com_codigo", None)):
        REDIS.chaves.clear()
        pessoa = CP.antes_de_acionar(CP.resolve_playbook_ref("zurich", "auto"), "carro_reserva",
                                     {**DADOS_CR, "carro_reserva_motivo": "pane"})
        com_marca = CP.motivo_com_codigo({**pessoa, "motivo": "a Zurich pede junto do "
                                          "sinistro (prosa com a palavra, de propósito)"})
        s = _acionar_e_pedir("cr-texto", "zurich", "auto", "carro_reserva",
                             {**DADOS_CR, "carro_reserva_motivo": "pane"},
                             envelhecer_ficha=True, motivo_do_agente=com_marca)
        razao = s["banco"].tabelas["conversations"][0]["human_handoff_reason"]
        certo(s["tipo"] == G.TIPO_PEDIDO_DE_AJUDA and s["primeira"] == "🚙 *CARRO RESERVA*",
              "ficha VELHA + marca no `reason` → pedido de ajuda 🚙, mesmo com 'sinistro' na prosa",
              (s["tipo"], s["primeira"]))
        certo(not str(razao).startswith("[") and "antes_de_acionar" not in s["texto"],
              "e a Fila e o grupo leem o motivo SEM a marca (português, sem nome de código)",
              (razao, s["texto"][:200]))
    else:
        print("  (o motor desta árvore ainda não publica `motivo_com_codigo` — ①b não se aplica)")

    # ------------------------------------------------------------------ ④
    print("\n" + "=" * 74 + "\n  ④ o outro lado: sinistro de verdade continua sinistro\n" + "=" * 74)
    REDIS.chaves.clear()
    s = _acionar_e_pedir("sin-contado", "yelum", "auto", "", {}, sem_acionamento=True,
                         motivo_do_agente="sinistro — o segurado bateu o carro agora e "
                                          "quer abrir o aviso")
    certo(s["tipo"] == G.TIPO_SINISTRO and s["primeira"] == "🚨 *NOVO SINISTRO*"
          and s["motivo_enum"] == "sinistro",
          "🔴 CONTROLE: o segurado CONTA um sinistro (sem acionamento) → 🚨 NOVO SINISTRO",
          (s["tipo"], s["primeira"], s["motivo_enum"]))
    REDIS.chaves.clear()
    s = _acionar_e_pedir("sin-ficha-velha", "zurich", "auto", "carro_reserva",
                         {**DADOS_CR, **sinistro_sim}, envelhecer_ficha=True,
                         motivo_do_agente="sinistro — nova batida hoje, o segurado quer abrir")
    certo(s["tipo"] == G.TIPO_SINISTRO and s["primeira"] == "🚨 *NOVO SINISTRO*",
          "🔴 CONTROLE: ficha de carro reserva de 2 DIAS ATRÁS não rebaixa o sinistro novo",
          (s["tipo"], s["primeira"]))
    marca_velha = (s["banco"].tabelas["conversations"][0]["ficha_atendimento"]
                   .get(H.CHAVE_DO_PEDIDO) or {})
    certo(marca_velha.get("codigo") == "",
          "   e a ficha grava 'sem marca' para ESTE pedido (o vigia não herda a de ontem)",
          marca_velha)

    # ------------------------------------------------------------------ ⑤
    print("\n" + "=" * 74 + "\n  ⑤ o guarda da tabela: todo código do motor tem tipo e caso\n" + "=" * 74)
    fonte = inspect.getsource(CP.antes_de_acionar)
    do_motor = set(re.findall(r'"codigo":\s*"(\w+)"', fonte))
    certo(len(do_motor) >= 9, "o motor declara %d códigos" % len(do_motor), sorted(do_motor))
    tabela = H._codigos_do_motor()
    certo(do_motor <= set(tabela), "todos têm tipo na tabela que o handoff lê",
          sorted(do_motor - set(tabela)))
    certo({k for k, v in tabela.items() if v == "sinistro"} == {"sinistro_danos_eletricos"}
          and {k for k, v in H._CODIGOS_ATE_A_TABELA_DO_MOTOR.items() if v == "sinistro"}
          == {"sinistro_danos_eletricos"},
          "e a tabela do motor e o paraquedas do handoff concordam: SÓ D10 é sinistro",
          tabela)
    certo(do_motor <= vistos, "todos atravessaram o fio neste arquivo",
          sorted(do_motor - vistos))


def test_spec121_costura_carro_reserva_grupo():
    _ok, falhas = rodar_tudo()
    assert falhas == 0


if __name__ == "__main__":
    _ok, _falhas = rodar_tudo()
    sys.exit(1 if _falhas else 0)
