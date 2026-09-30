# -*- coding: utf-8 -*-
"""SPEC-122 F2+F3 — o `sem_chute` pergunta ao segurado, e o cérebro V2 roda em SOMBRA.

O FIO (o do produto, nada reimplementado; dublê só na BORDA — modelo, banco, Redis, WhatsApp):

  F3 · webhook → dispatch_router.try_route_insurer_inbound → handle_insurer_message (motor)
       → cérebro de PRODUÇÃO (`human_reply_provider`, dublê do modelo V0) → guard → envio
       → acao_do_cerebro.agendar_sombra → modo_do_cerebro (a chave `cerebro_modos`)
       → bancada.mensagens_da_variante("V2") → llm_factory.invocar_com_reserva (DUBLÊ)
       → acao_do_cerebro.decidir → comparar → work_events `cerebro.sombra`
  F2 · … → handle_insurer_message: passo `sem_chute` sem o dado → `needs_human` + o PEDIDO
       → roteador: perguntar_ao_segurado (com as OPÇÕES da tela) → espera
       → responder_pergunta_do_acionamento → traduzir_resposta_do_segurado (MOTOR) → URA
       ou → uma pessoa (resposta ambígua; e Allianz/Alfa, sempre).

⛔ Nada sai da máquina. As telas são REAIS (`tests/corpus/telas_reais`, mascaradas).
"""
from __future__ import annotations

import asyncio
import inspect
import json
import os
import re
import sys
import types
from pathlib import Path

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.environ.setdefault("INSURER_DISPATCH_LIVE", "false")
os.environ["DISPATCH_MIRROR"] = "0"

from app.services import acao_do_cerebro as AC  # noqa: E402
from app.services import corridor_playbooks as CP  # noqa: E402
from app.services import dispatch_router as R  # noqa: E402
from app.services import insurer_dispatch_service as D  # noqa: E402
from app.services import o_grupo_so_o_que_importa as G  # noqa: E402
from app.tasks import dispatch_watchdog as W  # noqa: E402

CORPUS = Path(RAIZ) / "tests" / "corpus" / "telas_reais"
URA = "5511999990000"
CLIENTE = "5548988887777"
EMPRESA_A = "11111111-1111-1111-1111-111111111111"
EMPRESA_B = "22222222-2222-2222-2222-222222222222"


def tela_real(arquivo: str, padrao: str) -> str:
    """A PRIMEIRA tela do corpus real que casa `padrao` (o texto vem do acervo, não da imaginação)."""
    for linha in (CORPUS / f"{arquivo}.jsonl").read_text(encoding="utf-8").splitlines():
        t = json.loads(linha)["text"]
        if re.search(padrao, t, re.I):
            return t
    raise AssertionError(f"o corpus {arquivo} não tem tela que case {padrao!r}")


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

    async def delete(self, k):
        self.d.pop(k, None)

    async def lpop(self, k):
        return None

    async def scan_iter(self, match="*"):
        for k in list(self.d):
            if k.startswith(match.rstrip("*")):
                yield k


class _Banco:
    """O banco na BORDA: `work_events` (insert) e `cerebro_modos` (select … eq company_id)."""

    def __init__(self, amb):
        self.amb = amb
        self.client = self

    def table(self, nome):
        return _Consulta(self.amb, nome)


class _Consulta:
    def __init__(self, amb, tabela):
        self.amb, self.tabela, self.linha, self.filtros = amb, tabela, None, {}

    def insert(self, linha):
        self.linha = linha
        return self

    def eq(self, col, val):
        self.filtros[col] = val
        return self

    def __getattr__(self, _nome):
        return lambda *a, **k: self

    async def execute(self):
        if self.tabela == "work_events" and self.linha:
            self.amb.eventos.append(self.linha)
        if self.tabela == "cerebro_modos":
            linhas = list(self.amb.chaves)
            if not self.amb.banco_vaza:   # o banco real filtra; o "vazado" prova o cinto do código
                linhas = [x for x in linhas if all(str(x.get(c)) == str(v) for c, v in self.filtros.items())]
            return types.SimpleNamespace(data=linhas)
        return types.SimpleNamespace(data=[])


class _Wa:
    def __init__(self, amb):
        self.amb = amb

    def send_message(self, fone, texto, integ=None, **k):
        self.amb.wa.append((fone, texto))


