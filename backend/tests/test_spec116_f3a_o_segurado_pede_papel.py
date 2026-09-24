# -*- coding: utf-8 -*-
"""SPEC-116 F3a (U8) — o que LÊ, LEMBRA, BUSCA e OUVE para o segurado pede um PAPEL.

🔴 CHAMA O MOTOR (CLAUDE.md §9.4): `describe_image`, `_analyze_image` via
`process_message`, `webhook._midia_do_turno`, `attendance_media_vision`,
`MemoryService._get_memory_llm`, `SearchService._generate_hyde_doc`,
`IngestionService._chunk_agentic`, `AudioService`, `RerankService`. O BANCO é
o snapshot do catálogo (dublê da única borda de dados) e o PROVEDOR é dublado
na borda — o objeto que a fábrica construiu é interceptado no `ainvoke`/`invoke`
da classe-base (`BaseChatModel`), então QUALQUER cliente, inclusive um
`ChatOpenAI(model="gpt-4o-mini")` reintroduzido por fora, é visto.

Guardas e as mutações que os deixam VERMELHOS (protocolo §5 ③):
  G-VIS-1  visão segue a ROTA `visao` (mutação: default literal de volta ⇒ vermelho)
  G-VIS-2  UMA chamada de visão por foto (mutação: tirar `imagem_ja_descrita` ⇒ 2)
  G-VIS-3  attendance_media com DOIS tenants (mutação: tirar o filtro company_id)
  G-MEM    memória pela rota `memoria` (mutação: ler memory_settings ⇒ vermelho)

⛔ Sem rede, sem banco real, sem modelo real, sem PII. Tenants sintéticos.
Rodar (de backend/):  .venv/Scripts/python -m pytest -q tests/test_spec116_f3a_o_segurado_pede_papel.py
"""
from __future__ import annotations

import asyncio
import base64
import copy
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, List

import pytest

BACKEND = Path(__file__).resolve().parent.parent
for _c in (str(BACKEND), str(BACKEND / "tests")):
    if _c not in sys.path:
        sys.path.insert(0, _c)
os.environ["SEM_REDE"] = "1"


class _Q:
    data: list = []

    def __getattr__(self, _n):
        return lambda *a, **k: self

    def execute(self):
        return self


class _BancoMudo:
    client = None

    def table(self, _n):
        return _Q()


_BancoMudo.client = _BancoMudo()

import app.core.database as _db  # noqa: E402
import app.services.usage_service as _uso  # noqa: E402

_db.get_supabase_client = lambda: _BancoMudo()
_uso.get_supabase_client = _db.get_supabase_client

from langchain_core.language_models.chat_models import BaseChatModel  # noqa: E402
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel  # noqa: E402
from langchain_core.messages import AIMessage, HumanMessage  # noqa: E402

from app.factories import model_policy as MP  # noqa: E402
from app.factories.llm_factory import ChatAnthropicGovernado, ChatOpenAIGovernado  # noqa: E402

SNAP = json.loads(MP.SNAPSHOT_PATH.read_text(encoding="utf-8"))

#: 🔴 (24/09/2026 — conclusão da Onda A) PRODUÇÃO só aceita APPROVED. Estes testes
#: provam a MECÂNICA de trocar a rota (provedor, adaptador, temperatura, ledger)
#: usando modelos LEGADOS como dublês de "outro modelo" — no dublê eles são
#: promovidos a APPROVED. A regra de lifecycle (e o mínimo de esforço) é provada
#: em `test_nenhum_modelo_fora_do_catalogo.py` (§9.3: a lição migra, não morre).
MODELOS_LEGADOS_DUBLES = ("claude-sonnet-5", "claude-opus-5", "claude-haiku-4-5",
                          "claude-haiku-4-5-20251001", "gpt-4o", "gpt-4o-mini",
                          "gpt-4o-mini-2024-07-18", "whisper-1")


def _legados_como_dubles(cat):
    for m in MODELOS_LEGADOS_DUBLES:
        if m in cat:
            cat[m]["lifecycle"] = "APPROVED"
    return cat

