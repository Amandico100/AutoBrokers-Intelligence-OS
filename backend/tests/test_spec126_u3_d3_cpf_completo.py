# -*- coding: utf-8 -*-
"""SPEC-126 U3 · D3 — a MÁSCARA SÓ NA CONVERSA (gate G5).

    D3 (Founder, 02/10/2026): CPF mascarado SÓ no texto ao segurado; à URA da
    seguradora e ao portal de vidros os dados vão COMPLETOS (canal oficial).

O que se afirma é o MOTOR (CLAUDE.md §9.4), elo a elo, com o MESMO CPF sintético:

  (i)   o texto ao SEGURADO          `nodes.agent_node` REAL (modelo dublê)  → "final 4725"
  (ii)  o argumento e a sessão       `nodes.tool_node` REAL → `InsurerDispatchTool._arun`
                                     REAL → `dispatch_router.start_live_dispatch` REAL →
                                     a sessão guardada (`session["slots"]["titular_cpf"]`)
  (iii) a fala composta para a URA   `insurer_dispatch_service.handle_insurer_message` REAL
                                     sobre a TELA REAL do acervo (`telas_reais/allianz-auto`)
                                     → `render_reply` → `_emit(sender)` (o sender capturado)
  (iv)  o job do portal              `nodes.tool_node` REAL → `PortalActionTool._arun` REAL →
                                     `build_portal_params` REAL → o insert de `portal_jobs`

Dublês só na BORDA: o provedor de apólices, o banco e o Redis em memória, o canal de
WhatsApp (o `send_message` é capturado — nada sai), o interruptor do agente, o contato
da seguradora, o worker do portal. ⚠️ E o PORTÃO da confirmação (`_prova_da_confirmacao`)
é dublado como "comprovada": ele é da U2 e não é o objeto do D3.

🔴 MUTAÇÃO (relatório): mascarar os argumentos no `tool_node` → (ii)–(iv) VERMELHOS.
"""
from __future__ import annotations

import asyncio
import json
import os
import types

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agents import nodes as N
from tests.test_spec126_u3_d1_parente_aciona import (  # noqa: F401 — a borda é fixture
    EMPRESA_A, SESSAO_A, borda)

CPF = "52998224725"                  # sintético, DV válido
CPF_FMT = "529.982.247-25"
CONTATO_DA_SEGURADORA = "5511999998888"

CASO_AUTO = {
    "subservice": "guincho", "insurer_key": "allianz", "line_kind": "auto",
    "titular_cpf": CPF, "titular_nome": "Segurado Teste",
    "veiculo_placa": "AAA0A91", "telefone_contato": "48991234567",
    "local_atual": "Rua Um, 100, Florianopolis, SC",
    "local_destino": "Oficina Dois, Sao Jose, SC", "pessoa_no_local": "Segurado",
    "quando": "agora", "problema_descricao": "o carro nao liga e esta na rua",
    "local_seguro": "sim", "dados_confirmados": True,
}

PEDIDO_DO_PORTAL = {
    "cpf_cnpj": CPF, "data_dano": "05/07/2026",
    "peca": "vidro de porta", "como_ocorreu": "encontrou o veiculo danificado",
    "onde_ocorreu": "urbano",
    "descricao": "o carro estava estacionado e o vidro da porta foi quebrado",
    "especificos": {"onde_realizar_o_servico": "loja", "cidade_para_o_servico": "Joinville/SC",
                    "pelicula": "tem insulfilm sim", "porta_dianteira_ou_traseira": "dianteira",
                    "lado_motorista_ou_carona": "do lado do carona"},
}
INFOCAP_DO_PORTAL = {
    "ok": True,
    "policy": {"numapo": "000000", "seguradora": "SEGURADORA FICTICIA S/A"},
    "vehicle": {"placa": "AAA0A91", "veiculo": "MODELO EXEMPLO 1.0", "chassi": "9XX0000000000000"},
    "client": {"nome": "Segurado Exemplo", "cep": "88000-000", "logradouro": "Rua Exemplo",
               "numero": "1", "bairro": "Centro", "cidade": "Florianopolis", "estado": "SC",
               "telefone": "48900000000", "email": "segurado@exemplo.test"},
}
PERFIL_DA_CORRETORA = {
    "id": EMPRESA_A, "company_name": "Corretora Exemplo", "legal_name": "Corretora Exemplo LTDA",
    "primary_contact_name": "Atendimento Exemplo", "primary_contact_email": "operacao@exemplo.test",
    "primary_contact_phone": "4830000000", "cnpj": "00000000000191", "acionamento_profile": None,
}


