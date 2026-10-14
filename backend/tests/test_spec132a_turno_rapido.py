"""SPEC-132-A · fatia A3 — O TURNO RÁPIDO.

O que este guarda afirma, com o MOTOR real (dublê só na borda: banco, Storage, modelo,
o leitor de anexos da A2):

  (a) no PAINEL o 1º byte do stream sai ANTES de `chat_anexos.preparar` terminar
      (dublê lento de 2 s → 1º byte < 0,5 s) — e a MUTAÇÃO "o pré-trabalho volta para
      antes do StreamingResponse" fica VERMELHA (1º byte ≥ 1,5 s);
  (b) `esforco='rapido'` → `low` no modelo de `chat_principal`, `maximo` → `high`,
      `equilibrado` → o da rota, o MESMO modelo e a MESMA reserva; `turbo` → ignorado
      (mutações: aceitar `turbo` no Model Router OU no pedido → VERMELHO);
  (c) Rápido não chama HyDE; saudação curta no Equilibrado não chama HyDE; quem não é o
      chat do corretor (atendimento, widget) chama como antes;
  (d) o estado que `_build_initial_state` monta com as leituras EM PARALELO é IDÊNTICO
      ao da versão sequencial (a da base `76b1072`) — com tempos embaralhados — e é mais
      rápido; a mutação que perde uma leitura fica VERMELHA;
  (e) conversa de OUTRA corretora e anexo no prefixo de OUTRA corretora são recusados
      ANTES do stream (duas corretoras), sem ler anexo e sem gravar;
  (f) `messages.payload.turn.fases_ms`, `esforco`, `ttft_gerar_ms` gravados.

⛔ Mutação por CÓPIA EM MEMÓRIA: o arquivo mutado é compilado num módulo à parte; a
árvore compartilhada nunca é escrita (lição da SPEC-121).
"""
from __future__ import annotations

import ast
import asyncio
import importlib
import io
import json
import os
import subprocess
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

CHAT_PY = os.path.join(RAIZ, "app", "api", "chat.py")
GRAFO_PY = os.path.join(RAIZ, "app", "agents", "graph.py")
POLITICA_PY = os.path.join(RAIZ, "app", "factories", "model_policy.py")
#: a base auditada ANTES da fatia A3 — a versão SEQUENCIAL de `_build_initial_state`.
COMMIT_DA_BASE = "76b1072"

DEMORA_DOS_ANEXOS = 2.0
TETO_DO_PRIMEIRO_BYTE = 0.5


# =====================================================================================
# A borda: módulos dublados por cima dos dublês do guarda tipado (o mesmo arreio)
# =====================================================================================
def _tipado():
    import test_o_chat_fala_tipado as T

    return T


class _ResultadoDosAnexosD:
    def __init__(self, **campos):
        self.texto = campos.get("texto", [])
        self.imagens = campos.get("imagens", [])
        self.descricoes = campos.get("descricoes", [])
        self.transcricoes = campos.get("transcricoes", [])
        self.avisos = campos.get("avisos", [])
        self.lidos = campos.get("lidos", [])


class _Borda:
    """O que cada turno chamou na borda — por turno, nunca global entre testes."""

    def __init__(self, demora=DEMORA_DOS_ANEXOS, resultado=None):
        self.demora = demora
        self.resultado = resultado or _ResultadoDosAnexosD(
            texto=["[DOCUMENTO ANEXADO: apolice.pdf]\nSegurado: [CPF]\n[FIM DO DOCUMENTO]"],
            lidos=["apolice.pdf"])
        self.preparar = []          # (company_id, anexos)
        self.preparar_terminou = None
        self.grafos = []            # kwargs de get_or_create_graph
        self.motor = []             # kwargs de stream_agent_eventos

    def stubs(self, banco):
        T = _tipado()
        stubs = T._montar_stubs_d(banco)
        borda = self

        anexos_mod = types.ModuleType("app.services.chat_anexos")

        async def preparar(company_id, anexos, *, ao_progredir=None):
            borda.preparar.append((company_id, list(anexos)))
            for anexo in anexos:
                if ao_progredir is not None:
                    r = ao_progredir(anexo)
                    if asyncio.isfuture(r) or asyncio.iscoroutine(r):
                        await r
            await asyncio.sleep(borda.demora)
            borda.preparar_terminou = time.monotonic()
            return borda.resultado

        anexos_mod.preparar = preparar
        stubs["app.services.chat_anexos"] = anexos_mod

        async def _grafo(**k):
            borda.grafos.append(dict(k))
            return object()

        stubs["app.services.langchain_service"].get_or_create_graph = _grafo

        graph_mod = stubs["app.agents.graph"]

        async def _motor(graph, **k):
            borda.motor.append(dict(k))
            if k.get("fases") is not None:
                k["fases"]["contexto"] = 7
            async for ev in T._stream_agent_eventos_dublado(graph, **k):
                yield ev

        graph_mod.stream_agent_eventos = _motor
        stubs["app.services.vision_service"].nome_do_anexo_para_o_modelo = (
            lambda nome, padrao="o arquivo": str(nome or padrao))

        # o esforço que o modelo usaria — lido da MESMA ContextVar do Model Router
        fabrica = types.ModuleType("app.factories.llm_factory")

        class _LLMFactoryD:
            @staticmethod
            def resolver_para(*_a, **_k):
                from app.factories import model_policy as MP

                return types.SimpleNamespace(effort=MP._esforco_do_pedido.get() or "medium")

        fabrica.LLMFactory = _LLMFactoryD
        stubs["app.factories.llm_factory"] = fabrica
        return stubs