TENANT_A = "aaaaaaaa-0000-4000-8000-00000000000a"
TENANT_B = "bbbbbbbb-0000-4000-8000-00000000000b"
FOTO = "https://fixture.invalido/foto-sintetica.jpg"


# ---------------------------------------------------------------------------
# Bordas: o BANCO (snapshot copiado) e o PROVEDOR (a classe-base do chat)
# ---------------------------------------------------------------------------
@pytest.fixture
def banco(monkeypatch):
    cat = _legados_como_dubles(copy.deepcopy(SNAP["catalogo"]))
    pap = copy.deepcopy(SNAP["papeis"])
    original = MP.leitor_do_banco
    MP.leitor_do_banco = lambda: (cat, pap)
    MP.limpar_cache()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-teste-openai-falsa")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-teste-falsa")
    yield cat, pap
    MP.leitor_do_banco = original
    MP.limpar_cache()


@pytest.fixture(autouse=True)
def _banco_do_ledger_deste_modulo(monkeypatch):
    """🔴 (conserto único) o dublê do cliente Supabase é DESTE módulo durante o
    teste. Vários módulos trocam `get_supabase_client` no nível do import — na
    coleta, o último import vencia: 📊 com `test_spec116_f2_adaptadores.py` na
    mesma sessão, o `webhook` nascia com `client=None` e
    `test_uma_foto_uma_chamada…` caía em `IntegrationService` (ValueError)."""
    monkeypatch.setattr(_db, "get_supabase_client", lambda: _BancoMudo())
    monkeypatch.setattr(_uso, "get_supabase_client", _db.get_supabase_client)


#: 🔴 (conserto único — CLAUDE.md §9.3): a rota de HOJE, lida do snapshot (o banco
#: dublado). Os controles afirmavam `gpt-4o-mini` (o seed); a `_04` trocou visão e
#: memória. O teste lê o esperado da rota; nunca uma constante.
def _rota_hoje(papel):
    return SNAP["papeis"][papel]


def _trocar_rota(pap, papel, provider, modelo, esforco=None):
    # (24/09/2026) o esforço da rota nova (medium/high) não vale para o dublê
    pap[papel].update(provider=provider, modelo_primario=modelo, esforco=esforco)
    MP.limpar_cache()


class Provedor:
    """A BORDA: todo `ainvoke`/`invoke` de modelo de chat passa por aqui."""

    def __init__(self, resposta: Any = "um cano rompido embaixo da pia"):
        self.chamadas: List[dict] = []
        self.resposta = resposta

    def _anotar(self, modelo, mensagens):
        self.chamadas.append({
            "classe": type(modelo).__name__,
            "model": getattr(modelo, "model_name", None) or getattr(modelo, "model", None),
            "llm": modelo, "mensagens": mensagens,
        })
        return AIMessage(content=self.resposta)


@pytest.fixture
def provedor(monkeypatch):
    p = Provedor()

    async def _ainvoke(self, entrada, config=None, **kw):
        return p._anotar(self, entrada)

    def _invoke(self, entrada, config=None, **kw):
        return p._anotar(self, entrada)

    monkeypatch.setattr(BaseChatModel, "ainvoke", _ainvoke)
    monkeypatch.setattr(BaseChatModel, "invoke", _invoke)
    return p