def _tela_real_do_cpf() -> str:
    """A tela vem do ACERVO, não da imaginação (CLAUDE.md §9.4)."""
    caminho = os.path.join(os.path.dirname(__file__), "corpus", "telas_reais", "allianz-auto.jsonl")
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            texto = json.loads(linha).get("text") or ""
            if texto.startswith("Digite o *CPF* ou *CNPJ* do(a) titular"):
                return texto
    raise AssertionError("a tela do CPF sumiu do acervo")


# =========================================================================== #
# (i) o texto ao SEGURADO sai mascarado
# =========================================================================== #
class _Modelo:
    def __init__(self, texto):
        self.texto = texto

    async def ainvoke(self, mensagens, config=None):
        return AIMessage(content=self.texto)


def test_i_ao_segurado_o_cpf_sai_so_pelo_final(monkeypatch):
    import app.services.activity_log as AL

    async def _log(*_a, **_k):
        return None

    monkeypatch.setattr(AL, "log_activity", _log)
    monkeypatch.setattr(N, "_registrar_julgamento_no_diario", lambda *_a, **_k: None)
    monkeypatch.setattr(N, "_marcar_erro_leve_no_diario", lambda *_a, **_k: None)
    estado = {"messages": [HumanMessage(content=f"meu cpf é {CPF_FMT}, o carro não pega")],
              "company_id": EMPRESA_A, "session_id": SESSAO_A, "user_id": "u", "company_config": {},
              "agent_data": {"agent_role": "attendance", "prompt_versao": "v2"},
              "system_prompt": "prompt", "static_prompt": "prompt", "dynamic_context": "",
              "ficha_atendimento": {}, "tools_used": []}
    saida = asyncio.run(N.agent_node(estado, None, _Modelo(
        f"Anotei o CPF {CPF_FMT} do titular. Já vou localizar sua apólice.")))
    texto = " ".join(str(getattr(m, "content", "")) for m in saida.get("messages") or [])
    assert "final 4725" in texto, texto
    assert CPF not in texto and CPF_FMT not in texto, texto


# =========================================================================== #
# (ii) + (iii) o acionamento: argumento, sessão e a fala à URA — COMPLETOS
# =========================================================================== #
@pytest.fixture
def acionamento(borda, monkeypatch):
    """As BORDAS do acionamento real. Devolve `(enviados_pelo_canal, checkpoints)`."""
    import app.agents.tools.insurer_dispatch_tool as IT
    import app.services.corridor_playbooks as CP
    import app.services.dispatch_router as DR
    import app.services.insurer_dispatch_service as DS
    import app.services.integration_service as IS
    import app.services.whatsapp_service as WS

    enviados, checkpoints = [], []

    async def _sim(self, *_a, **_k):
        return True

    async def _comprovada(self, _kwargs):
        return {"comprovada": True, "motivo": ""}

    async def _checkpoint(company_id, insurer_phone, session):
        checkpoints.append(json.loads(json.dumps(session, default=str)))
        return None

    monkeypatch.setattr(DS, "dispatch_live_enabled", lambda: True)
    monkeypatch.setattr(DS, "finalize_live_for", lambda _ref: False)
    monkeypatch.setattr(CP, "resolve_insurer_contact", lambda *_a, **_k: CONTATO_DA_SEGURADORA)
    monkeypatch.setattr(CP, "contato_do_subservico", lambda *_a, **_k: (None, None))
    monkeypatch.setattr(IT.InsurerDispatchTool, "_acionamento_liberado", _sim)
    monkeypatch.setattr(IT.InsurerDispatchTool, "_prova_da_confirmacao", _comprovada)
    monkeypatch.setattr(IS, "get_integration_service", lambda *_a, **_k: types.SimpleNamespace(
        get_whatsapp_integration=lambda *_a, **_k: {"id": "integ"}))
    monkeypatch.setattr(WS, "get_whatsapp_service", lambda *_a, **_k: types.SimpleNamespace(
        send_message=lambda alvo, texto, *_a, **_k: enviados.append((alvo, texto))))
    monkeypatch.setattr(DR, "registrar_checkpoint", _checkpoint)
    monkeypatch.setattr(DR, "_agendar_reconciliacao_uma_vez", lambda: None)
    monkeypatch.setattr(DR, "_memory_store", {})
    return enviados, checkpoints


def _acionar_pelo_motor(borda):
    import app.agents.tools.insurer_dispatch_tool as IT

    banco, _prov = borda
    msgs = [HumanMessage(content=f"meu carro não liga, meu cpf é {CPF}"),
            AIMessage(content="", tool_calls=[{"name": "insurer_dispatch", "args": dict(CASO_AUTO),
                                               "id": "call-d3"}])]
    estado = {"company_id": EMPRESA_A, "user_id": "teste", "session_id": SESSAO_A, "company_config": {},
              "agent_data": {"id": None, "agent_role": "attendance", "tools_config": {}},
              "messages": msgs, "tools_used": [], "rag_chunks": [], "rag_search_time_ms": 0,
              "infocap_policy_context": None, "policy_response_contract": None, "internal_steps": []}
    tool = IT.InsurerDispatchTool(company_id=EMPRESA_A, supabase_client=banco)
    return asyncio.run(N.tool_node(estado, tools=[tool]))


