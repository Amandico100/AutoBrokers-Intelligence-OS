# -*- coding: utf-8 -*-
r"""S1 · S2 — O MCP TEM CERCA DE CORRETORA, E ELA MORA COLADA NA AÇÃO.
SPEC-EXTRA-001.8, FATIA 3 (P-098-MCP-ROTAS-SEM-COMPANY).

🔴 **O defeito, lido no código em 21/09/2026** (`app/services/mcp_oauth_service.py`
antes desta SPEC):

```
delete_connection     .delete().eq("id", connection_id)          id PURO
disconnect_agent      .update(...).eq("agent_id", agent_id)      id PURO
get_agent_connections .select(...).eq("agent_id", agent_id)      id PURO
```

A única cerca era um PRÉ-CHECK na rota (`app/api/mcp.py`): checa-e-depois-age.
Duas consequências, e a segunda é a que dói mais:

```
① janela TOCTOU entre a pergunta e o DELETE
② qualquer chamador NOVO do serviço herdava ZERO proteção — a regra não morava
   onde a ação acontece
```

⛔ `agent_mcp_connections` **não tem** coluna `company_id`. 📊 Medido em
`backend/supabase/migrations/schema_completo.sql:407-419` (11 colunas, nenhuma
delas). Quem sabe de quem é a conexão é o AGENTE dela — por isso a posse é
confirmada em DOIS SALTOS e a ação seguinte leva o agente CONFIRMADO no filtro.

O FIO que este arquivo atravessa — rota REAL, serviço REAL, dublê só no cliente
do banco e na borda HTTP do provider OAuth:

```
TestClient -> router REAL de app.api.mcp -> pré-check REAL da rota
   -> MCPOAuthService REAL -> _agente_da_corretora / _agente_dono_da_conexao REAIS
   -> [DUBLÊ: o cliente PostgREST, que FILTRA de verdade]
```

⛔ SEGURANÇA: zero rede, zero banco real, zero LLM, zero mensagem. Os dois
tenants são sintéticos (`corretora-a` / `corretora-b`, uuids fabricados) e
nenhum nome de corretora entra como constante (CLAUDE.md §13.9).

Rodar (de dentro de `backend/`):
    PYTHONIOENCODING=utf-8 python tests/test_o_mcp_tem_cerca_de_corretora.py
    ... --so S1   ·   ... --mutar   ·   ... --mutar M-183-1
    python -m pytest tests/test_o_mcp_tem_cerca_de_corretora.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import copy
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RAIZ = str(Path(__file__).resolve().parents[1])
sys.path.insert(0, RAIZ)

os.environ.setdefault("APP_SECRET", "segredo-sintetico-da-fatia-3")

# ---------------------------------------------------------------------------
# Os dois tenants. ⛔ Sintéticos: nenhuma corretora de verdade entra aqui.
# ---------------------------------------------------------------------------
CO_A = "11111111-1111-4111-8111-111111111111"   # "corretora-a"
CO_B = "22222222-2222-4222-8222-222222222222"   # "corretora-b"
AG_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
AG_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
CX_A = "cccccccc-cccc-4ccc-8ccc-aaaaaaaaaaaa"
CX_B = "cccccccc-cccc-4ccc-8ccc-bbbbbbbbbbbb"
SRV = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
TOOL_A = "eeeeeeee-eeee-4eee-8eee-aaaaaaaaaaaa"
TOOL_B = "eeeeeeee-eeee-4eee-8eee-bbbbbbbbbbbb"

PASS = 0
FAIL = 0


def _p(texto):
    try:
        print(texto)
    except UnicodeEncodeError:
        print(texto.encode("ascii", "replace").decode("ascii"))


def check(nome, cond, detalhe=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        _p("  [ok] %s" % nome)
    else:
        FAIL += 1
        _p("  [FALHOU] %s" % nome + ("\n         %s" % str(detalhe)[:900] if detalhe else ""))
    return bool(cond)


# ===========================================================================
# O DUBLÊ DE POSTGREST — ele FILTRA de verdade
# ===========================================================================
#
# 🔴 Um dublê que devolve sempre a mesma linha daria falso verde: o código
# poderia esquecer `.eq("company_id", ...)` e o teste continuaria passando.
# Este guarda a lista de `.eq()` recebidos e só devolve (ou apaga, ou atualiza)
# as linhas em que TODOS batem. O gate S0 prova que ele consegue dizer NÃO.


class _ErroDoBanco(Exception):
    """O que o PostgREST levanta quando `.single()` não acha linha (PGRST116)."""


class _Resultado:
    def __init__(self, data):
        self.data = data


class _Consulta:
    def __init__(self, mundo, tabela):
        self.mundo = mundo
        self.tabela = tabela
        self.filtros = []
        self.acao = "select"
        self.payload = None
        self.conflito = None
        self.unico = False
        self.limite = None

    # --- verbos -----------------------------------------------------------
    def select(self, *_a, **_k):
        self.acao = "select"
        return self

    def delete(self):
        self.acao = "delete"
        return self

    def update(self, dados):
        self.acao = "update"
        self.payload = dados
        return self

    def upsert(self, dados, on_conflict=None):
        self.acao = "upsert"
        self.payload = dados
        self.conflito = [c.strip() for c in (on_conflict or "").split(",") if c.strip()]
        return self

    def eq(self, coluna, valor):
        self.filtros.append((coluna, None if valor is None else str(valor)))
        return self

    def limit(self, n):
        self.limite = n
        return self

    def single(self):
        self.unico = True
        return self

    # --- execução ---------------------------------------------------------
    def _casa(self, linha):
        return all(str(linha.get(c)) == v for c, v in self.filtros)

    def execute(self):
        linhas = self.mundo.tabelas.setdefault(self.tabela, [])
        self.mundo.consultas.append(
            {"tabela": self.tabela, "acao": self.acao,
             "filtros": list(self.filtros)})

        if self.acao == "upsert":
            chaves = self.conflito or ["id"]
            for linha in linhas:
                if all(str(linha.get(k)) == str(self.payload.get(k)) for k in chaves):
                    linha.update(self.payload)
                    return _Resultado([copy.deepcopy(linha)])
            nova = dict(self.payload)
            nova.setdefault("id", "nova-" + str(len(linhas)))
            linhas.append(nova)
            return _Resultado([copy.deepcopy(nova)])

        casadas = [l for l in linhas if self._casa(l)]

        if self.acao == "delete":
            for l in casadas:
                linhas.remove(l)
            return _Resultado([copy.deepcopy(l) for l in casadas])

        if self.acao == "update":
            for l in casadas:
                l.update(self.payload)
            return _Resultado([copy.deepcopy(l) for l in casadas])

        if self.limite is not None:
            casadas = casadas[: self.limite]
        if self.unico:
            if not casadas:
                # ⚠️ O PostgREST de verdade ERRA aqui (406/PGRST116); um dublê que
                #    devolvesse `data=None` esconderia o caminho do `except`.
                raise _ErroDoBanco("PGRST116: 0 linhas")
            return _Resultado(copy.deepcopy(casadas[0]))
        return _Resultado([copy.deepcopy(l) for l in casadas])


class _Mundo:
    def __init__(self):
        self.consultas = []
        self.tabelas = {
            "agents": [
                {"id": AG_A, "company_id": CO_A},
                {"id": AG_B, "company_id": CO_B},
            ],
            "agent_mcp_connections": [
                {"id": CX_A, "agent_id": AG_A, "mcp_server_id": SRV,
                 "access_token": "cifra-a", "refresh_token": "cifra-ra",
                 "token_expires_at": "2099-01-01T00:00:00", "is_active": True,
                 "connected_at": "2026-09-01T00:00:00",
                 "mcp_servers": {"name": "google", "display_name": "Google",
                                 "oauth_provider": "google"}},
                {"id": CX_B, "agent_id": AG_B, "mcp_server_id": SRV,
                 "access_token": "cifra-b", "refresh_token": "cifra-rb",
                 "token_expires_at": "2099-01-01T00:00:00", "is_active": True,
                 "connected_at": "2026-09-01T00:00:00",
                 "mcp_servers": {"name": "google", "display_name": "Google",
                                 "oauth_provider": "google"}},
            ],
            "agent_mcp_tools": [
                {"id": TOOL_A, "agent_id": AG_A, "is_enabled": True},
                {"id": TOOL_B, "agent_id": AG_B, "is_enabled": True},
            ],
        }

    def table(self, nome):
        return _Consulta(self, nome)

    def linha(self, tabela, ident):
        for l in self.tabelas[tabela]:
            if l["id"] == ident:
                return l
        return None


class _Cliente:
    def __init__(self, mundo):
        self.client = mundo


class _Cofre:
    """Dublê do serviço de cifra: identidade marcada, para se reconhecer."""

    @staticmethod
    def encrypt(v):
        return "CIFRA(%s)" % v

    @staticmethod
    def decrypt(v):
        return str(v).replace("CIFRA(", "").rstrip(")")


# ===========================================================================
# O MOTOR — o serviço e o router REAIS, com o cliente do banco trocado
# ===========================================================================
import app.api.mcp as R  # noqa: E402
import app.services.mcp_oauth_service as S  # noqa: E402


def montar(mundo):
    """Serviço REAL + app FastAPI com o router REAL de `/api/mcp`."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    servico = S.MCPOAuthService()
    servico._supabase = mundo
    servico._encryption_service = _Cofre()
    # ⚠️ Credenciais SINTÉTICAS nos três providers: sem elas, o callback
    #    recusaria por "credenciais não configuradas" e toda recusa deste
    #    arquivo passaria pelo motivo ERRADO (§9.2 — a linha de controle).
    for provedor in servico.platform_credentials:
        servico.platform_credentials[provedor] = {
            "client_id": "cid-sintetico", "client_secret": "cs-sintetico"}
    S._oauth_service = servico

    R.get_supabase_client = lambda: _Cliente(mundo)          # noqa: E731
    R.invalidate_agent_graph_cache = lambda *_a, **_k: None   # noqa: E731

    app = FastAPI()
    app.include_router(R.router, prefix="/api/mcp")
    # 🔴 A chave interna é de OUTRA cerca (SPEC-098) e já tem guarda próprio
    #    (`test_098_builder_b_unit.py`). Aqui ela é satisfeita por override para
    #    que o que sobre em teste seja SÓ a cerca de corretora.
    app.dependency_overrides[R.require_internal_key] = lambda: None
    return servico, TestClient(app, raise_server_exceptions=False)