# ===========================================================================
# G-VIS-1 — a visão pede o PAPEL; a rota decide; sampling segue o catálogo
# ===========================================================================
def test_visao_segue_a_rota_do_papel_e_nao_o_default(banco, provedor):
    from app.services.vision_service import describe_image

    _, pap = banco
    # A rota diz Claude 5; o agente tem um vision_model VELHO gravado (D-116-17:
    # a rota vence). 🔴 Mutação "default gpt-4o-mini de volta" ⇒ model errado.
    _trocar_rota(pap, "visao", "anthropic", "claude-sonnet-5")
    desc = asyncio.run(describe_image(FOTO, company_id=TENANT_A, agent_id="ag-a",
                                      agent_data={"vision_model": "gpt-4o-mini"}))
    assert desc == "um cano rompido embaixo da pia"
    assert len(provedor.chamadas) == 1, provedor.chamadas
    ch = provedor.chamadas[0]
    assert (ch["classe"], ch["model"]) == ("ChatAnthropicGovernado", "claude-sonnet-5"), ch
    # Claude 5 recusa sampling: o payload REAL do adaptador não leva temperature.
    payload = ch["llm"]._get_request_payload(ch["mensagens"])
    assert "temperature" not in payload and "temperature" not in (payload.get("extra_body") or {})
    # a imagem vai por URL (o motor de visão, não um texto)
    assert '"image_url"' in json.dumps(ch["mensagens"][1].content)
    # ledger: o callback de custo da fábrica, com papel e o pedido do agente
    custo = ch["llm"].callbacks[0]
    assert custo.service_type == "vision" and custo.company_id == TENANT_A
    assert custo.details["papel"] == "visao" and custo.details["modelo_pedido"] == "gpt-4o-mini"
    assert custo.details["modelo_resolvido"] == "claude-sonnet-5"


def test_visao_controle_rota_openai_mantem_a_temperatura(banco, provedor):
    """LINHA DE CONTROLE: um modelo cujo catálogo ACEITA sampling mantém a
    temperatura — o mesmo motor que a tirou do Claude. E a rota de HOJE segue o
    catálogo dela (com ou sem temperature, conforme `sampling_ok`)."""
    from app.services.vision_service import describe_image

    cat, pap = banco
    # 1) a rota de hoje (lida do snapshot): o cliente e o payload seguem o catálogo
    hoje = _rota_hoje("visao")
    asyncio.run(describe_image(FOTO, company_id=TENANT_A))
    ch = provedor.chamadas[0]
    assert ch["model"] == hoje["modelo_primario"], ch
    amostra_ok = (cat[hoje["modelo_primario"]].get("capacidades") or {}).get("sampling_ok") is not False
    assert ("temperature" in ch["llm"]._get_request_payload(ch["mensagens"])) is amostra_ok
    # 2) CONTROLE: rota para um modelo que ACEITA sampling ⇒ a temperatura fica
    _trocar_rota(pap, "visao", "openai", "gpt-4o-mini")
    pap["visao"]["esforco"] = None   # a rota de hoje tem esforço; o gpt-4o-mini não aceita
    MP.limpar_cache()
    assert (cat["gpt-4o-mini"].get("capacidades") or {}).get("sampling_ok") is not False
    asyncio.run(describe_image(FOTO, company_id=TENANT_A))
    ch = provedor.chamadas[1]
    assert (ch["classe"], ch["model"]) == ("ChatOpenAIGovernado", "gpt-4o-mini")
    assert ch["llm"]._get_request_payload(ch["mensagens"]).get("temperature") == 0.3


def test_visao_sem_rota_e_sem_modelo_governado_e_erro_explicito(banco, provedor, caplog):
    from app.services.vision_service import describe_image

    _, pap = banco
    pap.pop("visao")
    MP.limpar_cache()
    # sem rota e sem vision_model: NENHUMA chamada (nunca um mini por omissão)
    assert asyncio.run(describe_image(FOTO, company_id=TENANT_A)) is None
    assert provedor.chamadas == []
    assert "papel 'visao' sem modelo governado" in caplog.text
    # modelo fora do catálogo (ex.: um Gemini sem linha) → erro, não um mini
    assert asyncio.run(describe_image(FOTO, company_id=TENANT_A,
                                      agent_data={"vision_model": "gemini-inexistente"})) is None
    assert provedor.chamadas == []
    # CONTROLE: papel sem rota + vision_model GOVERNADO do agente → o do agente
    asyncio.run(describe_image(FOTO, company_id=TENANT_A, agent_data={"vision_model": "gpt-4o"}))
    assert [c["model"] for c in provedor.chamadas] == ["gpt-4o"]