def _corpo(sessao=None, crid=None, **extra):
    T = _tipado()
    corpo = {"chatInput": "o que cobre esta apólice?", "sessionId": sessao or str(uuid.uuid4()),
             "companyId": T.CO_ALFA_D, "agentId": T.AGENTE_D,
             "client_request_id": crid or str(uuid.uuid4())}
    corpo.update(extra)
    return corpo


def _anexo(nome="apolice.pdf", mime="application/pdf", company=None, bytes_=1234):
    T = _tipado()
    return {"bucket": "chat-docs", "path": "%s/chat/%s" % (company or T.CO_ALFA_D, nome),
            "nome": nome, "mime": mime, "bytes": bytes_}


async def _turno_asgi(app, corpo, *, chave="__padrao__", prazo=30.0):
    """Um POST no ASGI CRU: mede quando os cabeçalhos e o 1º byte SAEM do app.

    ⚠️ Não é `httpx.ASGITransport`: ele junta o corpo inteiro antes de devolver, e o
    1º byte pareceria chegar no fim — exatamente o que este guarda precisa medir.
    """
    T = _tipado()
    if chave == "__padrao__":
        chave = T.CHAVE_INTERNA_D
    corpo_b = json.dumps(corpo).encode("utf-8")
    marcas, pedacos = {}, []
    entregue = False
    fim = asyncio.Event()
    t0 = time.monotonic()

    async def receive():
        nonlocal entregue
        if not entregue:
            entregue = True
            return {"type": "http.request", "body": corpo_b, "more_body": False}
        await fim.wait()
        return {"type": "http.disconnect"}

    async def send(msg):
        agora = time.monotonic() - t0
        if msg["type"] == "http.response.start":
            marcas.setdefault("cabecalhos", agora)
            marcas["status"] = msg.get("status")
        elif msg["type"] == "http.response.body":
            if msg.get("body"):
                marcas.setdefault("primeiro_byte", agora)
                pedacos.append(msg["body"])
            if not msg.get("more_body"):
                marcas["fim"] = agora
                fim.set()

    cabecalhos = [(b"host", b"t"), (b"content-type", b"application/json"),
                  (b"content-length", str(len(corpo_b)).encode())]
    if chave:
        cabecalhos.append((b"x-internal-key", chave.encode()))
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
             "method": "POST", "scheme": "http", "path": "/chat/stream",
             "raw_path": b"/chat/stream", "query_string": b"", "root_path": "",
             "headers": cabecalhos, "client": ("127.0.0.1", 5000), "server": ("t", 80)}
    await asyncio.wait_for(app(scope, receive, send), prazo)
    return marcas, b"".join(pedacos).decode("utf-8", errors="replace")


def _modulo_mutado(caminho, nome, de, para, *, trocar=None):
    """Compila uma CÓPIA mutada do arquivo num módulo à parte. A árvore não é tocada.

    `trocar` = {nome_em_sys_modules: módulo} valendo SÓ durante a compilação.
    """
    fonte = io.open(caminho, encoding="utf-8").read()
    assert de in fonte, "a âncora da mutação sumiu de %s: %r" % (os.path.basename(caminho), de[:60])
    mod = types.ModuleType(nome)
    mod.__file__ = caminho
    mod.__package__ = nome.rsplit(".", 1)[0]
    antes = {k: sys.modules.get(k) for k in (trocar or {})}
    sys.modules.update(trocar or {})
    # ⚠️ registrado durante a compilação: `dataclasses`/pydantic leem o módulo da
    # classe em `sys.modules[cls.__module__]`.
    sys.modules[nome] = mod
    try:
        exec(compile(fonte.replace(de, para, 1), caminho, "exec"), mod.__dict__)
    finally:
        sys.modules.pop(nome, None)
        for k, v in antes.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
    return mod


@pytest.fixture(autouse=True)
def _cache_do_model_router_limpo():
    """O que este arquivo põe no cache do Model Router (o snapshot) não fica para o vizinho."""
    yield
    from app.factories import model_policy as MP

    MP.limpar_cache()


@pytest.fixture
def ambiente(monkeypatch):
    T = _tipado()
    monkeypatch.setenv("ADMIN_API_KEY", T.CHAVE_INTERNA_D)
    chat_mod = importlib.import_module("app.api.chat")
    T.PODE_CONSUMIR_D[:] = [True, "ok"]
    T.EVENTOS_DO_GRAFO_D[:] = [T._delta_d("Oi"), T._delta_d(" tudo bem")]
    return T, chat_mod


def _rodar_turno(T, chat_mod, banco, borda, corpo, *, chave="__padrao__"):
    async def _rodar():
        with T._TrocaModulosD(borda.stubs(banco)):
            app = T._montar_app_d(chat_mod, banco)
            # aquece imports preguiçosos do caminho — mede-se o turno, não o import
            await _turno_asgi(app, _corpo(), chave=chave)
            borda.preparar.clear(), borda.grafos.clear(), borda.motor.clear()
            banco.dados["messages"] = [m for m in banco.dados.get("messages", [])
                                       if m.get("role") == "user"]
            inicio = time.monotonic()
            marcas, texto = await _turno_asgi(app, corpo, chave=chave)
            return marcas, texto, inicio
    return asyncio.run(_rodar())


# =====================================================================================
# (a) o 1º byte sai antes do pré-trabalho caro — e a mutação fica VERMELHA
# =====================================================================================
def _guarda_primeiro_byte(marcas) -> bool:
    return marcas.get("primeiro_byte") is not None and marcas["primeiro_byte"] < TETO_DO_PRIMEIRO_BYTE


