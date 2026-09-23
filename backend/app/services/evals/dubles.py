# -*- coding: utf-8 -*-
"""SPEC-116 U11 — os DUBLÊS da bancada. Só a BORDA é falsa; o motor é o do produto.

O que é dublê e o que NÃO é
---------------------------
A bancada roda o MOTOR real (``create_agent_graph``, ``agent_node``,
``tool_node``, ``decide_next_action``, ``o_cerebro_ja_sabe``, a extração de
fatos da memória…). Falso é só o que sai do prédio ou o que é caro/instável:

    LLMDuble ........... um "modelo" determinístico. Serve de LINHA DE CONTROLE
                         (CLAUDE.md §9.2): o `perfeito` responde o oráculo e o
                         `burro` sempre responde texto sem tool. Se a bancada não
                         separar os dois, ela não mede nada.
    LLMComFalhas ....... injeta 429 / 500 / timeout na chamada N do provedor.
    DubleDeTool ........ responde pelo ESTADO do caso e REGISTRA o efeito por
                         chave de idempotência. ⛔ Ele NÃO deduplica: se o
                         dublê engolisse a segunda chamada, o efeito duplicado
                         nunca apareceria — e é exatamente ele que se quer ver.
    SupabaseDuble ...... banco em memória, permissivo. Tudo que o motor
                         escreveria (feed, ficha, registro de invocação) fica
                         aqui; NADA chega ao banco de produção.
    borda_isolada() .... troca `app.core.database.get_supabase_client` pelo
                         dublê enquanto o motor roda.

⛔ Nenhum dublê envia mensagem, abre portal ou chama provedor.
"""

from __future__ import annotations

import asyncio
import contextlib
import contextvars
import copy
import hashlib
import json
import os
import re
import sys
import types
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional

# ---------------------------------------------------------------------------
# O caso que está rodando AGORA — só os dublês de LLM leem (o `perfeito`
# precisa saber a resposta-ouro; um modelo real nunca vê isto).
# ---------------------------------------------------------------------------
CASO_ATUAL: contextvars.ContextVar = contextvars.ContextVar("bancada_caso_atual", default=None)
TENANT_ATUAL: contextvars.ContextVar = contextvars.ContextVar("bancada_tenant_atual", default=None)


def _texto_de(conteudo: Any) -> str:
    if isinstance(conteudo, str):
        return conteudo
    if isinstance(conteudo, list):
        partes = []
        for b in conteudo:
            if isinstance(b, dict) and b.get("type") == "text":
                partes.append(str(b.get("text") or ""))
            elif isinstance(b, str):
                partes.append(b)
        return "\n".join(partes)
    return str(conteudo or "")