class Ambiente:
    def __init__(self):
        self.redis = _Redis()
        self.eventos, self.enviadas, self.wa, self.grupo = [], [], [], []
        self.chaves, self.banco_vaza = [], False
        self.chamadas_ao_modelo = []
        self.saida_do_modelo = '{"acao": "RESPONDER", "valor": "1", "motivo": "dublê"}'

    # os dois canais que o webhook entrega ao roteador
    def ura(self, texto):
        self.enviadas.append(("seguradora", texto))

    def cliente(self, fone, texto):
        self.enviadas.append(("cliente", texto))

    def sombras(self):
        return [e for e in self.eventos if e["event_type"] == AC.EVENTO_SOMBRA]


@pytest.fixture
def amb(monkeypatch):
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

    async def _invocar(papel, mensagens, *, company_id=None, agent_id=None, service_type=None,
                       classe_de_dado=None):
        # 🔴 A BORDA DO MODELO: nada sai da máquina. Guarda QUEM pediu, com que papel e ledger.
        a.chamadas_ao_modelo.append({"papel": papel, "company_id": company_id,
                                     "service_type": service_type,
                                     "system": mensagens[0].content, "user": mensagens[1].content})
        return types.SimpleNamespace(content=a.saida_do_modelo,
                                     response_metadata={"model_name": "dublê"})

    import app.core.database as _core_db
    import app.core.redis as _core_redis
    from app.factories import llm_factory

    monkeypatch.setattr(_core_redis, "get_async_redis_client", _redis)
    monkeypatch.setattr(_core_db, "get_supabase_client", lambda: None)
    monkeypatch.setattr(R, "_redis", _redis)
    monkeypatch.setattr(R, "_db", _db)
    monkeypatch.setattr(R, "resolver_destino_de_suporte", _destino)
    monkeypatch.setattr(G, "enviar_ao_grupo", _porta)
    monkeypatch.setattr(llm_factory, "invocar_com_reserva", _invocar)
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
    # AO VIVO: o envio passa pelos canais DUBLADOS (`amb.ura`/`amb.cliente`/`_Wa`), e é
    # exatamente por isso que dá para comparar o que SAIU, byte a byte.
    monkeypatch.setattr(D, "dispatch_live_enabled", lambda: True)
    AC._CACHE_DA_CHAVE.clear()
    R._memory_store.clear()
    yield a
    AC._CACHE_DA_CHAVE.clear()


def sessao(ref, subservice, *, estado="ura", company=EMPRESA_A, slots=None, run="run-122", **extra):
    s = D.new_dispatch_session(case_id="c122", company_id=company, playbook_ref=ref,
                               subservice=subservice, slots=dict(slots or {}))
    s.update({"state": estado, "client_phone": CLIENTE, "work_run_id": run, "live": True,
              "mirror_conversation_id": "conv-122", "retry_count": 1})
    s.update(extra)
    return s


def rodar_turno(amb, company, texto, provider=None):
    """UM inbound da seguradora pelo roteador REAL — e espera a sombra que ele agendou."""
    async def _turno():
        await R.try_route_insurer_inbound(company_id=company, from_phone=URA, text=texto,
                                          send_to_insurer=amb.ura, send_to_client=amb.cliente,
                                          human_reply_provider=provider)
        if AC._SOMBRAS:
            await asyncio.gather(*list(AC._SOMBRAS))
    asyncio.run(_turno())
    return asyncio.run(R.load_active_dispatch(company, URA))


def salvar(company, s):
    asyncio.run(R.save_active_dispatch(company, URA, s))


# =============================================================================
# F3 · A SOMBRA
# =============================================================================
def _caso_do_cerebro(chave: str) -> dict:
    for linha in (Path(RAIZ) / "tests/corpus/bancada/cerebro/casos.jsonl").read_text(encoding="utf-8").splitlines():
        c = json.loads(linha)
        if c["chave"] == chave:
            return c
    raise AssertionError(chave)


#: 📊 Uma tela REAL sem passo, gatilho nem armadilha (grupo A da bancada, mascarada) que o
#: roteador leva ao cérebro na fase humana — achada rodando o ROTEADOR sobre as do grupo A.
TELA_SEM_PASSO = _caso_do_cerebro("cer-A-porto-019")["entrada"]["tela"]
REF_PORTO = "porto-auto-whatsapp@v1"


