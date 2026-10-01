# -*- coding: utf-8 -*-
"""SPEC-123 F1b — o destravador LIGADO nos pontos de trava (roteador e Sentinela).

O FIO (o do produto; dublê só na BORDA — o destravador/modelo, o diário/banco, Redis, WhatsApp):

  PONTO B · dispatch_router.try_route_insurer_inbound → handle_insurer_message (MOTOR real, tela
            REAL do acervo) → `needs_human` + motivo → trava_destravavel → modo_do_destravador
            (`cerebro_modos`, DUBLÊ) → destravador.destravar (DUBLÊ, assinatura do contrato)
            → aplicar_destravamento → `_emit`/`reply_human_phase` (URA) · perguntar_ao_segurado
            (segurado) · o dossiê de hoje (pessoa) → save_active_dispatch
  PONTO A · o turno do cérebro da fase humana e a escada do Sentinela, em `on`, sem o provider.
  RESULTADO · captured / insurer_closed / a pessoa depois da decisão → diario.marcar_resultado.

⛔ Nada sai da máquina. `destravador.py` (F1a) e `diario_de_decisoes.py` (F4) são DUBLADOS por
`monkeypatch.setitem(sys.modules, …)` — o original volta sozinho no fim de cada teste (P-121-28).
"""
from __future__ import annotations

import asyncio
import copy
import json
import os
import re
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.environ.setdefault("INSURER_DISPATCH_LIVE", "false")
os.environ["DISPATCH_MIRROR"] = "0"

# =============================================================================
# O FIO COERENTE (o molde da SPEC-122: o teste patcha o MESMO objeto que o produto chama)
# =============================================================================
FIO_123 = (
    "app.services.corridor_playbooks",
    "app.services.insurer_dispatch_service",
    "app.services.acao_do_cerebro",
    "app.services.evals.bancada",
    "app.services.o_grupo_so_o_que_importa",
    "app.services.dispatch_router",
    "app.tasks.dispatch_watchdog",
)
_NADA = object()


def carregar_fio_coerente() -> dict:
    """O fio importado UMA vez, coerente entre si — e o `sys.modules` devolvido intacto."""
    import importlib

    antes = dict(sys.modules)
    pais = {}
    for nome in FIO_123:
        pai, _, filho = nome.rpartition(".")
        p = sys.modules.get(pai)
        pais[nome] = (p, filho, getattr(p, filho, _NADA) if p is not None else _NADA)
    try:
        for nome in FIO_123:
            sys.modules.pop(nome, None)
        return {nome: importlib.import_module(nome) for nome in FIO_123}
    finally:
        for nome in [n for n in sys.modules if n not in antes and (n == "app" or n.startswith("app."))]:
            novo = sys.modules.pop(nome)
            pai, _, filho = nome.rpartition(".")
            p = sys.modules.get(pai)
            if p is not None and getattr(p, filho, None) is novo:
                delattr(p, filho)
        for nome in FIO_123:
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


def fixar_fio(monkeypatch, fio: dict) -> None:
    for nome, mod in fio.items():
        monkeypatch.setitem(sys.modules, nome, mod)
        pai, _, filho = nome.rpartition(".")
        p = sys.modules.get(pai)
        if p is not None:
            monkeypatch.setattr(p, filho, mod, raising=False)


FIO = carregar_fio_coerente()
CP = FIO["app.services.corridor_playbooks"]
D = FIO["app.services.insurer_dispatch_service"]
AC = FIO["app.services.acao_do_cerebro"]
G = FIO["app.services.o_grupo_so_o_que_importa"]
R = FIO["app.services.dispatch_router"]
W = FIO["app.tasks.dispatch_watchdog"]

CORPUS = Path(RAIZ) / "tests" / "corpus" / "telas_reais"
URA = "5511999990000"
CLIENTE = "5548988887777"
EMPRESA_A = "11111111-1111-1111-1111-111111111111"
EMPRESA_B = "22222222-2222-2222-2222-222222222222"
REF_ALLIANZ_R = "allianz-residencial-whatsapp@v1"
REF_ALLIANZ_A = "allianz-auto-whatsapp@v1"
REF_PORTO = "porto-auto-whatsapp@v1"
#: Valores de TESTE (nada de PII; §13.9) — o caso residencial completo da bateria 5.
SLOTS_R = {"titular_cpf": "11122233344", "telefone_contato": "48900000000",
           "problema_descricao": "vazamento na coluna", "endereco_numero": "100",
           "periodo_preferido": "tarde"}


def tela_real(arquivo: str, padrao: str, sessao_id: str = "") -> str:
    """A PRIMEIRA tela do acervo que casa `padrao` (sobre `_norm`) — o texto vem do acervo."""
    for linha in (CORPUS / f"{arquivo}.jsonl").read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        x = json.loads(linha)
        if sessao_id and x["session_id"] != sessao_id:
            continue
        if re.search(padrao, CP._norm(x["text"]), re.I | re.S):
            return x["text"]
    raise AssertionError(f"o acervo {arquivo} não tem tela que case {padrao!r}")