def estimar_tokens(texto: str) -> int:
    """≈ 4 caracteres por token. É ESTIMATIVA — só serve ao teto (antes da
    chamada) e ao dublê. O custo gravado vem do `usage_metadata` real."""
    return max(1, len(texto or "") // 4)


def _tipo(msg: Any) -> str:
    return str(getattr(msg, "type", "") or (msg.get("role") if isinstance(msg, dict) else ""))


# ---------------------------------------------------------------------------
# LLM-DUBLÊ — determinístico
# ---------------------------------------------------------------------------
MODOS_DO_DUBLE = ("perfeito", "burro", "duplicador", "vazador")


class LLMDuble:
    """Um "modelo" que responde por regra, com `usage_metadata` de verdade.

    ``perfeito``   devolve o oráculo do caso (tool certa com args certos, ou o
                   texto-ouro). É o teto da régua: se ele não passa, o defeito
                   é da bancada, não de modelo nenhum.
    ``burro``      sempre texto genérico, nunca tool. É o chão.
    ``duplicador`` chama a tool do turno SEMPRE, ignorando o histórico — é o
                   comportamento que produz efeito duplicado.
    ``vazador``    responde o perfeito + um dado do OUTRO tenant.
    """

    def __init__(self, modo: str = "perfeito", *, tools: Optional[list] = None,
                 kwargs_de_bind: Optional[dict] = None):
        modo = str(modo or "perfeito").strip().lower()
        if modo not in MODOS_DO_DUBLE:
            raise ValueError(f"modo de dublê desconhecido: {modo!r} (use {MODOS_DO_DUBLE})")
        self.modo = modo
        self.model_name = f"duble:{modo}"
        self.tools = list(tools or [])
        self.kwargs_de_bind = dict(kwargs_de_bind or {})

    # -- API mínima de um chat model do LangChain --------------------------
    def bind_tools(self, tools, **kwargs):
        return LLMDuble(self.modo, tools=list(tools or []), kwargs_de_bind=kwargs)

    def invoke(self, entrada, config=None, **kwargs):
        return self._responder(entrada)

    async def ainvoke(self, entrada, config=None, **kwargs):
        await asyncio.sleep(0)
        return self._responder(entrada)

    # -- a regra ------------------------------------------------------------
    def _responder(self, entrada):
        from langchain_core.messages import AIMessage

        mensagens = entrada if isinstance(entrada, list) else [entrada]
        texto_entrada = "\n".join(_texto_de(getattr(m, "content", m)) for m in mensagens)
        caso = CASO_ATUAL.get() or {}
        conteudo, tool_calls = self._decidir(caso, mensagens)
        entrada_tokens = estimar_tokens(texto_entrada) + estimar_tokens(
            json.dumps([getattr(t, "name", str(t)) for t in self.tools]))
        saida_tokens = estimar_tokens(conteudo + json.dumps(tool_calls, ensure_ascii=False))
        return AIMessage(
            content=conteudo,
            tool_calls=tool_calls,
            usage_metadata={"input_tokens": entrada_tokens, "output_tokens": saida_tokens,
                            "total_tokens": entrada_tokens + saida_tokens},
            response_metadata={"model_name": self.model_name},
        )

    def _decidir(self, caso: dict, mensagens: list):
        oraculo = (caso or {}).get("oraculo") or {}
        if self.modo == "burro":
            if oraculo.get("formato") == "json_lista":
                return "Não sei.", []
            return "Entendi. Pode me dar mais detalhes, por favor?", []

        # Motores que não são o agente (memória, portal, dispatch, visão…):
        # a resposta-ouro é o texto que o motor espera receber do modelo.
        if "resposta_modelo_ouro" in oraculo and not self.tools:
            base = oraculo["resposta_modelo_ouro"]
            base = base if isinstance(base, str) else json.dumps(base, ensure_ascii=False)
            return self._talvez_vazar(base, caso), []

        ultima = mensagens[-1] if mensagens else None
        ent = caso.get("entrada") or {}
        turnos = list(ent.get("turnos") or []) + list((ent.get("outro_tenant") or {}).get("turnos") or [])
        if turnos:
            return self._decidir_trajetoria(caso, mensagens, turnos)

        # N1 — UMA volta: a tool certa na primeira chamada; depois, o texto.
        if _tipo(ultima) == "tool":
            return self._talvez_vazar(self._texto_ouro(oraculo), caso), []
        if oraculo.get("tool_esperada"):
            alvo = oraculo["tool_esperada"]
            alvo = alvo[0] if isinstance(alvo, list) else alvo
            return self._talvez_vazar("", caso).strip(), [
                self._chamada(alvo, self._args_ouro(oraculo.get("args_esperados") or {}))]
        return self._talvez_vazar(self._texto_ouro(oraculo), caso), []

    def _decidir_trajetoria(self, caso, mensagens, turnos):
        """N2 — acha o turno pelo TEXTO da última fala do segurado (uma retomada
        ou uma mensagem duplicada reenviam o MESMO texto)."""
        humanas = [(i, _texto_de(getattr(m, "content", ""))) for i, m in enumerate(mensagens)
                   if _tipo(m) == "human"]
        if not humanas:
            return "Olá!", []
        ultima_i, ultima_txt = humanas[-1]
        turno = next((t for t in turnos if str(t.get("segurado") or "").strip() == ultima_txt.strip()),
                     None) or {}
        acao = turno.get("acao_ouro") or {}
        ultima = mensagens[-1]
        texto_final = self._talvez_vazar(str(turno.get("resposta_ouro") or "Certo."), caso)
        if _tipo(ultima) == "tool":
            return texto_final, []
        if not acao.get("tool"):
            return texto_final, []
        if self.modo != "duplicador":
            # já chamou esta tool para este MESMO texto do segurado? então não repete.
            primeira = next(i for i, t in humanas if t.strip() == ultima_txt.strip())
            for m in mensagens[primeira:]:
                if _tipo(m) == "tool" and str(getattr(m, "name", "")) == acao["tool"]:
                    return texto_final, []
        return "", [self._chamada(acao["tool"], self._args_ouro(acao.get("args") or {}))]

    @staticmethod
    def _args_ouro(args: dict) -> dict:
        """O oráculo fala em `"~contém"` e listas de alternativas; o perfeito
        precisa de UM valor concreto."""
        out = {}
        for k, v in (args or {}).items():
            if isinstance(v, list):
                v = v[0] if v else None
            if isinstance(v, str) and v.startswith("~"):
                v = v[1:]
            out[k] = v
        return out

    @staticmethod
    def _texto_ouro(oraculo: dict) -> str:
        if oraculo.get("resposta_ouro"):
            return str(oraculo["resposta_ouro"])
        partes = [str(x) for x in (oraculo.get("deve_conter") or [])]
        return (" ".join(partes) + ".") if partes else "Certo, estou verificando para você."

    def _talvez_vazar(self, texto: str, caso: dict) -> str:
        if self.modo != "vazador":
            return texto
        outros = ((caso or {}).get("oraculo") or {}).get("dados_do_outro_tenant") or []
        return f"{texto} {outros[0]}" if outros else f"{texto} [dado-de-outra-corretora]"

    @staticmethod
    def _chamada(nome: str, args: dict) -> dict:
        return {"name": nome, "args": dict(args or {}),
                "id": "call_" + hashlib.sha1((nome + json.dumps(args, sort_keys=True,
                                                                ensure_ascii=False)).encode()).hexdigest()[:12],
                "type": "tool_call"}


# ---------------------------------------------------------------------------
# INJEÇÃO DE FALHA NO PROVEDOR
# ---------------------------------------------------------------------------
class FalhaInjetada(Exception):
    """Falha que A BANCADA provocou. Carrega o status como o SDK carregaria."""

    def __init__(self, tipo: str, status_code: Optional[int] = None):
        super().__init__(f"falha injetada: {tipo}")
        self.tipo = tipo
        self.status_code = status_code


_STATUS = {"provedor_429": 429, "provedor_500": 500, "provedor_timeout": None}


class LLMComFalhas:
    """Envolve um LLM e levanta a falha planejada na chamada N (1-based).

    O contador é COMPARTILHADO entre o objeto e seus `bind_tools` — no produto,
    o mesmo cliente é que é ligado às ferramentas.
    """

    def __init__(self, interno, plano: Iterable[dict], _contador: Optional[list] = None,
                 _disparadas: Optional[list] = None):
        self.interno = interno
        self.plano = [dict(p) for p in (plano or []) if str(p.get("tipo", "")).startswith("provedor_")]
        self._contador = _contador if _contador is not None else [0]
        self.disparadas = _disparadas if _disparadas is not None else []

    @property
    def model_name(self):
        return getattr(self.interno, "model_name", None) or getattr(self.interno, "model", None)

    def bind_tools(self, tools, **kwargs):
        return LLMComFalhas(self.interno.bind_tools(tools, **kwargs), self.plano,
                            self._contador, self.disparadas)

    def _talvez_falhar(self):
        self._contador[0] += 1
        n = self._contador[0]
        for p in self.plano:
            if int(p.get("na_chamada") or 1) == n:
                self.disparadas.append({"tipo": p["tipo"], "na_chamada": n})
                if p["tipo"] == "provedor_timeout":
                    raise asyncio.TimeoutError("falha injetada: provedor_timeout")
                raise FalhaInjetada(p["tipo"], _STATUS.get(p["tipo"]))

    def invoke(self, entrada, config=None, **kwargs):
        self._talvez_falhar()
        return self.interno.invoke(entrada, config=config, **kwargs)

    async def ainvoke(self, entrada, config=None, **kwargs):
        self._talvez_falhar()
        return await self.interno.ainvoke(entrada, config=config, **kwargs)


# ---------------------------------------------------------------------------
# EFEITOS — contados por chave de idempotência
# ---------------------------------------------------------------------------
#: Ferramentas cujo sucesso SAI DO PRÉDIO ou muda estado durável. Caso pode
#: sobrescrever por `efeito: true/false` no estado do dublê.
EFEITO_POR_PADRAO = frozenset({
    "insurer_dispatch", "portal_action", "request_human_agent",
    "create_routine", "manage_routine", "executar_auxiliar", "gerar_relatorio",
})


@dataclass
class RegistroDeEfeitos:
    chamadas: List[dict] = field(default_factory=list)

    def registrar(self, *, tool: str, args: dict, tenant: Optional[str], efeito: bool,
                  campos_da_chave: Optional[List[str]] = None, falha: Optional[str] = None) -> None:
        campos = list(campos_da_chave or [])
        base = {k: args.get(k) for k in campos} if campos else {
            k: v for k, v in (args or {}).items()
            if k not in ("session_id", "company_id", "user_query", "mensagem_atual",
                         "agent_id", "user_id", "selected_policy_number")}
        chave = hashlib.sha1(json.dumps([tool, tenant, base], sort_keys=True,
                                        ensure_ascii=False, default=str).encode()).hexdigest()[:16]
        self.chamadas.append({"tool": tool, "tenant": tenant, "efeito": bool(efeito),
                              "chave": chave, "falha": falha,
                              "args": {k: v for k, v in (args or {}).items()
                                       if k not in ("user_query",)}})

    def efeitos(self) -> List[dict]:
        return [c for c in self.chamadas if c["efeito"] and not c.get("falha")]

    def contagem(self, tool: str, tenant: Optional[str] = None) -> int:
        return sum(1 for c in self.efeitos()
                   if c["tool"] == tool and (tenant is None or c["tenant"] == tenant))

    def duplicados(self) -> int:
        """Efeitos a mais com a MESMA chave. Tem de ser 0."""
        vistos: Dict[str, int] = {}
        for c in self.efeitos():
            vistos[c["chave"]] = vistos.get(c["chave"], 0) + 1
        return sum(n - 1 for n in vistos.values() if n > 1)


# ---------------------------------------------------------------------------
# DUBLÊ DE TOOL — com o NOME e o SCHEMA da tool real
# ---------------------------------------------------------------------------
class DubleDeTool:
    """Responde pelo estado do caso; registra o efeito. Não deduplica (nunca).

    Estado aceito (``entrada.dubles[<nome>]`` no caso)::

        {"resposta": "..." | {...},         # ou "respostas_por_tenant": {"A": .., "B": ..}
                                            # dict = a FORMA da tool real, devolvida como dict
         "efeito": true,                    # default: EFEITO_POR_PADRAO
         "chave": ["subservice", "insurer_key"],
         "falhas": [{"tipo": "tool_timeout"|"tool_erro", "na_chamada": 1}]}
    """

    exige_async = True

    def __init__(self, real, *, registro: RegistroDeEfeitos, tenant: Optional[str],
                 estado: Optional[dict] = None):
        self.real = real
        self.name = getattr(real, "name", str(real))
        self.description = getattr(real, "description", "")
        self.args_schema = getattr(real, "args_schema", None)
        self.registro = registro
        self.tenant = tenant
        self.estado = dict(estado or {})
        self.n = 0

    def _efeito(self) -> bool:
        if "efeito" in self.estado:
            return bool(self.estado["efeito"])
        return self.name in EFEITO_POR_PADRAO

    async def _arun(self, **kwargs):
        self.n += 1
        falha = next((f for f in (self.estado.get("falhas") or [])
                      if int(f.get("na_chamada") or 1) == self.n), None)
        if falha:
            self.registro.registrar(tool=self.name, args=kwargs, tenant=self.tenant,
                                    efeito=self._efeito(), campos_da_chave=self.estado.get("chave"),
                                    falha=falha.get("tipo"))
            if falha.get("tipo") == "tool_timeout":
                raise asyncio.TimeoutError(f"{self.name}: tempo esgotado (falha injetada)")
            raise RuntimeError(f"{self.name}: erro do sistema externo (falha injetada)")
        self.registro.registrar(tool=self.name, args=kwargs, tenant=self.tenant,
                                efeito=self._efeito(), campos_da_chave=self.estado.get("chave"))
        por_tenant = self.estado.get("respostas_por_tenant") or {}
        resposta = por_tenant.get(self.tenant) if por_tenant else self.estado.get("resposta")
        if resposta is None:
            resposta = "Consulta concluída, sem dados adicionais para este caso."
        # 🔴 SPEC-116 F6 — a FORMA é a da tool real, não uma string. 📊 As tools
        # reais devolvem dict (`infocap_policy_lookup` → {content, data,
        # policy_response_contract}; `insurer_dispatch` → {status, content};
        # `knowledge_base_search` → {content, chunks, …}), e o `tool_node` decide
        # pelo TIPO: é do dict que nasce `infocap_policy_context`
        # (nodes.py:2139). Serializar aqui era o dublê decidir pelo produto.
        if isinstance(resposta, (dict, list)):
            return copy.deepcopy(resposta)
        return resposta if isinstance(resposta, str) else json.dumps(resposta, ensure_ascii=False)

    def _run(self, **kwargs):
        return asyncio.get_event_loop().run_until_complete(self._arun(**kwargs))


# ---------------------------------------------------------------------------
# SUPABASE-DUBLÊ — em memória, permissivo
# ---------------------------------------------------------------------------
class _Resposta:
    def __init__(self, data=None, count=None):
        self.data = data
        self.count = count


class _Consulta:
    def __init__(self, banco: "SupabaseDuble", tabela: str):
        self.banco = banco
        self.tabela = tabela
        self.op = "select"
        self.payload: Any = None
        self.filtros: List[tuple] = []
        self._limite: Optional[int] = None
        self._unico = False

    # operações
    def select(self, *_a, **_k):
        self.op = "select" if self.op == "select" else self.op
        return self

    def insert(self, linhas, **_k):
        self.op, self.payload = "insert", linhas
        return self

    def upsert(self, linhas, **_k):
        self.op, self.payload = "upsert", linhas
        return self

    def update(self, dados, **_k):
        self.op, self.payload = "update", dados
        return self

    def delete(self, **_k):
        self.op = "delete"
        return self

    # filtros
    def eq(self, col, val):
        self.filtros.append(("eq", col, val))
        return self

    def in_(self, col, vals):
        self.filtros.append(("in", col, list(vals or [])))
        return self

    def limit(self, n, **_k):
        self._limite = int(n)
        return self

    def single(self):
        self._unico = True
        return self

    maybe_single = single

    def __getattr__(self, nome):  # neq, gte, order, ilike, is_, range… — aceita e ignora
        def _qualquer(*_a, **_k):
            return self
        return _qualquer

    def _casa(self, linha: dict) -> bool:
        for tipo, col, val in self.filtros:
            if tipo == "eq" and str(linha.get(col)) != str(val):
                return False
            if tipo == "in" and str(linha.get(col)) not in {str(v) for v in val}:
                return False
        return True

    def execute(self):
        tabela = self.banco.tabelas.setdefault(self.tabela, [])
        if self.op in ("update", "delete") and self.tabela in self.banco.append_only:
            raise RuntimeError(f"{self.tabela} e append-only: rode um novo eval_run")
        if self.op in ("insert", "upsert"):
            linhas = self.payload if isinstance(self.payload, list) else [self.payload]
            novas = []
            for l in linhas:
                l = dict(l or {})
                l.setdefault("id", str(uuid.uuid4()))
                tabela.append(l)
                novas.append(copy.deepcopy(l))
            self.banco.escritas.append((self.op, self.tabela, copy.deepcopy(linhas)))
            return _Resposta(novas, len(novas))
        alvo = [l for l in tabela if self._casa(l)]
        if self.op == "update":
            for l in alvo:
                l.update(copy.deepcopy(self.payload or {}))
            self.banco.escritas.append(("update", self.tabela, copy.deepcopy(self.payload),
                                        list(self.filtros)))
            return _Resposta([copy.deepcopy(l) for l in alvo], len(alvo))
        if self.op == "delete":
            for l in alvo:
                tabela.remove(l)
            self.banco.escritas.append(("delete", self.tabela, list(self.filtros)))
            return _Resposta([], len(alvo))
        dados = [copy.deepcopy(l) for l in alvo]
        if self._limite is not None:
            dados = dados[: self._limite]
        if self._unico:
            return _Resposta(dados[0] if dados else None, len(dados))
        return _Resposta(dados, len(dados))


class SupabaseDuble:
    """Banco em memória. `.client` aponta para ele mesmo (o motor faz unwrap)."""

    def __init__(self, tabelas: Optional[Dict[str, List[dict]]] = None,
                 append_only: Iterable[str] = ("eval_case_results",)):
        self.tabelas: Dict[str, List[dict]] = {k: [dict(x) for x in v]
                                               for k, v in (tabelas or {}).items()}
        self.append_only = set(append_only or ())
        self.escritas: List[tuple] = []
        self.client = self

    def table(self, nome: str) -> _Consulta:
        return _Consulta(self, nome)

    from_ = table

    def rpc(self, *_a, **_k):
        return types.SimpleNamespace(execute=lambda: _Resposta(None, 0))


# ---------------------------------------------------------------------------
# A BORDA ISOLADA — nada do motor alcança o banco real enquanto a bancada roda
# ---------------------------------------------------------------------------
@contextlib.contextmanager
def borda_isolada(banco: Optional[SupabaseDuble] = None, env: Optional[Dict[str, str]] = None):
    """Troca o cliente do banco do PRODUTO pelo dublê e ajusta envs, e desfaz.

    📊 Os pontos do motor que escrevem (feed `log_activity`, ficha
    `attendance_ficha.gravar`, registro de invocação do Tool Gateway) importam
    `get_supabase_client` DENTRO da função — trocar o atributo do módulo basta.
    """
    import app.core.database as _db

    banco = banco or SupabaseDuble()
    original = _db.get_supabase_client
    antes = {k: os.environ.get(k) for k in (env or {})}
    _db.get_supabase_client = lambda *a, **k: banco  # type: ignore[assignment]
    for k, v in (env or {}).items():
        os.environ[k] = v
    try:
        yield banco
    finally:
        _db.get_supabase_client = original  # type: ignore[assignment]
        for k, v in antes.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@contextlib.contextmanager
def atributo_trocado(alvo: Any, nome: str, valor: Any):
    """Troca `alvo.nome` por `valor` e restaura — o monkeypatch da bancada."""
    tinha = hasattr(alvo, nome)
    antigo = getattr(alvo, nome, None)
    setattr(alvo, nome, valor)
    try:
        yield
    finally:
        if tinha:
            setattr(alvo, nome, antigo)
        else:
            delattr(alvo, nome)


# ---------------------------------------------------------------------------
# HTTP-DUBLÊ para o cérebro do PORTAL (adaptive.decide_next_action chama
# api.openai.com por HTTP direto — ver a COSTURA no LEIAME)
# ---------------------------------------------------------------------------
class _RespostaHttp:
    def __init__(self, status_code: int, corpo: dict):
        self.status_code = status_code
        self._corpo = corpo

    def json(self):
        return self._corpo


def cliente_http_que_fala_com(llm, pedidos: List[dict]):
    """Uma classe `AsyncClient` que entrega o prompt ao BRAÇO e devolve no
    formato de Chat Completions. Grava cada pedido (modelo e temperatura que o
    PRODUTO mandou) — é assim que o rebaixamento calado para o mini aparece."""
    from langchain_core.messages import HumanMessage, SystemMessage

    class _Cliente:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, headers=None, json=None, **_k):  # noqa: A002
            corpo = json or {}
            pedidos.append({"url": str(url), "model": corpo.get("model"),
                            "temperature": corpo.get("temperature"),
                            "response_format": corpo.get("response_format")})
            msgs = []
            for m in corpo.get("messages") or []:
                cls = SystemMessage if m.get("role") == "system" else HumanMessage
                msgs.append(cls(content=m.get("content") or ""))
            try:
                resp = await llm.ainvoke(msgs)
            except FalhaInjetada as exc:
                return _RespostaHttp(exc.status_code or 500,
                                     {"error": {"message": str(exc)}})
            return _RespostaHttp(200, {"choices": [{"message": {
                "content": _texto_de(getattr(resp, "content", ""))}}]})

    return _Cliente