async def _cerebro_de_producao(sess, tela):
    """O dublê do modelo de PRODUÇÃO (V0): texto livre, como hoje."""
    return "Para você"


def _turno_da_fase_humana(amb, company=EMPRESA_A, tela=TELA_SEM_PASSO, run="run-122"):
    salvar(company, sessao(REF_PORTO, "guincho", estado="human_phase", company=company, run=run))
    return rodar_turno(amb, company, tela, provider=_cerebro_de_producao)


def _ligar(amb, company, seguradora="porto", ramo="todos", modo="sombra"):
    amb.chaves.append({"company_id": company, "insurer_key": seguradora, "ramo": ramo, "modo": modo})


def test_o_fio_da_sombra_mesmo_envio_byte_a_byte_e_a_decisao_da_V2_na_linha_do_tempo(amb):
    """🔴 O TESTE DO FIO (F3). CONTROLE `off` × `sombra`, a MESMA tela real, o MESMO dublê de produção."""
    # CONTROLE: sem chave → o que o produto faz hoje, e NENHUMA chamada extra.
    s_off = _turno_da_fase_humana(amb)
    envio_off = list(amb.enviadas)
    assert envio_off == [("seguradora", "Para você")], (
        "o cérebro de produção tem de ter respondido a tela (senão o fio não passou por ele)", envio_off)
    assert amb.chamadas_ao_modelo == [] and amb.sombras() == []
    # SOMBRA
    amb.enviadas.clear()
    amb.redis.d.clear()
    AC._CACHE_DA_CHAVE.clear()
    _ligar(amb, EMPRESA_A)
    amb.saida_do_modelo = '{"acao": "PESSOA", "valor": "", "motivo": "escolhe o seguro"}'
    s_sombra = _turno_da_fase_humana(amb)
    # G9 — o que saiu é o MESMO, byte a byte; a sessão gravada, idem.
    assert amb.enviadas == envio_off
    assert [t.get("text") for t in s_sombra["transcript"]] == [t.get("text") for t in s_off["transcript"]]
    assert s_sombra["state"] == s_off["state"]
    # a V2 foi chamada UMA vez, pela rota do produto, com o ledger PRÓPRIO e a corretora certa
    assert len(amb.chamadas_ao_modelo) == 1
    ch = amb.chamadas_ao_modelo[0]
    assert (ch["papel"], ch["service_type"], ch["company_id"]) == ("dispatch", "cerebro_sombra", EMPRESA_A)
    assert "FORMATO DA SUA RESPOSTA" in ch["system"] and "REGRAS CURTAS" in ch["user"], "não é a V2 medida"
    # e a decisão dela está na linha do tempo, com o que o sistema FEZ ao lado
    [ev] = amb.sombras()
    p = ev["payload_redacted"]
    assert ev["company_id"] == EMPRESA_A and ev["work_run_id"] == "run-122"
    assert p["modo"] == "sombra" and p["variante"] == "V2" and (p["seguradora"], p["ramo"]) == ("porto", "auto")
    assert p["sistema"]["acao"] == "RESPONDER" and p["modelo"]["acao_final"] == "PESSOA"
    assert p["diverge"] is True and p["divergencia"] == "acao" and p["conta_como_acerto"] is False


def test_a_sombra_igual_ao_sistema_nao_diverge(amb):
    _ligar(amb, EMPRESA_A)
    amb.saida_do_modelo = '{"acao": "RESPONDER", "valor": "Para você", "motivo": "pessoa física"}'
    _turno_da_fase_humana(amb)
    [ev] = amb.sombras()
    p = ev["payload_redacted"]
    assert p["sistema"]["acao"] == "RESPONDER"
    if p["modelo"]["acao_final"] == "RESPONDER":        # o conferente/D3 do produto decidem
        assert p["diverge"] is False and p["conta_como_acerto"] is True
    else:
        assert p["diverge"] is True and p["modelo"]["proibicao"], p["modelo"]


def test_a_mesma_tela_duas_vezes_grava_uma(amb):
    _ligar(amb, EMPRESA_A)
    _turno_da_fase_humana(amb)
    rodar_turno(amb, EMPRESA_A, TELA_SEM_PASSO, provider=_cerebro_de_producao)
    assert len(amb.sombras()) == 1 and len(amb.chamadas_ao_modelo) == 1
    # CONTROLE: OUTRO acionamento (outro run) com a mesma tela grava de novo.
    _turno_da_fase_humana(amb, run="run-122-b")
    assert len(amb.sombras()) == 2


