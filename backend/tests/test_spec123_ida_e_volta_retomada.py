# -*- coding: utf-8 -*-
"""SPEC-123 F3 (D6) — a ida e volta com o segurado em TODAS as seguradoras, com retomada e sem duplicar.

O FIO (o do produto, nada reimplementado; dublê só na BORDA — Redis, banco, WhatsApp, o modelo do
`o_cerebro_ja_sabe`, o relógio do Vigia):

  dispatch_router.try_route_insurer_inbound → handle_insurer_message (motor) → `falta_para_a_ura`
  → perguntar_ao_segurado (prazo DA SEGURADORA) → a URA ENCERRA (tela real) → o roteador SEGURA
  (não reabre às cegas, não chama pessoa) → responder_pergunta_do_acionamento (a resposta TARDIA)
  → start_live_dispatch (o acionamento REABERTO, com o slot preenchido) → as telas REAIS da
  retomada ("Em nossa última conversa… Quer continuar com este?") → o corredor responde → a tela
  que pedia o dado é respondida DA FICHA → nenhum segundo acionamento, nenhuma segunda pergunta.

  … e numa retomada, a tela REAL "a assistência N está aberta" (HDI/Yelum/Porto) → a sessão fica
  com o pedido que JÁ EXISTE (não abre outro) · "não dá para seguir" → pessoa `ja_existe_solicitacao`.

⛔ Nada sai da máquina. As telas são REAIS (`tests/corpus/telas_reais`, mascaradas).
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.environ.setdefault("INSURER_DISPATCH_LIVE", "false")
os.environ["DISPATCH_MIRROR"] = "0"

# 🔴 O FIO COERENTE (P-121-28): o roteador, o motor, os playbooks e o Vigia nascem juntos, e o
#    `monkeypatch` cai no MESMO objeto que o produto chama.
FIO_F3 = (
    "app.services.corridor_playbooks",
    "app.services.insurer_dispatch_service",
    "app.services.o_grupo_so_o_que_importa",
    "app.services.dispatch_router",
    "app.tasks.dispatch_watchdog",
)
_NADA = object()


def _carregar_fio() -> dict:
    import importlib

    antes = dict(sys.modules)
    pais = {}
    for nome in FIO_F3:
        pai, _, filho = nome.rpartition(".")
        p = sys.modules.get(pai)
        pais[nome] = (p, filho, getattr(p, filho, _NADA) if p is not None else _NADA)
    try:
        for nome in FIO_F3:
            sys.modules.pop(nome, None)
        return {nome: importlib.import_module(nome) for nome in FIO_F3}
    finally:
        for nome in [n for n in sys.modules if n not in antes and (n == "app" or n.startswith("app."))]:
            novo = sys.modules.pop(nome)
            pai, _, filho = nome.rpartition(".")
            p = sys.modules.get(pai)
            if p is not None and getattr(p, filho, None) is novo:
                delattr(p, filho)
        for nome in FIO_F3:
            if nome in antes:
                sys.modules[nome] = antes[nome]
            else:
                sys.modules.pop(nome, None)
            p, filho, attr = pais[nome]
            if p is None:
                continue
            if attr is _NADA:
                if hasattr(p, filho):
                    delattr(p, filho)
            else:
                setattr(p, filho, attr)


FIO = _carregar_fio()
CP = FIO["app.services.corridor_playbooks"]
D = FIO["app.services.insurer_dispatch_service"]
G = FIO["app.services.o_grupo_so_o_que_importa"]
R = FIO["app.services.dispatch_router"]
W = FIO["app.tasks.dispatch_watchdog"]

CORPUS = Path(RAIZ) / "tests" / "corpus" / "telas_reais"
URA = "5511999990000"
CLIENTE = "5548988887777"
EMPRESA_A = "11111111-1111-1111-1111-111111111111"
EMPRESA_B = "22222222-2222-2222-2222-222222222222"
REF_ALLIANZ = "allianz-residencial-whatsapp@v1"
REF_HDI = "hdi-auto-whatsapp@v1"
REF_YELUM = "yelum-auto-whatsapp@v3"
REF_PORTO = "porto-auto-whatsapp@v1"
REF_MAPFRE = "mapfre-auto-whatsapp@v1"


def telas(arquivo: str) -> list:
    return [json.loads(l)["text"] for l in (CORPUS / f"{arquivo}.jsonl").read_text(encoding="utf-8").splitlines()]


def tela_real(arquivo: str, padrao: str) -> str:
    """A PRIMEIRA tela do acervo real cujo texto NORMALIZADO pelo produto casa `padrao` (§9.4)."""
    for t in telas(arquivo):
        if re.search(padrao, D._norm_text(t)):
            return t
    raise AssertionError(f"o corpus {arquivo} não tem tela que case {padrao!r}")


# --------------------------------------------------------------------------- as telas (do ACERVO)
RES = telas("allianz-residencial")
_PB_ALLIANZ = CP.get_playbook(REF_ALLIANZ)
#: a tela que pede um dado que a ficha não tem (o D3) — a MESMA escolha de `test_o_humano_da_seguradora_e_atendido`
PEDE = next(t for t in RES if CP.match_ura_step(_PB_ALLIANZ, t, subservice="encanador") is None
            and D.responder_da_ficha(_PB_ALLIANZ, t, {}).get("motivo") == "sem_dado_na_ficha"
            and not str(D.responder_da_ficha(_PB_ALLIANZ, t, {}).get("slot") or "").endswith("_opcao")
            and CP._COMO_PERGUNTAR.get(str(D.responder_da_ficha(_PB_ALLIANZ, t, {}).get("slot") or "")))
SLOT = str(D.responder_da_ficha(_PB_ALLIANZ, PEDE, {}).get("slot") or "")
ENCERRA_ALLIANZ = tela_real("allianz-residencial", r"encerrado por inatividade")
TERMO_ALLIANZ = tela_real("allianz-residencial", r"^termo de privacidade")
CONTINUAR_ALLIANZ = tela_real("allianz-residencial", r"em nossa ultima conversa, utilizamos o cpf")
JA_ABERTA_HDI = tela_real("hdi-auto", r"identifiquei que a assistencia \S+ esta aberta")
JA_ABERTA_YELUM_72H = tela_real("yelum-auto", r"foi aberta dentro das ultimas")
SEM_SAIDA_HDI = tela_real("hdi-residencial", r"assistencia ja esta em andamento com um de nossos prestadores")
SERVICO_ABERTO_PORTO = tela_real("porto-auto", r"voce tem um servico aberto")
PROTOCOLO_ABERTO_MAPFRE = tela_real("mapfre-auto", r"ja possui um protocolo aberto")
RISCO_HDI = tela_real("hdi-auto", r"situacoes de risco")

SLOTS_ALLIANZ = {"titular_cpf": "11122233344", "endereco_numero": "100", "telefone_contato": "48999998888",
                 "ramo_da_apolice": "resi", "problema_descricao": "vazamento no banheiro",
                 "periodo_preferido": "manha", "vazamento_local": "banheiro", "agua_escorrendo": "sim",
                 "risco_confirmado_registro_fechado": "sim"}


# --------------------------------------------------------------------------- a borda (dublês)
class _Redis:
    def __init__(self):
        self.d, self.listas = {}, {}

    async def get(self, k):
        return self.d.get(k)

    async def set(self, k, v, ex=None, nx=False):
        if nx and k in self.d:
            return None
        self.d[k] = v
        return True

    async def delete(self, *ks):
        for k in ks:
            self.d.pop(k, None)

    async def exists(self, k):
        return 1 if k in self.d else 0

    async def lpop(self, k):
        lst = self.listas.get(k) or []
        return lst.pop(0) if lst else None

    async def llen(self, k):
        return len(self.listas.get(k) or [])

    async def rpush(self, k, v):
        self.listas.setdefault(k, []).append(v)
        return len(self.listas[k])

    async def expire(self, k, s):
        return True

    async def scan_iter(self, match="*"):
        for k in list(self.d):
            if k.startswith(match.rstrip("*")):
                yield k


class _Consulta:
    def __init__(self, amb, tabela):
        self.amb, self.tabela, self.linha = amb, tabela, None

    def insert(self, linha):
        self.linha = linha
        return self

    def __getattr__(self, _nome):
        return lambda *a, **k: self

    async def execute(self):
        if self.tabela == "work_events" and self.linha:
            self.amb.eventos.append(self.linha)
        return types.SimpleNamespace(data=[])   # `cerebro_modos` vazio = destravador `off`


class _Banco:
    def __init__(self, amb):
        self.amb, self.client = amb, self

    def table(self, nome):
        return _Consulta(self.amb, nome)


class _Wa:
    def __init__(self, amb):
        self.amb = amb

    def send_message(self, fone, texto, integ=None, **k):
        self.amb.wa.append((fone, texto))


class Ambiente:
    def __init__(self):
        self.redis = _Redis()
        self.eventos, self.enviadas, self.wa, self.grupo, self.aberturas = [], [], [], [], []

    def ura(self, texto):
        self.enviadas.append(("seguradora", texto))

    def cliente(self, fone, texto):
        self.enviadas.append(("cliente", texto))

    def ao_cliente(self):
        return [t for q, t in self.enviadas if q == "cliente"]

    def a_seguradora(self):
        return [t for q, t in self.enviadas if q == "seguradora"] + [t for f, t in self.wa if f == URA]


@pytest.fixture
def amb(monkeypatch):
    for nome, mod in FIO.items():
        monkeypatch.setitem(sys.modules, nome, mod)
        pai, _, filho = nome.rpartition(".")
        p = sys.modules.get(pai)
        if p is not None:
            monkeypatch.setattr(p, filho, mod, raising=False)
    a = Ambiente()

    async def _redis():
        return a.redis

    async def _db():
        return _Banco(a)

    async def _porta(db, **kw):
        a.grupo.append(kw.get("tipo"))
        return {"enviado": True, "calado": False, "motivo": ""}

    async def _destino(company_id):
        return {"destino": "120363000000000000@g.us", "fonte": "teste", "recusa": ""}

    async def _cerebro_nao_sabe(company_id, session, *, slot, rotulo, tela, llm=None):
        return None, ""          # a BORDA do modelo: a ficha e a conversa não têm o dado

    async def _dossie(company_id, session, dossier, wa, integration):
        a.grupo.append("dossie")
        return True

    import app.core.database as _core_db
    import app.core.redis as _core_redis

    monkeypatch.setattr(_core_redis, "get_async_redis_client", _redis)
    monkeypatch.setattr(_core_db, "get_supabase_client", lambda: None)
    monkeypatch.setattr(R, "_redis", _redis)
    monkeypatch.setattr(R, "_db", _db)
    monkeypatch.setattr(R, "resolver_destino_de_suporte", _destino)
    monkeypatch.setattr(R, "o_cerebro_ja_sabe", _cerebro_nao_sabe)
    monkeypatch.setattr(G, "enviar_ao_grupo", _porta)
    monkeypatch.setattr(D, "dispatch_live_enabled", lambda: True)
    ws = types.ModuleType("app.services.whatsapp_service")
    ws.get_whatsapp_service = lambda: _Wa(a)
    monkeypatch.setitem(sys.modules, "app.services.whatsapp_service", ws)
    is_ = types.ModuleType("app.services.integration_service")
    is_.get_integration_service = lambda *x: types.SimpleNamespace()
    is_.IntegrationService = type("IntegrationService", (), {})
    monkeypatch.setitem(sys.modules, "app.services.integration_service", is_)
    monkeypatch.setattr(W, "_canal_da_conversa", lambda i, c, s: {"id": "canal-teste"})
    monkeypatch.setattr(W, "_entregar_dossie_com_marcador", _dossie)
    real_start = R.start_live_dispatch

    async def _start_contado(**kw):
        a.aberturas.append(dict(kw))
        return await real_start(**kw)

    monkeypatch.setattr(R, "start_live_dispatch", _start_contado)
    R._memory_store.clear()
    yield a
    R._memory_store.clear()


def sessao(ref, subservice, *, estado="ura", company=EMPRESA_A, slots=None, **extra):
    s = D.new_dispatch_session(case_id="c123f3", company_id=company, playbook_ref=ref,
                               subservice=subservice, slots=dict(slots or {}))
    s.update({"state": estado, "client_phone": CLIENTE, "work_run_id": "run-f3", "live": True,
              "mirror_conversation_id": "conv-f3", "retry_count": 0, "insurer_phone": URA})
    s.update(extra)
    return s


def salvar(company, s):
    asyncio.run(R.save_active_dispatch(company, URA, s))


def carregar(company=EMPRESA_A):
    return asyncio.run(R.load_active_dispatch(company, URA))


def turno(amb, texto, company=EMPRESA_A):
    asyncio.run(R.try_route_insurer_inbound(company_id=company, from_phone=URA, text=texto,
                                            send_to_insurer=amb.ura, send_to_client=amb.cliente))
    return carregar(company)


def responder(amb, texto, company=EMPRESA_A):
    return asyncio.run(R.responder_pergunta_do_acionamento(company, CLIENTE, texto,
                                                           send_to_client=amb.cliente))


def _pelo_turno(amb):
    """O que o roteador mandou à seguradora DENTRO dos turnos (a abertura da retomada sai pelo canal)."""
    return [t for q, t in amb.enviadas if q == "seguradora"]


def _perguntas(amb):
    return [t for t in amb.ao_cliente() if "Só mais uma informação" in t]


def _pergunta_allianz_e_ura_encerra(amb):
    s = sessao(REF_ALLIANZ, "encanador", slots={k: v for k, v in SLOTS_ALLIANZ.items() if k != SLOT})
    salvar(EMPRESA_A, s)
    s = turno(amb, PEDE)
    assert s.get("esperando_do_segurado", {}).get("slot") == SLOT, (s.get("state"), s.get("reason"))
    return turno(amb, ENCERRA_ALLIANZ)


# =============================================================================
# 🔴 O TESTE DO FIO — Allianz: pergunta → URA encerra → resposta TARDIA → retomada → não duplica
# =============================================================================
def test_o_fio_allianz_pergunta_ura_encerra_resposta_tardia_reabre_com_o_dado_e_nao_duplica(amb):
    assert SLOT and PEDE and ENCERRA_ALLIANZ and CONTINUAR_ALLIANZ
    s = _pergunta_allianz_e_ura_encerra(amb)
    # ① a URA fechou com a pergunta no ar: o roteador SEGURA — não reabre às cegas (o slot está
    #    vazio: a URA reaberta cairia na MESMA tela), não chama pessoa (o segurado ainda está no prazo).
    assert amb.aberturas == [], "a URA fechou e o roteador reabriu SEM a resposta (retomada às cegas)"
    assert amb.grupo == [], "o segurado ainda está no prazo e o caso já foi a uma pessoa"
    assert s is not None and s["state"] == "needs_human" and s["reason"] == "insurer_closed"
    assert (s.get("esperando_do_segurado") or {}).get("ura_fechou") is True
    assert len(_perguntas(amb)) == 1
    # ② a resposta TARDIA reabre o acionamento, com o dado na ficha
    assert responder(amb, "88010-400") is True
    assert len(amb.aberturas) == 1, amb.aberturas
    assert amb.aberturas[0]["slots"].get(SLOT) == "88010-400"
    nova = carregar()
    assert nova["state"] == "ura" and nova["slots"].get(SLOT) == "88010-400"
    assert nova.get("retry_count") == 1 and (nova.get("retomada") or {}).get("n") == 1
    assert SLOT in (nova.get("perguntado_ao_segurado") or [])
    assert amb.wa == [(URA, "Olá")] and _pelo_turno(amb) == [], (amb.wa, amb.enviadas)
    assert any("retomei" in t.lower() or "seguradora" in t.lower() for t in amb.ao_cliente()[1:])
    # ③ as telas REAIS da retomada: o corredor atravessa e a tela do dado é respondida DA FICHA
    turno(amb, TERMO_ALLIANZ)
    nova = turno(amb, CONTINUAR_ALLIANZ)
    respostas = _pelo_turno(amb)
    assert len(respostas) == 1 and nova["state"] == "ura", (respostas, nova.get("state"), nova.get("reason"))
    nova = turno(amb, PEDE)
    assert _pelo_turno(amb)[-1] == "88010-400", _pelo_turno(amb)
    # ④ NENHUM segundo acionamento, NENHUMA segunda pergunta — nem se o segurado repetir
    assert responder(amb, "88010-400") is False
    assert len(amb.aberturas) == 1 and len(_perguntas(amb)) == 1
    assert amb.grupo == [] and nova["state"] == "ura"


def test_a_resposta_a_tempo_na_hdi_segue_como_hoje_com_o_prazo_dela(amb):
    salvar(EMPRESA_A, sessao(REF_HDI, "socorro_mecanico", slots={"problema_descricao": "o carro morreu"}))
    s = turno(amb, RISCO_HDI)
    esp = s["esperando_do_segurado"]
    pedido = datetime.fromisoformat(esp["pedido_em"])
    assert (datetime.fromisoformat(esp["ate"]) - pedido).total_seconds() == pytest.approx(60, abs=1)
    assert responder(amb, "2") is True
    s = carregar()
    assert amb.a_seguradora() == ["Via com pouco movimento"] and s["state"] == "ura"
    assert amb.aberturas == [] and "esperando_do_segurado" not in s


# =============================================================================
# D6 — TODAS as seguradoras perguntam, e o prazo é o de CADA uma
# =============================================================================
def test_todas_as_seguradoras_dos_corredores_tem_ida_e_volta():
    chaves = {str((CP.get_playbook(r) or {}).get("insurer_key") or "") for r in CP._PLAYBOOKS}
    chaves.discard("")
    assert chaves and chaves <= set(D.IDA_E_VOLTA_AO_SEGURADO), chaves - set(D.IDA_E_VOLTA_AO_SEGURADO)
    assert D.ida_e_volta_permitida(REF_ALLIANZ) and D.ida_e_volta_permitida("alfa-auto-whatsapp@v1")
    assert not D.ida_e_volta_permitida("corredor-que-nao-existe@v1")   # desconhecido: falha fechada


def test_o_prazo_da_allianz_e_dois_minutos_e_cabe_antes_da_URA_fechar():
    """D6: "espera até ~2 min". 📊 Allianz encerra com p10 4,0 min (n=33): 120 s + o ciclo de 20 s
    do Vigia deixa folga. ⛔ Mutação: o prazo da Allianz de volta a 180 s → VERMELHO."""
    for ref in (REF_ALLIANZ, "allianz-auto-whatsapp@v1", "alfa-auto-whatsapp@v1"):
        assert D.prazo_da_pergunta_ao_segurado(ref) == 120, ref
    intervalo, maximo = R._env_pergunta({"playbook_ref": REF_ALLIANZ})
    assert intervalo * (maximo + 1) == 120
    # CONTROLE: as que esperam mais continuam com os 180 s de hoje
    assert R._env_pergunta({"playbook_ref": REF_HDI}) == (60, 2) == R._env_pergunta()


def test_a_pergunta_na_allianz_vence_em_40s_por_volta(amb):
    s = sessao(REF_ALLIANZ, "encanador", slots={k: v for k, v in SLOTS_ALLIANZ.items() if k != SLOT})
    salvar(EMPRESA_A, s)
    s = turno(amb, PEDE)
    esp = s["esperando_do_segurado"]
    total = (datetime.fromisoformat(esp["ate"]) - datetime.fromisoformat(esp["pedido_em"])).total_seconds()
    assert total == pytest.approx(40, abs=1)


# =============================================================================
# D6 — quem NÃO dispara retomada
# =============================================================================
def test_o_segurado_que_nao_respondeu_nunca_dispara_retomada(amb):
    s = _pergunta_allianz_e_ura_encerra(amb)
    # o prazo inteiro vence, em silêncio (com a URA fechada nada sai à seguradora)
    assert W.diagnose(dict(s, esperando_do_segurado=dict(s["esperando_do_segurado"],
                                                        ate=datetime.now(timezone.utc).isoformat()))) \
        == "segurado_sem_resposta"
    desfechos = []
    for _ in range(4):
        if not s.get("esperando_do_segurado"):
            break
        s["esperando_do_segurado"]["ate"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        desfechos.append(asyncio.run(W._segurar_ou_desistir(EMPRESA_A, URA, s, _Wa(amb), {"id": "x"})))
    assert desfechos[-1] == "desistiu" and s["reason"] == "segurado_nao_respondeu"
    assert amb.a_seguradora() == [], "o Vigia mandou 'um instante' a uma conversa que a URA já fechou"
    assert amb.aberturas == [] and amb.grupo == ["dossie"]
    assert (s.get("espera_vencida") or {}).get("ura_fechou") is True


def test_a_resposta_depois_da_pessoa_ainda_reabre_quando_a_URA_ja_fechou(amb):
    """A resposta tardia que chega DEPOIS do dossiê, com a URA fechada e ninguém na conversa,
    reabre — e a equipe, que recebeu o pedido de ajuda, é avisada da retomada."""
    s = _pergunta_allianz_e_ura_encerra(amb)
    s["esperando_do_segurado"]["holdings"] = 99
    s["esperando_do_segurado"]["ate"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    asyncio.run(W._segurar_ou_desistir(EMPRESA_A, URA, s, _Wa(amb), {"id": "x"}))
    salvar(EMPRESA_A, s)
    assert responder(amb, "88010-400") is True
    assert len(amb.aberturas) == 1 and carregar()["slots"].get(SLOT) == "88010-400"
    assert G.TIPO_RETOMADA in amb.grupo


def test_ura_que_fecha_depois_do_prazo_vencido_nao_reabre_as_cegas(amb):
    """`segurado_nao_respondeu` (URA ainda aberta) e DEPOIS a URA fecha: era a retomada cega
    (`insurer_closed` + `retry_count == 0`). Agora a sessão fica à espera da resposta."""
    s = sessao(REF_ALLIANZ, "encanador", estado="needs_human", reason="segurado_nao_respondeu",
               dossier_sent=True, slots={k: v for k, v in SLOTS_ALLIANZ.items() if k != SLOT},
               espera_vencida={"slot": SLOT, "rotulo": "o CEP", "client_phone": CLIENTE[-11:]},
               perguntado_ao_segurado=[SLOT])
    salvar(EMPRESA_A, s)
    asyncio.run(R._indexar_pergunta(EMPRESA_A, CLIENTE, URA, 600))
    s = turno(amb, ENCERRA_ALLIANZ)
    assert amb.aberturas == [] and s is not None and s["reason"] == "insurer_closed"
    assert responder(amb, "88010-400") is True and len(amb.aberturas) == 1


def test_CONTROLE_a_URA_que_fecha_sem_pergunta_no_ar_reabre_uma_vez_como_hoje(amb):
    salvar(EMPRESA_A, sessao(REF_ALLIANZ, "encanador", slots=SLOTS_ALLIANZ))
    turno(amb, ENCERRA_ALLIANZ)
    assert len(amb.aberturas) == 1 and carregar().get("retry_count") == 1
    assert (carregar().get("retomada") or {}).get("porque") == "seguradora_encerrou"


def test_o_teto_e_de_duas_retomadas_por_caso(amb):
    base = {"reason": "insurer_closed", "captured": {}, "esperando_do_segurado": {"ura_fechou": True}}
    assert D.pode_retomar_com_a_resposta(dict(base, retry_count=0))
    assert D.pode_retomar_com_a_resposta(dict(base, retry_count=1))
    assert not D.pode_retomar_com_a_resposta(dict(base, retry_count=2))
    assert not D.pode_retomar_com_a_resposta(dict(base, retry_count=0, captured={"protocol": "X1"}))
    assert not D.pode_retomar_com_a_resposta(dict(base, retry_count=0, reason=D.HUMANO_ASSUMIU))
    assert not D.pode_retomar_com_a_resposta({"reason": "segurado_nao_respondeu", "retry_count": 0,
                                              "espera_vencida": {"slot": "x"}}), "URA aberta não reabre"
    # e pelo roteador: na 3ª, a resposta fica na ficha e nada é reaberto
    s = _pergunta_allianz_e_ura_encerra(amb)
    s["retry_count"] = 2
    salvar(EMPRESA_A, s)
    assert responder(amb, "88010-400") is True
    assert amb.aberturas == [] and carregar()["slots"].get(SLOT) == "88010-400"


# =============================================================================
# 🔴 NUNCA DUPLICAR — o detector no MOTOR, com as telas REAIS
# =============================================================================
def _retomada(ref, sub, *, pode_ter_aberto=True, **extra):
    return sessao(ref, sub, retry_count=1,
                  retomada={"n": 1, "porque": "seguradora_encerrou",
                            "anterior_pode_ter_aberto": pode_ter_aberto}, **extra)


@pytest.mark.parametrize("ref,sub,tela", [
    (REF_HDI, "guincho", JA_ABERTA_HDI),
    (REF_YELUM, "guincho", JA_ABERTA_YELUM_72H),
    (REF_PORTO, "guincho", SERVICO_ABERTO_PORTO),
])
def test_na_retomada_a_assistencia_que_ja_existe_vira_o_pedido_do_caso_e_nada_e_aberto(amb, ref, sub, tela):
    salvar(EMPRESA_A, _retomada(ref, sub))
    s = turno(amb, tela)
    assert s["state"] == "monitoring" and s["captured"].get("ja_existia") is True, (s["state"], s.get("reason"))
    numero = str(s["captured"].get("protocol") or "")
    assert numero and numero.lower() in D._norm_text(tela)
    assert amb.a_seguradora() == [], "na retomada a tela de pedido JÁ ABERTO foi respondida (abre outro)"
    [aviso] = amb.ao_cliente()
    assert numero in aviso and "sem abrir outro" in aviso
    assert any(e["event_type"] == "acionamento.ja_existia" for e in amb.eventos)


def test_na_retomada_sem_saida_vai_a_uma_pessoa_com_o_motivo(amb):
    salvar(EMPRESA_A, _retomada("hdi-residencial-whatsapp@v1", "encanador"))
    s = turno(amb, SEM_SAIDA_HDI)
    assert s["state"] == "needs_human" and s["reason"] == "ja_existe_solicitacao"
    assert amb.aberturas == [] and amb.a_seguradora() == []
    assert D.politica_de_retomada("ja_existe_solicitacao") == D.DIRETO_AO_HUMANO
    assert "já existe" in D.motivo_em_portugues("ja_existe_solicitacao")


def test_na_retomada_a_mapfre_perguntando_se_ja_ha_protocolo_vai_a_uma_pessoa(amb):
    salvar(EMPRESA_A, _retomada(REF_MAPFRE, "guincho"))
    s = turno(amb, PROTOCOLO_ABERTO_MAPFRE)
    assert s["state"] == "needs_human" and s["reason"] == "ja_existe_solicitacao"
    assert amb.a_seguradora() == []


@pytest.mark.parametrize("ref,sub,tela", [
    (REF_PORTO, "guincho", SERVICO_ABERTO_PORTO),
    (REF_MAPFRE, "guincho", PROTOCOLO_ABERTO_MAPFRE),
    (REF_HDI, "guincho", JA_ABERTA_HDI),
])
def test_CONTROLE_fora_da_retomada_e_retomada_que_nao_confirmou_fazem_o_de_hoje(amb, monkeypatch, ref, sub, tela):
    """Byte a byte: sem retomada (e na retomada cujo acionamento anterior NUNCA chegou à confirmação —
    nada pôde ter sido aberto por nós) o motor faz exatamente o que fazia SEM o detector."""
    def _motor(s):
        s = D.handle_insurer_message(s, tela, sender=lambda t: None)
        return ([t["text"] for t in s["transcript"] if t["direction"] == "out"], s["state"],
                s.get("reason"), (s.get("captured") or {}).get("protocol"))
    sem_retomada = _motor(sessao(ref, sub))
    nao_confirmou = _motor(_retomada(ref, sub, pode_ter_aberto=False))
    monkeypatch.setattr(D, "JA_EXISTE_SOLICITACAO", {})
    hoje = _motor(sessao(ref, sub))
    assert sem_retomada == hoje and nao_confirmou == hoje


def test_o_detector_casa_as_telas_reais_pelo_motor_e_so_elas():
    """§9.4: o MOTOR sobre o texto REAL (normalizado pelo produto), por seguradora."""
    assert D.solicitacao_ja_existente(REF_HDI, JA_ABERTA_HDI)["tipo"] == "mostra_numero"
    assert D.solicitacao_ja_existente(REF_YELUM, JA_ABERTA_YELUM_72H)["tipo"] == "mostra_numero"
    assert D.solicitacao_ja_existente(REF_PORTO, SERVICO_ABERTO_PORTO)["tipo"] == "mostra_numero"
    assert D.solicitacao_ja_existente(REF_MAPFRE, PROTOCOLO_ABERTO_MAPFRE)["tipo"] == "pergunta"
    assert D.solicitacao_ja_existente("hdi-residencial-whatsapp@v1", SEM_SAIDA_HDI)["tipo"] == "sem_saida"
    # ⛔ a tela de SUCESSO do próprio acionamento não é "já existia" (📊 hdi/yelum "Assistência solicitada!")
    sucesso = tela_real("hdi-auto", r"assistencia solicitada! sua solicitacao esta em andamento")
    assert D.solicitacao_ja_existente(REF_HDI, sucesso) is None
    # 📊 em TODO o acervo, só as telas de pedido aberto casam (nenhuma das outras)
    casadas = 0
    for arq in ("hdi-auto", "yelum-auto", "porto-auto", "mapfre-auto", "hdi-residencial"):
        ref = {"hdi-auto": REF_HDI, "yelum-auto": REF_YELUM, "porto-auto": REF_PORTO,
               "mapfre-auto": REF_MAPFRE, "hdi-residencial": "hdi-residencial-whatsapp@v1"}[arq]
        for t in telas(arq):
            if D.solicitacao_ja_existente(ref, t):
                casadas += 1
                assert re.search(r"(esta|foi) aberta|servico aberto|protocolo aberto|ja esta em andamento com",
                                 D._norm_text(t)), t[:120]
    assert casadas >= 6


def test_o_freio_puro_o_segurado_sem_resposta_nao_reabre_as_cegas():
    base = {"reason": "insurer_closed", "retry_count": 0, "captured": {},
            "espera_vencida": {"slot": "local_cep"}, "slots": {}}
    assert D.pode_retomar(base) is False
    # CONTROLE: com o dado na ficha (a resposta chegou), a retomada de sempre volta
    assert D.pode_retomar(dict(base, slots={"local_cep": "88010-400"})) is True


def test_com_fila_a_URA_que_fecha_com_pergunta_no_ar_nao_reabre_o_caso_as_cegas(amb):
    """Com outro acionamento esperando este número, o roteador não segura (a fila anda) — e nem
    por isso reabre ESTE caso sem o dado: ele vai a uma pessoa com o dossiê, e a fila começa."""
    asyncio.run(R.enqueue_dispatch(EMPRESA_A, URA, {
        "case_id": "outro-caso", "playbook_ref": REF_ALLIANZ, "subservice": "encanador",
        "slots": SLOTS_ALLIANZ, "client_phone": "5548911112222"}))
    _pergunta_allianz_e_ura_encerra(amb)
    assert [a["case_id"] for a in amb.aberturas] == ["outro-caso"], amb.aberturas
    assert G.TIPO_PEDIDO_DE_AJUDA in amb.grupo