def _caso_do_cerebro(chave: str) -> dict:
    for linha in (Path(RAIZ) / "tests/corpus/bancada/cerebro/casos.jsonl").read_text(encoding="utf-8").splitlines():
        c = json.loads(linha)
        if c["chave"] == chave:
            return c
    raise AssertionError(chave)


#: 📊 allianz-residencial 44ff2017 — *"Qual serviço deseja acionar?"*: o motor a classifica
#: `tela_que_decide:escolhe_o_servico` (a trava DEDUZIR mais frequente do BLOCO 0).
TELA_ESCOLHE = tela_real("allianz-residencial", r"qual servi[çc]o deseja acionar", "44ff2017")
#: 📊 allianz-auto (4971b50b) — oficina referenciada + franquia: `handoff_trigger:sinistro`.
TELA_SINISTRO = tela_real("allianz-auto", r"oficina referenciada")
#: 📊 allianz-residencial — a tela dos três ramos (condomínio → `apolice_de_condominio_ou_empresa`).
TELA_APOLICE = tela_real("allianz-residencial", r"qual seguro deseja utilizar[\s\S]*condominio")
#: 📊 uma tela REAL sem passo (grupo A da bancada da 122) que vai ao cérebro na fase humana.
TELA_SEM_PASSO = _caso_do_cerebro("cer-A-porto-019")["entrada"]["tela"]
#: 💭 frase de recusa da Allianz — uma das 9 medidas na SPEC-121 F4 (texto sem PII).
FRASE_RECUSA = "Sua apólice não contempla o serviço desejado."


# --------------------------------------------------------------------------- a borda (dublês)
class _Redis:
    def __init__(self):
        self.d = {}

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
        return None

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
        return types.SimpleNamespace(data=[])


class _Banco:
    def __init__(self, amb):
        self.amb = amb
        self.client = self

    def table(self, nome):
        return _Consulta(self.amb, nome)


class _Wa:
    def __init__(self, amb):
        self.amb = amb

    def send_message(self, fone, texto, integ=None, **k):
        self.amb.wa.append((fone, texto))


@dataclass
class Destravamento:
    """A MESMA forma do contrato (`destravador.Destravamento`, dono F1a)."""
    classe: str
    acao: str
    valor: str = ""
    opcoes: Optional[list] = None
    nota: Optional[int] = None
    limiar: int = 70
    motivo: str = ""
    explicacao: str = ""
    segunda_opiniao: Optional[dict] = None
    modelo: str = ""
    proibicao: str = ""
    modo: str = "on"
    diario_id: Optional[str] = None
    custo_usd: float = 0.0


class Ambiente:
    def __init__(self):
        self.redis = _Redis()
        self.eventos, self.enviadas, self.wa, self.grupo = [], [], [], []
        self.modos = {}                  # (company, seguradora, ramo) → (modo, limiar)
        self.consultas_de_modo = []      # quem PERGUNTOU o modo (corretora, seguradora, ramo)
        self.destravar_chamadas = []     # o que o roteador entregou ao destravador
        self.sombras = []                # agendar_em_sombra
        self.resultados = []             # diario.marcar_resultado
        self.decisao = Destravamento(classe="deduzir", acao="RESPONDER", valor="Encanador",
                                     nota=88, diario_id="d-1")
        self.provider_chamado = 0
        self.chamadas_de_modelo = []

    def ura(self, texto):
        self.enviadas.append(("seguradora", texto))

    def cliente(self, fone, texto):
        self.enviadas.append(("cliente", texto))


def _destravador_duble(a: Ambiente) -> types.ModuleType:
    m = types.ModuleType("app.services.destravador")
    m.Destravamento = Destravamento
    m.CLASSES = ("conduzir", "responder_com_dado", "deduzir", "perguntar_ao_segurado", "nunca_sozinho")
    m.LIMIAR_MINIMO = 70

    async def modo_do_destravador(company_id, insurer_key, ramo):
        a.consultas_de_modo.append((company_id, insurer_key, ramo))
        return a.modos.get((company_id, insurer_key, ramo), ("off", 70))

    async def destravar(company_id, sessao, tela, *, gatilho, modo, limiar=70):
        a.destravar_chamadas.append({"company_id": company_id, "sessao": sessao, "tela": tela,
                                     "gatilho": gatilho, "modo": modo, "limiar": limiar})
        return copy.deepcopy(a.decisao)

    def agendar_em_sombra(company_id, sessao_copia, tela, *, gatilho):
        a.sombras.append({"company_id": company_id, "sessao": sessao_copia, "tela": tela,
                          "gatilho": gatilho})
        return None

    m.modo_do_destravador, m.destravar, m.agendar_em_sombra = modo_do_destravador, destravar, agendar_em_sombra
    return m


def _diario_duble(a: Ambiente) -> types.ModuleType:
    m = types.ModuleType("app.services.diario_de_decisoes")

    async def marcar_resultado(*, company_id, work_run_id, resultado):
        a.resultados.append((company_id, work_run_id, resultado))
        return 1

    async def registrar_decisao(**k):
        return "d-x"

    m.marcar_resultado, m.registrar_decisao = marcar_resultado, registrar_decisao
    return m


