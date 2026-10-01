# -*- coding: utf-8 -*-
"""SPEC-124 F1 — 🔴 O TESTE DO FIO: o portal de vidros passa pela MESMA política do WhatsApp.

🔴 A VERDADE DE HOJE (conserto SPEC-124, juiz B1 = red team B1): com o DEDUZIR desligado (sem
calibração), o destravador do portal NÃO RESPONDE NENHUMA PARADA SOZINHO. O que a F1 entrega hoje é a
fiação, a política única (o NÚCLEO do WhatsApp), o NUNCA e o diário — toda parada termina no caminho de
hoje (o agente pergunta ao segurado) com uma linha no diário dizendo isso. A única ação sozinha que
existia (a UF do serviço trocada pela "do caso") era uma DEDUÇÃO disfarçada e errava por construção.

O FIO (motor real; dublê SÓ na borda — o HAR do portal, o banco, o cliente do modelo):

  o segurado ESCREVE "<cidade>/<UF>" → `portal_params.cidade_do_servico_valida` (o produto só abre o
    pedido com a UF escrita e válida) → `local.cidade_servico` + `cidade_servico_uf_de = segurado`
  → HAR REAL (Yelum, para-brisa — `docs/intake/`, fora do Git) com UMA mudança na borda: o `GET /ufs`
    do portal não lista a UF dele (a única forma real de nascer `uf_desconhecida`)
  → `vidros_apifirst.abrir_atendimento_api` (o MOTOR) → `needs_human` `uf_desconhecida`,
    `acao_esperada = responder:cidade_servico`, as 26 UFs do portal em `opcoes`
  → `worker._augment_hitl_evidence` (o worker real) → a linha do `portal_jobs`
  → `PortalActionTool._aguardar` (a tool real) → modo `on` em `cerebro_modos`
  → `destravador.destravar_parada_do_portal` → `decidir_parada_do_portal`: a TABELA diz "só o segurado
    sabe" — o modelo NEM É CHAMADO (nem a UF do cadastro, nem com nota 100)
  → `diario_de_decisoes.registrar_decisao` (real; o banco é dublê) — `perguntou_segurado`
  → NADA vai ao portal (nenhum job de continuação) → `format_result` (o caminho de hoje).

E a FIAÇÃO de agir (para quando a calibração religar o DEDUZIR — aqui ligada por `monkeypatch`, nunca
no produto): o questionário sem uma resposta (o HAR real sem `pergunta_140`) → `questionario_incompleto`
com o slot ETIQUETADO `responder:pergunta_140` → o modelo + a 2ª opinião de OUTRO provedor → UM job de
continuação do MESMO pedido → o motor real continua e para no reparo → NUNCA → pergunta.

⛔ Nenhuma mensagem sai (`_notify` dublado), nenhum portal real, nenhum banco real, nenhum modelo real.
⛔ Nenhum valor pessoal do HAR é impresso nem afirmado em texto.
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


#: a UF do CADASTRO do segurado — outra, e presente na lista do portal: é a que a política antiga
#: mandava ao portal no lugar da que ele escreveu (juiz B1).
UF_DO_CADASTRO = next(u for u in ("SC", "PR", "RS", "SP") if u != UF_CERTA)
#: a pergunta do questionário que o HAR real respondeu e que, sem ela, para o pedido (📊 sondado:
#: tirar `pergunta_5` ou `pergunta_8` não para — o motor as tira do relato; `pergunta_140` para).
PERGUNTA_QUE_FALTA = "pergunta_140"


def portal_sem_a_uf(uf: str) -> list:
    """O DUBLÊ DA BORDA: o MESMO HAR, com o `GET /ufs` do portal sem a UF `uf` (📊 os 7 HAR reais
    trazem as 27; um portal que não atende o estado dele é a única forma real da parada nascer)."""
    import dataclasses

    saida = []
    for c in HAR:
        if c.metodo.upper() == "GET" and RV.caminho_de(c).split("?")[0] == "/ufs" and c.corpo_resp:
            lista = [u for u in json.loads(c.corpo_resp) if str(u.get("UF") or "").upper() != uf]
            c = dataclasses.replace(c, corpo_resp=json.dumps(lista))
        saida.append(c)
    return saida


def entrada_do_segurado():
    """O que o PRODUTO gera quando o segurado escreve "<cidade>/<UF>" (o mesmo validador que decide se o
    pedido pode nascer em `build_portal_params`). ⛔ Nunca uma UF inválida: o produto a recusa antes."""
    cidade, uf, erro = PP.cidade_do_servico_valida(f"{_CIDADE['cidade']}/{UF_CERTA}")
    assert erro == "" and uf == UF_CERTA
    assert PP.cidade_do_servico_valida(f"{_CIDADE['cidade']}/ZZ")[2] == "uf_ausente"   # a entrada velha
    return {"local": {"cidade_servico": {"uf": uf, "cidade": cidade}, "cidade_servico_uf_de": "segurado",
                      "estado": UF_DO_CADASTRO}}


def parada_real(*, uf_fora_do_portal: bool = False, sem_pergunta: bool = False):
    """(params_do_job, evidence_do_job, cursor). Sem flag: o HAR inteiro para em `decidir_reparo`.
    `uf_fora_do_portal`: a UF que o segurado ESCREVEU não está na lista do portal → `uf_desconhecida`.
    `sem_pergunta`: o segurado não respondeu uma pergunta do questionário → `questionario_incompleto`."""
    har = portal_sem_a_uf(UF_CERTA) if uf_fora_do_portal else HAR
    params = RV.params_do_har(HAR, extra=entrada_do_segurado())
    if sem_pergunta:
        params["especificos"] = {k: v for k, v in params["especificos"].items() if k != PERGUNTA_QUE_FALTA}
    params["_runtime"] = RT(True)
    page = RV.PaginaDeReplay(har)
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


def _montar(estado, *, modos=(), empresa=EMPRESA_A, **parada):
    params, ev, cursor = parada_real(**(parada or {"uf_fora_do_portal": True}))
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
def test_a_parada_nasce_de_uma_entrada_que_o_PRODUTO_gera():
    """A UF que o segurado escreveu (válida, uma das 27) e um portal que não a lista: `uf_desconhecida`."""
    _params, ev, _c = parada_real(uf_fora_do_portal=True)
    assert ev["stage"] == "uf_desconhecida"
    assert PP.acao_esperada(ev) == ("responder", "cidade_servico")
    assert PP.continuacao_possivel(ev) is True
    assert UF_CERTA not in ev["opcoes"] and UF_DO_CADASTRO in ev["opcoes"] and len(ev["opcoes"]) == 26
    # CONTROLE: a MESMA entrada no portal medido (27 UFs) não para na UF — passa e para no reparo
    _p, ev27, _c = parada_real()
    assert ev27["stage"] == "decidir_reparo"


def test_o_FIO_a_uf_que_o_segurado_escreveu_fora_da_lista_volta_para_ele(mundo):
    banco, params, ev = _montar(mundo, modos=[_modo(EMPRESA_A)])
    mundo["resposta"] = _resposta(UF_DO_CADASTRO, nota=100)        # o modelo mais agressivo possível

    saida = _aguardar(EMPRESA_A, banco, params)

    # ① o CÓDIGO decidiu: a UF é do segurado — o modelo nem foi chamado
    assert mundo["modelo"] == []
    # ② NADA vai ao portal: nenhum job de continuação, nenhuma página do worker
    assert [j["journey"] for j in banco.jobs] == ["abrir_atendimento"]
    assert banco.continuacoes_rodadas == 0
    # ③ o diário diz o que aconteceu: o agente pergunta ao segurado
    assert [(d["acao"], d["classe"]) for d in banco.diario] == [("perguntou_segurado", "perguntar_ao_segurado")]
    linha = banco.diario[0]
    assert linha["company_id"] == EMPRESA_A and linha["origem"] == "portal" and linha["ramo"] == "vidros"
    assert linha["seguradora"] == "yelum" and linha["modo"] == "on" and linha["work_run_id"] == RUN
    assert "so_o_segurado_sabe" in linha["motivo"]
    assert linha["explicacao_para_gente"].startswith("No portal da loja de vidros")
    assert "estado (UF)" in linha["explicacao_para_gente"]
    assert "deixou a pergunta para o segurado" in linha["explicacao_para_gente"]
    assert "respondeu ao portal" not in linha["explicacao_para_gente"]
    # ④ a resposta ao agente é a de HOJE (ele pergunta ao segurado)
    assert saida == {"content": PP.format_result(banco.jobs[0])}
    assert mundo["notificacoes"] == []


def test_CONTROLE_off_e_hoje_byte_a_byte(mundo):
    """Sem linha em `cerebro_modos`: o MESMO `format_result` de antes, nada no diário, nenhum modelo."""
    banco, params, ev = _montar(mundo, modos=[])
    mundo["resposta"] = _resposta(UF_DO_CADASTRO)
    antes = copy.deepcopy(banco.jobs[0])
    saida = _aguardar(EMPRESA_A, banco, params)
    assert saida == {"content": PP.format_result({**antes, "evidence": {**ev, "entregue_ao_agente": True}})}
    assert mundo["modelo"] == [] and banco.diario == []
    assert [j["journey"] for j in banco.jobs] == ["abrir_atendimento"]


def test_CONTROLE_modo_off_explicito_tambem_e_hoje(mundo):
    banco, params, _ev = _montar(mundo, modos=[_modo(EMPRESA_A, modo="off")])
    mundo["resposta"] = _resposta(UF_DO_CADASTRO)
    _aguardar(EMPRESA_A, banco, params)
    assert mundo["modelo"] == [] and banco.diario == [] and len(banco.jobs) == 1


def test_NUNCA_decidir_reparo_pergunta_ao_segurado_e_nada_vai_ao_portal(mundo):
    """D2: reparo × troca muda a franquia. O modelo nem é chamado — e se fosse, o mais agressivo possível."""
    banco, params, ev = _montar(mundo, modos=[_modo(EMPRESA_A)], uf_fora_do_portal=False)
    assert ev["stage"] == "decidir_reparo"
    mundo["resposta"] = _resposta("tentar o reparo", classe="conduzir", nota=99)
    saida = _aguardar(EMPRESA_A, banco, params)
    assert mundo["modelo"] == []
    assert [j["journey"] for j in banco.jobs] == ["abrir_atendimento"]
    assert [(d["acao"], d["classe"]) for d in banco.diario] == [("perguntou_segurado", "nunca_sozinho")]
    assert saida["content"] == PP.format_result(banco.jobs[0])


def test_sombra_decide_registra_e_nao_age(mundo, monkeypatch):
    banco, params, _ev = _montar(mundo, modos=[_modo(EMPRESA_A, modo="sombra")])
    mundo["resposta"] = _resposta(UF_DO_CADASTRO)

    async def _isolado(resolvido, mensagens, company_id, service_type):
        # a sombra chama o primário ISOLADO: a borda é aqui (um dublê que conta, nunca um modelo real)
        mundo["modelo"].append({"papel": service_type, "mensagens": mensagens})
        return AIMessage(content=mundo["resposta"],
                         response_metadata={"model_provider": "openai", "model_name": "gpt-6.1-sol"})

    monkeypatch.setattr(DT, "_chamar_isolado", _isolado)
    saida = _aguardar(EMPRESA_A, banco, params)
    assert mundo["modelo"] == []                     # a tabela decide também em sombra
    assert [j["journey"] for j in banco.jobs] == ["abrir_atendimento"]
    assert [(d["acao"], d["modo"]) for d in banco.diario] == [("nao_agiu", "sombra")]
    assert "Em sombra" in banco.diario[0]["explicacao_para_gente"]
    assert saida["content"] == PP.format_result(banco.jobs[0])


def test_hoje_o_DEDUZIR_desligado_o_questionario_tambem_volta_ao_segurado(mundo):
    """A outra parada que o segurado responde e o produto gera: sem calibração, nada vai ao portal."""
    banco, params, ev = _montar(mundo, modos=[_modo(EMPRESA_A)], sem_pergunta=True)
    assert ev["stage"] == "questionario_incompleto"
    assert PP.acao_esperada(ev) == ("responder", PERGUNTA_QUE_FALTA)       # o slot ETIQUETADO do worker
    mundo["resposta"] = _resposta(ev["opcoes"][0], classe="deduzir", nota=100)
    _aguardar(EMPRESA_A, banco, params)
    assert mundo["modelo"] == [] and [j["journey"] for j in banco.jobs] == ["abrir_atendimento"]
    assert [(d["acao"], d["classe"]) for d in banco.diario] == [("perguntou_segurado", "deduzir")]
    assert "deduzir_sem_calibracao" in banco.diario[0]["motivo"]


def test_a_FIACAO_de_agir_quando_a_calibracao_religar(mundo, monkeypatch):
    """⚠️ `DEDUZIR_AUTONOMO_CALIBRADO` ligado AQUI por monkeypatch (no produto: desligado). Prova que,
    no dia em que a calibração religar, a resposta vai no slot ETIQUETADO (`pergunta_<codigo>`, conserto
    red team P8) e continua o MESMO pedido pelo mecanismo da 001.10.1 até o desfecho, com UMA linha no diário."""
    monkeypatch.setattr(DT, "DEDUZIR_AUTONOMO_CALIBRADO", True)
    certa = " ".join(str(_BASE["especificos"][PERGUNTA_QUE_FALTA]).split()).lower()
    banco, params, ev = _montar(mundo, modos=[_modo(EMPRESA_A)], sem_pergunta=True)
    opcao = next(o for o in ev["opcoes"] if " ".join(o.split()).lower() == certa)
    mundo["resposta"] = _resposta(opcao, classe="deduzir", nota=95)

    class _Segunda:                                   # a borda: o cliente do OUTRO provedor
        async def ainvoke(self, mensagens):
            mundo["modelo"].append({"papel": "destravador_segunda", "mensagens": mensagens})
            return AIMessage(content=_resposta(opcao, classe="deduzir", nota=90),
                             response_metadata={"model_provider": "anthropic",
                                                "model_name": "claude-sonnet-5-5"})

    monkeypatch.setattr(LF.LLMFactory, "create_llm", staticmethod(lambda *a, **k: _Segunda()))
    saida = _aguardar(EMPRESA_A, banco, params)

    assert [c["papel"] for c in mundo["modelo"]] == ["destravador", "destravador_segunda"]
    prompt = "\n".join(str(m.content) for m in mundo["modelo"][0]["mensagens"])
    assert str(params["cpf_cnpj"]) not in prompt and str(params["placa"]) not in prompt   # sem PII ao modelo
    cont = [j for j in banco.jobs if j["journey"] == "continuar_atendimento"]
    assert len(cont) == 1 and len([j for j in banco.jobs if j["journey"] == "abrir_atendimento"]) == 1
    c = cont[0]
    assert c["params"]["_continuacao"]["respostas"] == {PERGUNTA_QUE_FALTA: opcao}
    assert c["params"]["_pedido_key"] == params["_idempotency_key"]
    assert c["params"]["_destravador"]["parada"] == "questionario_incompleto"
    assert str(c["idempotency_key"]).startswith("cont:")
    assert c["params"]["confirm"] is False            # o gate de hoje (`envio_liberado`) não mudou
    assert banco.continuacoes_rodadas == 1
    escritas = banco.paginas[0].escritas()
    assert ("POST", "/atendimentos") not in [(m, p.split("?")[0]) for m, p in escritas]
    # o MOTOR real continuou a partir do questionário: o pedido andou até o desfecho (o reparo foi
    # decidido pelo próprio questionário neste HAR) — e o resultado é o de HOJE (`format_result`)
    assert c["status"] == "done" and isinstance(c["evidence"].get("desfecho"), dict)
    assert c["evidence"].get("continuacao_pedida") is not None
    assert [d["acao"] for d in banco.diario] == ["respondeu_portal"]
    assert banco.diario[0]["classe"] == "deduzir"
    assert "respondeu ao portal" in banco.diario[0]["explicacao_para_gente"]
    assert saida == {"content": PP.format_result(c)}
    assert mundo["notificacoes"] == []


def test_o_teto_por_pedido_devolve_o_caminho_de_hoje(mundo):
    banco, params, _ev = _montar(mundo, modos=[_modo(EMPRESA_A)])
    for i in range(DT.TETO_DE_DESTRAVAMENTOS_POR_PEDIDO):
        banco.jobs.append({"id": f"job-velho-{i}", "company_id": EMPRESA_A, "journey": "continuar_atendimento",
                           "status": "failed", "params": {"_pedido_key": params["_idempotency_key"],
                                                          "_destravador": {"parada": "x"}}})
    mundo["resposta"] = _resposta(UF_DO_CADASTRO)
    _aguardar(EMPRESA_A, banco, params)
    assert mundo["modelo"] == [] and banco.diario == []
    assert len([j for j in banco.jobs if j["journey"] == "continuar_atendimento"]) == DT.TETO_DE_DESTRAVAMENTOS_POR_PEDIDO


def test_duas_corretoras_o_modo_de_uma_nao_liga_a_outra(mundo):
    """A corretora A ligou; a B não. O MESMO pedido na B segue o caminho de hoje."""
    banco, params, _ev = _montar(mundo, modos=[_modo(EMPRESA_A)], empresa=EMPRESA_B)
    mundo["resposta"] = _resposta(UF_DO_CADASTRO)
    _aguardar(EMPRESA_B, banco, params)
    assert mundo["modelo"] == [] and banco.diario == [] and len(banco.jobs) == 1