def test_a_o_primeiro_byte_sai_antes_da_leitura_do_anexo(ambiente):
    T, chat_mod = ambiente
    banco = T._banco_padrao_d(conversas=[])
    borda = _Borda()
    corpo = _corpo(attachments=[_anexo()])
    marcas, texto, inicio = _rodar_turno(T, chat_mod, banco, borda, corpo)

    print("📊 cabeçalhos %.3f s · 1º byte %.3f s · fim %.3f s (preparar dorme %.1f s)"
          % (marcas.get("cabecalhos"), marcas.get("primeiro_byte"), marcas.get("fim"),
             DEMORA_DOS_ANEXOS))
    assert marcas.get("status") == 200
    assert _guarda_primeiro_byte(marcas), marcas
    assert marcas["fim"] >= DEMORA_DOS_ANEXOS * 0.9, "o turno terminou sem esperar o anexo: %s" % marcas
    assert borda.preparar and borda.preparar[0][0] == T.CO_ALFA_D

    eventos = T._linhas_sse_d(texto)
    tipos = [e.get("type") for e in eventos]
    assert tipos[0] == "turn.accepted" and tipos[-2:] == ["turn.completed", "[DONE]"], tipos
    rotulos = [(e.get("payload") or {}).get("label") for e in eventos if e.get("type") == "stage.started"]
    assert rotulos[0] == "Lendo apolice.pdf…", rotulos
    assert "Pensando…" in rotulos, rotulos
    assert tipos.index("stage.started") < tipos.index("assistant.content.delta"), tipos
    # o texto lido entrou no turno, no mesmo lugar do documento antigo
    msg = borda.motor[0]["user_message"]
    assert msg.startswith("o que cobre esta apólice?") and "[DOCUMENTO ANEXADO: apolice.pdf]" in msg


def test_a_mutacao_pre_trabalho_antes_do_stream_fica_vermelha(ambiente):
    T, _ = ambiente
    mutado = _modulo_mutado(
        CHAT_PY, "app.api._chat_mutado_132a_pre",
        "    task = asyncio.create_task(_gerar(fila))",
        "    await _preparar_o_turno(lambda *a, **k: None, {}, {})\n"
        "    task = asyncio.create_task(_gerar(fila))")
    banco = T._banco_padrao_d(conversas=[])
    borda = _Borda()
    marcas, _texto, _ = _rodar_turno(T, mutado, banco, borda, _corpo(attachments=[_anexo()]))
    print("📊 MUTADO: 1º byte %.3f s" % marcas.get("primeiro_byte"))
    assert not _guarda_primeiro_byte(marcas), "a mutação passou — o guarda (a) é carimbo: %s" % marcas
    assert marcas["primeiro_byte"] >= DEMORA_DOS_ANEXOS * 0.75


def test_a_so_audio_a_transcricao_e_a_pergunta_e_fica_na_mensagem(ambiente):
    T, chat_mod = ambiente
    sessao, crid, umid = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    banco = T._banco_padrao_d(conversas=[{"id": "conv-alfa", "session_id": sessao, "status": "open",
                                          "unread_count": 0, "company_id": T.CO_ALFA_D}])
    banco.dados["messages"] = [{"id": umid, "conversation_id": "conv-alfa", "role": "user",
                                "content": "", "payload": {"client_request_id": crid}}]
    borda = _Borda(demora=0.05, resultado=_ResultadoDosAnexosD(
        transcricoes=["qual o prazo da vistoria do carro"], lidos=["audio.m4a"]))
    corpo = _corpo(sessao=sessao, crid=crid, user_message_id=umid,
                   attachments=[_anexo("audio.m4a", "audio/mp4")])
    corpo.pop("chatInput")
    marcas, texto, _ = _rodar_turno(T, chat_mod, banco, borda, corpo)
    assert marcas.get("status") == 200, texto[:300]
    assert borda.motor[-1]["user_message"] == "qual o prazo da vistoria do carro"
    rotulos = [(e.get("payload") or {}).get("label") for e in T._linhas_sse_d(texto)
               if e.get("type") == "stage.started"]
    assert rotulos[0] == "Ouvindo o áudio…", rotulos
    pergunta = next(m for m in banco.dados["messages"] if m["id"] == umid)
    assert pergunta["payload"].get("transcricao") == "qual o prazo da vistoria do carro"
    assert pergunta["payload"].get("client_request_id") == crid      # o resto do payload fica


def test_a_sem_leitor_o_anexo_vira_aviso_e_o_turno_segue(ambiente):
    T, chat_mod = ambiente
    banco = T._banco_padrao_d(conversas=[])
    borda = _Borda(demora=0.01)

    async def _quebra(*_a, **_k):
        raise RuntimeError("o leitor caiu")

    stubs_originais = borda.stubs

    def _stubs(b):
        s = stubs_originais(b)
        s["app.services.chat_anexos"].preparar = _quebra
        return s

    borda.stubs = _stubs
    marcas, texto, _ = _rodar_turno(T, chat_mod, banco, borda, _corpo(attachments=[_anexo()]))
    assert marcas.get("status") == 200
    assert "[AVISO INTERNO: não consegui ler os arquivos anexados agora" in borda.motor[-1]["user_message"]
    assert "o leitor caiu" not in texto


# =====================================================================================
# (b) o esforço por pedido — o MESMO modelo e a MESMA reserva do papel
# =====================================================================================
def _politica_com_snapshot(monkeypatch, MP=None):
    if MP is None:
        from app.factories import model_policy as MP
    monkeypatch.setattr(MP, "leitor_do_banco", MP._ler_snapshot)
    MP.limpar_cache()
    return MP