# ===========================================================================
# S0 — A LINHA DE CONTROLE DO DUBLÊ: ele CONSEGUE dizer não
# ===========================================================================

def s0():
    _p("\n[S0] o dublê FILTRA — sem isto, todo o resto é falso verde")
    m = _Mundo()
    achou = m.table("agents").select("id").eq("id", AG_A).eq("company_id", CO_A) \
        .limit(1).execute()
    check("S0.1 dublê ACHA o agente com a corretora certa",
          [l["id"] for l in achou.data] == [AG_A], achou.data)

    nada = m.table("agents").select("id").eq("id", AG_A).eq("company_id", CO_B) \
        .limit(1).execute()
    check("S0.2 dublê NÃO acha o mesmo agente com a corretora errada",
          nada.data == [], nada.data)

    m.table("agent_mcp_connections").delete().eq("id", CX_B).eq("agent_id", AG_A) \
        .execute()
    check("S0.3 DELETE com os dois filtros discordando não apaga nada",
          m.linha("agent_mcp_connections", CX_B) is not None)

    try:
        m.table("agents").select("id").eq("id", "nao-existe").single().execute()
        check("S0.4 `.single()` sem linha ERRA, como o PostgREST", False,
              "devolveu em vez de levantar")
    except _ErroDoBanco:
        check("S0.4 `.single()` sem linha ERRA, como o PostgREST", True)