def test_duas_corretoras_nao_se_misturam(amb):
    _ligar(amb, EMPRESA_A)
    _turno_da_fase_humana(amb, company=EMPRESA_B)            # B não ligou nada
    assert amb.chamadas_ao_modelo == [] and amb.sombras() == []
    _turno_da_fase_humana(amb, company=EMPRESA_A)
    assert [c["company_id"] for c in amb.chamadas_ao_modelo] == [EMPRESA_A]
    assert [e["company_id"] for e in amb.sombras()] == [EMPRESA_A]


def test_o_cinto_do_codigo_segura_um_banco_que_vaza_outra_corretora(amb):
    """A borda devolve a linha de A quando B pergunta — o filtro no CÓDIGO recusa (§7)."""
    _ligar(amb, EMPRESA_A)
    amb.banco_vaza = True
    assert asyncio.run(AC.modo_do_cerebro(EMPRESA_B, "porto", "auto")) == "off"
    AC._CACHE_DA_CHAVE.clear()
    assert asyncio.run(AC.modo_do_cerebro(EMPRESA_A, "porto", "auto")) == "sombra"   # CONTROLE


def test_o_modo_on_e_recusado_com_a_razao(amb):
    with pytest.raises(AC.ModoRecusado, match="bancada"):
        AC.validar_modo("on")
    with pytest.raises(AC.ModoRecusado):
        AC.validar_modo("talvez")
    assert AC.validar_modo("SOMBRA") == "sombra" and AC.validar_modo("off") == "off"
    assert "on" not in AC.MODOS
    # uma linha `on` que chegasse ao banco (a constraint a recusa) vale `off` — e nada é chamado
    _ligar(amb, EMPRESA_A, modo="on")
    _turno_da_fase_humana(amb)
    assert amb.chamadas_ao_modelo == [] and amb.sombras() == []


def test_o_ramo_explicito_vence_o_todos(amb):
    _ligar(amb, EMPRESA_A, ramo="todos", modo="sombra")
    _ligar(amb, EMPRESA_A, ramo="auto", modo="off")
    assert asyncio.run(AC.modo_do_cerebro(EMPRESA_A, "porto", "auto")) == "off"
    assert asyncio.run(AC.modo_do_cerebro(EMPRESA_A, "porto", "residencial")) == "sombra"
    assert asyncio.run(AC.modo_do_cerebro(EMPRESA_A, "hdi", "auto")) == "off"


def test_G9_a_sombra_nao_tem_como_enviar():
    """Estrutural: a sombra não recebe sender, não chama verbo de envio, não toca a sessão viva."""
    params = list(inspect.signature(AC.sombra_do_cerebro).parameters)
    assert params == ["company_id", "sessao", "tela", "sistema"]
    fonte = inspect.getsource(AC)
    proibidos = ("send_message", "reply_human_phase", "_emit(", "send_to_insurer", "send_to_client",
                 "save_active_dispatch", "enviar_ao_grupo")
    assert [p for p in proibidos if p in fonte] == []


def test_a_tela_de_sem_chute_nunca_vira_responder_nem_em_sombra(amb):
    """🔴 Em CÓDIGO (`decidir`): a tela casada por um passo `sem_chute` → pergunta / pessoa."""
    tela = tela_real("hdi-auto", r"situa[çc][õo]es de risco")
    s = sessao("hdi-auto-whatsapp@v1", "socorro_mecanico")
    modelo = '{"acao": "RESPONDER", "valor": "Nenhuma das anteriores", "motivo": "chute"}'
    d = AC.decidir(modelo, s, tela, estruturada=True, ida_e_volta_permitida=True)
    assert (d["acao_do_modelo"], d["acao_final"], d["proibicao"]) == (
        "RESPONDER", "PERGUNTAR_AO_SEGURADO", "passo_sem_chute")
    d = AC.decidir(modelo, s, tela, estruturada=True, ida_e_volta_permitida=False)
    assert d["acao_final"] == "PESSOA"
    # CONTROLE: numa tela SEM passo sem_chute a regra não dispara
    d = AC.decidir('{"acao": "RESPONDER", "valor": "Para você", "motivo": "x"}',
                   sessao(REF_PORTO, "guincho"), TELA_SEM_PASSO, estruturada=True)
    assert d["proibicao"] != "passo_sem_chute"
    # e na SOMBRA ela fica registrada, e não conta como acerto
    _ligar(amb, EMPRESA_A, seguradora="hdi")
    amb.saida_do_modelo = modelo
    p = asyncio.run(AC.sombra_do_cerebro(EMPRESA_A, s, tela, {"acao": "PESSOA", "valor": ""}))
    assert p["sem_chute"] is True and p["conta_como_acerto"] is False and p["grave_segurado_pelo_codigo"] is True