@pytest.fixture
def amb(monkeypatch):
    fixar_fio(monkeypatch, FIO)
    # O pacote `app.services` de VERDADE, antes dos dublês de canal (o `__init__` dele importa o
    # `integration_service` real) — e o que ESTE teste carregou sai no fim (P-121-28).
    _antes = set(sys.modules)
    import app.services  # noqa: F401
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

    import app.core.database as _core_db
    import app.core.redis as _core_redis
    # O pacote `app.services` carregado de VERDADE antes dos dublês de canal (o molde da 122).
    from app.factories import llm_factory

    async def _modelo_proibido(papel, mensagens, **kw):
        # ⛔ Nenhum modelo real neste arquivo: quem decide é o DUBLÊ do destravador.
        a.chamadas_de_modelo.append(papel)
        raise RuntimeError("modelo real proibido neste teste")

    monkeypatch.setattr(llm_factory, "invocar_com_reserva", _modelo_proibido)
    monkeypatch.setattr(_core_redis, "get_async_redis_client", _redis)
    monkeypatch.setattr(_core_db, "get_supabase_client", lambda: None)
    monkeypatch.setattr(R, "_redis", _redis)
    monkeypatch.setattr(R, "_db", _db)
    monkeypatch.setattr(R, "resolver_destino_de_suporte", _destino)
    monkeypatch.setattr(G, "enviar_ao_grupo", _porta)
    ws = types.ModuleType("app.services.whatsapp_service")
    ws.get_whatsapp_service = lambda: _Wa(a)
    monkeypatch.setitem(sys.modules, "app.services.whatsapp_service", ws)
    is_ = types.ModuleType("app.services.integration_service")
    is_.get_integration_service = lambda *x: types.SimpleNamespace()
    monkeypatch.setitem(sys.modules, "app.services.integration_service", is_)
    monkeypatch.setattr(W, "_canal_da_conversa", lambda i, c, s: {"id": "canal-teste"})

    async def _dossie(company_id, session, dossier, wa, integration):
        a.grupo.append("dossie")
        return True

    monkeypatch.setattr(W, "_entregar_dossie_com_marcador", _dossie)
    monkeypatch.setattr(D, "dispatch_live_enabled", lambda: True)
    # 🔴 A BORDA do destravador e do diário — o original (se a F1a/F4 já o escreveram) VOLTA no fim.
    monkeypatch.setitem(sys.modules, "app.services.destravador", _destravador_duble(a))
    monkeypatch.setitem(sys.modules, "app.services.diario_de_decisoes", _diario_duble(a))
    AC._CACHE_DA_CHAVE.clear()
    R._memory_store.clear()
    yield a
    AC._CACHE_DA_CHAVE.clear()
    monkeypatch.undo()
    for nome in [n for n in sys.modules if n not in _antes and (n == "app" or n.startswith("app."))]:
        novo = sys.modules.pop(nome)
        pai, _, filho = nome.rpartition(".")
        p = sys.modules.get(pai)
        if p is not None and getattr(p, filho, None) is novo:
            delattr(p, filho)


def ligar(amb, company=EMPRESA_A, seguradora="allianz", ramo="residencial", modo="on", limiar=70):
    amb.modos[(company, seguradora, ramo)] = (modo, limiar)


def sessao(ref, subservice, *, estado="ura", company=EMPRESA_A, slots=None, run="run-123", **extra):
    s = D.new_dispatch_session(case_id="c123", company_id=company, playbook_ref=ref,
                               subservice=subservice, slots=dict(SLOTS_R if slots is None else slots))
    s.update({"state": estado, "client_phone": CLIENTE, "work_run_id": run, "live": True,
              "mirror_conversation_id": "conv-123", "retry_count": 1})
    s.update(extra)
    return s


def salvar(company, s):
    asyncio.run(R.save_active_dispatch(company, URA, s))


def rodar_turno(amb, company, texto, provider=None):
    """UM inbound da seguradora pelo roteador REAL. Devolve a sessão GRAVADA."""
    async def _turno():
        await R.try_route_insurer_inbound(company_id=company, from_phone=URA, text=texto,
                                          send_to_insurer=amb.ura, send_to_client=amb.cliente,
                                          human_reply_provider=provider)
        if AC._SOMBRAS:
            await asyncio.gather(*list(AC._SOMBRAS))
    asyncio.run(_turno())
    return asyncio.run(R.load_active_dispatch(company, URA))


def turno_escolhe(amb, company=EMPRESA_A, **extra):
    salvar(company, sessao(REF_ALLIANZ_R, "encanador", company=company, **extra))
    return rodar_turno(amb, company, TELA_ESCOLHE)


def saidas(s):
    return [t.get("text") for t in (s.get("transcript") or []) if t.get("direction") == "out"]