def _guarda_turbo(MP, opcoes_validas) -> list:
    """Os defeitos que `turbo` causaria. Lista vazia = o guarda está verde."""
    defeitos = []
    if MP.nivel_da_escolha("turbo") is not None:
        defeitos.append("o Model Router traduziu 'turbo' em %r" % MP.nivel_da_escolha("turbo"))
    if "esforco" in (opcoes_validas({"esforco": "turbo"}) or {}):
        defeitos.append("o pedido aceitou esforco='turbo'")
    rota = MP.resolver("chat_principal")
    with MP.esforco_do_pedido(MP.nivel_da_escolha("turbo")):
        sob_turbo = MP.resolver("chat_principal")
    if sob_turbo.effort != rota.effort:
        defeitos.append("'turbo' mudou o esforço: %r → %r" % (rota.effort, sob_turbo.effort))
    return defeitos


def test_b_rapido_low_maximo_high_mesmo_modelo_mesma_reserva(monkeypatch):
    MP = _politica_com_snapshot(monkeypatch)
    rota = MP.resolver("chat_principal")
    with MP.esforco_do_pedido(MP.nivel_da_escolha("rapido")):
        rapido = MP.resolver("chat_principal")
        atendimento_no_rapido = MP.resolver("atendimento")
    with MP.esforco_do_pedido(MP.nivel_da_escolha("maximo")):
        maximo = MP.resolver("chat_principal")
    with MP.esforco_do_pedido(MP.nivel_da_escolha("equilibrado")):
        equilibrado = MP.resolver("chat_principal")
    print("📊 rota %s/%s esforço=%s · rápido=%s · máximo=%s · equilibrado=%s"
          % (rota.provider, rota.model, rota.effort, rapido.effort, maximo.effort, equilibrado.effort))
    assert (rapido.effort, maximo.effort) == ("low", "high")
    assert equilibrado.effort == rota.effort            # ⛔ a palavra não é fixada no código
    for r in (rapido, maximo, equilibrado):
        assert (r.provider, r.model) == (rota.provider, rota.model)
        assert (r.reserva and r.reserva.model) == (rota.reserva and rota.reserva.model)
    # ⛔ só o papel do chat: o atendimento ao segurado não muda sob o Rápido
    assert atendimento_no_rapido == MP.resolver("atendimento")
    # e a variável não vaza para fora do bloco
    assert MP.resolver("chat_principal").effort == rota.effort


def test_b_turbo_e_ignorado_e_as_mutacoes_ficam_vermelhas(monkeypatch):
    from app.api.chat import opcoes_validas

    MP = _politica_com_snapshot(monkeypatch)
    assert _guarda_turbo(MP, opcoes_validas) == []

    # MUTAÇÃO 1 — o Model Router passa a aceitar `turbo`
    MP_mutado = _modulo_mutado(POLITICA_PY, "app.factories._politica_mutada_132a",
                               '    "maximo": "high",\n', '    "maximo": "high",\n    "turbo": "xhigh",\n')
    _politica_com_snapshot(monkeypatch, MP_mutado)
    assert _guarda_turbo(MP_mutado, opcoes_validas), "aceitar 'turbo' no Model Router passou — carimbo"

    # MUTAÇÃO 2 — o PEDIDO passa a aceitar qualquer esforço
    chat_mutado = _modulo_mutado(CHAT_PY, "app.api._chat_mutado_132a_turbo",
                                 "and valor.strip().lower() in ESCOLHAS_DE_ESFORCO):",
                                 "and True):")
    assert _guarda_turbo(MP, chat_mutado.opcoes_validas), "aceitar 'turbo' no pedido passou — carimbo"


def test_b_opcoes_novas_nao_viram_422(ambiente):
    T, chat_mod = ambiente
    banco = T._banco_padrao_d(conversas=[])
    borda = _Borda(demora=0)
    corpo = _corpo(options={"esforco": "turbo", "web_search": True, "tema": "escuro", "x": 1})
    marcas, texto, _ = _rodar_turno(T, chat_mod, banco, borda, corpo)
    assert marcas.get("status") == 200, texto[:300]
    assert borda.motor[-1]["options"] == {"web_search": True}
    assert borda.motor[-1]["esforco"] == "equilibrado"
    assert "esforco_do_pedido" not in borda.grafos[-1]        # equilibrado = o grafo da rota


def test_b_o_rapido_chega_ao_grafo_e_ao_turno(ambiente):
    T, chat_mod = ambiente
    for escolha, nivel in (("rapido", "low"), ("maximo", "high")):
        banco = T._banco_padrao_d(conversas=[])
        borda = _Borda(demora=0)
        marcas, _t, _ = _rodar_turno(T, chat_mod, banco, borda, _corpo(options={"esforco": escolha}))
        assert marcas.get("status") == 200
        assert borda.grafos[-1].get("esforco_do_pedido") == nivel
        assert borda.motor[-1]["esforco"] == escolha
        turno = banco.dados["messages"][-1]["payload"]["turn"]
        assert (turno.get("esforco"), turno.get("esforco_nivel")) == (escolha, nivel), turno


