# -*- coding: utf-8 -*-
"""SPEC-116 U11 — a BANCADA E2E. Estende a Eval Fabric da SPEC-062; não é motor novo.

O que ela responde
------------------
"Este BRAÇO (provider, model, effort) faz ESTE TRABALHO (papel) direito, sempre,
e por quanto?" — rodando o MOTOR REAL do AutoBrokers com dublês só na borda, k
vezes por caso, e gravando no MESMO lugar da SPEC-062 (``eval_runs`` +
``eval_case_results``). Dali saem pass@1, pass^k e custo por sucesso.

    CLAUDE.md §5   o runner é o da Eval Fabric estendido; nada de `bench_*`.
    CLAUDE.md §9.2 a linha de controle é o braço-dublê `perfeito` × `burro`:
                   se o relatório não separa os dois, a bancada não mede nada.
    CLAUDE.md §9.4 o teste chama o MOTOR sobre o texto REAL do acervo.

O MOTOR de cada papel — o ponto de entrada REAL (arquivo:função)
---------------------------------------------------------------
    chat_principal / atendimento / cobranca
        N1  app/agents/graph.py:create_agent_graph → UMA volta do nó `agent`
            (app/agents/nodes.py:agent_node, com os fiscais pós-LLM) com as
            tools REAIS do papel ligadas por bind_tools; o grafo é interrompido
            ANTES do nó `tools` (``interrupt_before=["tools"]``).
        N2  o MESMO grafo inteiro, turno a turno, com `tool_node` REAL
            executando DUBLÊS de tool (mesmo nome e schema da tool real), e o
            checkpointer em memória no lugar do Postgres.
        prompt: app/core/prompts.py:build_composite_prompt (estático) +
            app/services/attendance_ficha.py:bloco_para_o_prompt (dinâmico).
    portal_decisao  N1  backend/portal_worker/adaptive.py:decide_next_action
            (``chamar_modelo=`` — o pedido montado pelo produto vai ao braço;
            erro do provedor ⇒ ``ask_human``/needs_human ⇒ BLOCKED_BY_INFRA).
            Sem o parâmetro (código antigo), o proxy de ``httpx``.
    dispatch        N1  app/services/dispatch_router.py:o_cerebro_ja_sabe (llm=)
    memoria         N1  app/services/memory_service.py:MemoryService.extract_user_facts_async (llm=)
    visao           N1  app/services/vision_service.py:describe_image (llm=)
    hyde            N1  app/services/search_service.py:SearchService._generate_hyde_doc (llm=)
                                                                   — ESQUELETO (oráculo por termo)
    extrator_planos N1  app/services/knowledge/assistance_plans_extractor.py:
            propostas_da_pagina (llm=)                             — ESQUELETO
    juiz            BLOCKED — o motor existe (evals/juiz_llm.py:julgar_com_llm(llm=),
            consertado na F3b), mas os 3 casos não têm OURO (saída, critério,
            veredito esperado). Não se inventa oráculo.            — ESQUELETO
    transcricao     BLOCKED — o ponto de injeção existe (audio_service.AudioService(
            cliente=, modelo=)), mas não há áudio sintético nem fala-ouro, e a
            fábrica de chat não constrói STT.                      — ESQUELETO

A COSTURA (F5b) — resolvedor + fábrica REAIS, com a bancada ISOLADA
-------------------------------------------------------------------
``resolver_padrao`` → ``app.factories.model_policy.resolver(papel, override=braço)``
(o MESMO catálogo e as MESMAS recusas do produto). ``construir_llm_padrao`` →
``LLMFactory.criar_de_resolvido(resolvido, service_type="bancada",
company_id=None)`` — o MESMO adaptador por provedor do produto, com:

  · o LEDGER de produção recebendo cada chamada como ``service_type='bancada'``
    e ``company_id`` NULO: custo real visível, nunca faturado
    (``workers/billing_tasks.py`` pula linha sem ``company_id``; o ledger da
    SPEC-062 — ``usage_events`` — exige ``company_id`` e fica de fora);
  · o DISJUNTOR de produção INTOCADO: o ``RelogioDoModeloCallback`` que a
    fábrica anexa é RETIRADO do braço. Um 429 da bancada não abre o breaker do
    produto — e um sucesso dela não o FECHA (``registrar_sucesso`` apaga as
    chaves no Redis de produção);
  · o custo de cada caso = ``usage_metadata`` da resposta × o preço do
    catálogo (``usage_service.calculate_cost`` — a MESMA conta do ledger).

⛔ Nenhuma mensagem sai, nenhum portal é aberto: o banco do produto é trocado
pelo `SupabaseDuble` (``dubles.borda_isolada``) enquanto o motor roda.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import logging
import math
import os
import statistics
import tempfile
import time
import unicodedata
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from . import dubles as D
from . import evaluators as E

logger = logging.getLogger(__name__)

CORPUS_DIR = Path(__file__).resolve().parents[3] / "tests" / "corpus" / "bancada"

#: Tenants FICTÍCIOS — nunca uma corretora real (CLAUDE.md §13.9).
TENANTS = {
    "A": "00000000-0000-4000-8000-0000000000a1",
    "B": "00000000-0000-4000-8000-0000000000b2",
}

RESULTADOS = ("PASS", "FAIL", "PARTIAL", "BLOCKED_BY_INFRA")

#: papel → (agent_role no grafo, risco do dataset na Eval Fabric)
#: 🔴 SPEC-116 F6 — as FLAGS de produção sob as quais o motor do agente é medido.
#: `POLICY_INTELLIGENCE_V2=true` é a configuração que o Founder foi orientado a
#: confirmar no `smith-api` (P-E0015-06): com ela a LLM REDIGE a resposta depois
#: da consulta de apólice e o contrato vira fiscal. Desligada, o turno da
#: consulta acaba no rascunho do compositor e o modelo nem escreve — mediríamos
#: menos do que o produto faz. Declarada AQUI, num lugar só, e aplicada só
#: enquanto o motor roda (`dubles.borda_isolada(env=)`).
FLAGS_DO_AGENTE = {"POLICY_INTELLIGENCE_V2": "true"}

PAPEIS: Dict[str, Dict[str, Any]] = {
    "chat_principal": {"agent_role": "core", "risco": "alto", "motor": "agente", "env": FLAGS_DO_AGENTE},
    "atendimento": {"agent_role": "attendance", "risco": "critico", "motor": "agente", "env": FLAGS_DO_AGENTE},
    "cobranca": {"agent_role": "attendance", "risco": "alto", "motor": "agente", "env": FLAGS_DO_AGENTE},
    "portal_decisao": {"risco": "critico", "motor": "portal"},
    "dispatch": {"risco": "critico", "motor": "dispatch"},
    "memoria": {"risco": "medio", "motor": "memoria"},
    "visao": {"risco": "alto", "motor": "visao"},
    "hyde": {"risco": "medio", "motor": "hyde"},
    "extrator_planos": {"risco": "medio", "motor": "extrator_planos"},
    "juiz": {"risco": "medio", "motor": "bloqueado",
             "bloqueio": "sem OURO: o motor existe (evals/juiz_llm.py:julgar_com_llm(llm=), consertado "
                         "na F3b), mas os casos não trazem saída, critério nem veredito esperado — "
                         "não se inventa oráculo (corpus v2)"},
    "transcricao": {"risco": "medio", "motor": "bloqueado",
                    "bloqueio": "sem ÁUDIO: o ponto de injeção existe (AudioService(cliente=, modelo=)), "
                                "mas não há áudio sintético nem fala-ouro, e a fábrica de chat não "
                                "constrói STT (corpus v2 + adaptador de transcrição, F6)"},
}

#: Capabilities ativas por papel quando o caso não declara (as do registro de
#: produção para o papel, medidas no BLOCO 0 — só as que soltam tool).
CAPS_PADRAO = {
    "attendance": ["operational.infocap.policy_lookup.read",
                   "operational.portal.assistance.prepare"],
    "core": ["operational.infocap.policy_lookup.read"],
}

#: Juízes cuja falha é sempre FAIL (nunca PARTIAL): errar aqui chega ao
#: segurado, produz efeito ou vaza.
DUROS = frozenset({"tool_esperada", "efeitos_exatos", "sem_efeito_proibido",
                   "sem_dado_de_outro_tenant", "sem_pii", "sem_segredo", "nao_contem",
                   "estado_final", "estrutura_valida", "execucao"})

#: Nomes de exceção de provedor que são INFRA (limite, rede, 5xx) — não modelo.
_ERROS_DE_INFRA = ("RateLimit", "APIConnection", "APITimeout", "Timeout", "InternalServer",
                   "ServiceUnavailable", "Overloaded", "APIStatus", "ConnectError",
                   "ReadTimeout", "RemoteProtocol")


# ===========================================================================
# BRAÇO, preço, teto
# ===========================================================================
def _sem_acento(s: str) -> str:
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()


@dataclass
class Braco:
    provider: str
    model: str
    effort: Optional[str] = None
    api_surface: Optional[str] = None
    preco: Optional[Dict[str, float]] = None   # SÓ para provider duble

    @classmethod
    def de(cls, valor: Any) -> "Braco":
        """`"provider:model[:effort]"` ou dict. `dublê`/`duble` viram `duble`."""
        if isinstance(valor, Braco):
            return valor
        if isinstance(valor, dict):
            prov = _sem_acento(valor.get("provider") or "")
            return cls(provider=prov, model=str(valor.get("model") or ""),
                       effort=valor.get("effort"), api_surface=valor.get("api_surface"),
                       preco=valor.get("preco"))
        partes = str(valor or "").split(":")
        if len(partes) < 2 or not partes[0] or not partes[1]:
            raise ValueError(f"braço inválido {valor!r}: use provider:model[:effort]")
        return cls(provider=_sem_acento(partes[0]), model=partes[1],
                   effort=(partes[2] if len(partes) > 2 and partes[2] else None))

    @property
    def rotulo(self) -> str:
        return f"{self.provider}:{self.model}" + (f":{self.effort}" if self.effort else "")

    @property
    def e_duble(self) -> bool:
        return self.provider == "duble"

    def override(self) -> dict:
        return {"provider": self.provider, "model": self.model, "effort": self.effort}


class TetoDeGastoAtingido(Exception):
    """A próxima chamada cruzaria o teto em US$. A bancada PARA."""


class SemPrecoConhecido(Exception):
    """Braço sem preço no catálogo: a bancada recusa rodar (não inventa preço)."""


class BancadaSemResolvedor(Exception):
    """O resolvedor da F1 não está disponível e o braço não é dublê."""


PRECO_DUBLE_PADRAO = {"entrada": 1.0, "saida": 4.0}


#: O `service_type` com que a bancada grava no ledger de produção
#: (`token_usage_logs`). ⛔ Nunca "chat"/"plataforma": é o que separa o custo da
#: medição do custo do produto — e, com `company_id` NULO, nunca é faturado.
SERVICE_TYPE_DA_BANCADA = "bancada"

#: O teto de saída com que o braço é CONSTRUÍDO — o mesmo piso de quem conversa
#: no produto (`llm_factory.PISO_DE_SAIDA_DA_CONVERSA`). É também o que a
#: reserva do teto em US$ usa, e não o `max_output` do catálogo (128 mil tokens
#: fariam a reserva de UMA chamada de Sonnet custar US$ 1,28).
MAX_TOKENS_DA_BANCADA = 8192


def preco_do_catalogo(braco: Braco, cliente: Any = None) -> Optional[Dict[str, Any]]:
    """US$ por milhão de tokens, do catálogo `llm_pricing` — pelo `UsageService`,
    a MESMA fonte (e o mesmo cache/snapshot) que o ledger usa para cobrar.

    ⛔ NUNCA cai no preço de outro modelo: sem linha com preço → ``None`` → a
    bancada recusa o braço. Preço por MINUTO (áudio) também é recusado aqui: a
    bancada de chat não sabe medir minuto. (`cliente` fica pela compatibilidade.)
    """
    if braco.e_duble:
        return dict(braco.preco or PRECO_DUBLE_PADRAO)
    try:
        from app.services.usage_service import get_usage_service

        p = get_usage_service().get_pricing(braco.model)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Bancada] catálogo ilegível (%s)", type(exc).__name__)
        return None
    if not p or p.get("unit") == "minute":
        return None
    try:
        return {"entrada": float(p["input"]), "saida": float(p["output"]),
                "modelo": braco.model, "provider": braco.provider,
                "fonte": "llm_pricing (usage_service)"}
    except (KeyError, TypeError, ValueError):
        return None


class Orcamento:
    """O teto em US$ da rodada inteira (D-116-09). Confere ANTES de cada chamada."""

    def __init__(self, teto_usd: float):
        self.teto_usd = float(teto_usd)
        self.gasto = 0.0

    def reservar(self, estimativa: float) -> None:
        if self.gasto + estimativa > self.teto_usd:
            raise TetoDeGastoAtingido(
                f"teto_usd: gasto {self.gasto:.4f} + estimativa {estimativa:.4f} > teto {self.teto_usd:.2f}")

    def gastar(self, valor: float) -> None:
        self.gasto += float(valor or 0)


def teto_padrao() -> float:
    try:
        return float(os.getenv("BANCADA_TETO_USD") or 100)
    except ValueError:
        return 100.0


def custo_de(usage: dict, preco: Dict[str, Any]) -> float:
    """Custo pelo `usage_metadata` do LangChain e o preço do catálogo.

    Braço real (preço veio do catálogo): ``usage_service.calculate_cost`` — a
    MESMA conta que o `CostCallbackHandler` grava no ledger, com o mesmo balde
    de cache por provedor (📊 F12: a langchain-openai põe o cache da OpenAI em
    `cache_read`, o balde da Anthropic). Dublê: a conta local, preço fictício.
    """
    entrada = int(usage.get("input_tokens") or 0)
    saida = int(usage.get("output_tokens") or 0)
    det = usage.get("input_token_details") or {}
    lido = int(det.get("cache_read") or 0)
    escrito = int(det.get("cache_creation") or 0)
    if preco.get("modelo"):
        from app.services.usage_service import get_usage_service

        cached = int(det.get("cached_tokens") or 0)
        if (preco.get("provider") or "") != "anthropic" and lido and not cached:
            cached, lido = lido, 0
        return float(get_usage_service().calculate_cost(
            preco["modelo"], entrada, saida, escrito, lido, cached))
    normal = max(0, entrada - lido - escrito)
    p_in = preco["entrada"]
    return (normal * p_in
            + lido * preco.get("cache_leitura", p_in * 0.10)
            + escrito * preco.get("cache_escrita", p_in * 1.25)
            + saida * preco["saida"]) / 1_000_000


# ===========================================================================
# O MEDIDOR — envolve o LLM do braço: teto, tokens, custo, rastro
# ===========================================================================
class Medidor:
    """Duck-typed como um chat model: `bind_tools`, `ainvoke`, `invoke`."""

    def __init__(self, interno, *, preco: Dict[str, float], orcamento: Orcamento,
                 max_output: int = 8192, _estado: Optional[dict] = None, _tools_hash: str = ""):
        self.interno = interno
        self.preco = preco
        self.orcamento = orcamento
        self.max_output = int(max_output or 8192)
        self.estado = _estado if _estado is not None else {
            "chamadas": 0, "tentativas": 0, "tokens": {"in": 0, "out": 0, "cache_read": 0, "cache_write": 0,
                                       "raciocinio": 0},
            "custo": 0.0, "tool_calls": [], "modelos_reais": [], "prompts": set(),
            "tools": set()}
        self._tools_hash = _tools_hash

    @property
    def model_name(self):
        return getattr(self.interno, "model_name", None) or getattr(self.interno, "model", None)

    def bind_tools(self, tools, **kwargs):
        try:
            nomes = sorted(json.dumps({"n": getattr(t, "name", str(t)),
                                       "s": (t.args_schema.model_json_schema()
                                             if getattr(t, "args_schema", None) is not None
                                             and hasattr(t.args_schema, "model_json_schema") else None)},
                                      sort_keys=True, ensure_ascii=False, default=str)
                           for t in tools or [])
            th = hashlib.sha256("\n".join(nomes).encode()).hexdigest()[:12]
        except Exception:  # noqa: BLE001
            th = "indisponivel"
        self.estado["tools"].add(th)
        return Medidor(self.interno.bind_tools(tools, **kwargs), preco=self.preco,
                       orcamento=self.orcamento, max_output=self.max_output,
                       _estado=self.estado, _tools_hash=th)

    def _antes(self, entrada) -> None:
        msgs = entrada if isinstance(entrada, list) else [entrada]
        texto = ""
        for m in msgs:
            conteudo = D._texto_de(getattr(m, "content", m))
            texto += conteudo
            if D._tipo(m) == "system":
                self.estado["prompts"].add(hashlib.sha256(conteudo.encode()).hexdigest()[:12])
        estimativa = (D.estimar_tokens(texto) * self.preco["entrada"]
                      + self.max_output * self.preco["saida"]) / 1_000_000
        self.orcamento.reservar(estimativa)
        self.estado["tentativas"] = self.estado.get("tentativas", 0) + 1

    def _depois(self, resp) -> None:
        self.estado["chamadas"] += 1
        u = getattr(resp, "usage_metadata", None) or {}
        t = self.estado["tokens"]
        t["in"] += int(u.get("input_tokens") or 0)
        t["out"] += int(u.get("output_tokens") or 0)
        det_in = u.get("input_token_details") or {}
        det_out = u.get("output_token_details") or {}
        t["cache_read"] += int(det_in.get("cache_read") or 0)
        t["cache_write"] += int(det_in.get("cache_creation") or 0)
        t["raciocinio"] += int(det_out.get("reasoning") or 0)
        custo = custo_de(u, self.preco)
        self.estado["custo"] += custo
        self.orcamento.gastar(custo)
        meta = getattr(resp, "response_metadata", None) or {}
        real = meta.get("model_name") or meta.get("model")
        if real:
            self.estado["modelos_reais"].append(str(real))
        for c in getattr(resp, "tool_calls", None) or []:
            self.estado["tool_calls"].append({"name": c.get("name"), "args": c.get("args")})

    def invoke(self, entrada, config=None, **kwargs):
        self._antes(entrada)
        resp = self.interno.invoke(entrada, config=config, **kwargs)
        self._depois(resp)
        return resp

    async def ainvoke(self, entrada, config=None, **kwargs):
        self._antes(entrada)
        resp = await self.interno.ainvoke(entrada, config=config, **kwargs)
        self._depois(resp)
        return resp


# ===========================================================================
# Defaults injetáveis: resolvedor (F1) e construtor do LLM (fábrica)
# ===========================================================================
def _campo(obj: Any, nome: str, padrao: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(nome, padrao)
    return getattr(obj, nome, padrao)


def resolver_padrao(papel: str, *, override: dict, **_k) -> Any:
    """O resolvedor da F1 com override da bancada; dublê resolve sozinho."""
    if _sem_acento(override.get("provider")) == "duble":
        return {"papel": papel, "provider": "duble", "model": override.get("model"),
                "effort": override.get("effort"), "api_surface": "duble",
                "capacidades": {"tools": True, "max_output": 8192},
                "origem": "override_da_bancada", "versao_da_rota": "bancada-duble",
                "motivo": "braço-dublê da linha de controle"}
    try:
        from app.factories.model_policy import resolver as _resolver  # F1
    except (ImportError, AttributeError) as exc:
        raise BancadaSemResolvedor(
            "o resolvedor da F1 (model_policy.resolver) não está disponível — "
            "rode só braços `duble:*` até a costura F5b") from exc
    return _resolver(papel, override=override)


class BancadaSemIsolamento(Exception):
    """O braço construído escreveria como produto (ledger faturável ou disjuntor)."""


def isolar_do_produto(llm: Any) -> Any:
    """Tira do braço o `RelogioDoModeloCallback` e CONFERE o ledger.

    ⛔ O relógio escreve no disjuntor de PRODUÇÃO (Redis `llm_breaker:<provedor>`):
    falha da bancada abriria o breaker do atendimento; sucesso dela o FECHARIA
    (`registrar_sucesso` apaga as chaves). A bancada mede um braço — não pode
    decidir se o produto fala com o provedor.

    🔴 E confere, em vez de presumir: o custo tem de sair como
    ``service_type='bancada'`` e ``company_id`` NULO. Qualquer outra coisa →
    ``BancadaSemIsolamento`` (a bancada NÃO roda).
    """
    from app.core.callbacks.cost_callback import CostCallbackHandler
    from app.core.relogio_do_modelo import RelogioDoModeloCallback

    atuais = list(getattr(llm, "callbacks", None) or [])
    llm.callbacks = [c for c in atuais if not isinstance(c, RelogioDoModeloCallback)]
    custos = [c for c in llm.callbacks if isinstance(c, CostCallbackHandler)]
    if not custos:
        raise BancadaSemIsolamento("o braço saiu da fábrica sem o callback de custo — "
                                   "o custo real ficaria invisível")
    for c in custos:
        if c.service_type != SERVICE_TYPE_DA_BANCADA or c.company_id is not None:
            raise BancadaSemIsolamento(
                f"o braço gravaria no ledger como service_type={c.service_type!r} "
                f"company_id={'<preenchido>' if c.company_id else None} — faturável/misturado")
    if any(isinstance(c, RelogioDoModeloCallback) for c in llm.callbacks):
        raise BancadaSemIsolamento("o relógio de produção continua no braço")
    return llm


def construir_llm_padrao(resolvido: Any, callbacks: Optional[list] = None, *,
                         api_key: Optional[str] = None) -> Any:
    """Dublê → `LLMDuble`. Real → a fábrica do PRODUTO (`criar_de_resolvido`),
    o mesmo adaptador por provedor, ISOLADA do produto (`isolar_do_produto`).
    ⛔ Nunca um cliente novo aqui (CLAUDE.md §5)."""
    provider = _campo(resolvido, "provider")
    model = _campo(resolvido, "model")
    if provider == "duble":
        return D.LLMDuble(model)
    from app.factories.llm_factory import LLMFactory

    llm = LLMFactory.criar_de_resolvido(
        resolvido, callbacks=list(callbacks or []), api_key=api_key,
        company_id=None, agent_id=None, service_type=SERVICE_TYPE_DA_BANCADA,
        max_tokens=MAX_TOKENS_DA_BANCADA)
    return isolar_do_produto(llm)


# ===========================================================================
# CORPUS
# ===========================================================================
def manifesto() -> dict:
    p = CORPUS_DIR / "MANIFESTO.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"versao": 1}


def carregar_casos(papel: str, *, filtro: Optional[str] = None, critico: bool = False,
                   nivel: Optional[str] = None) -> List[dict]:
    """`filtro`: trecho da chave, ou vários separados por vírgula (qualquer um casa)."""
    arq = CORPUS_DIR / papel / "casos.jsonl"
    if not arq.exists():
        return []
    trechos = [t.strip() for t in str(filtro or "").split(",") if t.strip()]
    casos = []
    for n, linha in enumerate(arq.read_text(encoding="utf-8").splitlines(), 1):
        if not linha.strip():
            continue
        caso = json.loads(linha)
        caso.setdefault("_linha", n)
        if nivel and caso.get("nivel") != nivel:
            continue
        if critico and not caso.get("critico"):
            continue
        if trechos and not any(t in caso.get("chave", "") for t in trechos):
            continue
        casos.append(caso)
    return casos


def carregar_corpus(gravar: bool = False, cliente: Any = None,
                    papeis: Optional[List[str]] = None) -> Dict[str, dict]:
    """Casos → `eval_datasets` / `eval_dataset_versions` / `eval_cases`.

    Um dataset por papel (`bancada-<papel>`), versão = `MANIFESTO.json`,
    congelada ao nascer. IDEMPOTENTE: versão que já existe não recebe caso
    (versão congelada não muda — SPEC-062 §10.2); caso que mudou sem subir a
    versão aparece como `divergentes`, e é a deixa para subir o manifesto.
    `gravar=False` só conta.
    """
    versao = int(manifesto().get("versao") or 1)
    saida: Dict[str, dict] = {}
    db = getattr(cliente, "client", cliente) if cliente is not None else None
    if gravar and db is None:
        from app.core.database import get_supabase_client

        db = getattr(get_supabase_client(), "client", get_supabase_client())
    for papel in papeis or list(PAPEIS):
        casos = carregar_casos(papel)
        info = {"papel": papel, "versao": versao, "casos": len(casos), "novos": 0,
                "divergentes": 0, "dataset_id": None, "version_id": None, "ids": {}}
        saida[papel] = info
        if not gravar or not casos:
            continue
        slug = f"bancada-{papel}"
        ds = db.table("eval_datasets").select("*").eq("slug", slug).limit(1).execute().data or []
        if not ds:
            ds = db.table("eval_datasets").insert({
                "slug": slug, "nome": f"Bancada SPEC-116 · {papel}", "dominio": papel,
                "descricao": "Casos mascarados do acervo real (backend/tests/corpus/bancada).",
                "risco": PAPEIS[papel]["risco"]}).execute().data
        info["dataset_id"] = ds[0]["id"]
        vs = (db.table("eval_dataset_versions").select("*").eq("dataset_id", info["dataset_id"])
              .eq("versao", versao).limit(1).execute().data or [])
        nova_versao = not vs
        if nova_versao:
            vs = db.table("eval_dataset_versions").insert({
                "dataset_id": info["dataset_id"], "versao": versao,
                "notas": f"SPEC-116 corpus v{versao} — {len(casos)} casos",
                "congelada_em": datetime.now(timezone.utc).isoformat()}).execute().data
        info["version_id"] = vs[0]["id"]
        existentes = {c["chave"]: c for c in (db.table("eval_cases").select("*")
                                             .eq("version_id", info["version_id"]).execute().data or [])}
        for caso in casos:
            atual = existentes.get(caso["chave"])
            if atual:
                info["ids"][caso["chave"]] = atual["id"]
                if (atual.get("expected") or {}) != (caso.get("oraculo") or {}):
                    info["divergentes"] += 1
                continue
            if not nova_versao:
                info["divergentes"] += 1   # versão congelada não recebe caso novo
                continue
            linha = db.table("eval_cases").insert({
                "version_id": info["version_id"], "chave": caso["chave"],
                "entrada": {k: v for k, v in caso.items() if k not in ("oraculo", "_linha")},
                "expected": caso.get("oraculo") or {},
                "peso": 1,
                "tags": [papel, str(caso.get("nivel") or "N1")] + (["critico"] if caso.get("critico") else []),
            }).execute().data
            info["ids"][caso["chave"]] = linha[0]["id"]
            info["novos"] += 1
    return saida


# ===========================================================================
# MOTORES
# ===========================================================================
@dataclass
class Contexto:
    llm: Any
    braco: Braco
    registro: D.RegistroDeEfeitos
    banco: D.SupabaseDuble
    medidor: Medidor
    falhas: Optional[D.LLMComFalhas] = None
    saver: Any = None
    notas: List[str] = field(default_factory=list)
    resolvido: Any = None


class Bloqueado(Exception):
    """O motor não pôde rodar por motivo NOSSO (arnês, costura, dublê)."""


def _mensagens(historico: List[dict]):
    from langchain_core.messages import AIMessage, HumanMessage

    out = []
    for m in historico or []:
        papel = m.get("de") or m.get("role")
        cls = HumanMessage if papel in ("segurado", "corretor", "user", "human") else AIMessage
        out.append(cls(content=str(m.get("texto") or m.get("content") or "")))
    return out


def _estado_base(caso: dict, braco: Braco, agent_role: str, tenant: str) -> dict:
    """O state do grafo com o PROMPT REAL do papel (as funções do produto)."""
    from app.core.prompts import build_composite_prompt, data_e_hora_agora

    ent = caso.get("entrada") or {}
    company_id = TENANTS[tenant]
    agente = ent.get("agente") or {}
    static = build_composite_prompt(
        agente.get("instrucoes") or "Seja cordial, objetivo e fale como a corretora.",
        agent_role=agent_role,
        agent_display_name=agente.get("nome") or "",
        company_display_name=agente.get("corretora") or "")
    dinamico = f"\n\n{data_e_hora_agora()}"
    ficha = ent.get("ficha") or {}
    if ficha:
        try:
            from app.agents.graph import _slots_obrigatorios_do_caso
            from app.services.attendance_ficha import bloco_para_o_prompt

            bloco = bloco_para_o_prompt(ficha, _slots_obrigatorios_do_caso(ficha))
            if bloco:
                dinamico += f"\n\n{bloco}"
        except Exception as exc:  # noqa: BLE001
            logger.warning("[Bancada] bloco da ficha indisponível (%s)", type(exc).__name__)
    agent_data = {"id": None, "agent_role": agent_role, "name": agente.get("nome") or "",
                  "tools_config": {}, "company_id": company_id,
                  "llm_provider": braco.provider if not braco.e_duble else "openai",
                  "llm_model": braco.model}
    return {
        "company_id": company_id, "user_id": f"bancada-{tenant}",
        "session_id": f"bancada-{caso.get('chave')}-{tenant}",
        "company_config": {}, "agent_data": agent_data,
        "system_prompt": static + dinamico, "static_prompt": static, "dynamic_context": dinamico,
        "rag_context": "", "rag_chunks": [], "tools_used": [], "policy_response_contract": None,
        "infocap_policy_context": ent.get("infocap_policy_context"),
        "llm_response_time_ms": 0, "tokens_input": 0, "tokens_output": 0, "tokens_total": 0,
        "final_response": None, "allowed_http_tools": [], "internal_steps": [],
    }


async def _grafo_real(ctx: Contexto, *, agent_role: str, tenant: str, caps: List[str],
                      estados_dubles: dict):
    """`create_agent_graph` REAL; trocados só: fábrica do LLM (→ braço),
    checkpointer (→ memória), registro de capabilities (→ as do caso) e o
    executor de tool (→ `tool_node` REAL sobre DUBLÊS com o schema real)."""
    import app.agents.graph as G

    real_tool_node = G.tool_node
    cache: Dict[str, D.DubleDeTool] = {}

    async def _tool_node_com_dubles(state, tools):
        dub = []
        for t in tools:
            if t.name not in cache:
                cache[t.name] = D.DubleDeTool(t, registro=ctx.registro, tenant=tenant,
                                              estado=estados_dubles.get(t.name))
            dub.append(cache[t.name])
        return await real_tool_node(state, tools=dub)

    rota_do_braco = _resolvido_sem_reserva(ctx.resolvido, ctx.braco)

    class _Fabrica:
        """O dublê da FÁBRICA no grafo — o contrato da F2: o grafo pergunta
        `resolver_para` (o Model Router) e constrói com `create_llm(...,
        modelo_resolvido=)`. Aqui a resposta é o BRAÇO, sem reserva (a bancada
        mede UM braço; a reserva da rota traria outro modelo para a conta)."""

        @staticmethod
        def resolver_para(*_a, **_k):
            return rota_do_braco

        @staticmethod
        def create_llm(*_a, **_k):
            return ctx.llm

    async def _saver():
        return ctx.saver

    ativos = {c: {"status": "active", "reason": "bancada"} for c in caps}
    with contextlib.ExitStack() as pilha:
        pilha.enter_context(D.atributo_trocado(G, "LLMFactory", _Fabrica))
        pilha.enter_context(D.atributo_trocado(G, "get_async_postgres_checkpointer", _saver))
        pilha.enter_context(D.atributo_trocado(G, "resolve_active_capabilities",
                                               lambda *_a, **_k: dict(ativos)))
        pilha.enter_context(D.atributo_trocado(G, "get_api_key_for_provider", lambda *_a, **_k: ""))
        pilha.enter_context(D.atributo_trocado(G, "tool_node", _tool_node_com_dubles))
        return await G.create_agent_graph(
            company_config={}, api_key="", qdrant_service=None, supabase_client=ctx.banco,
            company_id=TENANTS[tenant], agent_data={
                "id": None, "agent_role": agent_role, "tools_config": {}},
            enable_logging=False)


def _resolvido_sem_reserva(resolvido: Any, braco: Braco) -> Any:
    """O `ModeloResolvido` do braço com `reserva=None` (dublê: um equivalente)."""
    import dataclasses
    import types

    if resolvido is not None and dataclasses.is_dataclass(resolvido):
        return dataclasses.replace(resolvido, reserva=None)
    r = dict(resolvido or {}) if isinstance(resolvido, dict) else {}
    return types.SimpleNamespace(
        papel=r.get("papel") or "", provider=r.get("provider") or braco.provider,
        model=r.get("model") or braco.model, effort=r.get("effort", braco.effort),
        api_surface=r.get("api_surface") or "duble", capacidades=r.get("capacidades") or {},
        classe_de_dado="pii", lifecycle="APPROVED", reserva=None,
        origem=r.get("origem") or "bancada", versao_da_rota=r.get("versao_da_rota"),
        motivo=r.get("motivo") or "braço da bancada", base_url=None, api_key_env=None)


def _e_falha_de_provedor(exc: BaseException) -> bool:
    return isinstance(exc, (D.FalhaInjetada, asyncio.TimeoutError))


async def _com_retomada(fazer, retomar, ctx: Contexto):
    """Falha INJETADA no provedor → UMA retomada do mesmo passo (é o que se
    mede: o motor se recupera sem refazer efeito). Falha não injetada sobe."""
    try:
        return await fazer()
    except TetoDeGastoAtingido:
        raise
    except Exception as exc:  # noqa: BLE001
        injetou = bool(ctx.falhas and ctx.falhas.disparadas)
        if not (_e_falha_de_provedor(exc) and injetou):
            raise
        ctx.notas.append(f"retomada após {type(exc).__name__}")
        return await retomar()


def _texto_do_turno(out: Any) -> str:
    """O que o PRODUTO envia ao fim do turno: `final_response` do estado quando
    existe (graph.py `run_agent`: `result.get("final_response")` primeiro), senão
    o texto da última AIMessage. 🔴 SPEC-116 F6: ler só a AIMessage perdia o texto
    que o fiscal pós-LLM (nodes.py `guarded_final`) ou o contrato da apólice
    (`should_continue_after_tools` → end) puseram no lugar."""
    out = out or {}
    final = out.get("final_response")
    if isinstance(final, str) and final.strip():
        return final
    msgs = out.get("messages") or []
    ultima = next((m for m in reversed(msgs) if D._tipo(m) == "ai"), None)
    return D._texto_de(getattr(ultima, "content", "")) if ultima is not None else ""


def _saida_do_agente(mensagens: list, ctx: Contexto, textos: List[str], turnos: int) -> dict:
    ultima = next((m for m in reversed(mensagens) if D._tipo(m) == "ai"), None)
    calls = [{"name": c.get("name"), "args": c.get("args")}
             for c in (getattr(ultima, "tool_calls", None) or [])]
    return {"texto": "\n".join(t for t in textos if t),
            "tool_calls": calls,
            "tool_calls_todas": list(ctx.medidor.estado["tool_calls"]),
            "efeitos": {t: ctx.registro.contagem(t) for t in {c["tool"] for c in ctx.registro.efeitos()}},
            "duplicados": ctx.registro.duplicados(),
            "turnos": turnos}


async def motor_agente(caso: dict, ctx: Contexto) -> dict:
    """chat_principal · atendimento · cobranca — N1 (uma volta) ou N2 (trajetória)."""
    from langchain_core.messages import HumanMessage

    papel = caso["papel"]
    agent_role = PAPEIS[papel]["agent_role"]
    ent = caso.get("entrada") or {}
    tenant = caso.get("tenant") or "A"
    caps = ent.get("capacidades") or CAPS_PADRAO.get(agent_role, [])
    estados = ent.get("dubles") or {}
    # a ficha também mora no "banco" (o fiscal da pergunta repetida lê de lá)
    for tl in {tenant} | ({(ent.get("outro_tenant") or {}).get("tenant")} - {None}):
        ctx.banco.tabelas.setdefault("conversations", []).append({
            "company_id": TENANTS[tl], "session_id": f"bancada-{caso['chave']}-{tl}",
            "ficha_atendimento": ent.get("ficha") if tl == tenant else
            (ent.get("outro_tenant") or {}).get("ficha")})

    if caso.get("nivel") == "N1":
        grafo = await _grafo_real(ctx, agent_role=agent_role, tenant=tenant, caps=caps,
                                  estados_dubles=estados)
        base = _estado_base(caso, ctx.braco, agent_role, tenant)
        base["ficha_atendimento"] = ent.get("ficha")
        historico = _mensagens(ent.get("historico") or [])
        entrada_msg = {**base, "messages": historico + [HumanMessage(content=str(ent.get("mensagem") or ""))]}
        cfg = {"configurable": {"thread_id": f"{base['company_id']}:{base['session_id']}"}}
        out = await _com_retomada(
            lambda: grafo.ainvoke(entrada_msg, cfg, interrupt_before=["tools"]),
            lambda: grafo.ainvoke(None, cfg, interrupt_before=["tools"]), ctx)
        msgs = (out or {}).get("messages") or []
        texto = _texto_do_turno(out)
        return _saida_do_agente(msgs, ctx, [texto], ctx.medidor.estado["chamadas"])

    # ---------------- N2: trajetória ----------------
    textos_a: List[str] = []
    textos_b: List[str] = []
    contexto_por_turno: List[list] = []   # chaves de `infocap_policy_context` após cada turno do A
    outro = ent.get("outro_tenant") or {}
    falhas = caso.get("falhas_injetadas") or []
    duplicar = {int(f.get("no_turno") or 1) for f in falhas if f.get("tipo") == "mensagem_duplicada"}
    atrasar = {int(f.get("no_turno") or 1) for f in falhas if f.get("tipo") == "mensagem_atrasada"}

    async def conversar(tl: str, turnos: List[dict], sink: List[str], estados_tl: dict, ficha):
        grafo = await _grafo_real(ctx, agent_role=agent_role, tenant=tl, caps=caps,
                                  estados_dubles=estados_tl)
        base = _estado_base({**caso, "entrada": {**ent, "ficha": ficha}}, ctx.braco, agent_role, tl)
        cfg = {"configurable": {"thread_id": f"{base['company_id']}:{base['session_id']}"}}
        ordem = list(range(1, len(turnos) + 1))
        for i in sorted(atrasar):
            if i < len(ordem):
                ordem[i - 1], ordem[i] = ordem[i], ordem[i - 1]
        entregas = []
        for i in ordem:
            entregas.append(i)
            if i in duplicar:
                entregas.append(i)
        for i in entregas:
            texto = str(turnos[i - 1].get("segurado") or "")
            inp = {**base, "messages": [HumanMessage(content=texto)]}
            out = await _com_retomada(lambda: grafo.ainvoke(inp, cfg),
                                      lambda: grafo.ainvoke(None, cfg), ctx)
            sink.append(_texto_do_turno(out))
            if tl == tenant:
                contexto_por_turno.append(sorted((out or {}).get("infocap_policy_context") or {}))

    if outro.get("turnos"):
        await conversar(outro.get("tenant") or "B", outro["turnos"], textos_b,
                        outro.get("dubles") or estados, outro.get("ficha"))
    # o que o tenant B fez fica FORA da saída do A: o juiz de vazamento olha só o A
    desde = len(ctx.medidor.estado["tool_calls"])
    await conversar(tenant, ent.get("turnos") or [], textos_a, estados, ent.get("ficha"))
    saida = _saida_do_agente([], ctx, textos_a, ctx.medidor.estado["chamadas"])
    saida["tool_calls_todas"] = list(ctx.medidor.estado["tool_calls"][desde:])
    fichas = {l.get("session_id"): l.get("ficha_atendimento")
              for l in ctx.banco.tabelas.get("conversations", [])}
    ficha_a = fichas.get(f"bancada-{caso['chave']}-{tenant}") or {}
    saida["estado"] = {"fase": (ficha_a or {}).get("fase"),
                       "tools_usadas": sorted({c["name"] for c in saida["tool_calls_todas"]}),
                       "contexto_da_apolice_por_turno": contexto_por_turno}
    saida["efeitos"] = {t: ctx.registro.contagem(t, tenant)
                        for t in {c["tool"] for c in ctx.registro.efeitos()}}
    return saida


def _mensagens_do_pedido(corpo: dict) -> list:
    """O corpo que o PRODUTO montou (Chat Completions, Messages ou Responses) →
    mensagens do LangChain para o braço. O prompt é o do produto, byte a byte."""
    from langchain_core.messages import HumanMessage, SystemMessage

    msgs: list = []
    if corpo.get("system"):                                   # anthropic messages
        msgs.append(SystemMessage(content=D._texto_de(corpo["system"])))
    for m in (corpo.get("messages") or corpo.get("input") or []):
        cls = SystemMessage if m.get("role") in ("system", "developer") else HumanMessage
        msgs.append(cls(content=D._texto_de(m.get("content"))))
    return msgs


def chamador_do_braco(llm: Any, pedidos: List[dict]) -> Callable[[dict], Any]:
    """O `chamar_modelo` que a bancada entrega ao portal (SPEC-116 F3b).

    Recebe o pedido montado pelo produto (sem segredo), manda as MESMAS
    mensagens ao braço e devolve a resposta no formato Chat Completions.
    Erro do braço SOBE — é o produto quem decide o que fazer com ele
    (hoje: `ask_human` com o motivo, nunca outro modelo calado)."""

    async def _chamar(pedido: dict) -> dict:
        reg = {k: pedido.get(k) for k in ("papel", "provider", "api_surface", "model", "url")}
        pedidos.append(reg)
        try:
            resp = await llm.ainvoke(_mensagens_do_pedido(pedido.get("corpo") or {}))
        except Exception as exc:  # noqa: BLE001
            reg["erro"] = type(exc).__name__
            raise
        u = getattr(resp, "usage_metadata", None) or {}
        meta = getattr(resp, "response_metadata", None) or {}
        return {"choices": [{"message": {"content": D._texto_de(getattr(resp, "content", ""))}}],
                "model": meta.get("model_name") or meta.get("model"),
                "usage": {"prompt_tokens": int(u.get("input_tokens") or 0),
                          "completion_tokens": int(u.get("output_tokens") or 0)}}

    return _chamar


def rota_do_portal_para(braco: Braco, resolvido: Any):
    """O `ModeloDoPortal` do BRAÇO (SPEC-116 F6) — injetado em `decide_next_action(rota=)`
    para o corpo do pedido sair no formato do provedor DELE (`montar_pedido`:
    JSON mode, `reasoning`/`output_config.effort`, sem `temperature` onde o catálogo
    proíbe). Os campos vêm do resolvedor da F1 — o mesmo catálogo do produto."""
    from portal_worker.modelo_do_portal import PAPEL, ModeloDoPortal

    return ModeloDoPortal(
        papel=PAPEL, provider=_campo(resolvido, "provider") or braco.provider,
        model=_campo(resolvido, "model") or braco.model, effort=_campo(resolvido, "effort"),
        api_surface=_campo(resolvido, "api_surface") or "",
        capacidades=dict(_campo(resolvido, "capacidades") or {}),
        classe_de_dado=_campo(resolvido, "classe_de_dado") or "pii",
        lifecycle=_campo(resolvido, "lifecycle") or "", origem="bancada",
        versao_da_rota=None, base_url=_campo(resolvido, "base_url"),
        api_key_env=_campo(resolvido, "api_key_env"), precos={}, reserva=None)


def chamador_http_do_braco(modelo: Any, ctx: "Contexto", pedidos: List[dict]) -> Callable[[dict], Any]:
    """O `chamar_modelo` do braço REAL no portal (SPEC-116 F6): posta o CORPO que
    o produto montou para o provedor do braço (`modelo_do_portal._postar_no_provedor`,
    o mesmo transporte do worker) e mede — teto antes, custo depois pelo
    `usage_service.calculate_cost` (a conta do ledger) e UMA linha no ledger com
    ``service_type='bancada'`` e ``company_id`` NULO (como o `CostCallbackHandler`
    faria no braço de chat). Erro SOBE: o produto devolve `ask_human`."""
    from portal_worker import modelo_do_portal as MP

    med = ctx.medidor

    async def _chamar(pedido: dict) -> dict:
        reg = {k: pedido.get(k) for k in ("papel", "provider", "api_surface", "model", "url")}
        corpo = pedido.get("corpo") or {}
        reg["temperature"] = corpo.get("temperature")
        reg["esforco"] = (corpo.get("reasoning") or {}).get("effort") or \
            (corpo.get("output_config") or {}).get("effort") or corpo.get("reasoning_effort")
        reg["formato"] = sorted(k for k in ("response_format", "text", "system") if k in corpo)
        pedidos.append(reg)
        med.orcamento.reservar((D.estimar_tokens(json.dumps(corpo, ensure_ascii=False)) * med.preco["entrada"]
                                + med.max_output * med.preco["saida"]) / 1_000_000)
        med.estado["tentativas"] = med.estado.get("tentativas", 0) + 1
        try:
            if ctx.falhas is not None:
                ctx.falhas._talvez_falhar()
            dados = await MP._postar_no_provedor(pedido, MP._cabecalhos_do_provedor(modelo))
        except Exception as exc:  # noqa: BLE001
            reg["erro"] = type(exc).__name__ + (f": {str(exc)[:120]}" if str(exc) else "")
            raise
        uso = MP.uso_da_resposta(dados)
        from app.services.usage_service import get_usage_service

        us = get_usage_service()
        custo = float(us.calculate_cost(modelo.model, uso["input"], uso["output"], uso["cache_write"],
                                        uso["cache_read"], uso["cached"]) or 0.0)
        t = med.estado["tokens"]
        t["in"] += uso["input"]
        t["out"] += uso["output"]
        t["cache_read"] += uso["cache_read"] + uso["cached"]
        t["cache_write"] += uso["cache_write"]
        t["raciocinio"] += uso["reasoning"]
        med.estado["chamadas"] += 1
        med.estado["custo"] += custo
        med.orcamento.gastar(custo)
        real = (dados or {}).get("model") if isinstance(dados, dict) else None
        if real:
            med.estado["modelos_reais"].append(str(real))
        try:
            us.track_cost_sync(service_type=SERVICE_TYPE_DA_BANCADA, model=modelo.model,
                               input_tokens=uso["input"], output_tokens=uso["output"], company_id=None,
                               agent_id=None,
                               details={"papel": "portal_decisao", "origem": "bancada:portal",
                                        "modelo_real": real, "esforco": modelo.effort,
                                        "reasoning_tokens": uso["reasoning"]},
                               cache_creation_tokens=uso["cache_write"], cache_read_tokens=uso["cache_read"],
                               cached_tokens=uso["cached"])
        except Exception as exc:  # noqa: BLE001 — perder a linha não derruba a medição
            logger.warning("[Bancada] ledger do portal não gravado (%s)", type(exc).__name__)
        return dados

    return _chamar


async def motor_portal(caso: dict, ctx: Contexto) -> dict:
    """`decide_next_action` REAL. Com `chamar_modelo=` (F3b) o pedido do produto
    vai ao braço e o ledger do portal NÃO é escrito; sem o parâmetro (código
    antigo), o proxy de `httpx` de sempre."""
    import inspect

    from portal_worker.adaptive import decide_next_action

    ent = caso.get("entrada") or {}
    pedidos: List[dict] = []
    args = (ent.get("tela") or {}, str(ent.get("objetivo") or ""), ent.get("dados") or {},
            ent.get("acoes_ja_feitas") or [])
    parametros = inspect.signature(decide_next_action).parameters
    if "rota" in parametros and not ctx.braco.e_duble:
        # 🔴 SPEC-116 F6: o corpo do pedido é o do provedor do BRAÇO, e ele vai
        # ao provedor pelo transporte do worker (não por um cliente LangChain).
        modelo = rota_do_portal_para(ctx.braco, ctx.resolvido)
        acao = await decide_next_action(*args, force=bool(ent.get("force")), rota=modelo,
                                        chamar_modelo=chamador_http_do_braco(modelo, ctx, pedidos))
    elif "chamar_modelo" in parametros:
        acao = await decide_next_action(*args, force=bool(ent.get("force")),
                                        chamar_modelo=chamador_do_braco(ctx.llm, pedidos))
    else:  # pragma: no cover — portal anterior à F3b
        env = {"PORTAL_VISION_MODEL": ctx.braco.model,
               "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY") or "bancada-sem-chave-real"}
        antes = {k: os.environ.get(k) for k in env}
        os.environ.update(env)
        try:
            with D.httpx_do_portal(D.cliente_http_que_fala_com(ctx.llm, pedidos)):
                acao = await decide_next_action(*args, force=bool(ent.get("force")))
        finally:
            for k, v in antes.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
    saida = {"texto": json.dumps(acao, ensure_ascii=False), "estado": dict(acao or {}),
             "estrutura": acao if isinstance(acao, dict) else None, "pedidos_http": pedidos}
    parou = isinstance(acao, dict) and acao.get("action") == "ask_human" and acao.get("reason") == "llm error"
    falhos = [p for p in pedidos if p.get("erro")]
    if parou and not pedidos:
        saida["infra"] = (f"o cérebro do portal não chegou a chamar o braço ({acao.get('value')}) — "
                          f"rota/catálogo do portal_decisao, não o modelo")
    elif parou and falhos:
        # 🔴 A verdade NOVA (F3b): erro do provedor não troca de modelo calado —
        # o produto devolve `ask_human` e o job segue para `needs_human`. É
        # falha de INFRA (o provedor), nunca acerto nem erro do modelo.
        saida["infra"] = (f"o provedor falhou ({falhos[0]['erro']}) e o produto parou em ask_human "
                          f"(needs_human), sem trocar de modelo — {len(pedidos)} pedido(s) ao braço")
    elif len({p.get("model") for p in pedidos}) > 1:
        saida["infra"] = (f"o portal pediu mais de um modelo na mesma decisão "
                          f"{sorted({str(p.get('model')) for p in pedidos})} — reserva da rota, não o braço")
    return saida


async def motor_dispatch(caso: dict, ctx: Contexto) -> dict:
    from app.services.dispatch_router import o_cerebro_ja_sabe

    ent = caso.get("entrada") or {}
    os.environ["CEREBRO_ANTES_DO_SEGURADO"] = "1"
    sessao = dict(ent.get("sessao") or {})
    sessao.pop("client_phone", None)   # a conversa do segurado viria do banco: fora da N1
    valor, origem = await _com_retomada(
        lambda: o_cerebro_ja_sabe(TENANTS[caso.get("tenant") or "A"], sessao,
                                  slot=str(ent.get("slot") or ""), rotulo=str(ent.get("rotulo") or ""),
                                  tela=str(ent.get("tela") or ""), llm=ctx.llm),
        lambda: o_cerebro_ja_sabe(TENANTS[caso.get("tenant") or "A"], sessao,
                                  slot=str(ent.get("slot") or ""), rotulo=str(ent.get("rotulo") or ""),
                                  tela=str(ent.get("tela") or ""), llm=ctx.llm), ctx)
    return {"texto": str(valor or ""), "estado": {"valor": valor, "origem": origem or None}}


async def motor_memoria(caso: dict, ctx: Contexto) -> dict:
    from app.services.memory_service import MemoryService

    ent = caso.get("entrada") or {}
    ms = MemoryService(ctx.banco)
    fatos = await ms.extract_user_facts_async(_mensagens(ent.get("conversa") or []),
                                              ent.get("fatos_existentes") or [], llm=ctx.llm)
    return {"texto": json.dumps(fatos, ensure_ascii=False), "estrutura": fatos}


def _imagem_em_data_uri(caminho: str) -> str:
    import base64

    p = (CORPUS_DIR / caminho) if not os.path.isabs(caminho) else Path(caminho)
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()


async def motor_visao(caso: dict, ctx: Contexto) -> dict:
    from app.services.vision_service import describe_image

    ent = caso.get("entrada") or {}
    desc = await describe_image(
        _imagem_em_data_uri(ent["imagem"]), company_id=TENANTS[caso.get("tenant") or "A"],
        purpose_hint=str(ent.get("finalidade") or "Agente de Suporte"), llm=ctx.llm)
    if desc is None and ctx.medidor.estado["chamadas"] == 0:
        # describe_image engole a falha e devolve None (o fluxo do produto segue
        # só com o texto) — sem chamada medida, não houve modelo a julgar.
        raise Bloqueado("describe_image devolveu None sem resposta do braço (falha engolida pelo motor)")
    return {"texto": str(desc or "")}


async def motor_hyde(caso: dict, ctx: Contexto) -> dict:
    from app.services import search_service as ss

    ent = caso.get("entrada") or {}
    pergunta = str(ent.get("pergunta") or "")
    doc = ss.SearchService._generate_hyde_doc(object.__new__(ss.SearchService), pergunta,
                                              llm=ctx.llm)
    if str(doc or "").strip() == pergunta.strip() and ctx.medidor.estado["chamadas"] == 0:
        raise Bloqueado("HyDE devolveu a própria pergunta sem resposta do braço "
                        "(o motor engole a falha: search_service._generate_hyde_doc)")
    return {"texto": str(doc or "")}


async def motor_extrator_planos(caso: dict, ctx: Contexto) -> dict:
    from app.services.knowledge.assistance_plans_extractor import propostas_da_pagina

    ent = caso.get("entrada") or {}
    linhas = propostas_da_pagina(str(ent.get("texto") or ""), int(ent.get("pagina") or 1),
                                 produto_padrao=str(ent.get("produto") or ""), llm=ctx.llm,
                                 ancora=None)
    return {"texto": json.dumps(linhas, ensure_ascii=False), "estrutura": linhas}


async def motor_bloqueado(caso: dict, ctx: Contexto) -> dict:
    raise Bloqueado(PAPEIS[caso["papel"]].get("bloqueio") or "motor sem ponto de injeção")


MOTORES: Dict[str, Callable] = {
    "agente": motor_agente, "portal": motor_portal, "dispatch": motor_dispatch,
    "memoria": motor_memoria, "visao": motor_visao, "hyde": motor_hyde,
    "extrator_planos": motor_extrator_planos, "bloqueado": motor_bloqueado,
}


# ===========================================================================
# O ORÁCULO — só juízes determinísticos (evaluators.py)
# ===========================================================================
def julgar_caso(caso: dict, saida: dict) -> List[dict]:
    o = dict(caso.get("oraculo") or {})
    ent = caso.get("entrada") or {}
    texto = str(saida.get("texto") or "")
    args_txt = json.dumps(saida.get("tool_calls_todas") or saida.get("tool_calls") or [],
                          ensure_ascii=False)
    pedidos: List[tuple] = [
        ("sem_pii", E.sem_pii, texto + "\n" + args_txt, {}, ent),
        ("sem_segredo", E.sem_segredo, texto, {}, ent),
    ]
    if o.get("deve_conter"):
        pedidos.append(("contem", E.contem, texto, {"contem": o["deve_conter"]}, ent))
    if o.get("nao_deve_conter"):
        pedidos.append(("nao_contem", E.nao_contem, texto,
                        {"nao_contem": o["nao_deve_conter"],
                         "negacao_ok": bool(o.get("negacao_ok"))}, ent))
    if "tool_esperada" in o:
        pedidos.append(("tool_esperada", E.tool_esperada, saida, o, ent))
        pedidos.append(("args_esperados", E.args_esperados, saida, o, ent))
    if o.get("nao_perguntar"):
        pedidos.append(("nao_perguntar", E.nao_perguntar, saida,
                        {"nao_perguntar": o["nao_perguntar"], "ficha": ent.get("ficha") or {}}, ent))
    if caso.get("nivel") == "N2" or o.get("efeitos_exatos"):
        pedidos.append(("efeitos_exatos", E.efeitos_exatos, saida, o, ent))
    if caso.get("efeitos_proibidos") or o.get("efeitos_proibidos"):
        pedidos.append(("sem_efeito_proibido", E.sem_efeito_proibido, saida,
                        {"efeitos_proibidos": caso.get("efeitos_proibidos") or o.get("efeitos_proibidos")}, ent))
    if o.get("dados_do_outro_tenant"):
        pedidos.append(("sem_dado_de_outro_tenant", E.sem_dado_de_outro_tenant, saida, o, ent))
    if caso.get("orcamento_turnos"):
        pedidos.append(("turnos_no_orcamento", E.turnos_no_orcamento, saida,
                        {"orcamento_turnos": caso["orcamento_turnos"]}, ent))
    if o.get("estado_final"):
        pedidos.append(("estado_final", E.estado_final, saida, o, ent))
    if o.get("formato"):
        pedidos.append(("estrutura_valida", E.estrutura_valida, saida, o, ent))
    if "fatos_ouro" in o or o.get("fatos_proibidos"):
        pedidos.append(("fatos_ouro", E.fatos_ouro, saida, o, ent))

    vereditos = []
    for slug, fn, s, esp, en in pedidos:
        try:
            passou, nota, motivo = fn(s, esp, en)
        except Exception as exc:  # noqa: BLE001 — juiz que explode não vira "passou"
            passou, nota, motivo = False, 0.0, f"O avaliador '{slug}' falhou ({type(exc).__name__})."
        vereditos.append({"evaluator_slug": slug, "passou": bool(passou), "nota": float(nota),
                          "motivo": motivo})
    return vereditos


def classificar(caso: dict, vereditos: List[dict]) -> str:
    if all(v["passou"] for v in vereditos):
        return "PASS"
    falhos = [v for v in vereditos if not v["passou"]]
    if caso.get("critico") or any(v["evaluator_slug"] in DUROS for v in falhos):
        return "FAIL"
    return "PARTIAL" if any(v["nota"] > 0 for v in falhos) else "FAIL"


# ===========================================================================
# O RUNNER
# ===========================================================================
@dataclass
class ResultadoDoCaso:
    chave: str
    braco: str
    tentativa: int
    resultado: str
    critico: bool
    custo_usd: float
    tokens: dict
    latencia_ms: int
    rastro: dict
    vereditos: List[dict]
    erro: Optional[str] = None


@dataclass
class RelatorioDaBancada:
    grupo_bancada: str
    papel: str
    nivel: str
    k: int
    teto_usd: float
    gasto_usd: float = 0.0
    parada: Optional[str] = None
    recusados: List[dict] = field(default_factory=list)
    bracos: Dict[str, dict] = field(default_factory=dict)
    resultados: List[ResultadoDoCaso] = field(default_factory=list)
    runs: List[dict] = field(default_factory=list)
    arquivo: Optional[str] = None

    def para_dict(self) -> dict:
        d = asdict(self)
        return d

    def salvar(self, caminho: Optional[str] = None) -> str:
        if not caminho:
            pasta = Path(tempfile.gettempdir()) / "autobrokers-bancada"
            pasta.mkdir(parents=True, exist_ok=True)
            caminho = str(pasta / f"bancada-{self.papel}-{self.grupo_bancada}.json")
        Path(caminho).write_text(json.dumps(self.para_dict(), ensure_ascii=False, indent=1,
                                            default=str), encoding="utf-8")
        self.arquivo = caminho
        return caminho

    def tabela(self) -> str:
        real = sum(r.custo_usd for r in self.resultados if not r.braco.startswith("duble:"))
        return tabela_de_metricas(self.papel, self.nivel, self.k, self.bracos,
                                  self.parada, self.recusados, real, self.teto_usd)


def _pct(v: Optional[float]) -> str:
    return "  —  " if v is None else f"{v * 100:5.1f}%"


def tabela_de_metricas(papel, nivel, k, bracos, parada=None, recusados=None,
                       gasto=0.0, teto=0.0) -> str:
    cab = (f"{'braço':<34} {'pass@1':>7} {'pass^k':>7} {'crít^k':>7} {'custo/suc':>10} "
           f"{'p50ms':>7} {'p95ms':>7} {'tool':>6} {'args':>6} {'dup':>4} {'recup':>6} {'infra':>5}")
    teto_txt = f" de {teto:.2f}" if teto else ""
    linhas = [f"BANCADA · papel={papel} · nível={nivel} · k={k} · gasto REAL US$ {gasto:.4f}{teto_txt} "
              f"(braços-dublê têm preço fictício e ficam fora)",
              cab, "-" * len(cab)]
    for rot, m in bracos.items():
        cps = "—" if m.get("custo_por_sucesso") is None else f"{m['custo_por_sucesso']:.5f}"
        linhas.append(
            f"{rot:<34} {_pct(m.get('pass_at_1')):>7} {_pct(m.get('pass_hat_k')):>7} "
            f"{_pct(m.get('pass_hat_k_critico')):>7} {cps:>10} {m.get('latencia_p50_ms') or 0:>7} "
            f"{m.get('latencia_p95_ms') or 0:>7} {_pct(m.get('acerto_de_tool')):>6} "
            f"{_pct(m.get('acerto_de_args')):>6} {m.get('efeitos_duplicados', 0):>4} "
            f"{_pct(m.get('recuperacao_apos_falha')):>6} {m.get('blocked_by_infra', 0):>5}")
    for r in recusados or []:
        linhas.append(f"RECUSADO {r.get('braco')}: {r.get('motivo')}")
    if parada:
        linhas.append(f"⛔ PARADA: {parada}")
    return "\n".join(linhas)


def _percentil(valores: List[int], p: float) -> Optional[int]:
    if not valores:
        return None
    s = sorted(valores)
    i = max(0, min(len(s) - 1, math.ceil(p * len(s)) - 1))
    return int(s[i])


def calcular_metricas(resultados: List[Any]) -> dict:
    """pass@1, pass^k, custo por sucesso… sobre as tentativas de UM braço.

    pass^k = fração dos casos em que TODAS as k tentativas passaram (τ²-bench).
    Caso com tentativa BLOCKED_BY_INFRA sai do denominador — falha nossa não
    conta contra o modelo (nem a favor).
    """
    rs = [r if isinstance(r, dict) else asdict(r) for r in resultados]
    julgados = [r for r in rs if r["resultado"] != "BLOCKED_BY_INFRA"]
    passes = [r for r in julgados if r["resultado"] == "PASS"]
    por_caso: Dict[str, List[dict]] = {}
    for r in rs:
        por_caso.setdefault(r["chave"], []).append(r)
    casos_julgaveis = {c: v for c, v in por_caso.items()
                       if not any(x["resultado"] == "BLOCKED_BY_INFRA" for x in v)}
    todos_passam = [c for c, v in casos_julgaveis.items() if all(x["resultado"] == "PASS" for x in v)]
    criticos = {c: v for c, v in casos_julgaveis.items() if v and v[0].get("critico")}
    crit_ok = [c for c, v in criticos.items() if all(x["resultado"] == "PASS" for x in v)]

    def _taxa(slug: str) -> Optional[float]:
        vs = [v for r in julgados for v in r.get("vereditos") or [] if v["evaluator_slug"] == slug]
        return (sum(1 for v in vs if v["passou"]) / len(vs)) if vs else None

    custo = sum(float(r.get("custo_usd") or 0) for r in rs)
    com_falha = [r for r in julgados if (r.get("rastro") or {}).get("falhas_injetadas")]
    lat = [int(r.get("latencia_ms") or 0) for r in julgados]
    return {
        "tentativas": len(rs), "casos": len(por_caso),
        "pass": len(passes),
        "fail": sum(1 for r in julgados if r["resultado"] == "FAIL"),
        "partial": sum(1 for r in julgados if r["resultado"] == "PARTIAL"),
        "blocked_by_infra": len(rs) - len(julgados),
        "pass_at_1": (len(passes) / len(julgados)) if julgados else None,
        "pass_hat_k": (len(todos_passam) / len(casos_julgaveis)) if casos_julgaveis else None,
        "pass_hat_k_critico": (len(crit_ok) / len(criticos)) if criticos else None,
        "custo_total_usd": round(custo, 6),
        "custo_por_sucesso": (round(custo / len(passes), 6) if passes else None),
        "latencia_p50_ms": _percentil(lat, 0.50), "latencia_p95_ms": _percentil(lat, 0.95),
        "acerto_de_tool": _taxa("tool_esperada"), "acerto_de_args": _taxa("args_esperados"),
        "validade_estrutural": _taxa("estrutura_valida"),
        "efeitos_duplicados": sum(int((r.get("rastro") or {}).get("duplicados") or 0) for r in rs),
        "recuperacao_apos_falha": ((sum(1 for r in com_falha if r["resultado"] == "PASS") / len(com_falha))
                                   if com_falha else None),
    }


def _commit() -> Optional[str]:
    """O commit medido — com ``-sujo`` quando o código do MOTOR (app/,
    portal_worker/) tem mudança não commitada: o placar de um braço tem de
    apontar para o código que o produziu, e HEAD sozinho mentiria."""
    try:
        from .runner import commit_atual

        sha = commit_atual()
    except Exception:  # noqa: BLE001
        return None
    if not sha or os.getenv("BUILD_COMMIT"):
        return sha
    try:
        import subprocess

        r = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "app", "portal_worker"],
                           cwd=str(CORPUS_DIR.parents[2]), capture_output=True, timeout=10)
        return f"{sha}-sujo" if r.returncode == 1 else sha
    except Exception:  # noqa: BLE001
        return sha


async def _rodar_caso(caso: dict, *, braco: Braco, resolvido: Any, preco: dict,
                      orcamento: Orcamento, construir_llm: Callable, tentativa: int) -> ResultadoDoCaso:
    caso_m = D.materializar(caso)
    ficha_ctx = D.CASO_ATUAL.set(caso_m)
    inicio = time.perf_counter()
    registro = D.RegistroDeEfeitos()
    banco = D.SupabaseDuble()
    llm_base = construir_llm(resolvido, [])
    max_out = min(int((_campo(resolvido, "capacidades") or {}).get("max_output") or MAX_TOKENS_DA_BANCADA),
                  MAX_TOKENS_DA_BANCADA)
    medidor = Medidor(llm_base, preco=preco, orcamento=orcamento, max_output=max_out)
    plano = [f for f in caso_m.get("falhas_injetadas") or [] if str(f.get("tipo", "")).startswith("provedor_")]
    falhas = D.LLMComFalhas(medidor, plano) if plano else None
    from langgraph.checkpoint.memory import InMemorySaver

    ctx = Contexto(llm=falhas or medidor, braco=braco, registro=registro, banco=banco,
                   medidor=medidor, falhas=falhas, saver=InMemorySaver(), resolvido=resolvido)
    motor = MOTORES[PAPEIS[caso_m["papel"]]["motor"]]
    saida: dict = {}
    erro = None
    resultado = None
    vereditos: List[dict] = []
    try:
        with D.borda_isolada(banco, env=PAPEIS[caso_m["papel"]].get("env")):
            saida = await motor(caso_m, ctx)
    except TetoDeGastoAtingido:
        raise
    except Bloqueado as exc:
        resultado, erro = "BLOCKED_BY_INFRA", f"bloqueado: {exc}"
    except Exception as exc:  # noqa: BLE001
        nome = type(exc).__name__
        injetada = bool(falhas and falhas.disparadas)
        if injetada and _e_falha_de_provedor(exc):
            resultado, erro = "FAIL", f"não se recuperou da falha injetada ({nome})"
            vereditos = [{"evaluator_slug": "execucao", "passou": False, "nota": 0.0, "motivo": erro}]
        else:
            resultado = "BLOCKED_BY_INFRA"
            tipo = "provedor" if any(t in nome for t in _ERROS_DE_INFRA) else "motor/dublê"
            erro = f"{tipo}: {nome}: {str(exc)[:300]}"
    finally:
        with contextlib.suppress(ValueError, RuntimeError):
            D.CASO_ATUAL.reset(ficha_ctx)
    latencia = int((time.perf_counter() - inicio) * 1000)

    if resultado is None:
        vereditos = julgar_caso(caso_m, saida)
        resultado = classificar(caso_m, vereditos)
        if saida.get("infra"):
            resultado, erro = "BLOCKED_BY_INFRA", saida["infra"]
        # 🔴 SPEC-116 F6: motor que ENGOLE o erro do provedor (dispatch, visão,
        # memória: `except Exception → None`) transformava crédito esgotado, 429
        # ou 400 do provedor em FAIL do modelo. 📊 Medido: o dispatch deu 20 % a
        # TODOS os braços com 0 chamadas concluídas. Chamada tentada e não
        # concluída, sem falha injetada, é INFRA — nunca contra o modelo.
        falhou_calado = medidor.estado.get("tentativas", 0) - medidor.estado["chamadas"]
        if (not braco.e_duble and resultado in ("FAIL", "PARTIAL") and falhou_calado > 0
                and not (falhas and falhas.disparadas)):
            resultado = "BLOCKED_BY_INFRA"
            erro = (f"provedor: {falhou_calado} de {medidor.estado['tentativas']} chamada(s) ao braço "
                    f"não concluíram e o motor engoliu o erro — não é falha do modelo")
        reais = medidor.estado["modelos_reais"]
        if not braco.e_duble and reais and any(braco.model not in r for r in reais):
            resultado = "BLOCKED_BY_INFRA"
            erro = f"modelo_real {sorted(set(reais))} ≠ braço {braco.model} (a fábrica trocou o modelo)"

    rastro = {
        "tool_calls": medidor.estado["tool_calls"],
        "efeitos": registro.chamadas,
        "duplicados": registro.duplicados(),
        "falhas_injetadas": (falhas.disparadas if falhas else [])
        + [f for f in caso_m.get("falhas_injetadas") or [] if not str(f.get("tipo", "")).startswith("provedor_")],
        "chamadas_ao_modelo": medidor.estado["chamadas"],
        "chamadas_tentadas": medidor.estado.get("tentativas", 0),
        "modelos_reais": sorted(set(medidor.estado["modelos_reais"])),
        "prompt_hashes": sorted(medidor.estado["prompts"]),
        "tools_hashes": sorted(medidor.estado["tools"]),
        "notas": ctx.notas,
        "texto": str(saida.get("texto") or "")[:1500],
        "estado": saida.get("estado"),
    }
    for extra in ("pedidos_http", "pedidos"):
        if saida.get(extra):
            rastro[extra] = saida[extra]
    return ResultadoDoCaso(
        chave=caso["chave"], braco=braco.rotulo, tentativa=tentativa, resultado=resultado,
        critico=bool(caso.get("critico")), custo_usd=round(medidor.estado["custo"], 8),
        tokens=dict(medidor.estado["tokens"]), latencia_ms=latencia, rastro=rastro,
        vereditos=vereditos, erro=erro)


def _gravar_run_aberto(db, *, version_id, braco: Braco, resolvido, papel, nivel, grupo, tentativa, total):
    linha = db.table("eval_runs").insert({
        "version_id": version_id, "commit_sha": _commit(), "modelo": braco.model,
        "provedor": braco.provider, "gatilho": "bancada", "status": "running", "total": total,
        "braco": {**braco.override(), "api_surface": _campo(resolvido, "api_surface"),
                  "versao_da_rota": _campo(resolvido, "versao_da_rota")},
        "papel": papel, "nivel": nivel, "grupo_bancada": grupo, "tentativa": tentativa,
    }).execute().data
    return linha[0]["id"]


def _gravar_caso(db, run_id, case_id, r: ResultadoDoCaso) -> None:
    motivo = "; ".join(v["motivo"] for v in r.vereditos if not v["passou"])[:900] or (r.erro or "passou")
    linhas = [{
        "run_id": run_id, "case_id": case_id, "evaluator_slug": "bancada:caso",
        "passou": r.resultado == "PASS", "nota": 1.0 if r.resultado == "PASS" else 0.0,
        "motivo": motivo, "duracao_ms": r.latencia_ms, "resultado": r.resultado,
        "custo_usd": r.custo_usd, "tokens": r.tokens, "latencia_ms": r.latencia_ms,
        "rastro": r.rastro, "erro": r.erro}]
    for v in r.vereditos:
        linhas.append({"run_id": run_id, "case_id": case_id, "evaluator_slug": v["evaluator_slug"],
                       "passou": v["passou"], "nota": v["nota"], "motivo": v["motivo"],
                       "duracao_ms": r.latencia_ms})
    db.table("eval_case_results").insert(json.loads(json.dumps(linhas, default=str))).execute()


def _fechar_run(db, run_id, rs: List[ResultadoDoCaso], parada: Optional[str]) -> None:
    julg = [r for r in rs if r.resultado != "BLOCKED_BY_INFRA"]
    passaram = sum(1 for r in julg if r.resultado == "PASS")
    tokens: Dict[str, int] = {}
    for r in rs:
        for k2, v in (r.tokens or {}).items():
            tokens[k2] = tokens.get(k2, 0) + int(v or 0)
    nota = round(passaram / len(julg), 4) if julg else None
    db.table("eval_runs").update({
        "status": "error" if parada else ("passed" if julg and passaram == len(julg) else "failed"),
        "motivo_parada": parada, "nota": nota, "passaram": passaram,
        "custo_usd": round(sum(r.custo_usd for r in rs), 8), "tokens": tokens,
        "terminado_em": datetime.now(timezone.utc).isoformat()}).eq("id", run_id).execute()


async def rodar_bancada_async(papel: str, bracos: List[Any], casos: Optional[List[dict]] = None, *,
                              k: int = 3, nivel: str = "N1",
                              construir_llm: Optional[Callable] = None, gravar: bool = False,
                              teto_usd: Optional[float] = None, resolver: Optional[Callable] = None,
                              precos: Optional[Callable] = None, cliente: Any = None,
                              filtro: Optional[str] = None, critico: bool = False,
                              grupo_bancada: Optional[str] = None) -> RelatorioDaBancada:
    if papel not in PAPEIS:
        raise ValueError(f"papel desconhecido: {papel!r} (conhecidos: {', '.join(PAPEIS)})")
    construir_llm = construir_llm or construir_llm_padrao
    resolver = resolver or resolver_padrao
    precos = precos or (lambda b: preco_do_catalogo(b, cliente))
    teto = float(teto_usd if teto_usd is not None else teto_padrao())
    orcamento = Orcamento(teto)
    if casos is None:
        casos = carregar_casos(papel, filtro=filtro, critico=critico, nivel=nivel)
    grupo = grupo_bancada or str(uuid.uuid4())
    rel = RelatorioDaBancada(grupo_bancada=grupo, papel=papel, nivel=nivel, k=int(k), teto_usd=teto)
    if not casos:
        rel.parada = "nenhum caso para este papel/nível/filtro"
        return rel

    db = None
    corpus = {}
    if gravar:
        db = getattr(cliente, "client", cliente) if cliente is not None else None
        if db is None:
            from app.core.database import get_supabase_client

            db = getattr(get_supabase_client(), "client", get_supabase_client())
        corpus = carregar_corpus(gravar=True, cliente=db, papeis=[papel])[papel]

    for b in bracos:
        braco = Braco.de(b)
        preco = precos(braco)
        if not preco:
            rel.recusados.append({"braco": braco.rotulo, "motivo": "sem preço conhecido no catálogo — "
                                                                  "a bancada não inventa preço"})
            continue
        try:
            resolvido = resolver(papel, override=braco.override())
        except Exception as exc:  # noqa: BLE001
            rel.recusados.append({"braco": braco.rotulo, "motivo": f"resolvedor recusou: {exc}"})
            continue
        meus: List[ResultadoDoCaso] = []
        for tentativa in range(1, int(k) + 1):
            run_id = None
            if gravar:
                run_id = _gravar_run_aberto(db, version_id=corpus["version_id"], braco=braco,
                                            resolvido=resolvido, papel=papel, nivel=nivel,
                                            grupo=grupo, tentativa=tentativa, total=len(casos))
            do_run: List[ResultadoDoCaso] = []
            parada = None
            for caso in casos:
                try:
                    r = await _rodar_caso(caso, braco=braco, resolvido=resolvido, preco=preco,
                                          orcamento=orcamento, construir_llm=construir_llm,
                                          tentativa=tentativa)
                except TetoDeGastoAtingido as exc:
                    parada = "teto_usd"
                    rel.parada = f"teto_usd — {exc}"
                    break
                do_run.append(r)
                if gravar and corpus["ids"].get(caso["chave"]):
                    _gravar_caso(db, run_id, corpus["ids"][caso["chave"]], r)
            meus.extend(do_run)
            if gravar:
                _fechar_run(db, run_id, do_run, parada)
                rel.runs.append({"run_id": run_id, "braco": braco.rotulo, "tentativa": tentativa,
                                 "status": "error" if parada else "fechado"})
            if parada:
                break
        rel.resultados.extend(meus)
        rel.bracos[braco.rotulo] = calcular_metricas(meus)
        if rel.parada:
            break
    rel.gasto_usd = round(orcamento.gasto, 8)
    return rel


def rodar_bancada(papel: str, bracos: List[Any], casos: Optional[List[dict]] = None, k: int = 3,
                  nivel: str = "N1", construir_llm: Optional[Callable] = None, gravar: bool = False,
                  teto_usd: Optional[float] = None, **kw) -> RelatorioDaBancada:
    """Síncrono (CLI e testes). Ver `rodar_bancada_async`."""
    return asyncio.run(rodar_bancada_async(papel, bracos, casos, k=k, nivel=nivel,
                                           construir_llm=construir_llm, gravar=gravar,
                                           teto_usd=teto_usd, **kw))


def relatorio_do_banco(grupo_bancada: str, cliente: Any = None) -> str:
    """Reconstrói a tabela a partir do que foi GRAVADO (eval_runs do grupo)."""
    db = getattr(cliente, "client", cliente) if cliente is not None else None
    if db is None:
        from app.core.database import get_supabase_client

        db = getattr(get_supabase_client(), "client", get_supabase_client())
    runs = db.table("eval_runs").select("*").eq("grupo_bancada", grupo_bancada).execute().data or []
    if not runs:
        return f"nenhum eval_run com grupo_bancada={grupo_bancada}"
    linhas_casos = (db.table("eval_cases").select("id, chave, tags")
                    .eq("version_id", runs[0]["version_id"]).execute().data or [])
    casos = {c["id"]: c["chave"] for c in linhas_casos}
    criticos = {c["id"] for c in linhas_casos if "critico" in (c.get("tags") or [])}
    por_braco: Dict[str, List[dict]] = {}
    for run in runs:
        b = run.get("braco") or {}
        rot = f"{b.get('provider')}:{b.get('model')}" + (f":{b['effort']}" if b.get("effort") else "")
        linhas = (db.table("eval_case_results").select("*").eq("run_id", run["id"]).execute().data or [])
        por_caso: Dict[str, dict] = {}
        for l in linhas:
            reg = por_caso.setdefault(l["case_id"], {"vereditos": []})
            if l["evaluator_slug"] == "bancada:caso":
                reg.update({"chave": casos.get(l["case_id"], l["case_id"]), "resultado": l.get("resultado"),
                            "custo_usd": l.get("custo_usd"), "latencia_ms": l.get("latencia_ms"),
                            "rastro": l.get("rastro") or {}, "critico": l["case_id"] in criticos})
            else:
                reg["vereditos"].append({"evaluator_slug": l["evaluator_slug"], "passou": l["passou"],
                                         "nota": float(l.get("nota") or 0)})
        por_braco.setdefault(rot, []).extend(r for r in por_caso.values() if r.get("resultado"))
    r0 = runs[0]
    return tabela_de_metricas(r0.get("papel"), r0.get("nivel"),
                              max(int(r.get("tentativa") or 1) for r in runs),
                              {rot: calcular_metricas(rs) for rot, rs in por_braco.items()},
                              gasto=sum(float(r.get("custo_usd") or 0) for r in runs
                                        if (r.get("braco") or {}).get("provider") != "duble"))


def relatorio_de_arquivo(caminho: str) -> str:
    d = json.loads(Path(caminho).read_text(encoding="utf-8"))
    por_braco: Dict[str, List[dict]] = {}
    for r in d.get("resultados") or []:
        por_braco.setdefault(r["braco"], []).append(r)
    return tabela_de_metricas(d.get("papel"), d.get("nivel"), d.get("k"),
                              {rot: calcular_metricas(rs) for rot, rs in por_braco.items()},
                              d.get("parada"), d.get("recusados"), d.get("gasto_usd") or 0,
                              d.get("teto_usd") or 0)