# ===========================================================================
# S1 — DOIS TENANTS: A não alcança B, e A alcança A (a linha de controle)
# ===========================================================================

def s1():
    _p("\n[S1] dois tenants nas rotas REAIS de /api/mcp")
    m = _Mundo()
    servico, cli = montar(m)

    # --- LISTAR -----------------------------------------------------------
    r = cli.get("/api/mcp/agent/%s/connections?company_id=%s" % (AG_B, CO_A))
    check("S1.1 A lista as conexões do agente de B -> 404",
          r.status_code == 404, "%s %s" % (r.status_code, r.text[:200]))
    check("S1.2 e a resposta NÃO conta que o agente existe",
          "corretora" not in r.text.lower() and "empresa" not in r.text.lower(),
          r.text[:200])

    ok = cli.get("/api/mcp/agent/%s/connections?company_id=%s" % (AG_A, CO_A))
    check("S1.3 CONTROLE: A lista as DELA -> 200 com 1 conexão",
          ok.status_code == 200 and len(ok.json()["connections"]) == 1,
          "%s %s" % (ok.status_code, ok.text[:300]))
    check("S1.4 e a conexão listada é a de A, nunca a de B",
          ok.json()["connections"][0]["id"] == CX_A, ok.text[:300])

    # --- APAGAR (escrita DESTRUTIVA) --------------------------------------
    antes = copy.deepcopy(m.linha("agent_mcp_connections", CX_B))
    r = cli.delete("/api/mcp/connections/%s?company_id=%s" % (CX_B, CO_A))
    check("S1.5 A apaga a conexão de B -> 404", r.status_code == 404,
          "%s %s" % (r.status_code, r.text[:200]))
    check("S1.6 e a linha de B CONTINUA INTEIRA no banco",
          m.linha("agent_mcp_connections", CX_B) == antes,
          m.linha("agent_mcp_connections", CX_B))

    ok = cli.delete("/api/mcp/connections/%s?company_id=%s" % (CX_A, CO_A))
    check("S1.7 CONTROLE: A apaga a DELA -> 200", ok.status_code == 200,
          "%s %s" % (ok.status_code, ok.text[:200]))
    check("S1.8 e a linha de A saiu", m.linha("agent_mcp_connections", CX_A) is None)

    # 🔴 O FILTRO QUE FECHA A JANELA TOCTOU: o DELETE que chegou ao banco leva
    #    `id` E `agent_id` confirmado — não o `id` sozinho.
    apagas = [c for c in m.consultas
              if c["tabela"] == "agent_mcp_connections" and c["acao"] == "delete"]
    check("S1.9 o DELETE sai com `id` E `agent_id` confirmado (TOCTOU)",
          bool(apagas) and all(
              {c for c, _ in q["filtros"]} == {"id", "agent_id"} for q in apagas),
          apagas)

    # --- DESCONECTAR ------------------------------------------------------
    r = cli.post("/api/mcp/agent/%s/disconnect/%s?company_id=%s" % (AG_B, SRV, CO_A))
    check("S1.10 A desconecta o agente de B -> 404", r.status_code == 404,
          "%s %s" % (r.status_code, r.text[:200]))
    check("S1.11 e os tokens de B continuam lá",
          m.linha("agent_mcp_connections", CX_B)["access_token"] == "cifra-b",
          m.linha("agent_mcp_connections", CX_B))

    ok = cli.post("/api/mcp/agent/%s/disconnect/%s?company_id=%s" % (AG_A, SRV, CO_A))
    check("S1.12 CONTROLE: A desconecta o DELA -> 200", ok.status_code == 200,
          "%s %s" % (ok.status_code, ok.text[:200]))

    # --- ALTERNAR TOOL ----------------------------------------------------
    r = cli.patch("/api/mcp/agent/%s/tool/%s/toggle?enabled=false&company_id=%s"
                  % (AG_B, TOOL_B, CO_A))
    check("S1.13 A desliga a tool do agente de B -> 404", r.status_code == 404,
          "%s %s" % (r.status_code, r.text[:200]))
    check("S1.14 e a tool de B continua ligada",
          m.linha("agent_mcp_tools", TOOL_B)["is_enabled"] is True,
          m.linha("agent_mcp_tools", TOOL_B))

    ok = cli.patch("/api/mcp/agent/%s/tool/%s/toggle?enabled=false&company_id=%s"
                   % (AG_A, TOOL_A, CO_A))
    check("S1.15 CONTROLE: A desliga a DELA -> 200 e o dado muda",
          ok.status_code == 200
          and m.linha("agent_mcp_tools", TOOL_A)["is_enabled"] is False,
          "%s %s" % (ok.status_code, m.linha("agent_mcp_tools", TOOL_A)))

    # --- O CHAMADOR NOVO: o SERVIÇO, sem rota nenhuma ---------------------
    #
    # 🔴 É o coração desta fatia. Antes, a cerca morava só na rota — quem
    #    chamasse o serviço de outro lugar não herdava proteção nenhuma.
    m2 = _Mundo()
    servico2, _ = montar(m2)
    for nome, chamada in (
        ("get_agent_connections", lambda: servico2.get_agent_connections(AG_B, CO_A)),
        ("disconnect_agent", lambda: servico2.disconnect_agent(AG_B, SRV, CO_A)),
        ("delete_connection", lambda: servico2.delete_connection(CX_B, CO_A)),
    ):
        try:
            asyncio.run(chamada())
            check("S1.16 %s recusa a corretora alheia (sem passar por rota)"
                  % nome, False, "devolveu em vez de levantar")
        except S.ConexaoNaoEncontrada:
            check("S1.16 %s recusa a corretora alheia (sem passar por rota)"
                  % nome, True)
    check("S1.17 e nada de B mudou pelo caminho do serviço",
          m2.linha("agent_mcp_connections", CX_B)["access_token"] == "cifra-b"
          and m2.linha("agent_mcp_connections", CX_B) is not None)

    # CONTROLE do par: as mesmas três, na corretora certa, funcionam.
    m3 = _Mundo()
    servico3, _ = montar(m3)
    conexoes = asyncio.run(servico3.get_agent_connections(AG_A, CO_A))
    check("S1.18 CONTROLE: o serviço lista a conexão da própria corretora",
          [c["id"] for c in conexoes] == [CX_A], conexoes)
    check("S1.19 CONTROLE: o serviço apaga a conexão da própria corretora",
          asyncio.run(servico3.delete_connection(CX_A, CO_A)) is True
          and m3.linha("agent_mcp_connections", CX_A) is None)