# =============================================================================
# F2 · O `sem_chute` PERGUNTA AO SEGURADO (D-122 D1/D2)
# =============================================================================
TELA_RISCO_HDI = tela_real("hdi-auto", r"situa[çc][õo]es de risco")
TELA_TAXI_PORTO = tela_real("porto-auto", r"s[ãa]o quantos passageiros")
TELA_APARELHO_ALLIANZ = tela_real("allianz-residencial", r"qual eletrodom[ée]stico precisa de conserto")
REF_HDI = "hdi-auto-whatsapp@v1"
REF_ALLIANZ = "allianz-residencial-whatsapp@v1"


class _Cerebro:
    """O cérebro de produção DUBLADO — para provar que NINGUÉM o chama numa tela `sem_chute`."""

    def __init__(self):
        self.chamadas = 0

    async def __call__(self, sess, tela):
        self.chamadas += 1
        return "1"


def _responder(amb, texto, company=EMPRESA_A):
    return asyncio.run(R.responder_pergunta_do_acionamento(company, CLIENTE, texto,
                                                           send_to_client=amb.cliente))


def _ao_cliente(amb):
    return [t for q, t in amb.enviadas if q == "cliente"]


def _a_seguradora(amb):
    return [t for q, t in amb.enviadas if q == "seguradora"] + [t for f, t in amb.wa if f == URA]


def _risco_hdi(amb, cerebro=None):
    salvar(EMPRESA_A, sessao(REF_HDI, "socorro_mecanico", slots={"problema_descricao": "o carro morreu"}))
    return rodar_turno(amb, EMPRESA_A, TELA_RISCO_HDI, provider=cerebro)


def test_o_fio_do_sem_chute_hdi_pergunta_com_as_opcoes_e_a_resposta_vira_a_opcao_pelo_motor(amb):
    """🔴 O TESTE DO FIO (F2): tela REAL de risco da HDI → pergunta ao segurado → "2" → a URA
    recebe o RÓTULO da opção 2, pelo motor. O cérebro nunca é chamado; nenhuma pessoa é acionada."""
    cerebro = _Cerebro()
    s = _risco_hdi(amb, cerebro)
    assert s["state"] == "ura" and "reason" not in s, (s["state"], s.get("reason"))
    esp = s["esperando_do_segurado"]
    assert esp["sem_chute"] is True and esp["slot"] == "situacao_risco_opcao" and esp["passo"] == "situacao_risco"
    [pergunta] = _ao_cliente(amb)
    assert "rua está escura ou deserta" in pergunta and "2 - Via com pouco movimento" in pergunta
    assert _a_seguradora(amb) == [] and amb.grupo == [] and cerebro.chamadas == 0
    assert s["falta_para_a_ura"]["sem_chute"] is True
    # a resposta do segurado — o NÚMERO da opção
    assert _responder(amb, "2") is True
    s = asyncio.run(R.load_active_dispatch(EMPRESA_A, URA))
    assert _a_seguradora(amb) == ["Via com pouco movimento"]
    assert s["slots"]["situacao_risco_opcao"] == "Via com pouco movimento"
    assert "esperando_do_segurado" not in s and s["state"] == "ura" and amb.grupo == []


def test_a_resposta_pelo_texto_de_uma_opcao_tambem_vira_a_opcao(amb):
    _risco_hdi(amb)
    assert _responder(amb, "Nenhuma das anteriores") is True
    assert _a_seguradora(amb) == ["Nenhuma das anteriores"]