# =============================================================================
# 🔴 O TESTE DO FIO — PONTO B, a tela REAL que o motor manda a uma pessoa
# =============================================================================
def test_o_fio_a_tela_que_decide_vira_UMA_resposta_a_URA_e_a_sessao_segue_viva(amb):
    """Nasce VERMELHO sem a F1b (a tela vai ao dossiê); VERDE com ela: UM envio à URA com o valor."""
    ligar(amb)
    s = turno_escolhe(amb)
    assert amb.enviadas == [("seguradora", "Encanador")], amb.enviadas
    assert amb.grupo == [], "destravou e mesmo assim o dossiê foi à equipe"
    assert s["state"] == "ura" and not s.get("reason"), (s.get("state"), s.get("reason"))
    assert s.get("retry_count") == 1, "a sessão perdeu o teto da retomada"
    assert saidas(s)[-1] == "Encanador" and s["transcript"][-1].get("via") == "destravador"
    [ch] = amb.destravar_chamadas
    assert (ch["gatilho"], ch["modo"], ch["limiar"], ch["company_id"]) == (
        "tela_que_decide:escolhe_o_servico", "on", 70, EMPRESA_A)
    assert "Qual serviço deseja acionar" in ch["tela"]
    assert ch["sessao"]["state"] == "needs_human", "o destravador tem de ver a trava como o motor a deixou"
    assert amb.consultas_de_modo == [(EMPRESA_A, "allianz", "residencial")]
    assert s.get("destravamentos") == {"tela_que_decide": 1}


def test_o_fio_com_PERGUNTAR_a_pergunta_sai_ao_segurado_e_a_espera_fica_gravada(amb):
    ligar(amb)
    amb.decisao = Destravamento(classe="perguntar_ao_segurado", acao="PERGUNTAR_AO_SEGURADO",
                                valor="Qual serviço você precisa: encanador ou eletricista?",
                                diario_id="d-2")
    s = turno_escolhe(amb)
    [(canal, texto)] = amb.enviadas
    assert canal == "cliente" and "encanador ou eletricista?" in texto and "me diga Qual" not in texto
    assert amb.grupo == [], "perguntou ao segurado e também chamou a equipe"
    espera = s.get("esperando_do_segurado") or {}
    assert espera.get("destravador") is True and espera.get("diario_id") == "d-2"
    assert s["state"] == "ura" and not s.get("reason")
    assert (s.get("falta_para_a_ura") or {}).get("slot") == espera.get("slot")


def test_o_fio_com_PESSOA_e_o_dossie_de_hoje_com_o_motivo_ORIGINAL(amb):
    # CONTROLE: o que sai HOJE (modo off)
    s_off = turno_escolhe(amb)
    envio_off, grupo_off = list(amb.enviadas), list(amb.grupo)
    # PESSOA em `on`
    amb.enviadas.clear(), amb.grupo.clear(), amb.redis.d.clear()
    ligar(amb)
    amb.decisao = Destravamento(classe="deduzir", acao="PESSOA", proibicao="nota_abaixo_do_limiar")
    s_on = turno_escolhe(amb)
    assert len(amb.destravar_chamadas) == 1
    assert amb.enviadas == envio_off and amb.grupo == grupo_off == ["pedido_de_ajuda"]
    assert (s_on["state"], s_on["reason"]) == (s_off["state"], s_off["reason"]) == (
        "needs_human", "tela_que_decide:escolhe_o_servico")


# =============================================================================
# CONTROLES — `off` é o de hoje, byte a byte; `sombra` também
# =============================================================================
def test_CONTROLE_off_e_sombra_saem_IGUAIS_ao_caminho_sem_o_gancho(amb, monkeypatch):
    def _rodar():
        amb.enviadas.clear(), amb.grupo.clear(), amb.redis.d.clear()
        s = turno_escolhe(amb)
        return list(amb.enviadas), list(amb.grupo), s["state"], s["reason"], saidas(s)

    # o caminho SEM o gancho do destravador (o de antes da F1b)
    with monkeypatch.context() as m:
        m.setattr(R, "trava_destravavel", lambda *a, **k: False)
        sem_gancho = _rodar()
    off = _rodar()                              # sem linha = off
    ligar(amb, modo="off")
    off_explicito = _rodar()
    ligar(amb, modo="sombra")
    sombra = _rodar()
    assert sem_gancho == off == off_explicito == sombra, (sem_gancho, off, sombra)
    assert sem_gancho[2:4] == ("needs_human", "tela_que_decide:escolhe_o_servico")
    assert amb.destravar_chamadas == [], "off/sombra CHAMARAM o destravador para agir"
    # a sombra decide numa CÓPIA, com a trava como o motor a deixou
    [sb] = amb.sombras
    assert sb["gatilho"] == "tela_que_decide:escolhe_o_servico" and sb["sessao"]["state"] == "needs_human"


@pytest.mark.parametrize("nome,ref,sub,texto,slots,motivo", [
    ("sinistro", REF_ALLIANZ_A, "guincho", TELA_SINISTRO, None, "handoff_trigger:sinistro"),
    ("condominio", REF_ALLIANZ_R, "encanador", TELA_APOLICE, {**SLOTS_R, "ramo_da_apolice": "Condomínio"},
     "apolice_de_condominio_ou_empresa"),
    ("recusa", REF_ALLIANZ_R, "encanador", FRASE_RECUSA, None, "recusa_de_cobertura:"),
], ids=["sinistro", "condominio", "recusa"])
def test_CONTROLE_o_que_NUNCA_se_destrava_nem_consulta_o_modo(amb, nome, ref, sub, texto, slots, motivo):
    """⛔ Em `on`, o irreversível vai à pessoa BYTE A BYTE: `destravar` nunca é chamado."""
    for ramo in ("auto", "residencial"):
        ligar(amb, ramo=ramo)
    salvar(EMPRESA_A, sessao(ref, sub, slots=slots))
    s = rodar_turno(amb, EMPRESA_A, texto)
    assert s["state"] == "needs_human" and str(s["reason"]).startswith(motivo), (s["state"], s["reason"])
    assert amb.destravar_chamadas == [] and amb.consultas_de_modo == [], nome
    assert "pedido_de_ajuda" in amb.grupo