def test_b_o_grafo_e_construido_com_o_esforco_do_pedido(monkeypatch):
    """`get_or_create_graph` REAL: a chave do cache leva o esforço e o grafo nasce sob ele."""
    MP = _politica_com_snapshot(monkeypatch)
    import app.agents as A
    from app.factories.llm_factory import LLMFactory
    from app.services import langchain_service as LS

    vistos = []

    async def _criar(**k):
        vistos.append(LLMFactory.resolver_para(k["agent_data"], k["agent_data"]).effort)
        return object()

    monkeypatch.setattr(A, "create_agent_graph", _criar)
    LS._graphs_cache.clear()
    agente = {"id": "ag-1", "agent_role": "core", "updated_at": "t0"}

    async def _rodar():
        g_low = await LS.get_or_create_graph("co-1", "ag-1", agente, "k", None, None,
                                             esforco_do_pedido="low")
        g_rota = await LS.get_or_create_graph("co-1", "ag-1", agente, "k", None, None)
        g_low2 = await LS.get_or_create_graph("co-1", "ag-1", agente, "k", None, None,
                                              esforco_do_pedido="low")
        return g_low, g_rota, g_low2

    g_low, g_rota, g_low2 = asyncio.run(_rodar())
    chaves = sorted(LS._graphs_cache.keys())
    LS._graphs_cache.clear()
    rota = MP.resolver("chat_principal").effort
    assert vistos == ["low", rota], vistos
    assert g_low is g_low2 and g_low is not g_rota
    assert any("/low/" in c for c in chaves) and any("/%s/" % rota in c for c in chaves), chaves


# =====================================================================================
# (c) o HyDE — e (d) o estado montado em paralelo é o MESMO da versão sequencial
# =====================================================================================
AGENTE_CORE = {"id": "ag-core", "name": "Assistente de Teste", "agent_role": "core",
               "agent_system_prompt": "Você ajuda corretores. Use {consulta_cep} e {mcp_docs_buscar}.",
               "is_hyde_enabled": True, "config": {"display_name": "Ajudante"}}


class _ConsultaD:
    def __init__(self, banco, tabela):
        self.banco, self.tabela, self.filtros = banco, tabela, []

    def select(self, *_a, **_k):
        return self

    def eq(self, campo, valor):
        self.filtros.append((campo, valor))
        return self

    def in_(self, campo, valores):
        self.filtros.append((campo, list(valores)))
        return self

    def limit(self, _n):
        return self

    def execute(self):
        time.sleep(self.banco.demoras.get(self.tabela, 0))
        linhas = []
        for linha in self.banco.dados.get(self.tabela, []):
            ok = True
            for campo, valor in self.filtros:
                atual = linha.get(campo)
                ok = ok and ((atual in valor) if isinstance(valor, list) else str(atual) == str(valor))
            if ok:
                linhas.append(dict(linha))
        return types.SimpleNamespace(data=linhas)


class _SupabaseD:
    def __init__(self, demoras=None):
        self.demoras = demoras or {}
        self.dados = {
            "agent_http_tools": [{"name": "consulta_cep", "description": "consulta CEP", "method": "GET",
                                  "parameters": {}, "agent_id": "ag-core", "is_active": True}],
            "agent_delegations": [{"subagent_id": "sub-1", "task_description": "cotar auto",
                                   "orchestrator_id": "ag-core", "is_active": True}],
            "agents": [{"id": "sub-1", "name": "Cotador"}],
            "companies": [{"id": "co-1", "company_name": "Corretora Exemplo", "legal_name": "Exemplo Ltda"}],
        }

    def table(self, nome):
        return _ConsultaD(self, nome)


def _instalar_borda_do_estado(monkeypatch, modulos, demoras, buscas):
    import app.core.prompts as PR
    import app.services.brand.capture as BC
    import app.services.mcp_gateway_service as MCP
    import app.services.search_service as SS

    monkeypatch.setenv("CONTEXT_ASSEMBLY_MODE", "off")
    monkeypatch.setattr(PR, "data_e_hora_agora", lambda: "AGORA: 14/10/2026 10:00")

    class _AgentesD:
        def get_agent_by_id(self, _aid):
            return types.SimpleNamespace(model_dump=lambda: dict(AGENTE_CORE))

    class _MemoriaD:
        def __init__(self, _cli):
            pass

        async def build_memory_context_async(self, **_k):
            await asyncio.sleep(demoras.get("memoria", 0))
            return "o corretor prefere respostas curtas"

    class _GatewayD:
        async def get_agent_mcp_tools(self, _aid):
            await asyncio.sleep(demoras.get("mcp", 0))
            return [{"variable_name": "mcp_docs_buscar", "description": "busca documentos",
                     "input_schema": {}}]

    class _MarcaD:
        def __init__(self, _cli):
            pass

        def render_blocos_do_prompt(self, _cid):
            time.sleep(demoras.get("marca", 0))
            return "FATOS DA CORRETORA: atende auto", "JEITO: direto"

    class _BuscaD:
        def smart_search(self, company_id, query, agent_id, is_hyde, include_global):
            time.sleep(demoras.get("rag", 0))
            buscas.append({"is_hyde": is_hyde, "query": query, "global": include_global})
            return {"found": True, "content": "Trecho 1: franquia reduzida.\n\nTrecho 2: vidros.",
                    "chunks": [{"id": 1}, {"id": 2}], "search_time_ms": 12, "strategy": "hybrid",
                    "max_score": 0.71}

    for mod in modulos:
        monkeypatch.setattr(mod, "AgentService", _AgentesD)
        monkeypatch.setattr(mod, "MemoryService", _MemoriaD)
    monkeypatch.setattr(MCP, "get_mcp_gateway", lambda: _GatewayD())
    monkeypatch.setattr(BC, "BrandCaptureService", _MarcaD)
    monkeypatch.setattr(SS, "get_search_service", lambda: _BuscaD())