# ===========================================================================
# S2 — O CALLBACK OAUTH: a única rota sem chave interna
# ===========================================================================
#
# 📊 AUDITORIA (21/09/2026, por leitura de `mcp_oauth_service.py`):
#   · o `state` É assinado com HMAC-SHA256 e verificado com `compare_digest`
#     (`_encode_state:~500` / `_decode_state:~530`) -> forjar exige o APP_SECRET
#   · ele carrega `agent_id` e `mcp_server_id`; NÃO carregava `company_id`
#   · NÃO tinha instante nenhum: um convite valia para sempre
#   · o `provider` ia dentro e NUNCA era comparado com o da URL
#   · o `nonce` é gerado e nunca consumido -> replay dentro da validade
# VEREDITO: **não é BLOCKER** — sem o segredo ninguém escreve no agente de outra
# corretora, e é isto que S2.1 prova. O resto virou conserto nesta fatia.


def _estado(servico, **campos):
    dados = {"agent_id": AG_A, "company_id": CO_A, "mcp_server_id": SRV,
             "provider": "google", "nonce": "n"}
    dados.update(campos)
    return servico._encode_state(dados)


def _trocar(servico, provider, state, tokens=None):
    """Roda o callback com a borda HTTP do provider DUBLADA. ⛔ zero rede."""
    class _Resp:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return tokens or {"access_token": "tok", "refresh_token": "ref",
                              "expires_in": 3600}

    class _Http:
        def __init__(self, *_a, **_k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_a):
            return False

        async def post(self, *_a, **_k):
            return _Resp()

    original = S.httpx.AsyncClient
    S.httpx.AsyncClient = _Http
    try:
        return asyncio.run(servico.exchange_code_for_tokens(provider, "code-x", state))
    finally:
        S.httpx.AsyncClient = original