def test_resposta_ambigua_vai_a_uma_pessoa_e_nada_vai_a_seguradora(amb):
    _risco_hdi(amb)
    # 📊 "via": o casador frouxo do Atlas casava SÓ "Rodovia" — a troca que o sem_chute proíbe.
    assert _responder(amb, "via") is True
    s = asyncio.run(R.load_active_dispatch(EMPRESA_A, URA))
    assert _a_seguradora(amb) == []
    assert s["state"] == "needs_human" and s["reason"] == "sem_chute:situacao_risco_opcao"
    assert "dossie" in amb.grupo and s.get("dossier_sent") is True
    assert s["transcript"][-1]["step"] == "resposta_do_segurado_sem_opcao"
    # e a resposta que não é opção nenhuma, idem
    assert D.traduzir_resposta_do_segurado(s, {**s.get("motivo_legivel", {}), "slot": "situacao_risco_opcao",
                                               "passo": "situacao_risco", "tela": TELA_RISCO_HDI,
                                               "opcoes": [["1", "Via com pouca iluminação"],
                                                          ["2", "Via com pouco movimento"]]},
                                           "não sei")[0] is None


def test_numero_fora_das_opcoes_vai_a_uma_pessoa(amb):
    _risco_hdi(amb)
    assert _responder(amb, "9") is True
    s = asyncio.run(R.load_active_dispatch(EMPRESA_A, URA))
    assert _a_seguradora(amb) == [] and s["state"] == "needs_human"


def test_porto_taxi_tecla_de_botao_pergunta_e_volta_pelo_motor(amb):
    salvar(EMPRESA_A, sessao("porto-auto-whatsapp@v1", "guincho"))
    s = rodar_turno(amb, EMPRESA_A, TELA_TAXI_PORTO)
    assert s["state"] == "ura" and s["esperando_do_segurado"]["slot"] == "taxi_passageiros_opcao"
    [pergunta] = _ao_cliente(amb)
    assert "1 - 1 a 4" in pergunta and "2 - Mais de 4" in pergunta
    assert _responder(amb, "1") is True
    assert _a_seguradora(amb) == ["1 a 4"]


def test_CONTROLE_allianz_continua_indo_a_uma_pessoa_exatamente_como_hoje(amb, monkeypatch):
    """D-122 D2: na Allianz a URA encerra no meio da pergunta — o `sem_chute` vai a uma PESSOA.
    E "como hoje" é medido: o MESMO envio com a regra nova e SEM ela (tabela D2 vazia)."""
    def _rodar():
        amb.enviadas.clear(); amb.wa.clear(); amb.grupo.clear(); amb.redis.d.clear()
        salvar(EMPRESA_A, sessao(REF_ALLIANZ, "eletrodomesticos"))
        return rodar_turno(amb, EMPRESA_A, TELA_APARELHO_ALLIANZ)
    s = _rodar()
    agora = (list(amb.enviadas), list(amb.grupo), s["state"], s.get("reason"))
    assert s["state"] == "needs_human" and str(s.get("reason")).startswith("sem_chute:")
    assert "esperando_do_segurado" not in s and "sem_chute_ao_segurado" not in s
    assert not [t for t in _ao_cliente(amb) if "Só mais uma informação" in t], "a Allianz PERGUNTOU"
    monkeypatch.setattr(D, "IDA_E_VOLTA_AO_SEGURADO", {})
    s2 = _rodar()
    assert (list(amb.enviadas), list(amb.grupo), s2["state"], s2.get("reason")) == agora


def test_alfa_e_seguradora_sem_medicao_nao_perguntam():
    assert not D.ida_e_volta_permitida("alfa-auto-whatsapp@v1")
    assert not D.ida_e_volta_permitida(REF_ALLIANZ)
    assert not D.ida_e_volta_permitida("bradesco-auto-whatsapp@v1")   # sem decisão D2 → fechado
    assert all(D.ida_e_volta_permitida(r) for r in ("porto-auto-whatsapp@v1", REF_HDI,
                                                     "yelum-auto-whatsapp@v3", "zurich-auto-whatsapp@v1"))
    # a bancada e o produto não discordam sobre onde é PROIBIDO
    from app.services.evals.bancada import SEM_IDA_E_VOLTA
    assert not (set(D.IDA_E_VOLTA_AO_SEGURADO) & set(SEM_IDA_E_VOLTA))