def test_visao_ponto_de_injecao_llm(banco, provedor):
    from app.services.vision_service import describe_image

    duble = GenericFakeChatModel(messages=iter([AIMessage(content=[
        {"type": "thinking", "thinking": "rascunho"}, {"type": "text", "text": "uma fatura"}])]))
    # GenericFakeChatModel também é BaseChatModel: a borda anota, e devolve o texto do dublê
    provedor.resposta = [{"type": "thinking", "thinking": "rascunho"},
                         {"type": "text", "text": "uma fatura"}]
    desc = asyncio.run(describe_image(FOTO, company_id=TENANT_A, llm=duble))
    assert desc == "uma fatura", "o raciocínio nunca vira descrição"
    assert [c["classe"] for c in provedor.chamadas] == ["GenericFakeChatModel"]


# ===========================================================================
# G-VIS-2 — UMA chamada de visão por foto num turno de atendimento
# ===========================================================================
class _Sup:
    client = _BancoMudo()

    def get_company(self, cid):
        return {"id": cid}

    def get_conversation_history(self, **_k):
        return []


class _GuardaQuePassa:
    fail_close = True

    def __init__(self, *a, **k):
        pass

    async def validate_input(self, texto):
        return False, None, texto


def _servico(monkeypatch, visto):
    import app.agents as AG
    import app.services.langchain_service as LS

    svc = object.__new__(LS.LangChainService)
    svc.supabase = _Sup()
    svc.qdrant = None
    agente = {"id": "ag-a", "company_id": TENANT_A, "agent_role": "attendance",
              "llm_provider": "anthropic", "llm_model": "claude-sonnet-5", "security_settings": {}}

    async def _agente(*_a, **_k):
        return dict(agente)

    async def _grafo(**_k):
        return object()

    async def _invoke_agent(**k):
        visto["mensagem"] = k.get("user_message")
        return {"response": "ok", "tools_used": []}

    svc._get_raw_agent = _agente
    monkeypatch.setattr(LS, "SmithGuardrail", _GuardaQuePassa)
    monkeypatch.setattr(LS, "get_or_create_graph", _grafo)
    monkeypatch.setattr(AG, "invoke_agent", _invoke_agent)
    return svc


def test_uma_foto_uma_chamada_de_visao_no_turno_do_segurado(banco, provedor, monkeypatch):
    """📊 BLOCO 0 (23/09/2026, rodado): webhook descrevia + process_message
    descrevia de novo = 2 chamadas por foto e o contexto visual 2× no prompt."""
    import app.api.webhook as W

    async def _subiu(url, *a, **k):
        return FOTO

    monkeypatch.setattr(W, "process_image_for_vision", _subiu)
    visto: dict = {}
    svc = _servico(monkeypatch, visto)

    async def _turno():
        texto, url = await W._midia_do_turno(
            [{"tipo": "image", "midia": {"imageUrl": "https://wa.invalido/x"}}],
            company_id=TENANT_A, agent_id="ag-a", supabase_client=None, is_human_mode=False)
        await svc.process_message("segue a foto\n\n" + texto, TENANT_A, "u", "s",
                                  collect_metrics=False, image_url=url, agent_id="ag-a",
                                  required_role="attendance")

    asyncio.run(_turno())
    assert len(provedor.chamadas) == 1, [c["model"] for c in provedor.chamadas]
    assert visto["mensagem"].count("CONTEXTO VISUAL") == 1, visto["mensagem"]


def test_controle_foto_sem_descricao_previa_e_descrita_no_process_message(banco, provedor,
                                                                          monkeypatch):
    """LINHA DE CONTROLE: quem chama `process_message` com a imagem e SEM a
    descrição prévia (o chat não-streaming) continua vendo a foto."""
    visto: dict = {}
    svc = _servico(monkeypatch, visto)
    asyncio.run(svc.process_message("o que é isto?", TENANT_A, "u", "s", collect_metrics=False,
                                    image_url=FOTO, agent_id="ag-a", required_role="attendance"))
    assert len(provedor.chamadas) == 1
    assert "[CONTEXTO VISUAL]" in visto["mensagem"]
    assert provedor.chamadas[0]["llm"].callbacks[0].details["papel"] == "visao"