def s2():
    _p("\n[S2] o callback OAuth — state assinado, com corretora, provider e relógio")
    m = _Mundo()
    servico, cli = montar(m)

    # --- FORJADO: a assinatura é o guarda ---------------------------------
    bom = _estado(servico, agent_id=AG_B, company_id=CO_B)
    cru, assinatura = bom.rsplit(".", 1)
    import base64
    carga = json.loads(base64.urlsafe_b64decode(cru.encode()).decode())
    carga["agent_id"] = AG_A          # "quero gravar no agente da OUTRA corretora"
    carga["company_id"] = CO_A
    forjado = base64.urlsafe_b64encode(
        json.dumps(carga, sort_keys=True).encode()).decode() + "." + assinatura

    antes = copy.deepcopy(m.tabelas["agent_mcp_connections"])
    r = _trocar(servico, "google", forjado)
    check("S2.1 state FORJADO (carga trocada, assinatura antiga) -> recusado",
          r.get("success") is False, r)
    check("S2.2 e NADA foi gravado no agente da outra corretora",
          m.tabelas["agent_mcp_connections"] == antes)

    # 🔴 CONTROLE do ataque: o state ORIGINAL, não mexido, é aceito — senão
    #    S2.1 poderia estar passando por qualquer outro motivo.
    ok = _trocar(servico, "google", bom)
    check("S2.3 CONTROLE: o state ORIGINAL de B é aceito (a recusa foi da carga)",
          ok.get("success") is True, ok)
    check("S2.4 e ele gravou no agente de B, que é o dono dele",
          m.linha("agent_mcp_connections", CX_B)["access_token"].startswith("CIFRA("),
          m.linha("agent_mcp_connections", CX_B))

    # --- TROCA DE CORRETORA DEPOIS DO CONVITE -----------------------------
    m2 = _Mundo()
    servico2, _ = montar(m2)
    convite = _estado(servico2, agent_id=AG_A, company_id=CO_A)
    m2.linha("agents", AG_A)["company_id"] = CO_B   # o agente mudou de dono
    antes2 = copy.deepcopy(m2.tabelas["agent_mcp_connections"])
    r = _trocar(servico2, "google", convite)
    check("S2.5 convite assinado cuja corretora deixou de ser dona -> recusado",
          r.get("success") is False, r)
    check("S2.6 e nada foi gravado", m2.tabelas["agent_mcp_connections"] == antes2)

    # --- PROVIDER TROCADO -------------------------------------------------
    m3 = _Mundo()
    servico3, _ = montar(m3)
    antes3 = copy.deepcopy(m3.tabelas["agent_mcp_connections"])
    r = _trocar(servico3, "github", _estado(servico3, provider="google"))
    check("S2.7 state de `google` apresentado no callback de `github` -> recusado",
          r.get("success") is False, r)
    check("S2.8 e nada foi gravado", m3.tabelas["agent_mcp_connections"] == antes3)

    # --- VENCIDO ----------------------------------------------------------
    m4 = _Mundo()
    servico4, _ = montar(m4)
    velho = _estado(servico4, iat=int(time.time()) - S.STATE_VALIDADE_SEGUNDOS - 10)
    antes4 = copy.deepcopy(m4.tabelas["agent_mcp_connections"])
    r = _trocar(servico4, "google", velho)
    check("S2.9 convite mais velho que a validade -> recusado",
          r.get("success") is False, r)
    check("S2.10 e nada foi gravado", m4.tabelas["agent_mcp_connections"] == antes4)

    sem_relogio = servico4._encode_state({"agent_id": AG_A, "company_id": CO_A,
                                          "mcp_server_id": SRV,
                                          "provider": "google", "iat": "ontem"})
    check("S2.11 state sem instante INTEIRO -> recusado (fecha o formato antigo)",
          _trocar(servico4, "google", sem_relogio).get("success") is False)

    # --- O CONVITE: assinar o agente alheio ------------------------------
    m5 = _Mundo()
    servico5, cli5 = montar(m5)
    r = cli5.get("/api/mcp/oauth/url/google?agent_id=%s&mcp_server_id=%s&company_id=%s"
                 % (AG_B, SRV, CO_A))
    check("S2.12 A pede convite OAuth para o agente de B -> 404",
          r.status_code == 404, "%s %s" % (r.status_code, r.text[:200]))
    try:
        asyncio.run(servico5.get_authorization_url("google", AG_B, SRV, CO_A))
        check("S2.13 e o SERVIÇO recusa sozinho, sem a rota", False, "não levantou")
    except S.ConexaoNaoEncontrada:
        check("S2.13 e o SERVIÇO recusa sozinho, sem a rota", True)

    # CONTROLE: o convite da própria corretora nasce, e nasce com relógio.
    os.environ.setdefault("GOOGLE_OAUTH_CLIENT_ID", "cid-sintetico")
    os.environ.setdefault("GOOGLE_OAUTH_CLIENT_SECRET", "cs-sintetico")
    servico5.platform_credentials["google"] = {"client_id": "cid-sintetico",
                                               "client_secret": "cs-sintetico"}
    conv = asyncio.run(servico5.get_authorization_url("google", AG_A, SRV, CO_A))
    check("S2.14 CONTROLE: o convite da PRÓPRIA corretora é gerado",
          "url" in conv and "state" in conv, conv)
    dentro = servico5._decode_state(conv["state"])
    check("S2.15 e ele carrega corretora, agente e instante",
          dentro and dentro["company_id"] == CO_A and dentro["agent_id"] == AG_A
          and isinstance(dentro.get("iat"), int), dentro)