def _grafo_da_base():
    """O `graph.py` da base (sequencial), compilado à parte — ou None sem git/commit."""
    try:
        fonte = subprocess.run(["git", "show", "%s:backend/app/agents/graph.py" % COMMIT_DA_BASE],
                               cwd=RAIZ, capture_output=True, timeout=60, check=True).stdout.decode("utf-8")
    except Exception:  # noqa: BLE001
        return None
    nome = "app.agents._grafo_da_base_132a"
    mod = types.ModuleType(nome)
    mod.__file__ = GRAFO_PY
    mod.__package__ = "app.agents"
    sys.modules[nome] = mod
    try:
        exec(compile(fonte, GRAFO_PY, "exec"), mod.__dict__)
    finally:
        sys.modules.pop(nome, None)
    return mod


def _estado(G, pergunta, supabase, **k):
    async def _rodar():
        inicio = time.monotonic()
        estado, config, agente = await G._build_initial_state(
            pergunta, "co-1", "user-1", "sessao-1", {"id": "co-1"}, {}, supabase, "ag-core", **k)
        return (estado, config, agente), time.monotonic() - inicio
    return asyncio.run(_rodar())


def test_c_o_hyde_por_esforco_e_por_tamanho(monkeypatch):
    import app.agents.graph as G

    buscas = []
    _instalar_borda_do_estado(monkeypatch, [G], {}, buscas)
    longa = "qual a cobertura de vidros da apolice do cliente hoje"
    curta = "qual a cobertura?"
    casos = [("rapido", longa, False), ("equilibrado", longa, True), ("maximo", longa, True),
             ("equilibrado", curta, False), (None, curta, True), (None, longa, True)]
    for esforco, pergunta, esperado in casos:
        buscas.clear()
        _estado(G, pergunta, _SupabaseD(), esforco_do_chat=esforco)
        assert buscas and buscas[0]["is_hyde"] is esperado, (esforco, pergunta, buscas)
    # o RAG denso + BM25 continua rodando no Rápido (só o HyDE sai)
    buscas.clear()
    _estado(G, longa, _SupabaseD(), esforco_do_chat="rapido")
    assert len(buscas) == 1
    # ⛔ o agente que DESLIGOU o HyDE continua desligado em todo esforço
    assert G.hyde_no_turno(False, "maximo", longa) is False and G.hyde_no_turno(False, None, longa) is False
    assert G.PALAVRAS_MINIMAS_PARA_HYDE == 6


def test_c_so_o_chat_do_corretor_passa_o_esforco():
    """O atendimento (invoke_agent), o wrapper do widget e o /chat não passam esforço."""
    arvore = ast.parse(io.open(GRAFO_PY, encoding="utf-8").read())
    for fn in ast.walk(arvore):
        if isinstance(fn, ast.AsyncFunctionDef) and fn.name in ("invoke_agent", "stream_agent"):
            for chamada in ast.walk(fn):
                if isinstance(chamada, ast.Call):
                    nomes = {kw.arg for kw in chamada.keywords}
                    assert not ({"esforco", "esforco_do_chat"} & nomes), fn.name
    chat = ast.parse(io.open(CHAT_PY, encoding="utf-8").read())
    for chamada in ast.walk(chat):
        if isinstance(chamada, ast.Call) and getattr(chamada.func, "id", "") == "stream_agent":
            assert "esforco" not in {kw.arg for kw in chamada.keywords}, "o widget ganhou esforço"


def test_d_o_estado_em_paralelo_e_o_mesmo_da_versao_sequencial(monkeypatch):
    import app.agents.graph as G

    base = _grafo_da_base()
    if base is None:
        pytest.skip("sem git/commit %s nesta máquina — a comparação com a base não roda" % COMMIT_DA_BASE)
    pergunta = "qual a cobertura de vidros da apolice do cliente hoje"
    demora = 0.15
    todas = {"memoria": demora, "mcp": demora, "marca": demora, "rag": demora}
    tabelas = {"agent_http_tools": demora, "agent_delegations": demora, "agents": demora, "companies": demora}

    buscas = []
    _instalar_borda_do_estado(monkeypatch, [G, base], todas, buscas)
    sequencial, t_seq = _estado(base, pergunta, _SupabaseD(tabelas))

    resultados = []
    for embaralho in ({}, {"memoria": 0.4, "rag": 0.0}, {"rag": 0.4, "memoria": 0.0, "mcp": 0.3}):
        demoras = dict(todas, **embaralho)
        _instalar_borda_do_estado(monkeypatch, [G, base], demoras, buscas)
        resultados.append(_estado(G, pergunta, _SupabaseD(tabelas)))
    for (paralelo, _t) in resultados:
        assert paralelo[0] == sequencial[0], _diferenca(sequencial[0], paralelo[0])
        assert paralelo[1:] == sequencial[1:]
    t_par = resultados[0][1]
    print("📊 _build_initial_state com 8 leituras de %.2f s: sequencial %.2f s · paralelo %.2f s"
          % (demora, t_seq, t_par))
    assert t_par < t_seq * 0.6, (t_seq, t_par)

    # 🔴 o comparador CONSEGUE ficar vermelho: a mutação que perde a memória
    mutado = _modulo_mutado(GRAFO_PY, "app.agents._grafo_mutado_132a",
                            "            memory_context = await _t_memoria\n",
                            "            memory_context = (await _t_memoria) and \"\"\n")
    _instalar_borda_do_estado(monkeypatch, [G, base, mutado], todas, buscas)
    (estado_mutado, _c, _a), _ = _estado(mutado, pergunta, _SupabaseD(tabelas))
    assert estado_mutado != sequencial[0], "a mutação passou — o comparador (d) é carimbo"