# ===========================================================================
# G-VIS-3 — attendance_media: visão por papel e o agente SÓ da corretora
# ===========================================================================
class _ConsultaAgentes:
    def __init__(self, linhas):
        self.linhas, self.filtros = linhas, []

    def select(self, *_a, **_k):
        return self

    def eq(self, coluna, valor):
        self.filtros.append((coluna, valor))
        return self

    def limit(self, _n):
        return self

    async def execute(self):
        return SimpleNamespace(data=[dict(l) for l in self.linhas
                                     if all(str(l.get(c)) == str(v) for c, v in self.filtros)])


class _DbDoisTenants:
    def __init__(self):
        self.client = self
        self.linhas = [
            {"id": "ag-a", "company_id": TENANT_A, "vision_model": None, "agent_role": "attendance"},
            {"id": "ag-b", "company_id": TENANT_B, "vision_model": "gpt-4o", "agent_role": "attendance"},
        ]

    def table(self, _nome):
        return _ConsultaAgentes(self.linhas)


def _visao_do_atendimento(company_id, agent_id):
    import app.api.attendance_media as AM

    return asyncio.run(AM.attendance_media_vision(
        AM.VisionPayload(company_id=company_id, agent_id=agent_id, image_url=FOTO),
        x_autobrokers_internal_key="chave-interna-de-teste", db=_DbDoisTenants()))


def test_attendance_media_agente_de_outra_corretora_nao_e_achado(banco, provedor, monkeypatch):
    monkeypatch.setenv("BACKEND_INTERNAL_API_KEY", "chave-interna-de-teste")
    # agente do B pedido com a empresa do A ⇒ NÃO acha, e nenhum modelo é chamado
    r = _visao_do_atendimento(TENANT_A, "ag-b")
    assert r["ok"] is False and r["error"] == "agent_not_found", r
    assert provedor.chamadas == []
    # CONTROLE: o mesmo agente com a SUA empresa ⇒ processa, pelo papel `visao`
    r = _visao_do_atendimento(TENANT_B, "ag-b")
    assert r["ok"] is True and r["status"] == "processed", r
    assert len(provedor.chamadas) == 1
    ch = provedor.chamadas[0]
    assert _rota_hoje("visao")["modelo_primario"] != "gpt-4o", "rota e gravado CONSEGUEM divergir"
    assert ch["model"] == _rota_hoje("visao")["modelo_primario"],         "a ROTA manda, não o vision_model gravado (D-116-17)"
    custo = ch["llm"].callbacks[0]
    assert (custo.service_type, custo.company_id, custo.agent_id) == ("vision", TENANT_B, "ag-b")
    assert custo.details["papel"] == "visao" and custo.details["modelo_pedido"] == "gpt-4o"


def test_attendance_media_sem_agente_usa_a_rota(banco, provedor, monkeypatch):
    monkeypatch.setenv("BACKEND_INTERNAL_API_KEY", "chave-interna-de-teste")
    _, pap = banco
    _trocar_rota(pap, "visao", "anthropic", "claude-sonnet-5")
    r = _visao_do_atendimento(TENANT_A, None)
    assert r["ok"] is True and r["provenance"] == "vision:claude-sonnet-5", r
    ch = provedor.chamadas[0]
    assert "temperature" not in ch["llm"]._get_request_payload(ch["mensagens"])