def test_as_listas_sao_disjuntas_e_cobrem_o_NUNCA_do_contrato():
    """🔴 Quem puser uma família do NUNCA na lista destravável fica VERMELHO aqui."""
    assert R.FAMILIAS_DESTRAVAVEIS.isdisjoint(R.FAMILIAS_QUE_NUNCA_DESTRAVAM), (
        R.FAMILIAS_DESTRAVAVEIS & R.FAMILIAS_QUE_NUNCA_DESTRAVAM)
    for fam in ("handoff_trigger", "recusa_de_cobertura", "consultora_da_seguradora",
                "fora_do_horario", "exige_documento", "apolice_de_condominio_ou_empresa",
                "playbook_not_found", "confirmacao_bloqueada"):
        assert fam in R.FAMILIAS_QUE_NUNCA_DESTRAVAM, fam
        assert not R.trava_destravavel(f"{fam}:x"), fam
    for motivo in ("formulario_incompleto:x", "formulario_em_laco", "handoff_trigger:encaminhamento_exige_pessoa",
                   "destravador:pessoa:custo_e_do_segurado", "insurer_closed", ""):
        assert not R.trava_destravavel(motivo), motivo
    # CONTROLE POSITIVO: a regra CONSEGUE dizer sim
    for motivo in ("tela_que_decide:escolhe_o_servico", "tela_que_decide:aceite_de_custo", "sem_chute:via",
                   "tecla_ambigua", "ramo_indeterminado", "conducao_esgotada", "loop_guard",
                   "missing_slots:ponto_referencia", "conferencia_divergente:endereco",
                   "human_phase_guard:model_declined", "sentinela_stall"):
        assert R.trava_destravavel(motivo), motivo
    # o `sem_chute` do FORMULÁRIO do app nunca (a resposta não é texto à URA)
    assert not R.trava_destravavel("sem_chute:x", {"flow_resposta": {"ok": False, "missing": ["x"]},
                                                   "missing_slots": ["x"]})


def test_duas_corretoras_uma_ligada_a_outra_segue_o_de_hoje(amb):
    ligar(amb, company=EMPRESA_A)
    s_b = turno_escolhe(amb, company=EMPRESA_B)
    assert amb.destravar_chamadas == [] and s_b["reason"] == "tela_que_decide:escolhe_o_servico"
    assert amb.consultas_de_modo == [(EMPRESA_B, "allianz", "residencial")]
    amb.enviadas.clear()
    s_a = turno_escolhe(amb, company=EMPRESA_A)
    assert [c["company_id"] for c in amb.destravar_chamadas] == [EMPRESA_A]
    assert s_a["state"] == "ura" and amb.enviadas == [("seguradora", "Encanador")]


def test_o_teto_por_trava_para_o_laco_e_a_terceira_vai_a_pessoa(amb):
    """A URA devolve a MESMA tela depois de cada resposta: 2 destravamentos, a 3ª é de gente."""
    ligar(amb)
    salvar(EMPRESA_A, sessao(REF_ALLIANZ_R, "encanador"))
    for _ in range(3):
        s = rodar_turno(amb, EMPRESA_A, TELA_ESCOLHE)
    assert len(amb.destravar_chamadas) == R.TETO_DO_DESTRAVADOR_POR_TRAVA == 2
    assert [e for e in amb.enviadas if e[0] == "seguradora"] == [("seguradora", "Encanador")] * 2
    assert s["state"] == "needs_human" and s["reason"] == "tela_que_decide:escolhe_o_servico"
    assert "pedido_de_ajuda" in amb.grupo


def test_o_teto_de_volta_ao_menu_e_de_sessao():
    s = {}
    assert R._cabe_mais_um_destravamento(s, "conducao_esgotada")
    s["destravamentos"] = {"conducao_esgotada": 1}
    assert not R._cabe_mais_um_destravamento(s, "conducao_esgotada")
    assert R._cabe_mais_um_destravamento(s, "loop_guard"), "o teto de uma família travou outra"
    s["destravamentos"] = {"tela_que_decide": 2, "sem_chute": 2}
    assert not R._cabe_mais_um_destravamento(s, "tecla_ambigua"), "o teto de SESSÃO (4) não segurou"
    assert R.TETO_DE_VOLTA_AO_MENU == 1 and R.TETO_DO_DESTRAVADOR_NA_SESSAO == 4


#: 📊 allianz-auto d2edf0dd — *"Vamos lá! Informe o tipo de serviço: 1 - Serviços Emergenciais…"*.
TELA_TIPO_DE_SERVICO = tela_real("allianz-auto", r"informe o tipo de servico", "d2edf0dd")


