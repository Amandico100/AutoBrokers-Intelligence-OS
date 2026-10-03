# -*- coding: utf-8 -*-
"""SPEC-127 P4 + P8 — 🔴 O FIO: cada TIPO de parada do P4 resolvida SEM PESSOA, pelo motor real, no replay.

  HAR REAL (`docs/intake/`, fora do Git) com UMA mudança na BORDA quando a parada precisa dela
  → `vidros_apifirst.abrir_atendimento_api` (o MOTOR) → a parada, com a TELA (P8) na evidence
  → `worker._augment_hitl_evidence` → `portal_jobs` (dublê) → `PortalActionTool._aguardar` (a tool real)
  → `destravador.destravar_parada_do_portal` → a CLASSE pela TABELA → o VALOR pelo CÓDIGO (o modelo NEM é
    chamado) → `montar_job_de_continuacao` → `vidros_continuacao.continuar_atendimento` (o motor real,
    outra página do MESMO HAR) → o MESMO pedido: **1** `POST /atendimentos` no total.

  tipo                                 parada                            quem resolve
  ───────────────────────────────────  ────────────────────────────────  ─────────────────────────────────
  CONDUZIR                             tipo_de_telefone_desconhecido     o código (a opção do CONTRATO)
  RESPONDER COM DADO (outra chave)     peca_ambigua                      o código (`especificos` desambigua)
  PERGUNTAR (P1, antes da fronteira)   faltou_peca                       o segurado → o MESMO pedido recomeça
  DEDUZIR calibrado (a fiação do P5)   questionario_incompleto           modelo + 2ª opinião de OUTRO provedor

⛔ Nenhum portal real, nenhum banco real, nenhum modelo real, nenhuma mensagem. Nenhum valor pessoal do HAR é
impresso nem afirmado em texto. 💭 Corretoras fictícias (ids gerados).
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import copy
import dataclasses
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import _replay_vidros as RV  # noqa: E402

try:
    _NOVO = RV.carregar("NOVO")
    _LATERAL = RV.carregar("LATERAL")
except RV.HarAusente as _e:  # pragma: no cover — sem o acervo local
    pytest.skip(f"sem os HAR do portal (fora do Git): {_e}", allow_module_level=True)

from langchain_core.messages import AIMessage  # noqa: E402

from app.agents.tools import portal_params as PP  # noqa: E402
from app.factories import llm_factory as LF  # noqa: E402
from app.services import destravador as DT  # noqa: E402
from portal_worker.journeys import vidros_apifirst as AF  # noqa: E402
from portal_worker.journeys import vidros_continuacao as VC  # noqa: E402
from test_spec124_portal_destrava_o_fio import (  # noqa: E402,F401 — o MESMO dublê de borda da SPEC-124
    EMPRESA_A, EMPRESA_B, RT, RUN, Banco, Portal, _evidencia_do_worker, _modo, _resposta, mundo)


def _troca(har, caminho, f):
    """O DUBLÊ DA BORDA: o MESMO HAR com UMA resposta do portal trocada."""
    saida = []
    for c in har:
        if c.metodo.upper() == "GET" and RV.caminho_de(c).split("?")[0] == caminho and c.corpo_resp:
            c = dataclasses.replace(c, corpo_resp=json.dumps(f(json.loads(c.corpo_resp))))
        saida.append(c)
    return saida


#: o portal RENOMEOU o tipo do contrato (💭 a forma de nascer a parada: o nome exato sumiu da lista)
_NOVO_TEL = _troca(_NOVO, "/tipos-telefone",
                   lambda l: [{**t, "Descricao": "CELULAR DO SEGURADO"} if t.get("Codigo") == 20 else t for t in l])


class BancoDoHar(Banco):
    """O banco dublê da SPEC-124, com o worker da continuação rodando sobre ESTE har (não o global)."""

    def __init__(self, har, **k):
        super().__init__(**k)
        self.har = har

    def _worker(self, job):
        params = copy.deepcopy(job["params"])
        params["_runtime"] = RT(False)
        page = RV.PaginaDeReplay(self.har, cursor=self.cursor)
        ev: dict = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            r = ex.submit(asyncio.run, VC.continuar_atendimento(page, params, ev)).result()
        self.continuacoes_rodadas += 1
        self.paginas.append(page)
        job.update({"status": r.status, "evidence": _evidencia_do_worker(r, ev)})


def _abrir(har, params):
    p = dict(params)
    p["_runtime"] = RT(True)
    page = RV.PaginaDeReplay(har)
    ev: dict = {}
    r = asyncio.run(AF.abrir_atendimento_api(page, p, ev))
    assert r is not None, (ev.get("api_first") or {}).get("motivo")
    return {k: v for k, v in p.items() if k != "_runtime"}, _evidencia_do_worker(r, ev), page


def _montar(estado, har, params, *, modos=(), empresa=EMPRESA_A):
    params, ev, page = _abrir(har, params)
    params["_idempotency_key"] = PP.chave_de_idempotencia(params, empresa)
    params["_conversation_id"] = "whatsapp:5500000000000:co:ag"
    banco = BancoDoHar(har, cursor=page.cursor, modos=modos)
    banco.jobs.append({"id": "job-abertura", "company_id": empresa, "portal_key": "vidros_lanternas",
                       "journey": "abrir_atendimento", "params": params, "status": "needs_human",
                       "evidence": ev, "idempotency_key": params["_idempotency_key"],
                       "session_id": params["_conversation_id"], "agent_id": None, "work_run_id": RUN,
                       "created_at": "2026-10-01T09:00:00Z"})
    estado["banco"] = banco
    return banco, params, ev, page


def _aguardar(empresa, banco, params):
    return asyncio.run(Portal(company_id=empresa, supabase_client=banco)._aguardar("job-abertura", RUN, params))


def _posts_de_abertura(*paginas) -> int:
    return sum(1 for pg in paginas for m, c in pg.escritas() if (m, c.split("?")[0]) == ("POST", "/atendimentos"))


# ═════════════════════════════════════════════════════════════════════════════
# CONDUZIR — o tipo de telefone
# ═════════════════════════════════════════════════════════════════════════════
def test_CONDUZIR_o_tipo_de_telefone_continua_o_MESMO_pedido_com_1_POST_sem_pessoa(mundo):
    banco, params, ev, origem = _montar(mundo, _NOVO_TEL, RV.params_do_har(_NOVO), modos=[_modo(EMPRESA_A)])
    assert ev["stage"] == "tipo_de_telefone_desconhecido"
    assert PP.acao_esperada(ev) == ("responder", "tipo_telefone") and PP.continuacao_possivel(ev)
    assert ev["tela_da_parada"]["campo"] == "Tipo de telefone"                     # P8: a TELA viaja
    assert "CELULAR DO SEGURADO" in ev["opcoes"] and ev["tipo_telefone_do_contrato"] == "CELULAR SEGURADO"
    mundo["resposta"] = _resposta("CELULAR CORRETOR", classe="conduzir", nota=100)   # o modelo errado, se chamado

    saida = _aguardar(EMPRESA_A, banco, params)

    assert mundo["modelo"] == []                                                   # o CÓDIGO conduziu
    cont = [j for j in banco.jobs if j["journey"] == "continuar_atendimento"]
    assert len(cont) == 1 and cont[0]["params"]["_continuacao"]["respostas"] == {"tipo_telefone": "CELULAR DO SEGURADO"}
    assert cont[0]["params"]["_destravador"]["classe"] == "conduzir"
    c_ev = cont[0]["evidence"]
    assert c_ev.get("stage") != "tipo_de_telefone_desconhecido"                     # passou do contato
    assert c_ev["contato_no_portal"]["codigo_tipo_telefone"] == 20                  # o código do SEGURADO
    assert _posts_de_abertura(origem, *banco.paginas) == 1                          # o MESMO pedido
    # a 1ª linha é a deste destravamento; a continuação parou adiante (outra parada, outra linha)
    assert (banco.diario[0]["acao"], banco.diario[0]["classe"]) == ("respondeu_portal", "conduzir")
    assert all(d["acao"] != "respondeu_portal" for d in banco.diario[1:])
    assert saida == {"content": PP.format_result(cont[0])}
    assert mundo["notificacoes"] == []


def test_CONTROLE_tipo_de_telefone_com_o_destravador_OFF_e_o_texto_de_HOJE(mundo):
    """Sem linha em `cerebro_modos` (B não ligou): o agente recebe a RELEITURA técnica de antes — nunca
    "pergunte ao segurado" um código do portal. Nada no diário, nenhuma continuação."""
    banco, params, ev, _o = _montar(mundo, _NOVO_TEL, RV.params_do_har(_NOVO), modos=[_modo(EMPRESA_A)],
                                    empresa=EMPRESA_B)
    saida = _aguardar(EMPRESA_B, banco, params)
    job = banco.jobs[0]
    hoje = {**job, "evidence": {**job["evidence"],
                                "continuacao": {**job["evidence"]["continuacao"], "acao_esperada": "reler"}}}
    assert saida == {"content": PP.format_result(hoje)}
    assert "tipo_telefone" not in saida["content"] and "Faca a pergunta" not in saida["content"]
    assert banco.diario == [] and len(banco.jobs) == 1 and mundo["modelo"] == []


# ═════════════════════════════════════════════════════════════════════════════
# RESPONDER COM DADO — a peça que `especificos` desambigua
# ═════════════════════════════════════════════════════════════════════════════
def _params_da_lanterna():
    p = RV.params_do_har(_NOVO)
    # 💭 o pedido: "a lanterna da frente" — a peça veio pela família e a posição, sob outra chave
    p["dano"] = {**p["dano"], "peca": "lanterna"}
    p["especificos"] = {"lanterna_posicao": "da frente"}
    return p


def test_RESPONDER_COM_DADO_a_peca_que_especificos_desambigua_continua_o_MESMO_pedido(mundo):
    banco, params, ev, origem = _montar(mundo, _NOVO, _params_da_lanterna(), modos=[_modo(EMPRESA_A)])
    assert ev["stage"] == "peca_ambigua" and len(ev["opcoes"]) >= 2                  # o worker parou
    assert ev["tela_da_parada"]["campo"] == "Qual foi a peça danificada?"
    mundo["resposta"] = _resposta(ev["opcoes"][-1], classe="deduzir", nota=100)

    _aguardar(EMPRESA_A, banco, params)

    assert mundo["modelo"] == []
    cont = [j for j in banco.jobs if j["journey"] == "continuar_atendimento"]
    assert len(cont) == 1
    assert cont[0]["params"]["_continuacao"]["respostas"] == {"peca": "LANTERNA DIANTEIRA CONVENCIONAL"}
    assert cont[0]["evidence"]["peca"]["descricao"] == "LANTERNA DIANTEIRA CONVENCIONAL"   # o motor aceitou
    assert cont[0]["evidence"].get("stage") != "peca_ambigua"
    assert _posts_de_abertura(origem, *banco.paginas) == 1
    assert (banco.diario[0]["acao"], banco.diario[0]["classe"]) == ("respondeu_portal", "responder_com_dado")
    assert all(d["acao"] != "respondeu_portal" for d in banco.diario[1:])


def test_CONTROLE_sem_a_resposta_que_desambigua_a_peca_volta_ao_segurado(mundo):
    p = _params_da_lanterna()
    p["especificos"] = {}
    banco, params, ev, _o = _montar(mundo, _NOVO, p, modos=[_modo(EMPRESA_A)])
    assert ev["stage"] == "peca_ambigua"
    saida = _aguardar(EMPRESA_A, banco, params)
    assert mundo["modelo"] == [] and len(banco.jobs) == 1
    assert [(d["acao"], d["classe"]) for d in banco.diario] == [("perguntou_segurado", "deduzir")]
    assert saida == {"content": PP.format_result(banco.jobs[0])}


# ═════════════════════════════════════════════════════════════════════════════
# PERGUNTAR — a parada ANTES da fronteira (P1) passa pelo destravador (o desvio saiu)
# ═════════════════════════════════════════════════════════════════════════════
def test_PERGUNTAR_faltou_peca_passa_pelo_destravador_e_a_resposta_volta_ao_MESMO_pedido(mundo):
    p = RV.params_do_har(_NOVO)
    certa = p["dano"]["peca"]
    p["dano"] = {**p["dano"], "peca": ""}
    banco, params, ev, origem = _montar(mundo, _NOVO, p, modos=[_modo(EMPRESA_A)])
    assert ev["stage"] == "faltou_peca" and _posts_de_abertura(origem) == 0       # nada escrito
    assert ev["tela_da_parada"]["campo"] == "Qual foi a peça danificada?"

    saida = _aguardar(EMPRESA_A, banco, params)

    # ① a TABELA decidiu (o modelo nem foi chamado): o dado é do segurado; o diário registra
    assert mundo["modelo"] == [] and len(banco.jobs) == 1
    assert [(d["acao"], d["classe"]) for d in banco.diario] == [("perguntou_segurado", "perguntar_ao_segurado")]
    assert saida == {"content": PP.format_result(banco.jobs[0])}
    # ② o segurado responde (a tool monta a continuação — o contrato da 001.10.1/P1) → o MESMO pedido
    linha = PP.montar_job_de_continuacao(
        company_id=EMPRESA_A, job_origem=banco.jobs[0], operacao="responder",
        pedido_key=params["_idempotency_key"], protocolo=params["_idempotency_key"], confirm=True,
        respostas={"peca": certa})
    lp = copy.deepcopy(linha["params"])
    lp["_runtime"] = RT(True)
    page = RV.PaginaDeReplay(_NOVO)
    ev2: dict = {}
    r = asyncio.run(VC.continuar_atendimento(page, lp, ev2))
    assert ev2["continuacao_pedida"].get("recomecou_a_abertura") is True
    assert (r.captured or {}).get("stage") != "faltou_peca"
    assert _posts_de_abertura(origem, page) == 1                                   # 0 + 1: um pedido só


# ═════════════════════════════════════════════════════════════════════════════
# DEDUZIR calibrado — a FIAÇÃO que o P5 liga (migrada da SPEC-124, P-124-07)
# ═════════════════════════════════════════════════════════════════════════════
def test_a_FIACAO_calibrada_responde_o_questionario_e_continua_com_1_POST(mundo, monkeypatch):
    """⚠️ `DEDUZIR_AUTONOMO_CALIBRADO` ligado AQUI (no produto: só com a prova do P5). O HAR do vidro
    lateral sem a resposta do LADO (📊 a real não é "Não sabe") → `questionario_incompleto` com o slot
    ETIQUETADO → modelo + 2ª opinião de OUTRO provedor → a continuação → o MESMO pedido."""
    monkeypatch.setattr(DT, "DEDUZIR_AUTONOMO_CALIBRADO", True)
    p = RV.params_do_har(_LATERAL)
    falta = next(k for k in p["especificos"] if k.startswith("pergunta_")
                 and "lado" in " ".join(str(p["especificos"][k]).lower().split()))
    certa = p["especificos"].pop(falta)
    # 📊 o HAR traz o perímetro "N" (não sabe) → o P1 pararia antes (faltou_onde); 💭 o pedido diz urbano
    p["dano"] = {**p["dano"], "onde": "U"}
    banco, params, ev, origem = _montar(mundo, _LATERAL, p, modos=[_modo(EMPRESA_A)])
    assert ev["stage"] == "questionario_incompleto" and PP.acao_esperada(ev) == ("responder", falta)
    assert ev["tela_da_parada"]["campo"] == ev["pergunta"]                         # P8: o campo É a pergunta
    opcao = next(o for o in ev["opcoes"] if " ".join(o.split()).lower() == " ".join(certa.split()).lower())
    mundo["resposta"] = _resposta(opcao, classe="deduzir", nota=95)

    class _Segunda:
        async def ainvoke(self, mensagens):
            mundo["modelo"].append({"papel": "destravador_segunda", "mensagens": mensagens})
            return AIMessage(content=_resposta(opcao, classe="deduzir", nota=90),
                             response_metadata={"model_provider": "anthropic", "model_name": "claude-sonnet-5-5"})

    monkeypatch.setattr(LF.LLMFactory, "create_llm", staticmethod(lambda *a, **k: _Segunda()))
    _aguardar(EMPRESA_A, banco, params)

    assert [c["papel"] for c in mundo["modelo"]] == ["destravador", "destravador_segunda"]
    prompt = "\n".join(str(m.content) for m in mundo["modelo"][0]["mensagens"])
    assert "O campo que pede a resposta:" in prompt                                # P8: o modelo LÊ a tela
    assert str(params["cpf_cnpj"]) not in prompt and str(params["placa"]) not in prompt
    cont = [j for j in banco.jobs if j["journey"] == "continuar_atendimento"]
    assert len(cont) == 1 and cont[0]["params"]["_continuacao"]["respostas"] == {falta: opcao}
    assert cont[0]["evidence"].get("stage") != "questionario_incompleto"
    assert _posts_de_abertura(origem, *banco.paginas) == 1
    assert (banco.diario[0]["acao"], banco.diario[0]["classe"]) == ("respondeu_portal", "deduzir")
