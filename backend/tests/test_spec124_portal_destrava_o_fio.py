# -*- coding: utf-8 -*-
"""SPEC-124 F1 — 🔴 O TESTE DO FIO: o portal de vidros destrava com a MESMA política do WhatsApp.

O FIO (motor real; dublê SÓ na borda — o HAR do portal, o banco, o cliente do modelo):

  HAR REAL (Yelum, para-brisa — `docs/intake/`, fora do Git) com a UF do serviço ilegível
  → `vidros_apifirst.abrir_atendimento_api` (o MOTOR) → `needs_human` `uf_desconhecida`,
    `acao_esperada = responder:cidade_servico`, as 27 UFs do portal em `opcoes`
  → `worker._augment_hitl_evidence` (o worker real) → a linha do `portal_jobs`
  → `PortalActionTool._aguardar` (a tool real) → modo `on` em `cerebro_modos` (seguradora pela chave
    do corredor, ramo `vidros`, a linha `todos` vale)
  → `destravador.destravar_parada_do_portal` → o papel `destravador` (`invocar_com_reserva`, DUBLÊ)
    → `decidir_parada_do_portal` → `regua_do_nucleo` (o MESMO núcleo do WhatsApp)
  → `diario_de_decisoes.registrar_decisao` (real; o banco é dublê) — `respondeu_portal`
  → `montar_job_de_continuacao` + `enfileirar_continuacao` (o mecanismo da 001.10.1)
  → o "worker" dublado roda o MOTOR REAL `vidros_continuacao.continuar_atendimento` com a UF certa
  → o pedido passa a cidade e para em `decidir_reparo` → o destravador: NUNCA (custo) → pergunta ao
    segurado, nada vai ao portal → `format_result` (o caminho de hoje).

Nasceu VERMELHO: sem a F1, `_aguardar` devolvia `format_result` na primeira parada (nenhum job de
continuação, nenhuma linha no diário). ⛔ Nenhuma mensagem sai (`_notify` dublado), nenhum portal real,
nenhum banco real, nenhum modelo real. ⛔ Nenhum valor pessoal do HAR é impresso nem afirmado em texto.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import copy
import json
import os
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from cryptography.fernet import Fernet  # noqa: E402

os.environ.setdefault("PORTAL_VAULT_KEY", Fernet.generate_key().decode())

import _replay_vidros as RV  # noqa: E402

try:
    HAR = RV.carregar("NOVO")
except RV.HarAusente as _e:  # pragma: no cover — sem o acervo local
    pytest.skip(f"sem os HAR do portal (fora do Git): {_e}", allow_module_level=True)

from langchain_core.messages import AIMessage  # noqa: E402

from app.agents.tools import portal_params as PP  # noqa: E402
from app.agents.tools import portal_tool as PT  # noqa: E402
from app.factories import llm_factory as LF  # noqa: E402
from app.services import acao_do_cerebro as AC  # noqa: E402
from app.services import destravador as DT  # noqa: E402
from portal_worker import guardrails as G  # noqa: E402
from portal_worker import worker as W  # noqa: E402
from portal_worker.journeys import vidros_apifirst as AF  # noqa: E402
from portal_worker.journeys import vidros_continuacao as VC  # noqa: E402

# 💭 Corretoras fictícias (CLAUDE.md §13.9): ids gerados aqui, nenhum nome.
EMPRESA_A = "aaaaaaaa-0000-4000-8000-0000000124a1"
EMPRESA_B = "bbbbbbbb-0000-4000-8000-0000000124b2"
RUN = str(uuid.UUID(int=124))


class RT:
    """O que o worker injeta em `params["_runtime"]`: guard + checkpoint em memória."""

    def __init__(self, liberado: bool):
        self.guard = G.PortalActionGuard(material_liberado=liberado, _checkpoint=self.cp)

    async def cp(self, _patch):
        return None


def _evidencia_do_worker(r, ev):
    """O que o worker grava em `portal_jobs.evidence` (o mesmo ramo de `worker.py`)."""
    if r.status == "needs_human":
        return W._augment_hitl_evidence(r, ev)
    return {**ev, **(r.captured or {}), "message": r.message}


# ── a parada REAL, pelo motor ───────────────────────────────────────────────────
_BASE = RV.params_do_har(HAR)
_CIDADE = dict(_BASE["local"]["cidade_servico"])
UF_CERTA = _CIDADE["uf"]


def parada_real(*, uf_ilegivel: bool):
    """(params_do_job, evidence_do_job, cursor) — `uf_ilegivel=False` para em `decidir_reparo`."""
    extra = ({"local": {"cidade_servico": {"uf": "ZZ", "cidade": _CIDADE["cidade"]}, "estado": UF_CERTA}}
             if uf_ilegivel else None)
    params = RV.params_do_har(HAR, extra=extra)
    params["_runtime"] = RT(True)
    page = RV.PaginaDeReplay(HAR)
    ev: dict = {}
    r = asyncio.run(AF.abrir_atendimento_api(page, params, ev))
    assert r is not None, (ev.get("api_first") or {}).get("motivo")
    sem_rt = {k: v for k, v in params.items() if k != "_runtime"}
    return sem_rt, _evidencia_do_worker(r, ev), page.cursor


# ── o banco: portal_jobs (síncrono, como a tool) + cerebro_modos/diário (assíncrono) ─────
class _Resp:
    def __init__(self, data):
        self.data = data


def _campo(linha, chave):
    if chave.startswith("params->>"):
        return str((linha.get("params") or {}).get(chave.split(">>", 1)[1]) or "")
    return linha.get(chave)


class _Q:
    def __init__(self, banco, tabela, assincrono=False):
        self.banco, self.tabela, self.assincrono = banco, tabela, assincrono
        self.f, self.op, self.linha = {}, "select", {}

    def select(self, *_a, **_k):
        return self

    def insert(self, linha):
        self.op, self.linha = "insert", copy.deepcopy(dict(linha))
        return self

    def update(self, patch):
        self.op, self.linha = "update", copy.deepcopy(dict(patch))
        return self

    def eq(self, c, v):
        self.f[c] = v
        return self

    def in_(self, c, v):
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a):
        return self

    def execute(self):
        r = self.banco.executar(self)
        if self.assincrono:
            async def _a():
                return r
            return _a()
        return r


class Banco:
    def __init__(self, *, cursor: int, modos=None):
        self.jobs: list = []
        self.diario: list = []
        self.modos = list(modos or [])
        self.cursor = cursor
        self.continuacoes_rodadas = 0
        self.paginas: list = []

    # o cliente síncrono da tool e o assíncrono do diário/modo
    @property
    def client(self):
        return self

    def table(self, nome):
        return _Q(self, nome)

    def executar(self, q):
        f = q.f
        if q.tabela == "cerebro_modos":
            return _Resp([dict(m) for m in self.modos if m["company_id"] == f.get("company_id")])
        if q.tabela == "diario_de_decisoes":
            if q.op == "insert":
                linha = {**q.linha, "id": f"diario-{len(self.diario) + 1}"}
                self.diario.append(linha)
                return _Resp([{"id": linha["id"]}])
            return _Resp([{"id": d["id"]} for d in self.diario
                          if all(d.get(k) == v for k, v in f.items())])
        if q.tabela != "portal_jobs":
            return _Resp([])
        if q.op == "insert":
            linha = {**q.linha, "id": f"job-{len(self.jobs) + 1}",
                     "created_at": f"2026-10-01T10:00:{len(self.jobs):02d}Z"}
            self.jobs.append(linha)
            return _Resp([{"id": linha["id"]}])
        if q.op == "update":
            for j in self.jobs:
                if all(_campo(j, k) == v for k, v in f.items()):
                    j.update(q.linha)
            return _Resp([])
        achados = [j for j in self.jobs if all(_campo(j, k) == v for k, v in f.items())]
        if "id" in f:
            for j in achados:
                if j.get("journey") == "continuar_atendimento" and j.get("status") == "queued":
                    self._worker(j)
        return _Resp([copy.deepcopy(j) for j in achados])

    def _worker(self, job):
        """O worker, dublado só na fila: roda o MOTOR REAL da continuação sobre o HAR."""
        params = copy.deepcopy(job["params"])
        params["_runtime"] = RT(False)
        page = RV.PaginaDeReplay(HAR, cursor=self.cursor)
        ev: dict = {}
        # o worker é OUTRO processo: aqui, outra thread com o seu próprio laço (a tool está dentro do dela)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            r = ex.submit(asyncio.run, VC.continuar_atendimento(page, params, ev)).result()
        self.continuacoes_rodadas += 1
        self.paginas.append(page)
        job.update({"status": r.status, "evidence": _evidencia_do_worker(r, ev)})


class BancoAssincrono:
    def __init__(self, banco):
        self.banco = banco

    @property
    def client(self):
        return self

    def table(self, nome):
        return _Q(self.banco, nome, assincrono=True)


class Portal(PT.PortalActionTool):
    async def _fechar_work_run(self, run_id, job):  # noqa: D102 — borda (work_runs)
        return None


@pytest.fixture
def mundo(monkeypatch):
    import app.core.database as DB
    import app.services.tela_cega as TC

    estado = {"banco": None, "modelo": [], "resposta": "", "notificacoes": []}

    async def _assinc():
        return BancoAssincrono(estado["banco"])

    async def _nada(**_k):
        return True

    async def _modelo(papel, mensagens, **_k):
        estado["modelo"].append({"papel": papel, "mensagens": mensagens})
        return AIMessage(content=estado["resposta"],
                         response_metadata={"model_provider": "openai", "model_name": "gpt-6.1-sol"})

    monkeypatch.setattr(DB, "create_async_supabase_client", _assinc)
    monkeypatch.setattr(DB, "get_supabase_client", lambda: estado["banco"])
    monkeypatch.setattr(TC, "registrar_tela_cega", _nada)
    monkeypatch.setattr(LF, "invocar_com_reserva", _modelo)
    monkeypatch.setattr(PT, "POLL_EVERY_S", 0)
    monkeypatch.setattr(PT, "POLL_TIMEOUT_S", 30)    # o "worker" responde no 1º poll; um defeito não prende 150 s
    monkeypatch.setattr(Portal, "_notify", lambda self, *a, **k: estado["notificacoes"].append(a))
    AC._CACHE_DA_CHAVE.clear()
    yield estado
    AC._CACHE_DA_CHAVE.clear()


def _modo(company_id, modo="on", insurer_key="yelum", ramo="todos"):
    return {"company_id": company_id, "insurer_key": insurer_key, "ramo": ramo, "modo": modo, "limiar": 70}


def _montar(estado, *, uf_ilegivel=True, modos=(), empresa=EMPRESA_A):
    params, ev, cursor = parada_real(uf_ilegivel=uf_ilegivel)
    params["_idempotency_key"] = PP.chave_de_idempotencia(params, empresa)
    params["_conversation_id"] = "whatsapp:5500000000000:co:ag"
    banco = Banco(cursor=cursor, modos=modos)
    banco.jobs.append({"id": "job-abertura", "company_id": empresa, "portal_key": "vidros_lanternas",
                       "journey": "abrir_atendimento", "params": params, "status": "needs_human",
                       "evidence": ev, "idempotency_key": params["_idempotency_key"],
                       "session_id": params["_conversation_id"], "agent_id": None, "work_run_id": RUN,
                       "created_at": "2026-10-01T09:00:00Z"})
    estado["banco"] = banco
    return banco, params, ev


def _aguardar(empresa, banco, params):
    return asyncio.run(Portal(company_id=empresa, supabase_client=banco)._aguardar("job-abertura", RUN, params))


def _resposta(valor, classe="responder_com_dado", nota=95, acao="RESPONDER"):
    return json.dumps({"classe": classe, "acao": acao, "valor": valor, "nota": nota,
                       "motivo": "o estado do cadastro do segurado"})


# ═════════════════════════════════════════════════════════════════════════════
def test_a_parada_e_real_e_do_tipo_que_o_destravador_responde():
    _params, ev, _c = parada_real(uf_ilegivel=True)
    assert ev["stage"] == "uf_desconhecida"
    assert PP.acao_esperada(ev) == ("responder", "cidade_servico")
    assert PP.continuacao_possivel(ev) is True
    assert UF_CERTA in ev["opcoes"] and len(ev["opcoes"]) == 27


def test_o_FIO_uf_destrava_continua_o_mesmo_pedido_e_o_reparo_volta_ao_segurado(mundo):
    banco, params, ev = _montar(mundo, modos=[_modo(EMPRESA_A)])
    mundo["resposta"] = _resposta(UF_CERTA)
    saida = _aguardar(EMPRESA_A, banco, params)

    # ① o modelo do papel `destravador` foi chamado UMA vez (a UF); o reparo é decidido pelo CÓDIGO
    assert [c["papel"] for c in mundo["modelo"]] == ["destravador"]
    prompt = "\n".join(str(m.content) for m in mundo["modelo"][0]["mensagens"])
    assert "O portal de vidros parou o pedido" in prompt and f"- {UF_CERTA}" in prompt
    assert str(params["cpf_cnpj"]) not in prompt and str(params["placa"]) not in prompt   # sem PII ao modelo

    # ② UM job de continuação, do MESMO pedido, com a resposta no contrato da 001.10.1
    cont = [j for j in banco.jobs if j["journey"] == "continuar_atendimento"]
    assert len(cont) == 1 and len([j for j in banco.jobs if j["journey"] == "abrir_atendimento"]) == 1
    c = cont[0]
    assert c["params"]["_continuacao"]["operacao"] == "responder"
    assert c["params"]["_continuacao"]["respostas"] == {
        "cidade_servico": {"uf": UF_CERTA, "cidade": _CIDADE["cidade"]}}
    assert c["params"]["_pedido_key"] == params["_idempotency_key"]
    assert c["params"]["_destravador"]["parada"] == "uf_desconhecida"
    assert str(c["idempotency_key"]).startswith("cont:")
    assert c["params"]["confirm"] is False            # o gate de hoje (`envio_liberado`) não mudou
    assert c["work_run_id"] == RUN

    # ③ o MOTOR real continuou: passou a cidade e parou no reparo — sem 2º POST /atendimentos
    assert banco.continuacoes_rodadas == 1
    escritas = banco.paginas[0].escritas()
    assert ("POST", "/atendimentos") not in [(m, p.split("?")[0]) for m, p in escritas]
    assert any(p.startswith("/cidades") for _m, p in banco.paginas[0].emitidas())
    assert c["status"] == "needs_human" and c["evidence"]["stage"] == "decidir_reparo"

    # ④ o diário: duas decisões, por corretora, em português de gente
    assert [d["acao"] for d in banco.diario] == ["respondeu_portal", "perguntou_segurado"]
    uf, reparo = banco.diario
    assert uf["company_id"] == EMPRESA_A and uf["origem"] == "portal" and uf["ramo"] == "vidros"
    assert uf["seguradora"] == "yelum" and uf["classe"] == "responder_com_dado" and uf["modo"] == "on"
    assert uf["explicacao_para_gente"].startswith("No portal da loja de vidros")
    assert "estado (UF)" in uf["explicacao_para_gente"] and uf["work_run_id"] == RUN
    assert reparo["classe"] == "nunca_sozinho" and "aceite_de_custo" in reparo["motivo"]
    assert "reparar ou trocar" in reparo["explicacao_para_gente"]

    # ⑤ a resposta ao agente é a de HOJE para a parada do reparo (ele pergunta ao segurado)
    assert saida == {"content": PP.format_result(c)}
    assert "aceita_reparo" in saida["content"]
    assert mundo["notificacoes"] == []                # nenhuma mensagem saiu daqui


def test_CONTROLE_off_e_hoje_byte_a_byte(mundo):
    """Sem linha em `cerebro_modos`: o MESMO `format_result` de antes, nada no diário, nenhum modelo."""
    banco, params, ev = _montar(mundo, modos=[])
    mundo["resposta"] = _resposta(UF_CERTA)
    antes = copy.deepcopy(banco.jobs[0])
    saida = _aguardar(EMPRESA_A, banco, params)
    assert saida == {"content": PP.format_result({**antes, "evidence": {**ev, "entregue_ao_agente": True}})}
    assert mundo["modelo"] == [] and banco.diario == []
    assert [j["journey"] for j in banco.jobs] == ["abrir_atendimento"]


def test_CONTROLE_modo_off_explicito_tambem_e_hoje(mundo):
    banco, params, _ev = _montar(mundo, modos=[_modo(EMPRESA_A, modo="off")])
    mundo["resposta"] = _resposta(UF_CERTA)
    _aguardar(EMPRESA_A, banco, params)
    assert mundo["modelo"] == [] and banco.diario == [] and len(banco.jobs) == 1


def test_NUNCA_decidir_reparo_pergunta_ao_segurado_e_nada_vai_ao_portal(mundo):
    """D2: reparo × troca muda a franquia. O modelo nem é chamado — e se fosse, o mais agressivo possível."""
    banco, params, ev = _montar(mundo, uf_ilegivel=False, modos=[_modo(EMPRESA_A)])
    assert ev["stage"] == "decidir_reparo"
    mundo["resposta"] = _resposta("tentar o reparo", classe="conduzir", nota=99)
    saida = _aguardar(EMPRESA_A, banco, params)
    assert mundo["modelo"] == []
    assert [j["journey"] for j in banco.jobs] == ["abrir_atendimento"]
    assert [(d["acao"], d["classe"]) for d in banco.diario] == [("perguntou_segurado", "nunca_sozinho")]
    assert saida["content"] == PP.format_result(banco.jobs[0])


def test_sombra_decide_registra_e_nao_age(mundo, monkeypatch):
    banco, params, _ev = _montar(mundo, modos=[_modo(EMPRESA_A, modo="sombra")])
    mundo["resposta"] = _resposta(UF_CERTA)

    async def _isolado(resolvido, mensagens, company_id, service_type):
        # a sombra chama o primário ISOLADO (sem reserva, sem o relógio de produção): a borda é aqui
        mundo["modelo"].append({"papel": service_type, "mensagens": mensagens})
        return AIMessage(content=mundo["resposta"],
                         response_metadata={"model_provider": "openai", "model_name": "gpt-6.1-sol"})

    monkeypatch.setattr(DT, "_chamar_isolado", _isolado)
    saida = _aguardar(EMPRESA_A, banco, params)
    assert len(mundo["modelo"]) == 1
    assert [j["journey"] for j in banco.jobs] == ["abrir_atendimento"]
    assert [(d["acao"], d["modo"]) for d in banco.diario] == [("nao_agiu", "sombra")]
    assert "Em sombra" in banco.diario[0]["explicacao_para_gente"]
    assert saida["content"] == PP.format_result(banco.jobs[0])


def test_o_valor_que_nao_e_dado_do_caso_vira_pergunta(mundo):
    """Uma UF da lista que NÃO está no caso é DEDUZIR — desligado sem calibração: pergunta, nada ao portal."""
    banco, params, _ev = _montar(mundo, modos=[_modo(EMPRESA_A)])
    outra = next(u for u in ("AC", "AP", "RR", "TO") if u != UF_CERTA)
    mundo["resposta"] = _resposta(outra)
    _aguardar(EMPRESA_A, banco, params)
    assert [j["journey"] for j in banco.jobs] == ["abrir_atendimento"]
    assert banco.diario[0]["acao"] == "perguntou_segurado" and "deduzir_sem_calibracao" in banco.diario[0]["motivo"]


def test_o_teto_por_pedido_devolve_o_caminho_de_hoje(mundo):
    banco, params, _ev = _montar(mundo, modos=[_modo(EMPRESA_A)])
    for i in range(DT.TETO_DE_DESTRAVAMENTOS_POR_PEDIDO):
        banco.jobs.append({"id": f"job-velho-{i}", "company_id": EMPRESA_A, "journey": "continuar_atendimento",
                           "status": "failed", "params": {"_pedido_key": params["_idempotency_key"],
                                                          "_destravador": {"parada": "x"}}})
    mundo["resposta"] = _resposta(UF_CERTA)
    _aguardar(EMPRESA_A, banco, params)
    assert mundo["modelo"] == [] and banco.diario == []
    assert len([j for j in banco.jobs if j["journey"] == "continuar_atendimento"]) == DT.TETO_DE_DESTRAVAMENTOS_POR_PEDIDO


def test_duas_corretoras_o_modo_de_uma_nao_liga_a_outra(mundo):
    """A corretora A ligou; a B não. O MESMO pedido na B segue o caminho de hoje."""
    banco, params, _ev = _montar(mundo, modos=[_modo(EMPRESA_A)], empresa=EMPRESA_B)
    mundo["resposta"] = _resposta(UF_CERTA)
    _aguardar(EMPRESA_B, banco, params)
    assert mundo["modelo"] == [] and banco.diario == [] and len(banco.jobs) == 1