def test_o_fio_da_ida_e_volta_a_pergunta_com_as_opcoes_e_a_resposta_vira_a_tecla(amb):
    """PERGUNTAR com as opções da TELA → o segurado responde "1" → a URA recebe "1" (a volta)."""
    ligar(amb, ramo="auto")
    amb.decisao = Destravamento(classe="perguntar_ao_segurado", acao="PERGUNTAR_AO_SEGURADO",
                                valor="Que tipo de serviço você precisa?", diario_id="d-3",
                                opcoes=[r for _d, r in D.opcoes_numeradas(TELA_TIPO_DE_SERVICO)])
    salvar(EMPRESA_A, sessao(REF_ALLIANZ_A, "guincho"))
    s = rodar_turno(amb, EMPRESA_A, TELA_TIPO_DE_SERVICO)
    assert [c["gatilho"] for c in amb.destravar_chamadas] == ["tela_que_decide:escolhe_o_servico"]
    [(canal, pergunta)] = amb.enviadas
    assert canal == "cliente" and "1 - " in pergunta and "Responda com o número" in pergunta
    espera = s["esperando_do_segurado"]
    assert espera["numeradas"] and espera["slot"].endswith("_opcao") and espera["destravador"]
    # a VOLTA, pela porta do atendimento (o índice diz de qual acionamento é)
    foi = asyncio.run(R.responder_pergunta_do_acionamento(EMPRESA_A, CLIENTE, "1",
                                                           send_to_client=amb.cliente))
    assert foi is True
    assert amb.wa == [(URA, "1")], "a resposta do segurado não virou a tecla da tela"
    s = asyncio.run(R.load_active_dispatch(EMPRESA_A, URA))
    assert not s.get("esperando_do_segurado") and s["state"] == "ura"


# =============================================================================
# A volta da pergunta numa tela SEM passo — a opção escolhida, nunca o texto cru
# =============================================================================
def test_a_resposta_do_segurado_a_pergunta_do_destravador_vira_a_opcao_da_tela():
    tela = "Qual serviço deseja?\n1 - Encanador\n2 - Eletricista\n3 - Voltar"
    opcoes, numeradas = R._opcoes_para_o_segurado(tela, ["Encanador", "Eletricista", "Voltar"])
    assert numeradas and opcoes == [["1", "Encanador"], ["2", "Eletricista"]], opcoes
    espera = {"slot": "destravador_x_opcao", "opcoes": opcoes, "numeradas": True, "tela": tela,
              "sem_chute": True, "destravador": True, "passo": ""}
    s = {"transcript": [{"direction": "in", "text": tela}]}
    assert R.resposta_do_destravador_para_a_ura(s, espera, "2", tela_atual=tela) == ("2", "ok")
    assert R.resposta_do_destravador_para_a_ura(s, espera, "eletricista", tela_atual=tela) == ("2", "ok")
    # ⛔ o texto cru não vai; a tela que mudou não recebe a resposta da outra
    assert R.resposta_do_destravador_para_a_ura(s, espera, "o cano estourou", tela_atual=tela)[0] is None
    assert R.resposta_do_destravador_para_a_ura(s, espera, "2", tela_atual="Informe o CEP")[1] == "tela_mudou"


# =============================================================================
# PONTO A — o turno do cérebro da fase humana, em `on`, sem o provider
# =============================================================================
def _turno_humano(amb, company=EMPRESA_A):
    async def _provider(sess, tela):
        amb.provider_chamado += 1
        return "Para você"

    salvar(company, sessao(REF_PORTO, "guincho", estado="human_phase", company=company))
    return rodar_turno(amb, company, TELA_SEM_PASSO, provider=_provider)


def test_ponto_A_em_on_o_destravador_responde_no_lugar_do_cerebro(amb):
    ligar(amb, seguradora="porto", ramo="auto")
    amb.decisao = Destravamento(classe="conduzir", acao="RESPONDER", valor="Para você", nota=91)
    s = _turno_humano(amb)
    assert amb.provider_chamado == 0, "em `on` o cérebro antigo foi chamado junto"
    assert amb.enviadas == [("seguradora", "Para você")]
    assert [c["gatilho"] for c in amb.destravar_chamadas] == ["cerebro"]
    assert s["state"] == "human_phase" and not s.get("pending_insurer_messages")


def test_ponto_A_CONTROLE_off_e_o_cerebro_de_hoje(amb):
    s = _turno_humano(amb)
    assert amb.provider_chamado == 1 and amb.destravar_chamadas == []
    assert amb.enviadas == [("seguradora", "Para você")] and s["state"] == "human_phase"


def test_ponto_A_PESSOA_vira_needs_human_com_o_motivo_do_destravador_em_portugues(amb):
    ligar(amb, seguradora="porto", ramo="auto")
    amb.decisao = Destravamento(classe="nunca_sozinho", acao="PESSOA", proibicao="custo_e_do_segurado",
                                explicacao="A seguradora quer que o segurado aceite um custo.")
    s = _turno_humano(amb)
    assert s["state"] == "needs_human" and s["reason"] == "destravador:pessoa:custo_e_do_segurado"
    assert "pedido_de_ajuda" in amb.grupo, "a pessoa não recebeu o dossiê"
    frase = D.motivo_em_portugues(s["reason"])
    assert frase == D._MOTIVOS_EM_PORTUGUES["destravador"], "o cartão caiu na frase genérica"
    assert "_" not in frase and ":" not in frase and "custo_e_do_segurado" not in frase, frase
    assert D.politica_de_retomada(s["reason"]) == D.DIRETO_AO_HUMANO
    assert [e for e in amb.enviadas if e[0] == "seguradora"] == []