GATES = {"S0": s0, "S1": s1, "S2": s2}


# ===========================================================================
# AS MUTAÇÕES — por CÓPIA, em SUBPROCESSO. A árvore precisa estar parada.
# ===========================================================================
SVC = "app/services/mcp_oauth_service.py"
API = "app/api/mcp.py"

#: Cada mutação é `(id, [(arquivo, de, para), ...], gate)`.
#:
#: 🔴 Por que algumas mexem em DOIS arquivos: a cerca é em profundidade — rota
#: **e** serviço. Tirar só a da rota deixa o produto seguro (e o gate verde, com
#: razão). Para provar que a cerca do SERVIÇO é a que decide, a mutação tem de
#: derrubar as duas ao mesmo tempo, que é o cenário do "chamador novo".
MUTACOES = [
    # M-183-1 — a cerca do SERVIÇO no DELETE cai; a da rota fica de pé.
    #           Quem pega é o gate que chama o serviço DIRETO (S1.16/S1.17).
    ("M-183-1", [
        (SVC,
         '        agente = self._agente_dono_da_conexao(connection_id, company_id)\n'
         '        if not agente:\n'
         '            raise ConexaoNaoEncontrada("conexão não encontrada")',
         '        agente = self._agente_dono_da_conexao(connection_id, company_id) \\\n'
         '            or str((self.supabase.table("agent_mcp_connections").select("agent_id")\n'
         '                    .eq("id", connection_id).limit(1).execute().data or [{}])[0]\n'
         '                   .get("agent_id") or "")  # MUTACAO'),
    ], "S1"),
    # M-183-2 — as DUAS cercas do DELETE caem juntas: é o buraco de verdade,
    #           e a conexão da outra corretora some pela ROTA.
    ("M-183-2", [
        (API,
         "    if not await _validate_connection_belongs_to_company(connection_id, company_id):\n"
         "        raise _nao_existe()",
         "    if False:  # MUTACAO\n        raise _nao_existe()"),
        (SVC,
         '        agente = self._agente_dono_da_conexao(connection_id, company_id)\n'
         '        if not agente:\n'
         '            raise ConexaoNaoEncontrada("conexão não encontrada")',
         '        agente = self._agente_dono_da_conexao(connection_id, company_id) \\\n'
         '            or str((self.supabase.table("agent_mcp_connections").select("agent_id")\n'
         '                    .eq("id", connection_id).limit(1).execute().data or [{}])[0]\n'
         '                   .get("agent_id") or "")  # MUTACAO'),
    ], "S1"),
    # M-183-3 — a lista volta a usar o agent_id que veio de fora
    ("M-183-3", [
        (SVC,
         '        agente = self._agente_da_corretora(agent_id, company_id)\n'
         '        if not agente:\n'
         '            raise ConexaoNaoEncontrada("agente não encontrado")\n'
         '        try:\n'
         '            result = self.supabase.table("agent_mcp_connections") \\',
         '        agente = agent_id  # MUTACAO\n'
         '        try:\n'
         '            result = self.supabase.table("agent_mcp_connections") \\'),
    ], "S1"),
    # M-183-4 — o callback para de comparar o provider do state com o da URL
    ("M-183-4", [
        (SVC, '        if str(state_data.get("provider") or "") != provider:',
         "        if False:  # MUTACAO"),
    ], "S2"),
    # M-183-5 — o callback para de reconferir a posse do agente na hora da escrita
    ("M-183-5", [
        (SVC, '        if not self._agente_da_corretora(str(agent_id), str(company_id)):',
         "        if False:  # MUTACAO"),
    ], "S2"),
    # M-183-6 — o state volta a não vencer
    ("M-183-6", [
        (SVC, "            if idade < -60 or idade > STATE_VALIDADE_SEGUNDOS:",
         "            if False:  # MUTACAO"),
    ], "S2"),
]