def test_tecla_sem_opcoes_legiveis_nao_se_pergunta():
    pb = D.get_playbook(REF_HDI)
    s = sessao(REF_HDI, "socorro_mecanico")
    assert D.sem_chute_ao_segurado(pb, "situacao_risco", ["situacao_risco_opcao"],
                                   "Você se encontra em situação de risco?", s, estado_antes="ura") is None
    # CONTROLE: com a tela real, pede
    assert D.sem_chute_ao_segurado(pb, "situacao_risco", ["situacao_risco_opcao"],
                                   TELA_RISCO_HDI, s, estado_antes="ura")
    # e já perguntado → não pergunta de novo
    s["perguntado_ao_segurado"] = ["situacao_risco_opcao"]
    assert D.sem_chute_ao_segurado(pb, "situacao_risco", ["situacao_risco_opcao"],
                                   TELA_RISCO_HDI, s, estado_antes="ura") is None


def test_prazo_vencido_vai_a_uma_pessoa_pelo_caminho_que_ja_existe(amb):
    s = _risco_hdi(amb)
    _intervalo, maximo = R._env_pergunta()
    s["esperando_do_segurado"]["holdings"] = maximo
    desfecho = asyncio.run(W._segurar_ou_desistir(EMPRESA_A, URA, s, _Wa(amb), {"id": "canal"}))
    assert desfecho == "desistiu" and s["state"] == "needs_human"
    assert s["reason"] == "segurado_nao_respondeu" and s["espera_vencida"]["sem_chute"] is True


# ----------------------------------------------------------------------------- coletar ANTES
def test_situacao_de_risco_sai_da_resposta_do_segurado_a_local_situacao():
    def deriva(**slots):
        D._derivar_teclas_do_caso(slots)
        return slots.get("situacao_risco_opcao")
    assert deriva(local_atual="Rua das Flores 10", local_situacao="escuro ou mal iluminado") == "Via com pouca iluminação"
    assert deriva(local_atual="Rua das Flores 10", local_situacao="pouca circulação de pessoas") == "Via com pouco movimento"
    assert deriva(local_atual="Rua das Flores 10", local_situacao="local seguro") == "Nenhuma das anteriores"
    # CONTROLE: o veto da rodovia continua valendo — "seguro" no acostamento não vira "nenhuma"
    assert deriva(local_atual="Rodovia dos Bandeirantes km 42", local_situacao="local seguro") is None
    # CONTROLE: sem resposta, sem chute
    assert deriva(local_atual="Rua das Flores 10") is None


def test_o_portao_cobra_os_dois_antes_de_acionar():
    for sub in ("guincho", "bateria", "pneu", "chaveiro"):
        assert "via_ou_rodovia_opcao" in CP.get_playbook("bradesco-auto-whatsapp@v1")["subservices"][sub]["required_slots"]
    for sub in ("guincho", "pneu", "chaveiro", "socorro_mecanico"):
        assert "local_situacao" in CP.get_playbook(REF_HDI)["subservices"][sub]["required_slots"]
    # a derivação vem ANTES do portão: endereço de rua não é perguntado; zona rural é
    rua = D.new_dispatch_session(case_id="x", company_id=EMPRESA_A, playbook_ref="bradesco-auto-whatsapp@v1",
                                 subservice="guincho", slots={"local_atual": "Rua das Flores 10, Centro"})
    assert rua["slots"]["via_ou_rodovia_opcao"] == "Via local"
    assert "via_ou_rodovia_opcao" not in (rua.get("missing_slots") or [])
    rural = D.new_dispatch_session(case_id="x", company_id=EMPRESA_A, playbook_ref="bradesco-auto-whatsapp@v1",
                                   subservice="guincho", slots={"local_atual": "Sitio Boa Vista, zona rural"})
    assert "via_ou_rodovia_opcao" in (rural.get("missing_slots") or [])


def test_o_valor_coletado_vira_o_rotulo_do_botao_pelo_formatador():
    tela = tela_real("bradesco-auto", r"via local\*? ou \*?rodovia")
    passo = CP.match_ura_step(CP.get_playbook("bradesco-auto-whatsapp@v1"), tela, subservice="guincho")
    assert passo["step"] == "via_local_rodovia"
    assert CP.render_reply(passo, {"via_ou_rodovia_opcao": "estou na rodovia"})["reply"] == "Rodovia"
    assert CP.render_reply(passo, {"via_ou_rodovia_opcao": "Via local"})["reply"] == "Via local"
    # sem valor que case UMA opção → não responde (vai ao `sem_chute`)
    assert CP.render_reply(passo, {"via_ou_rodovia_opcao": "sei lá"})["ok"] is False