def test_ponto_A_SILENCIO_nao_envia_nada_e_marca_o_silencio(amb):
    ligar(amb, seguradora="porto", ramo="auto")
    amb.decisao = Destravamento(classe="conduzir", acao="SILENCIO")
    s = _turno_humano(amb)
    assert amb.enviadas == [] and s["state"] == "human_phase"
    assert s.get("silencio_deliberado_ate") and s.get("silencios_seguidos") == 1


# =============================================================================
# O SENTINELA — PONTO A (a escada) e PONTO B (o esgotamento)
# =============================================================================
def _sentinela(amb, s):
    salvar(EMPRESA_A, s)
    return asyncio.run(W._sentinela_recover(EMPRESA_A, URA, s, _Wa(amb), {"id": "canal-teste"}))


def _sessao_parada(**extra):
    s = sessao(REF_PORTO, "guincho", estado="human_phase", **extra)
    s["transcript"].append({"direction": "in", "text": TELA_SEM_PASSO, "at": "2026-09-30T10:00:00+00:00"})
    return s


def test_sentinela_em_on_a_tentativa_e_do_destravador_e_sai_pelo_envio_de_hoje(amb):
    ligar(amb, seguradora="porto", ramo="auto")
    amb.decisao = Destravamento(classe="conduzir", acao="RESPONDER", valor="Para você")
    s = _sessao_parada()
    assert _sentinela(amb, s) == "recovered"
    assert amb.wa == [(URA, "Para você")] and [c["gatilho"] for c in amb.destravar_chamadas] == ["sentinela"]
    assert s["transcript"][-1].get("via") == "sentinela"


def test_sentinela_esgotado_a_trava_vai_ao_destravador_antes_do_dossie(amb):
    ligar(amb, seguradora="porto", ramo="auto")
    amb.decisao = Destravamento(classe="conduzir", acao="RESPONDER", valor="Para você")
    s = _sessao_parada(sentinela_attempts=W.MAX_TENTATIVAS_NA_SESSAO)
    assert _sentinela(amb, s) == "destravador_respondeu"
    assert [c["gatilho"] for c in amb.destravar_chamadas] == ["sentinela_stall"]
    assert amb.wa == [(URA, "Para você")] and s["state"] == "human_phase" and amb.grupo == []


def test_sentinela_CONTROLE_off_esgota_como_hoje(amb):
    s = _sessao_parada(sentinela_attempts=W.MAX_TENTATIVAS_NA_SESSAO)
    assert _sentinela(amb, s) == "handoff"
    assert s["reason"] == "sentinela_stall" and amb.destravar_chamadas == [] and "dossie" in amb.grupo


def test_sentinela_PESSOA_do_destravador_diz_o_motivo_dele(amb):
    ligar(amb, seguradora="porto", ramo="auto")
    amb.decisao = Destravamento(classe="deduzir", acao="PESSOA", proibicao="segunda_opiniao_discordou")
    s = _sessao_parada()
    assert _sentinela(amb, s) == "handoff"
    assert s["reason"] == "destravador:pessoa:segunda_opiniao_discordou"
    assert len(amb.destravar_chamadas) == 1, "o esgotamento chamou o destravador de novo"


# =============================================================================
# O RESULTADO no diário — best-effort, e só quando o destravador decidiu algo
# =============================================================================
#: 📊 allianz-residencial — a tela REAL do protocolo (o número nunca é impresso).
TELA_PROTOCOLO = tela_real("allianz-residencial", r"assistencia foi solicitada com sucesso[\s\S]*protocolo")


def test_o_protocolo_que_sai_depois_de_destravar_vira_resultado(amb):
    ligar(amb)
    turno_escolhe(amb)                                  # o destravador agiu neste acionamento
    s = rodar_turno(amb, EMPRESA_A, TELA_PROTOCOLO)
    assert s["state"] == "monitoring", (s.get("state"), s.get("reason"))
    assert amb.resultados == [(EMPRESA_A, "run-123", "protocolo_saiu")]


def test_a_ura_que_fecha_vira_resultado_uma_vez(amb):
    s2 = sessao(REF_ALLIANZ_R, "encanador", destravador_agiu=True, diario_do_destravador=True)
    asyncio.run(R.marcar_resultado_no_diario(EMPRESA_A, s2, "ura_fechou"))
    asyncio.run(R.marcar_resultado_no_diario(EMPRESA_A, s2, "ura_fechou"))   # uma vez só
    assert amb.resultados == [(EMPRESA_A, "run-123", "ura_fechou")]


def test_CONTROLE_o_protocolo_sem_destravador_nao_toca_o_diario(amb):
    salvar(EMPRESA_A, sessao(REF_ALLIANZ_R, "encanador"))
    s = rodar_turno(amb, EMPRESA_A, TELA_PROTOCOLO)
    assert s["state"] == "monitoring" and amb.resultados == []