def _diferenca(a, b):
    return {k: (a.get(k), b.get(k)) for k in set(a) | set(b) if a.get(k) != b.get(k)}


# =====================================================================================
# (e) duas corretoras: recusado ANTES do stream, sem ler anexo e sem gravar
# =====================================================================================
def test_e_conversa_de_outra_corretora_e_recusada_antes_do_stream(ambiente):
    T, chat_mod = ambiente
    sessao_da_beta = str(uuid.uuid4())
    banco = T._banco_padrao_d(conversas=[{"id": "conv-beta", "session_id": sessao_da_beta, "status": "open",
                                          "unread_count": 0, "company_id": T.CO_BETA_D}])
    borda = _Borda()
    marcas, texto, _ = _rodar_turno(T, chat_mod, banco, borda,
                                    _corpo(sessao=sessao_da_beta, attachments=[_anexo()]))
    tipos = [e.get("type") for e in T._linhas_sse_d(texto)]
    assert "policy.blocked" in tipos and "assistant.content.delta" not in tipos, tipos
    assert borda.preparar == [] and borda.grafos == [] and borda.motor == []
    assert [m for m in banco.dados["messages"] if m.get("role") == "assistant"] == []
    assert marcas["fim"] < DEMORA_DOS_ANEXOS / 2         # nada caro rodou


def test_e_anexo_no_prefixo_de_outra_corretora_e_recusado(ambiente):
    T, chat_mod = ambiente
    banco = T._banco_padrao_d(conversas=[])
    borda = _Borda()
    for alheio in (_anexo(company=T.CO_BETA_D),
                   {**_anexo(), "path": "%s/../%s/x.pdf" % (T.CO_ALFA_D, T.CO_BETA_D)},
                   {**_anexo(), "path": ""}):
        borda.preparar.clear()
        marcas, texto, _ = _rodar_turno(T, chat_mod, banco, borda,
                                        _corpo(attachments=[_anexo(), alheio]))
        tipos = [e.get("type") for e in T._linhas_sse_d(texto)]
        assert "policy.blocked" in tipos, (alheio, tipos)
        assert borda.preparar == [] and borda.motor == []
    # CONTROLE: os dois anexos DESTA corretora passam
    borda.preparar.clear()
    borda.demora = 0
    marcas, texto, _ = _rodar_turno(T, chat_mod, banco, borda,
                                    _corpo(attachments=[_anexo(), _anexo("b.xlsx", "application/vnd.ms-excel")]))
    assert "policy.blocked" not in texto and len(borda.preparar[-1][1]) == 2


def test_e_o_widget_nao_le_anexo_por_lista(ambiente):
    T, chat_mod = ambiente
    banco = T._banco_padrao_d(conversas=[])
    borda = _Borda(demora=0)
    corpo = _corpo(attachments=[_anexo()])
    corpo.pop("client_request_id")
    marcas, texto, _ = _rodar_turno(T, chat_mod, banco, borda, corpo, chave=None)
    assert marcas.get("status") == 200
    assert borda.preparar == []
    assert '"token"' in texto                             # a forma legada, intacta


# =====================================================================================
# (f) as fases medidas no payload do turno
# =====================================================================================
def test_f_fases_ms_gravadas(ambiente):
    T, chat_mod = ambiente
    banco = T._banco_padrao_d(conversas=[])
    borda = _Borda(demora=0.2)
    marcas, _t, _ = _rodar_turno(T, chat_mod, banco, borda,
                                 _corpo(attachments=[_anexo()], options={"esforco": "rapido"}))
    turno = banco.dados["messages"][-1]["payload"]["turn"]
    fases = turno.get("fases_ms") or {}
    print("📊 fases_ms do turno dublado: %s · ttft_ms=%s · ttft_gerar_ms=%s"
          % (fases, turno.get("ttft_ms"), turno.get("ttft_gerar_ms")))
    for chave in ("preparo", "anexos", "guardrail", "grafo", "contexto", "primeiro_token"):
        assert isinstance(fases.get(chave), int) and fases[chave] >= 0, (chave, fases)
    assert fases["anexos"] >= 150                        # o dublê dormiu 0,2 s
    assert turno["ttft_ms"] >= turno["ttft_gerar_ms"] >= 0
    assert turno["total_ms"] >= turno["total_gerar_ms"]
    assert turno["esforco"] == "rapido" and turno["anexos"]["recebidos"] == 1
    assert turno["status"] == "complete"


# =====================================================================================
# as peças puras
# =====================================================================================
def test_pecas_puras_do_chat():
    from app.api import chat as C

    assert C.rotulo_dos_anexos([]) == "Pensando…"
    assert C.rotulo_dos_anexos([{"mime": "image/jpeg"}] * 3) == "Olhando as 3 fotos…"
    assert C.rotulo_dos_anexos([{"mime": "audio/ogg"}]) == "Ouvindo o áudio…"
    assert C.rotulo_dos_anexos([{"mime": "image/png"}, {"mime": "application/pdf"}]) == "Lendo 2 arquivos…"
    texto, transcricao = C.incorporar_os_anexos("veja", _ResultadoDosAnexosD(
        texto=["[DOCUMENTO ANEXADO: a.pdf]\nx\n[FIM DO DOCUMENTO]"], descricoes=["um carro batido"],
        transcricoes=["e o prazo?"], avisos=["a planilha veio vazia"]))
    assert texto.index("veja") < texto.index("[CONTEXTO VISUAL") < texto.index("[DOCUMENTO ANEXADO") \
        < texto.index("[ÁUDIO ENVIADO") < texto.index("[AVISO INTERNO: a planilha veio vazia")
    assert transcricao == "e o prazo?"
    assert C.anexos_fora_da_corretora("co-a", [{"path": "co-a/x.pdf"}]) == 0
    assert C.anexos_fora_da_corretora("co-a", [{"path": "co-b/x.pdf"}, {"path": "co-a/../co-b/y"}]) == 2
    assert C.anexos_fora_da_corretora("", [{"path": "/x.pdf"}]) == 1
    assert C.opcoes_validas({"esforco": "MAXIMO", "web_search": "sim"}) == {"esforco": "maximo"}
    assert C.opcoes_validas(None) is None and C.opcoes_validas([1]) is None