@contextlib.contextmanager
def httpx_do_portal(cliente_cls):
    """Durante a janela, `import httpx` devolve um PROXY cujo `AsyncClient` é o
    dublê. O módulo httpx real fica intacto (os SDKs que já o importaram não
    são afetados)."""
    import httpx as _real

    proxy = types.ModuleType("httpx")
    proxy.__dict__.update({k: v for k, v in _real.__dict__.items()})
    proxy.AsyncClient = cliente_cls
    sys.modules["httpx"] = proxy
    try:
        yield
    finally:
        sys.modules["httpx"] = _real


# ---------------------------------------------------------------------------
# Valores sintéticos para os marcadores do corpus — o corpus NÃO guarda CPF,
# telefone, placa ou e-mail; o carregador materializa na hora.
# ---------------------------------------------------------------------------
_MARCADOR = re.compile(r"\{\{(CPF|CNPJ|FONE|PLACA|EMAIL|CEP|NOME|APOLICE|CORRETORA):([A-Za-z0-9_]+)\}\}")

#: Nomes FICTÍCIOS (nenhum é cliente, funcionário ou corretora real — CLAUDE.md §13.9).
_NOMES = ("Carlos Exemplo", "Beatriz Modelo", "Joana Ficticia", "Paulo Amostra", "Livia Teste",
          "Otavio Simulado", "Renata Hipotese", "Mauro Ensaio")