def _sessao_guardada():
    import app.services.dispatch_router as DR

    chave = DR._key(EMPRESA_A, CONTATO_DA_SEGURADORA)
    bruto = DR._memory_store.get(chave)
    assert bruto, "o acionamento não guardou a sessão: %r" % list(DR._memory_store)
    return json.loads(bruto)


def test_ii_o_argumento_e_a_sessao_do_dispatch_tem_o_cpf_inteiro(borda, acionamento):
    _enviados, checkpoints = acionamento
    saida = _acionar_pelo_motor(borda)
    conteudo = " ".join(str(m.content) for m in saida.get("messages") or [])
    assert "ACIONAMENTO" in conteudo and "INICIADO" in conteudo, conteudo
    sessao = _sessao_guardada()
    assert sessao["slots"]["titular_cpf"] == CPF, sessao["slots"].get("titular_cpf")
    assert checkpoints and checkpoints[-1]["slots"]["titular_cpf"] == CPF


def test_iii_a_fala_composta_para_a_ura_leva_o_cpf_inteiro(borda, acionamento):
    import app.services.insurer_dispatch_service as DS

    enviados, _ = acionamento
    _acionar_pelo_motor(borda)
    sessao = _sessao_guardada()
    a_ura = []
    DS.handle_insurer_message(sessao, _tela_real_do_cpf(), sender=a_ura.append)
    assert a_ura, "a URA pediu o CPF e o motor não respondeu: %r" % sessao.get("transcript", [])[-2:]
    assert a_ura[-1] == CPF, a_ura
    # e o que sai pelo CANAL da corretora até aqui (a abertura) foi para a seguradora, não ao segurado
    assert all(alvo == CONTATO_DA_SEGURADORA for alvo, _t in enviados), enviados


# =========================================================================== #
# (iv) o job do portal de vidros
# =========================================================================== #
def test_iv_o_job_do_portal_leva_o_cpf_inteiro(borda, monkeypatch):
    import app.agents.tools.portal_tool as PT

    banco, _prov = borda
    banco.tabelas["companies"] = [dict(PERFIL_DA_CORRETORA)]

    class _Portal(PT.PortalActionTool):
        async def _fetch_infocap(self, cpf, policy_number):   # a BORDA: a InfoCap é rede
            return json.loads(json.dumps(INFOCAP_DO_PORTAL))

    async def _nao(self, *_a, **_k):
        return False

    async def _nada(self, *_a, **_k):
        return None

    async def _pronto(self, *_a, **_k):
        return {"content": "pedido recebido pelo portal"}

    monkeypatch.setattr(PT.PortalActionTool, "_envio_liberado", _nao)
    monkeypatch.setattr(PT.PortalActionTool, "_garantir_work_run", _nada)
    monkeypatch.setattr(PT.PortalActionTool, "_aguardar", _pronto)
    monkeypatch.setattr(PT.PortalActionTool, "_notify", lambda *_a, **_k: None)
    # 🔴 SPEC-127 P1 (D-127-E) — §9.3, a lição MIGRA: o job só nasce depois do resumo + o "sim"
    # (o portão da SPEC-126). O assunto aqui é o CPF INTEIRO no job: o "sim" é BORDA (provado em
    # `test_spec127_p1_*`).
    monkeypatch.setattr(PT.PortalActionTool, "_portao_do_ok", _nada)

    msgs = [HumanMessage(content=f"quebraram o vidro do meu carro, cpf {CPF}"),
            AIMessage(content="", tool_calls=[{"name": "portal_action", "args": dict(PEDIDO_DO_PORTAL),
                                               "id": "call-portal"}])]
    estado = {"company_id": EMPRESA_A, "user_id": "teste", "session_id": SESSAO_A, "company_config": {},
              "agent_data": {"id": None, "agent_role": "attendance", "tools_config": {}},
              "messages": msgs, "tools_used": [], "rag_chunks": [], "rag_search_time_ms": 0,
              "infocap_policy_context": None, "policy_response_contract": None, "internal_steps": []}
    asyncio.run(N.tool_node(estado, tools=[_Portal(company_id=EMPRESA_A, supabase_client=banco)]))
    jobs = banco.tabelas.get("portal_jobs") or []
    assert len(jobs) == 1, "o job do portal não nasceu: %r" % jobs
    assert jobs[0]["params"]["cpf_cnpj"] == CPF, jobs[0]["params"].get("cpf_cnpj")
    assert jobs[0]["company_id"] == EMPRESA_A
