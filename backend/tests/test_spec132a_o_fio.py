# -*- coding: utf-8 -*-
"""SPEC-132-A · A4 — O TESTE DO FIO (a costura de A1 · A2 · A3).

    POST /chat/stream (painel, attachments = 1 foto PNG + 1 PDF + 1 xlsx com CPF + 1 áudio, esforco='rapido')
    → `chat_stream` REAL (`app/api/chat.py`) → StreamingResponse imediato → `_gerar` → `_preparar_o_turno`
    → `chat_anexos.preparar` REAL (download DUBLÊ · imagem → JPEG/data URL → `describe_image` REAL com o LLM de visão
      DUBLÊ · PDF → o leitor REAL da 130-B com o modelo dele DUBLÊ · xlsx → o leitor tabular REAL · áudio →
      `AudioService` REAL com a API de transcrição DUBLÊ · tudo pela máscara REAL da 130-B)
    → `incorporar_os_anexos` REAL → `get_or_create_graph` REAL (o grafo nasce sob o esforço do pedido; a fábrica do
      grafo é DUBLÊ e constrói o modelo pelo `LLMFactory` REAL) → `stream_agent_eventos` + `_build_initial_state` REAIS
      (memória/RAG/MCP/marca DUBLÊS, como no guarda da A3) → o LLM do chat DUBLÊ (registra TUDO o que recebeu)
    → deltas → `payload.turn` gravado.

O que este guarda afirma:
  (a) o 1º byte do stream sai ANTES de a leitura dos anexos terminar (o Storage dublê demora);
  (b) `stage.started` com "Lendo …" / "Ouvindo …" / "Olhando …" chegam antes do 1º `assistant.content.delta`;
  (c) o que o LLM do chat recebe (mensagens + prompt do turno) traz o conteúdo de CADA anexo e NENHUM CPF/telefone/
      data de nascimento crus — e o guardrail é passa-tudo de propósito: a máscara que vale é a dos anexos;
  (d) `rapido` → `low` no modelo do papel `chat_principal` (o mesmo modelo); a linha de CONTROLE (`equilibrado`)
      prova que o guarda consegue ver diferença;
  (e) `payload.turn.fases_ms` e `payload.turn.esforco` gravados; a transcrição gravada na pergunta, mascarada;
  (f) um path de OUTRA corretora → `policy.blocked`, nada baixado, nenhum modelo chamado, nada gravado;
  + só áudio: a transcrição é a pergunta;
  + MUTAÇÕES em memória (a árvore compartilhada nunca é escrita): o leitor tabular sem a máscara → (c) VERMELHO;
    o pré-trabalho antes do StreamingResponse → (a) VERMELHO.

⛔ Dados fictícios (CPF sintético com DV válido, DDD 00, corretoras com UUID inventado). Rede FECHADA (só loopback).
Rodar: cd backend && python -m pytest tests/test_spec132a_o_fio.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import importlib
import os
import socket
import sys
import time
import types
import uuid

import pytest

TESTES = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(TESTES)
for _p in (RAIZ, TESTES):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import test_o_chat_fala_tipado as T  # noqa: E402 — o arreio do endpoint (banco dublê, app, SSE)
import test_spec132a_anexos as AX  # noqa: E402 — os arquivos fictícios e as bordas da A2
import test_spec132a_turno_rapido as TR  # noqa: E402 — o ASGI cru que mede o 1º byte e a borda do estado

CHAT_PY = os.path.join(RAIZ, "app", "api", "chat.py")
ANEXOS_PY = os.path.join(RAIZ, "app", "services", "chat_anexos.py")

#: o Storage dublê demora isto por arquivo (em paralelo): a leitura inteira leva ≥ isto
DEMORA_DO_STORAGE = 1.5
TETO_DO_PRIMEIRO_BYTE = 0.5

AGENTE = {"id": T.AGENTE_D, "company_id": T.CO_ALFA_D, "name": "Assistente de Teste", "agent_role": "core",
          "agent_system_prompt": "Você ajuda corretores de seguros.", "is_hyde_enabled": True,
          "config": {"display_name": "Ajudante"}, "widget_config": {}, "updated_at": "t-fio-132a"}

TRANSCRICAO = f"Oi, é sobre o sinistro do carro, meu CPF é {AX.CPF} e o telefone {AX.TELEFONE}."
PERGUNTA = "Resuma o que eu mandei"


# =====================================================================================================================
# as bordas
# =====================================================================================================================
class _LlmDoChat:
    """O LLM do papel `chat_principal`: registra TUDO o que o grafo lhe passaria e responde em dois pedaços."""

    def __init__(self):
        self.chamadas = []

    def texto_recebido(self, i=-1) -> str:
        chamada = self.chamadas[i]
        partes = [str(getattr(m, "content", m)) for m in chamada["mensagens"]]
        partes += [str(v or "") for v in chamada["prompt"].values()]
        return "\n".join(partes)


class _GrafoDoFio:
    """O grafo que `create_agent_graph` (dublê) devolve: guarda o modelo REAL construído pela fábrica e encaminha o
    `astream_events` ao LLM dublê — o que o nó `agent` mandaria ao provedor é exatamente o que fica registrado."""

    def __init__(self, llm_doble, resolvido, llm_real):
        self.llm_doble, self.resolvido, self.llm_real = llm_doble, resolvido, llm_real

    async def astream_events(self, estado, config, version="v1"):
        from langchain_core.messages import AIMessageChunk

        from app.agents.nodes import CHAVE_DO_PROMPT_DO_TURNO

        portador = ((config or {}).get("configurable") or {}).get(CHAVE_DO_PROMPT_DO_TURNO)
        self.llm_doble.chamadas.append({
            "mensagens": list((estado or {}).get("messages") or []),
            "prompt": dict(getattr(portador, "campos", None) or {}),
            "papel": self.resolvido.papel, "modelo": (self.resolvido.provider, self.resolvido.model),
            "esforco_da_rota": self.resolvido.effort,
            "esforco_do_modelo": _esforco_do_modelo_construido(self.llm_real),
        })
        for pedaco in ("Li os quatro ", "anexos."):
            await asyncio.sleep(0)
            yield {"event": "on_chat_model_stream", "name": "modelo", "data": {"chunk": AIMessageChunk(content=pedaco)},
                   "metadata": {"langgraph_node": "agent"}}

    async def aget_state(self, _config):
        return types.SimpleNamespace(values={"messages": []}, created_at=None)


def _esforco_do_modelo_construido(llm):
    """O esforço que o cliente do provedor levaria no pedido (Responses: `reasoning.effort`; Chat: `reasoning_effort`)."""
    if llm is None:
        return None
    raciocinio = getattr(llm, "reasoning", None)
    if isinstance(raciocinio, dict) and raciocinio.get("effort"):
        return raciocinio["effort"]
    for campo in ("reasoning_effort", "effort"):
        valor = getattr(llm, campo, None)
        if isinstance(valor, str) and valor:
            return valor
    thinking = getattr(llm, "thinking", None)
    return str(thinking) if thinking else None


class _Ambiente:
    def __init__(self, monkeypatch):
        self.mp = monkeypatch
        self.storage = AX._Storage()
        self.llm_visao = AX._LlmDaVisao()
        self.api_audio = AX._ApiDeTranscricao(TRANSCRICAO)
        self.llm_chat = _LlmDoChat()
        self.preparar = []          # (company_id, n_anexos)
        self.fim_da_leitura = None  # time.monotonic() quando `preparar` devolveu
        self.grafos = []            # (esforço resolvido, erro ao construir o modelo)

    # -- o Storage, a visão, o áudio, o leitor de PDF e o docling: as bordas da A2, no módulo que o turno vai usar
    def bordas_dos_anexos(self, CA):
        storage, mp = self.storage, self.mp

        async def _baixar_devagar(bucket, path):
            await asyncio.sleep(DEMORA_DO_STORAGE)
            return await storage.baixar(bucket, path)

        mp.setattr(CA, "_baixar_do_storage", _baixar_devagar)
        mp.setattr(CA, "_servico_de_audio", lambda: AX.AU.AudioService("chave-de-teste", modelo="gpt-transcribe",
                                                                         cliente=self.api_audio))
        original = CA.preparar
        amb = self

        async def _preparar_espiao(company_id, anexos, **k):
            amb.preparar.append((company_id, len(anexos or [])))
            try:
                return await original(company_id, anexos, **k)
            finally:
                amb.fim_da_leitura = time.monotonic()

        mp.setattr(CA, "preparar", _preparar_espiao)


@pytest.fixture
def amb(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", AX._sem_rede)
    monkeypatch.setattr(socket.socket, "connect_ex", AX._sem_rede_ex)
    monkeypatch.setenv("ADMIN_API_KEY", T.CHAVE_INTERNA_D)
    from app.services import sanitization_service as S

    monkeypatch.setattr(S, "SanitizationService", AX._SanitizacaoForaDoAr)
    a = _Ambiente(monkeypatch)
    monkeypatch.setattr(AX.VS, "criar_llm_de_visao", lambda **_k: a.llm_visao)
    monkeypatch.setattr(AX.AU.AudioService, "_registrar_uso", lambda *x, **k: None)
    monkeypatch.setattr(AX.AU, "prompt_de_dominio", lambda: "Atendimento de corretora de seguros no Brasil.")
    original = AX.P.ler_anexo_de_seguro

    async def _vazio(*_x, **_k):
        return None

    async def _leitor(file_bytes, file_name, *, company_id, orcamento_s=40.0, leitor_modelo=None):
        return await original(file_bytes, file_name, company_id=company_id, orcamento_s=orcamento_s,
                              leitor_modelo=_vazio)

    monkeypatch.setattr(AX.P, "ler_anexo_de_seguro", _leitor)
    a.bordas_dos_anexos(AX.CA)

    # -- o Model Router lê o snapshot do repositório (a borda é o banco)
    from app.factories import model_policy as MP

    monkeypatch.setattr(MP, "leitor_do_banco", MP._ler_snapshot)
    MP.limpar_cache()

    # -- a fábrica do grafo: o MODELO é construído pela fábrica REAL, sob o esforço do pedido; o grafo é o do fio
    import app.agents as A
    import app.agents.graph as G
    from app.services import langchain_service as LS

    async def _criar_grafo(**k):
        from app.factories.llm_factory import LLMFactory

        resolvido = LLMFactory.resolver_para(k.get("company_config"), k.get("agent_data"))
        llm_real, erro = None, None
        try:
            llm_real = LLMFactory.create_llm(company_config=k.get("company_config"), agent_data=k.get("agent_data"),
                                             api_key="chave-de-teste", company_id=k.get("company_id"),
                                             agent_id=(k.get("agent_data") or {}).get("id"),
                                             modelo_resolvido=resolvido)
        except Exception as exc:  # noqa: BLE001 — registrado; o teste decide
            erro = "%s: %s" % (type(exc).__name__, str(exc)[:120])
        a.grafos.append((resolvido.effort, erro))
        return _GrafoDoFio(a.llm_chat, resolvido, llm_real)

    monkeypatch.setattr(A, "create_agent_graph", _criar_grafo)
    LS._graphs_cache.clear()

    # -- o estado do turno: memória, RAG, MCP, marca (a borda do guarda da A3) e o agente do banco
    TR._instalar_borda_do_estado(monkeypatch, [G], {}, [])

    class _AgentesD:
        def get_agent_by_id(self, _aid):
            return types.SimpleNamespace(model_dump=lambda: dict(AGENTE))

    monkeypatch.setattr(G, "AgentService", _AgentesD)
    chat_mod = importlib.import_module("app.api.chat")
    monkeypatch.setattr(chat_mod, "get_supabase_client", lambda: TR._SupabaseD())
    T.PODE_CONSUMIR_D[:] = [True, "ok"]
    a.chat_mod = chat_mod
    yield a
    LS._graphs_cache.clear()
    MP.limpar_cache()


def _stubs(banco):
    """SÓ o que não é deste fio: o banco (agente, porteira), o Qdrant e o guardrail (Presidio = spaCy, minutos aqui).
    ⚠️ O guardrail é PASSA-TUDO de propósito: se o CPF não chegar cru ao modelo, o mérito é da máscara dos anexos."""
    guard = types.ModuleType("app.agents.guardrails")
    guard.SmithGuardrail = T._GuardrailDubladoD
    billing = types.ModuleType("app.services.billing_gate")
    billing.pode_consumir = T._pode_consumir_d
    qdrant = types.ModuleType("app.services.qdrant_service")
    qdrant.get_qdrant_service = lambda: None
    agentes = types.ModuleType("app.services.agent_service")
    agentes.AgentService = lambda: T._AgentServiceDubladoD(banco)
    return {"app.agents.guardrails": guard, "app.services.billing_gate": billing,
            "app.services.qdrant_service": qdrant, "app.services.agent_service": agentes}


def _banco(sessao, umid, crid):
    banco = T._banco_padrao_d(agentes=[dict(AGENTE)], conversas=[{
        "id": "conv-alfa", "session_id": sessao, "status": "open", "unread_count": 0, "company_id": T.CO_ALFA_D}])
    banco.dados["messages"] = [{"id": umid, "conversation_id": "conv-alfa", "role": "user", "content": PERGUNTA,
                                "payload": {"client_request_id": crid}}]
    return banco


def _anexos(st, empresa=None):
    empresa = empresa or T.CO_ALFA_D
    return [
        AX._anexo(st, empresa, "chat-media", "png", AX._png(), "para-choque.png", "image/png", n=1),
        AX._anexo(st, empresa, "chat-docs", "pdf", AX._pdf(), "ata.pdf", "application/pdf", n=2),
        AX._anexo(st, empresa, "chat-docs", "xlsx", AX._xlsx(), "carteira.xlsx",
                  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", n=3),
        AX._anexo(st, empresa, "chat-docs", "ogg", b"OggS" + b"\0" * 400, "nota de voz.ogg", "audio/ogg", n=4),
    ]


def _corpo(sessao, crid, umid, **extra):
    corpo = {"chatInput": PERGUNTA, "sessionId": sessao, "companyId": T.CO_ALFA_D, "agentId": T.AGENTE_D,
             "client_request_id": crid, "user_message_id": umid}
    corpo.update(extra)
    return corpo


def _turno(amb, corpo, banco, *, chat_mod=None, aquecer=True):
    """Um turno pelo ASGI cru. `aquecer`: um turno de CONTROLE antes (Equilibrado, sem anexo) — paga os imports
    preguiçosos e é a linha de controle do esforço."""
    chat_mod = chat_mod or amb.chat_mod

    async def _rodar():
        with T._TrocaModulosD(_stubs(banco)):
            app = T._montar_app_d(chat_mod, banco)
            controle = None
            if aquecer:
                s2, c2 = str(uuid.uuid4()), str(uuid.uuid4())
                # ⚠️ prazo largo: o 1º modelo construído no processo importa o SDK do provedor (📊 ~50 s nesta
                # máquina, 14/10 — `openai/resources/*` preguiçoso). É o aquecimento, não o turno medido.
                _m, texto_c = await TR._turno_asgi(app, {"chatInput": "oi, tudo bem por aí hoje?", "sessionId": s2,
                                                         "companyId": T.CO_ALFA_D, "agentId": T.AGENTE_D,
                                                         "client_request_id": c2,
                                                         "options": {"esforco": "equilibrado"}}, prazo=240)
                controle = (T._linhas_sse_d(texto_c), list(amb.llm_chat.chamadas))
                amb.llm_chat.chamadas.clear()
                amb.preparar.clear()
                amb.grafos.clear()
                amb.storage.baixados.clear()
                amb.fim_da_leitura = None
            inicio = time.monotonic()
            marcas, texto = await TR._turno_asgi(app, corpo, prazo=240 if not aquecer else 60)
            return marcas, texto, inicio, controle
    return asyncio.run(_rodar())


# =====================================================================================================================
# o guarda — uma função, para o fio verde e para as mutações
# =====================================================================================================================
def _defeitos_do_fio(amb, marcas, texto, inicio, banco, umid) -> list:
    defeitos = []
    eventos = T._linhas_sse_d(texto)
    tipos = [e.get("type") for e in eventos]
    if marcas.get("status") != 200:
        return ["status %s: %s" % (marcas.get("status"), texto[:300])]

    # (a) o 1º byte antes do fim da leitura
    if amb.fim_da_leitura is None:
        defeitos.append("(a) `chat_anexos.preparar` não rodou")
    else:
        fim_rel = amb.fim_da_leitura - inicio
        pb = marcas.get("primeiro_byte")
        if pb is None or pb >= TETO_DO_PRIMEIRO_BYTE or pb >= fim_rel:
            defeitos.append("(a) 1º byte %.3f s · leitura terminou em %.3f s" % (pb or -1, fim_rel))

    # (b) as linhas de atividade antes do 1º delta
    if "assistant.content.delta" not in tipos:
        defeitos.append("(b) nenhum delta: %s" % tipos)
    else:
        primeiro_delta = tipos.index("assistant.content.delta")
        rotulos = [(e.get("payload") or {}).get("label") or "" for e in eventos[:primeiro_delta]
                   if e.get("type") == "stage.started"]
        for comeco in ("Lendo ", "Ouvindo ", "Olhando "):
            if not any(r.startswith(comeco) for r in rotulos):
                defeitos.append("(b) faltou a linha %r antes do 1º delta: %s" % (comeco, rotulos))
    if AX._sem_pii(texto):
        defeitos.append("(b) PII crua no STREAM que vai à tela: %s" % AX._sem_pii(texto))

    # (c) o que o LLM do chat recebeu
    if not amb.llm_chat.chamadas:
        defeitos.append("(c) o LLM do chat não foi chamado")
    else:
        recebido = amb.llm_chat.texto_recebido()
        for marca, rotulo in (("para-choque amassado", "a descrição da foto"), ("fachada", "o texto do PDF"),
                              ('Aba "Clientes"', "a planilha"), ("1.234,56", "o valor da planilha"),
                              ("sinistro do carro", "a transcrição do áudio"), (PERGUNTA, "a pergunta")):
            if marca not in recebido:
                defeitos.append("(c) %s não chegou ao modelo (%r)" % (rotulo, marca))
        crus = AX._sem_pii(recebido)
        if crus:
            defeitos.append("(c) PII CRUA no que o modelo recebeu: %s" % crus)

        # (d) o esforço do pedido no modelo do papel
        ch = amb.llm_chat.chamadas[-1]
        if ch["papel"] != "chat_principal" or ch["esforco_da_rota"] != "low":
            defeitos.append("(d) papel/esforço resolvido: %s/%s" % (ch["papel"], ch["esforco_da_rota"]))
        if ch["esforco_do_modelo"] != "low":
            defeitos.append("(d) o modelo CONSTRUÍDO não leva `low`: %r (erro na fábrica: %s)"
                            % (ch["esforco_do_modelo"], [g[1] for g in amb.grafos]))

    # (e) o turno gravado
    respostas = [m for m in banco.dados.get("messages", []) if m.get("role") == "assistant"]
    turno = ((respostas[-1].get("payload") or {}).get("turn") or {}) if respostas else {}
    fases = turno.get("fases_ms") or {}
    for chave in ("preparo", "anexos", "grafo", "guardrail", "contexto", "primeiro_token"):
        if not isinstance(fases.get(chave), int):
            defeitos.append("(e) fases_ms[%r] ausente: %s" % (chave, fases))
    if turno.get("esforco") != "rapido" or turno.get("esforco_nivel") != "low":
        defeitos.append("(e) esforço gravado: %r/%r" % (turno.get("esforco"), turno.get("esforco_nivel")))
    if (turno.get("anexos") or {}).get("recebidos") != 4:
        defeitos.append("(e) anexos gravados: %s" % turno.get("anexos"))
    pergunta = next((m for m in banco.dados["messages"] if m.get("id") == umid), {})
    transcricao = (pergunta.get("payload") or {}).get("transcricao") or ""
    if "sinistro do carro" not in transcricao:
        defeitos.append("(e) a transcrição não foi gravada na pergunta: %r" % transcricao[:80])
    if AX._sem_pii(transcricao) or AX._sem_pii(repr(turno)):
        defeitos.append("(e) PII crua gravada no banco")
    return defeitos


# =====================================================================================================================
# o fio
# =====================================================================================================================
def test_o_fio_inteiro_quatro_anexos_rapido(amb):
    sessao, crid, umid = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    banco = _banco(sessao, umid, crid)
    corpo = _corpo(sessao, crid, umid, attachments=_anexos(amb.storage), options={"esforco": "rapido"})
    marcas, texto, inicio, controle = _turno(amb, corpo, banco)

    print("📊 1º byte %.3f s · leitura dos anexos terminou em %.3f s · fim %.3f s (Storage dorme %.1f s)"
          % (marcas.get("primeiro_byte") or -1, (amb.fim_da_leitura or inicio) - inicio, marcas.get("fim") or -1,
             DEMORA_DO_STORAGE))
    defeitos = _defeitos_do_fio(amb, marcas, texto, inicio, banco, umid)
    assert defeitos == [], "\n".join(defeitos)

    # o que foi baixado: os 4, todos desta corretora, e o provedor de visão só viu data URL
    assert sorted(b for b, _ in amb.storage.baixados) == ["chat-docs"] * 3 + ["chat-media"]
    assert all(p.startswith(T.CO_ALFA_D + "/") for _, p in amb.storage.baixados)
    urls = [p["image_url"]["url"] for m in amb.llm_visao.recebido[-1]
            for p in (m.content if isinstance(m.content, list) else []) if isinstance(p, dict)
            and p.get("type") == "image_url"]
    assert urls and all(u.startswith("data:image/jpeg;base64,") for u in urls), [u[:40] for u in urls]
    assert amb.preparar == [(T.CO_ALFA_D, 4)]

    # 🔴 a linha de CONTROLE: o mesmo motor, Equilibrado → o esforço da ROTA (≠ low) — o guarda (d) vê diferença
    eventos_c, chamadas_c = controle
    assert chamadas_c and chamadas_c[-1]["papel"] == "chat_principal"
    assert chamadas_c[-1]["esforco_da_rota"] not in (None, "low"), chamadas_c[-1]
    assert chamadas_c[-1]["modelo"] == amb.llm_chat.chamadas[-1]["modelo"], "o esforço trocou de MODELO"
    print("📊 esforço no modelo: Rápido=%s · Equilibrado (controle)=%s · modelo %s"
          % (amb.llm_chat.chamadas[-1]["esforco_do_modelo"], chamadas_c[-1]["esforco_do_modelo"],
             "/".join(amb.llm_chat.chamadas[-1]["modelo"])))


def test_f_path_de_outra_corretora_e_barrado_e_nada_e_lido(amb):
    sessao, crid, umid = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    banco = _banco(sessao, umid, crid)
    meus = _anexos(amb.storage)
    alheio = AX._anexo(amb.storage, T.CO_BETA_D, "chat-docs", "pdf", AX._pdf(), "da-outra.pdf", "application/pdf", n=9)
    corpo = _corpo(sessao, crid, umid, attachments=meus[:2] + [alheio], options={"esforco": "rapido"})
    marcas, texto, _inicio, _c = _turno(amb, corpo, banco, aquecer=False)
    tipos = [e.get("type") for e in T._linhas_sse_d(texto)]
    assert marcas.get("status") == 200 and "policy.blocked" in tipos, tipos
    assert "assistant.content.delta" not in tipos, tipos
    assert amb.storage.baixados == [] and amb.preparar == [], (amb.storage.baixados, amb.preparar)
    assert amb.llm_chat.chamadas == [] and amb.llm_visao.recebido == [] and amb.api_audio.recebidos == []
    assert [m for m in banco.dados["messages"] if m.get("role") == "assistant"] == []
    assert marcas["fim"] < DEMORA_DO_STORAGE, "algo caro rodou antes da recusa: %s" % marcas
    # CONTROLE: sem o alheio, os mesmos dois anexos DESTA corretora são lidos
    crid2 = str(uuid.uuid4())
    corpo2 = _corpo(sessao, crid2, umid, attachments=meus[:2], options={"esforco": "rapido"})
    _m2, texto2, _i2, _c2 = _turno(amb, corpo2, banco, aquecer=False)
    assert "policy.blocked" not in texto2 and amb.preparar == [(T.CO_ALFA_D, 2)], (texto2[:300], amb.preparar)


def test_so_audio_a_transcricao_mascarada_e_a_pergunta(amb):
    sessao, crid, umid = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    banco = _banco(sessao, umid, crid)
    audio = _anexos(amb.storage)[3]
    corpo = _corpo(sessao, crid, umid, attachments=[audio])
    corpo["chatInput"] = ""                       # o que o BFF repassa quando o corretor só gravou
    marcas, texto, _inicio, _c = _turno(amb, corpo, banco, aquecer=False)
    assert marcas.get("status") == 200, texto[:300]
    mensagens = amb.llm_chat.chamadas[-1]["mensagens"]
    ultima = str(getattr(mensagens[-1], "content", mensagens[-1]))
    assert ultima.startswith("Oi, é sobre o sinistro do carro"), ultima[:120]
    assert "[CPF]" in ultima and AX._sem_pii(ultima) == [], ultima
    rotulos = [(e.get("payload") or {}).get("label") for e in T._linhas_sse_d(texto) if e.get("type") == "stage.started"]
    assert rotulos[0] == "Ouvindo o áudio…", rotulos
    gravada = next(m for m in banco.dados["messages"] if m["id"] == umid)["payload"]
    assert gravada.get("transcricao", "").startswith("Oi, é sobre") and AX._sem_pii(gravada["transcricao"]) == []


# =====================================================================================================================
# as mutações — em memória: um módulo compilado à parte; a árvore compartilhada nunca é escrita
# =====================================================================================================================
def test_mutacao_leitor_tabular_sem_mascara_fica_vermelho(amb, monkeypatch):
    mutado = TR._modulo_mutado(
        ANEXOS_PY, "app.services._chat_anexos_mutado_fio",
        "        corpo = await _texto_mascarado(bruto)\n        if not corpo:\n"
        "            r.aviso = f\"Não consegui ler a planilha",
        "        corpo = bruto\n        if not corpo:\n"
        "            r.aviso = f\"Não consegui ler a planilha")
    amb.bordas_dos_anexos(mutado)
    monkeypatch.setitem(sys.modules, "app.services.chat_anexos", mutado)
    sessao, crid, umid = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    banco = _banco(sessao, umid, crid)
    corpo = _corpo(sessao, crid, umid, attachments=_anexos(amb.storage), options={"esforco": "rapido"})
    marcas, texto, inicio, _c = _turno(amb, corpo, banco)
    defeitos = _defeitos_do_fio(amb, marcas, texto, inicio, banco, umid)
    print("📊 MUTADO (planilha sem máscara): %s" % defeitos)
    assert any(d.startswith("(c) PII CRUA") for d in defeitos), "a mutação passou — o guarda (c) é carimbo: %s" % defeitos


def test_mutacao_pre_trabalho_antes_do_stream_fica_vermelho(amb):
    mutado = TR._modulo_mutado(
        CHAT_PY, "app.api._chat_mutado_fio_pre",
        "    task = asyncio.create_task(_gerar(fila))",
        "    await _preparar_o_turno(lambda *a, **k: None, {}, {})\n"
        "    task = asyncio.create_task(_gerar(fila))")
    amb.mp.setattr(mutado, "get_supabase_client", lambda: TR._SupabaseD())
    sessao, crid, umid = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    banco = _banco(sessao, umid, crid)
    corpo = _corpo(sessao, crid, umid, attachments=_anexos(amb.storage), options={"esforco": "rapido"})
    marcas, texto, inicio, _c = _turno(amb, corpo, banco, chat_mod=mutado)
    defeitos = _defeitos_do_fio(amb, marcas, texto, inicio, banco, umid)
    print("📊 MUTADO (pré-trabalho antes do stream): 1º byte %.3f s · %s" % (marcas.get("primeiro_byte") or -1, defeitos))
    assert any(d.startswith("(a)") for d in defeitos), "a mutação passou — o guarda (a) é carimbo: %s" % defeitos