# ===========================================================================
# G-MEM — a memória vem SEMPRE da rota `memoria` (D-116-15)
# ===========================================================================
def test_memoria_ignora_memory_settings_e_segue_a_rota(banco):
    from app.services.memory_service import MemoryService

    _, pap = banco
    svc = MemoryService(None)
    # a linha de memory_settings diz gpt-4o (legado); a ROTA diz Claude 5.
    # 🔴 Mutação "ler memory_settings" ⇒ gpt-4o ⇒ VERMELHO.
    _trocar_rota(pap, "memoria", "anthropic", "claude-sonnet-5")
    llm = svc._get_memory_llm({"memory_llm_model": "gpt-4o"}, company_id=TENANT_A, agent_id="ag-a")
    assert isinstance(llm, ChatAnthropicGovernado) and llm.model == "claude-sonnet-5"
    assert "temperature" not in llm._get_request_payload([HumanMessage(content="x")])
    custo = llm.callbacks[0]
    assert (custo.service_type, custo.company_id) == ("memory", TENANT_A)
    assert custo.details["papel"] == "memoria" and custo.details["modelo_pedido"] is None
    # sem company_id (tarefa de fundo) o ledger continua anexado
    assert svc._get_memory_llm({}, company_id=None).callbacks[0].details["papel"] == "memoria"


def test_memoria_controle_a_rota_de_hoje_e_o_mini_no_cliente_openai(banco):
    """LINHA DE CONTROLE: a rota de HOJE (lida do snapshot) monta o cliente DO
    PROVEDOR DELA — nunca um Claude dentro de `ChatOpenAI` (o defeito de antes),
    e a coluna legada `memory_llm_model` (Haiku) não manda."""
    from app.services.memory_service import MemoryService

    hoje = _rota_hoje("memoria")
    assert hoje["modelo_primario"] != "claude-haiku-4-5-20251001", "legado e rota CONSEGUEM divergir"
    llm = MemoryService(None)._get_memory_llm({"memory_llm_model": "claude-haiku-4-5-20251001"})
    classe = {"openai": ChatOpenAIGovernado, "anthropic": ChatAnthropicGovernado}[hoje["provider"]]
    assert isinstance(llm, classe), type(llm)
    assert (getattr(llm, "model_name", None) or llm.model) == hoje["modelo_primario"]


def test_memoria_ponto_de_injecao_aceita_resposta_em_blocos():
    from app.services.memory_service import MemoryService

    duble = GenericFakeChatModel(messages=iter([AIMessage(content=[
        {"type": "thinking", "thinking": "pensando"},
        {"type": "text", "text": '["o segurado tem um Onix 2020"]'}])]))
    fatos = asyncio.run(MemoryService(None).extract_user_facts_async(
        [HumanMessage(content="meu carro é um Onix 2020")], [], llm=duble))
    assert fatos == ["o segurado tem um Onix 2020"]


# ===========================================================================
# HyDE · chunking agêntico · embeddings — pelo papel
# ===========================================================================
def test_hyde_pede_o_papel_hyde(banco, provedor):
    from app.services import search_service as ss

    _, pap = banco
    _trocar_rota(pap, "hyde", "anthropic", "claude-sonnet-5")
    svc = object.__new__(ss.SearchService)
    doc = svc._generate_hyde_doc("cobre vazamento?", TENANT_A, "ag-a")
    assert doc == "um cano rompido embaixo da pia"
    ch = provedor.chamadas[0]
    assert (ch["model"], ch["llm"].callbacks[0].details["papel"]) == ("claude-sonnet-5", "hyde")
    assert ch["llm"].callbacks[0].service_type == "rag_query"
    # ponto de injeção
    duble = GenericFakeChatModel(messages=iter([AIMessage(content="trecho hipotético")]))
    provedor.resposta = "trecho hipotético"
    assert svc._generate_hyde_doc("q", llm=duble) == "trecho hipotético"


def test_chunking_agentico_pede_o_papel(banco, provedor):
    from app.services import ingestion_service as ing

    provedor.resposta = json.dumps({"chunks": [{"topic": "Coberturas", "content": "texto exato " * 8}]})
    svc = object.__new__(ing.IngestionService)
    chunks, metas = svc._chunk_agentic("texto exato " * 20, {}, TENANT_A)
    assert chunks and "texto exato" in chunks[0]
    ch = provedor.chamadas[0]
    assert ch["model"] == banco[1]["chunking_agentico"]["modelo_primario"]
    custo = ch["llm"].callbacks[0]
    assert (custo.service_type, custo.details["papel"]) == ("ingestion", "chunking_agentico")