def _rodar(gate):
    return subprocess.run(
        [sys.executable, os.path.abspath(__file__), "--so", gate],
        cwd=RAIZ, capture_output=True, text=True, timeout=1800,
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8",
             "PYTHONDONTWRITEBYTECODE": "1"})


def rodar_mutacoes(filtro=None):
    _p("\n[MUT] MUTACOES POR COPIA -- cada uma em SUBPROCESSO. A arvore precisa estar parada.")
    vermelhas = verdes = 0
    for mid, edicoes, gate in MUTACOES:
        if filtro and mid != filtro:
            continue
        alvos = []
        faltou = None
        for relativo, de, para in edicoes:
            caminho = os.path.normpath(os.path.join(RAIZ, relativo))
            original = io.open(caminho, encoding="utf-8").read()
            if de not in original:
                faltou = relativo
                break
            alvos.append((caminho, original, de, para, relativo))
        if faltou:
            _p("  [FALHOU] %s: a ancora nao existe em %s -- mutacao NAO aplicada "
               "NAO e mutacao passada" % (mid, faltou))
            verdes += 1
            continue
        base = _rodar(gate)
        backups = []
        for caminho, _o, _d, _pa, _rel in alvos:
            b = tempfile.NamedTemporaryFile(delete=False, suffix=".bak-0183").name
            shutil.copyfile(caminho, b)
            backups.append(b)
        try:
            for caminho, original, de, para, _rel in alvos:
                io.open(caminho, "w", encoding="utf-8", newline="\n").write(
                    original.replace(de, para, 1))
            r = _rodar(gate)
            falhas = [l.strip() for l in (r.stdout or "").splitlines() if "[FALHOU]" in l]
            if base.returncode == 0 and r.returncode != 0 and falhas:
                vermelhas += 1
                _p("  [ok] %s deixa %s VERMELHO: %s" % (mid, gate, falhas[0][:220]))
            else:
                verdes += 1
                _p("  [FALHOU] %s NAO deixou %s vermelho (base rc=%s, mutado rc=%s)\n%s"
                   % (mid, gate, base.returncode, r.returncode,
                      (r.stdout or r.stderr)[-900:]))
        finally:
            for (caminho, original, _d, _pa, relativo), b in zip(alvos, backups):
                shutil.copyfile(b, caminho)
                os.unlink(b)
                assert io.open(caminho, encoding="utf-8").read() == original, \
                    "restauracao falhou em " + relativo
    _p("\n  PLACAR DAS MUTACOES: %d vermelhas - %d verdes" % (vermelhas, verdes))
    return verdes == 0


def main():
    args = sys.argv[1:]
    if "--mutar" in args:
        i = args.index("--mutar")
        filtro = args[i + 1] if len(args) > i + 1 and args[i + 1].startswith("M-") else None
        return 0 if rodar_mutacoes(filtro) else 1

    so = args[args.index("--so") + 1] if "--so" in args else None
    if not so:
        _p("=" * 78)
        _p("  S0 · S1 · S2 -- O MCP TEM CERCA DE CORRETORA")
        _p("  (SPEC-EXTRA-001.8, FATIA 3 -- P-098-MCP-ROTAS-SEM-COMPANY)")
        _p("=" * 78)
    for gid, fn in GATES.items():
        if so and gid != so:
            continue
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            import traceback
            check("%s EXPLODIU (defeito do guarda ou do produto)" % gid, False,
                  "%s: %s\n%s" % (type(exc).__name__, exc,
                                  traceback.format_exc()[-1500:]))
    if not so:
        _p("\n" + "=" * 78)
        _p("  %d assercoes verdes - %d vermelhas" % (PASS, FAIL))
        _p("=" * 78)
    return 1 if FAIL else 0


def test_o_mcp_tem_cerca_de_corretora():
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