def test_CONTROLE_sem_decisao_do_destravador_o_diario_nao_e_tocado(amb):
    s = sessao(REF_ALLIANZ_R, "encanador")
    asyncio.run(R.marcar_resultado_no_diario(EMPRESA_A, s, "protocolo_saiu"))
    assert amb.resultados == []


def test_a_pessoa_depois_de_uma_decisao_autonoma_e_humano_corrigiu(amb):
    ligar(amb)
    turno_escolhe(amb)                                 # o destravador AGIU (respondeu)
    amb.decisao = Destravamento(classe="deduzir", acao="PESSOA", proibicao="nota_abaixo_do_limiar")
    rodar_turno(amb, EMPRESA_A, TELA_ESCOLHE)          # a mesma trava: agora vai à pessoa
    assert (EMPRESA_A, "run-123", "humano_corrigiu") in amb.resultados


def test_o_diario_que_cai_nao_derruba_o_turno(amb, monkeypatch):
    ligar(amb)

    async def _cai(**k):
        raise RuntimeError("banco fora")

    monkeypatch.setattr(sys.modules["app.services.diario_de_decisoes"], "marcar_resultado", _cai)
    s = sessao(REF_ALLIANZ_R, "encanador", diario_do_destravador=True)
    asyncio.run(R.marcar_resultado_no_diario(EMPRESA_A, s, "protocolo_saiu"))   # não levanta


# =============================================================================
# 🧵 COSTURA com o destravador REAL da F1a (o módulo de verdade; dublê só no MODELO)
# =============================================================================
def _destravador_real(amb, monkeypatch, resposta_do_modelo: str, segunda=None):
    """O `app.services.destravador` REAL no fio, com a borda do modelo dublada (nada sai da máquina)."""
    import importlib

    monkeypatch.delitem(sys.modules, "app.services.destravador", raising=False)
    real = importlib.import_module("app.services.destravador")
    assert not hasattr(real, "_e_duble"), "o módulo carregado não é o da F1a"

    async def _modo(company_id, insurer_key, ramo):
        amb.consultas_de_modo.append((company_id, insurer_key, ramo))
        return amb.modos.get((company_id, insurer_key, ramo), ("off", 70))

    async def _quem_decide(mensagens, company_id, modo):
        amb.destravar_chamadas.append({"company_id": company_id, "modo": modo,
                                       "user": mensagens[-1].content})
        return types.SimpleNamespace(content=resposta_do_modelo), "openai", "gpt-6.1-sol"

    async def _segunda(conversa, cid, modo, provedor, tela):
        return segunda, 0.0

    monkeypatch.setattr(real, "modo_do_destravador", _modo)
    monkeypatch.setattr(real, "_chamar_quem_decide", _quem_decide)
    monkeypatch.setattr(real, "_segunda_opiniao", _segunda)
    return real


def test_costura_real_PERGUNTAR_do_modelo_vira_a_pergunta_ao_segurado(amb, monkeypatch):
    """PONTO A (Porto — ida e volta permitida hoje; a Allianz/Alfa é a D6, da F3)."""
    real = _destravador_real(amb, monkeypatch, json.dumps({
        "classe": "perguntar_ao_segurado", "acao": "PERGUNTAR_AO_SEGURADO",
        "valor": "Para quem é o atendimento: para você ou para outra pessoa?", "nota": 80,
        "motivo": "só o segurado sabe"}))
    ligar(amb, seguradora="porto", ramo="auto")
    s = _turno_humano(amb)
    assert amb.provider_chamado == 0 and len(amb.destravar_chamadas) == 1
    assert amb.destravar_chamadas[0]["modo"] == "on"
    [(canal, texto)] = amb.enviadas
    assert canal == "cliente" and "para você ou para outra pessoa?" in texto, texto
    assert (s.get("esperando_do_segurado") or {}).get("destravador") is True
    assert s["state"] == "human_phase" and not s.get("reason") and amb.grupo == []
    assert real.Destravamento is not Destravamento


def test_costura_real_PESSOA_do_modelo_e_o_dossie_de_hoje(amb, monkeypatch):
    _destravador_real(amb, monkeypatch, json.dumps({
        "classe": "nunca_sozinho", "acao": "PESSOA", "valor": "", "nota": 95,
        "motivo": "não dá para saber"}))
    ligar(amb)
    s = turno_escolhe(amb)
    assert (s["state"], s["reason"]) == ("needs_human", "tela_que_decide:escolhe_o_servico")
    assert "pedido_de_ajuda" in amb.grupo and [e for e in amb.enviadas if e[0] == "seguradora"] == []


def test_costura_real_o_lixo_do_modelo_nunca_vai_a_URA(amb, monkeypatch):
    _destravador_real(amb, monkeypatch, '[{"type": "reasoning", "encrypted_content": "gAAAA"}]')
    ligar(amb)
    s = turno_escolhe(amb)
    assert [e for e in amb.enviadas if e[0] == "seguradora"] == [], amb.enviadas
    assert s["state"] == "needs_human"