class _UsoGravado:
    def __init__(self):
        self.linhas: List[dict] = []

    def track_cost_sync(self, **kw):
        self.linhas.append(kw)
        return True


@pytest.fixture
def uso(monkeypatch):
    g = _UsoGravado()
    monkeypatch.setattr(_uso, "get_usage_service", lambda: g)
    return g


def test_embedding_o_id_vem_da_rota(banco, uso):
    from app.services import ingestion_service as ing
    from app.services import search_service as ss

    cat, pap = banco
    cat["text-embedding-rota-de-teste"] = dict(cat["text-embedding-3-small"],
                                               model_name="text-embedding-rota-de-teste")
    _trocar_rota(pap, "embedding", "openai", "text-embedding-rota-de-teste")
    object.__new__(ss.SearchService)._track_query_embedding_cost("cobre vidro?", TENANT_A, "ag-a")
    object.__new__(ing.IngestionService)._track_embedding_cost(["um trecho"], TENANT_A, "ag-a")
    assert [l["model"] for l in uso.linhas] == ["text-embedding-rota-de-teste"] * 2
    assert all(l["details"]["papel"] == "embedding" for l in uso.linhas)


# ===========================================================================
# Transcrição e rerank — pela rota, com ledger
# ===========================================================================
class _Transcricoes:
    def __init__(self, resposta=None):
        self.pedidos: List[dict] = []
        self.resposta = resposta or SimpleNamespace(text="quebrou o cano", duration=4.2)

    async def create(self, **kw):
        self.pedidos.append({k: v for k, v in kw.items() if k != "file"})
        return self.resposta


def _cliente_de_audio(resposta=None):
    return SimpleNamespace(audio=SimpleNamespace(transcriptions=_Transcricoes(resposta)))


def _ogg_opus(segundos: float) -> bytes:
    """Um OGG/Opus MÍNIMO: cabeçalho OpusHead (pre-skip 312) + a última página com
    o grânulo de `segundos` a 48 kHz — o bastante para medir a duração."""
    pre_skip = 312
    head = b"OggS" + b"\x00\x02" + (0).to_bytes(8, "little") + b"\x00" * 12 + \
        b"OpusHead" + b"\x01\x01" + pre_skip.to_bytes(2, "little") + (48000).to_bytes(4, "little")
    granulo = int(segundos * 48000) + pre_skip
    fim = b"OggS" + b"\x00\x04" + granulo.to_bytes(8, "little") + b"\x00" * 12
    return head + b"\x00" * 64 + fim