def test_aquecimento_desligavel_e_nao_levanta(monkeypatch):
    fonte = io.open(os.path.join(RAIZ, "app", "main.py"), encoding="utf-8").read()
    arvore = ast.parse(fonte)
    fns = {n.name: n for n in arvore.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert "aquecer_no_arranque" in fns and "aquecimento_ligado" in fns
    # executa as duas funções SEM subir o app (main.py importa o mundo)
    mod = types.ModuleType("app._aquecimento_132a")
    mod.__dict__.update({"os": os, "logger": __import__("logging").getLogger("aquecimento-teste")})
    for nome in ("aquecimento_ligado", "aquecer_no_arranque"):
        exec(compile(ast.Module(body=[fns[nome]], type_ignores=[]), "main.py", "exec"), mod.__dict__)
    monkeypatch.setenv("AQUECER_NO_ARRANQUE", "0")
    assert mod.aquecimento_ligado() is False
    monkeypatch.setenv("AQUECER_NO_ARRANQUE", "1")
    assert mod.aquecimento_ligado() is True

    # ⚠️ módulos da borda DUBLADOS em `sys.modules`: importar o Presidio de verdade
    # custa minutos nesta máquina (📊 156 s, ver o relatório da A3).
    class _PresidioD:
        def analyze_and_anonymize(self, *_a, **_k):
            raise RuntimeError("spaCy ausente")

    PS = types.ModuleType("app.services.presidio_service")
    PS.get_presidio_service = lambda: _PresidioD()
    SS = types.ModuleType("app.services.search_service")
    SS.get_search_service = lambda: object()
    G = types.ModuleType("app.agents.graph")

    async def _pool():
        return None

    G.get_async_postgres_checkpointer = _pool
    G._async_postgres_pool = None
    G._checkpointer_init_attempted = True
    pacote = types.ModuleType("app.agents")
    pacote.graph = G
    for nome, falso in (("app.services.presidio_service", PS), ("app.services.search_service", SS),
                        ("app.agents", pacote), ("app.agents.graph", G)):
        monkeypatch.setitem(sys.modules, nome, falso)
    tempos = asyncio.run(mod.aquecer_no_arranque())
    assert tempos["presidio"] is None and isinstance(tempos["busca"], float)
    # pool que não abriu no arranque: o 1º turno tenta de novo (não herda o "já tentei")
    assert G._checkpointer_init_attempted is False


def test_o_aquecimento_e_o_1o_turno_nao_disputam_o_pool(monkeypatch):
    """Duas chamadas ao mesmo tempo (o aquecimento e o 1º turno): o pool abre UMA vez e
    ninguém recebe o pool ainda FECHADO (sem a trava, o grafo nascia com MemorySaver)."""
    import app.agents.graph as G
    import psycopg_pool
    from langgraph.checkpoint.postgres import aio as PGAIO

    from app.core import settings

    abertos = []

    class _PoolD:
        def __init__(self, *a, **k):
            self.aberto = False
            self.closed = False

        async def open(self):
            await asyncio.sleep(0.2)
            self.aberto = True
            abertos.append(self)

        @staticmethod
        async def check_connection(_c):
            return None

    class _SaverD:
        def __init__(self, pool):
            if not pool.aberto:
                raise RuntimeError("the pool is not open yet")
            self.pool = pool

        async def setup(self):
            return None

    monkeypatch.setattr(psycopg_pool, "AsyncConnectionPool", _PoolD)
    monkeypatch.setattr(PGAIO, "AsyncPostgresSaver", _SaverD)
    monkeypatch.setattr(settings, "SUPABASE_DB_URL", "postgresql://dublê/sem-rede", raising=False)
    monkeypatch.setattr(G, "_async_postgres_pool", None)
    monkeypatch.setattr(G, "_checkpointer_init_attempted", False)

    async def _dois():
        return await asyncio.gather(G.get_async_postgres_checkpointer(),
                                    G.get_async_postgres_checkpointer())

    um, outro = asyncio.run(_dois())
    assert isinstance(um, _SaverD) and isinstance(outro, _SaverD), (type(um), type(outro))
    assert len(abertos) == 1 and um.pool is outro.pool

    # 🔴 MUTAÇÃO — sem a trava, o 2º chamador pega o pool FECHADO e cai no MemorySaver
    mutado = _modulo_mutado(GRAFO_PY, "app.agents._grafo_sem_trava_132a",
                            "    async with _trava_do_pool():\n", "    if True:\n")
    abertos.clear()

    async def _dois_mutado():
        return await asyncio.gather(mutado.get_async_postgres_checkpointer(),
                                    mutado.get_async_postgres_checkpointer())

    um, outro = asyncio.run(_dois_mutado())
    assert not (isinstance(um, _SaverD) and isinstance(outro, _SaverD)), \
        "sem a trava os dois receberam o saver — o guarda é carimbo"