_CORRETORAS = ("Corretora Alfa", "Corretora Beta", "Corretora Gama")


def _cpf_ficticio(semente: str) -> str:
    base = [int(c) for c in str(int(hashlib.sha1(semente.encode()).hexdigest(), 16))[:9]]
    for _ in range(2):
        pesos = range(len(base) + 1, 1, -1)
        resto = sum(a * b for a, b in zip(base, pesos)) % 11
        base.append(0 if resto < 2 else 11 - resto)
    d = "".join(map(str, base))
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"


def valor_sintetico(tipo: str, rotulo: str) -> str:
    h = int(hashlib.sha1(f"{tipo}:{rotulo}".encode()).hexdigest(), 16)
    if tipo == "CPF":
        return _cpf_ficticio(f"cpf:{rotulo}")
    if tipo == "FONE":
        return f"(99) 9{h % 10000:04d}-{(h // 10000) % 10000:04d}"
    if tipo == "PLACA":
        letras = "".join(chr(65 + (h >> (5 * i)) % 26) for i in range(3))
        return f"{letras}{h % 10}{chr(65 + (h // 7) % 26)}{(h // 13) % 100:02d}"
    if tipo == "EMAIL":
        return f"segurado.{rotulo.lower()}@exemplo.invalid"
    if tipo == "CEP":
        return f"{h % 100000:05d}-{(h // 100000) % 1000:03d}"
    if tipo == "CNPJ":
        d = f"{h % 10**12:012d}"
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/0001-{h % 97:02d}"
    if tipo == "NOME":
        return _NOMES[h % len(_NOMES)]
    if tipo == "APOLICE":
        return f"9{h % 10**14:014d}"
    if tipo == "CORRETORA":
        return _CORRETORAS[h % len(_CORRETORAS)]
    return rotulo


def materializar(obj: Any) -> Any:
    """Troca `{{CPF:A1}}` & cia por valores sintéticos DETERMINÍSTICOS."""
    if isinstance(obj, str):
        return _MARCADOR.sub(lambda m: valor_sintetico(m.group(1), m.group(2)), obj)
    if isinstance(obj, list):
        return [materializar(x) for x in obj]
    if isinstance(obj, dict):
        return {k: materializar(v) for k, v in obj.items()}
    return obj