def test_transcricao_pela_rota_gpt_transcribe_json_prompt_e_ledger_por_minuto(banco, uso, monkeypatch):
    """🔴 (24/09/2026) a rota `transcricao` é gpt-transcribe: API de TRANSCRIÇÃO
    (não a fábrica de chat), `json` (verbose_json não é documentado para ele),
    `prompt` de domínio SEM PII, e o ledger por MINUTO com a duração medida AQUI."""
    from app.services import audio_service as A
    from app.services.insurer_registry import INSURER_REGISTRY

    cat, pap = banco
    _trocar_rota(pap, "transcricao", "openai", "gpt-transcribe")
    assert cat["gpt-transcribe"]["unit"] == "minute"
    cli = _cliente_de_audio(SimpleNamespace(text="quebrou o cano da Porto"))  # sem duration
    svc = A.AudioService("sem-chave", cliente=cli)

    class _Http:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url):
            return SimpleNamespace(content=_ogg_opus(42.0), headers={"Content-Type": "audio/ogg"},
                                   raise_for_status=lambda: None)

    monkeypatch.setattr(A.httpx, "AsyncClient", _Http)
    texto = asyncio.run(svc.transcribe_audio_from_url("https://wa.invalido/a.ogg",
                                                      company_id=TENANT_B, agent_id="ag-b"))
    assert texto == "quebrou o cano da Porto"
    pedido = cli.audio.transcriptions.pedidos[-1]
    assert (pedido["model"], pedido["language"], pedido["response_format"]) == ("gpt-transcribe", "pt", "json")
    # o prompt: contexto genérico + seguradoras da FONTE CANÔNICA, com teto e sem PII
    assert pedido["prompt"].startswith("Atendimento de corretora de seguros no Brasil.")
    assert all(v["label"] in pedido["prompt"] for v in list(INSURER_REGISTRY.values())[:3])
    assert len(pedido["prompt"]) <= A.LIMITE_DO_PROMPT
    import re as _re
    assert not _re.search(r"\d{4,}", pedido["prompt"]), "nenhum número (telefone/CPF/placa) no prompt"
    # o ledger: 42 s MEDIDOS do OGG → input_tokens=42 (a conta por minuto do UsageService)
    linha = uso.linhas[-1]
    assert (linha["model"], linha["input_tokens"], linha["company_id"]) == ("gpt-transcribe", 42, TENANT_B)
    assert linha["details"]["papel"] == "transcricao" and linha["details"]["duration_seconds"] == 42.0

    # sem duração mensurável (webm) e sem `usage`: NÃO inventa uma linha
    antes = len(uso.linhas)
    asyncio.run(svc.transcribe_audio(base64.b64encode(b"webm sem cabecalho").decode(), company_id=TENANT_A))
    assert len(uso.linhas) == antes
    # `usage.seconds` da resposta vence a medição local
    cli.audio.transcriptions.resposta = SimpleNamespace(
        text="ok", usage=SimpleNamespace(type="duration", seconds=7))
    asyncio.run(svc.transcribe_audio(base64.b64encode(b"x").decode(), company_id=TENANT_A))
    assert uso.linhas[-1]["input_tokens"] == 7

    # CONTROLE — a bancada fixa o whisper-1 (DEPRECATED, baseline): `verbose_json` volta
    wh = A.AudioService("sem-chave", modelo="whisper-1", cliente=_cliente_de_audio())
    asyncio.run(wh.transcribe_audio(base64.b64encode(b"x").decode(), company_id=TENANT_A))
    assert wh.client.audio.transcriptions.pedidos[-1]["response_format"] == "verbose_json"
    assert uso.linhas[-1]["model"] == "whisper-1" and uso.linhas[-1]["input_tokens"] == 4


def test_duracao_local_do_audio():
    from app.services.audio_service import duracao_local_em_segundos as D
    import io
    import wave

    assert abs(D(_ogg_opus(3.5), ".ogg") - 3.5) < 1e-6
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\x00\x00" * 16000)
    assert D(buf.getvalue(), ".wav") == 2.0
    # CONTROLE: formato sem medição e lixo → None (nunca um número inventado)
    assert D(b"qualquer coisa", ".mp3") is None and D(b"OggS", ".ogg") is None


def test_rerank_pela_rota_e_no_ledger(banco, uso):
    from app.services.rerank_service import RerankService

    class _Cohere:
        def __init__(self):
            self.pedidos = []

        def rerank(self, model, query, documents, top_n):
            self.pedidos.append(model)
            return SimpleNamespace(
                results=[SimpleNamespace(index=1, relevance_score=0.9),
                         SimpleNamespace(index=0, relevance_score=0.2)],
                meta=SimpleNamespace(billed_units=SimpleNamespace(search_units=1)))

    cli = _Cohere()
    saida = RerankService(cliente=cli).rerank("cobre?", [{"content": "a"}, {"content": "b"}],
                                             top_k=2, company_id=TENANT_A, agent_id="ag-a")
    assert [d["content"] for d in saida] == ["b", "a"]
    assert cli.pedidos == ["rerank-multilingual-v3.0"]
    linha = uso.linhas[-1]
    assert (linha["service_type"], linha["model"], linha["company_id"]) == (
        "rerank", "rerank-multilingual-v3.0", TENANT_A)
    assert linha["details"]["papel"] == "rerank" and linha["details"]["search_units"] == 1
