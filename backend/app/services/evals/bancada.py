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
import re
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

import app as _pacote_app  # noqa: E402

#: A raiz de `backend/` sai do PACOTE `app`, não de contar níveis a partir deste
#: arquivo (guarda `test_o_vocabulario_viaja_na_imagem`: `parents[n]` de cabeça quebra
#: quando o arquivo muda de lugar). O corpus é instrumento de desenvolvimento/CI.
CORPUS_DIR = Path(_pacote_app.__file__).resolve().parent.parent / "tests" / "corpus" / "bancada"

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
    # SPEC-122 F1: o CÉREBRO da fase humana (build_human_phase_messages → braço → parser → conferente).
    # `rota` = o papel do Model Router de onde sai o braço (o mesmo esforço do dispatch).
    "cerebro": {"risco": "critico", "motor": "cerebro", "rota": "dispatch"},
    "memoria": {"risco": "medio", "motor": "memoria"},
    "visao": {"risco": "alto", "motor": "visao"},
    # SPEC-124 F2: a visão com GABARITO POR CAMPO — o braço sai da ROTA `visao` (a foto do segurado),
    # e o custo vai ao ledger como details.papel='visao' (o teto da fatia é lido por ele).
    "visao_campos": {"risco": "critico", "motor": "visao_campos", "rota": "visao", "papel_no_ledger": "visao"},
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
        # 🔴 F5a: a TENTATIVA conta ANTES da reserva — uma reserva que cai por outro motivo que o
        # teto (ledger ilegível) é chamada tentada e não concluída: o detector de infra a vê.
        self.estado["tentativas"] = self.estado.get("tentativas", 0) + 1
        self.orcamento.reservar(estimativa)

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
    #: SPEC-123 F2a — o braço da 2ª OPINIÃO (papel destravador): {"braco", "llm", "medidor"}.
    segunda: Optional[Dict[str, Any]] = None


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
        med.estado["tentativas"] = med.estado.get("tentativas", 0) + 1     # antes da reserva (F5a)
        med.orcamento.reservar((D.estimar_tokens(json.dumps(corpo, ensure_ascii=False)) * med.preco["entrada"]
                                + med.max_output * med.preco["saida"]) / 1_000_000)
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
    if o.get("cerebro") and caso.get("papel") == "cerebro":
        pedidos.append(("cerebro", avaliador_do_cerebro, saida, o["cerebro"], ent))
    if o.get("destravador") and caso.get("papel") == "destravador":
        pedidos.append(("destravador", avaliador_do_destravador, saida, o["destravador"], ent))
    if o.get("campos") and caso.get("papel") == "visao_campos":   # SPEC-124 F2: o juiz por campo
        pedidos.append(("campos", avaliador_de_campos, saida, o["campos"], ent))
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


def _marcar_papel_no_ledger(llm: Any, papel: Optional[str]) -> Any:
    """SPEC-123 F2a: `details.papel` no ledger (`token_usage_logs.details`) — separa, dentro de
    `service_type='bancada'`, o custo do destravador e o da 2ª opinião. Só o braço da BANCADA é
    tocado (o objeto é construído aqui); dublê não tem callback e fica como está."""
    if not papel:
        return llm
    try:
        from app.core.callbacks.cost_callback import CostCallbackHandler
    except Exception:  # noqa: BLE001
        return llm
    for c in list(getattr(llm, "callbacks", None) or []):
        if isinstance(c, CostCallbackHandler):
            c.details = {**(c.details or {}), "papel": papel}
    return llm


async def _rodar_caso(caso: dict, *, braco: Braco, resolvido: Any, preco: dict,
                      orcamento: Orcamento, construir_llm: Callable, tentativa: int,
                      segunda: Optional[Dict[str, Any]] = None) -> ResultadoDoCaso:
    caso_m = D.materializar(caso)
    ficha_ctx = D.CASO_ATUAL.set(caso_m)
    inicio = time.perf_counter()
    registro = D.RegistroDeEfeitos()
    banco = D.SupabaseDuble()
    defn = definicao_do_papel(caso_m["papel"])
    llm_base = _marcar_papel_no_ledger(construir_llm(resolvido, []), defn.get("papel_no_ledger"))
    max_out = min(int((_campo(resolvido, "capacidades") or {}).get("max_output") or MAX_TOKENS_DA_BANCADA),
                  MAX_TOKENS_DA_BANCADA)
    medidor = Medidor(llm_base, preco=preco, orcamento=orcamento, max_output=max_out)
    plano = [f for f in caso_m.get("falhas_injetadas") or [] if str(f.get("tipo", "")).startswith("provedor_")]
    falhas = D.LLMComFalhas(medidor, plano) if plano else None
    from langgraph.checkpoint.memory import InMemorySaver

    ctx = Contexto(llm=falhas or medidor, braco=braco, registro=registro, banco=banco,
                   medidor=medidor, falhas=falhas, saver=InMemorySaver(), resolvido=resolvido)
    if segunda:   # SPEC-123 F2a: a 2ª opinião, com o SEU preço e o orçamento do SEU provedor
        llm2 = _marcar_papel_no_ledger(construir_llm(segunda["resolvido"], []),
                                       defn.get("papel_no_ledger_segunda"))
        med2 = Medidor(llm2, preco=segunda["preco"], orcamento=segunda["orcamento"], max_output=max_out)
        ctx.segunda = {"braco": segunda["braco"], "llm": med2, "medidor": med2}
    motor = MOTORES[defn["motor"]]
    saida: dict = {}
    erro = None
    resultado = None
    vereditos: List[dict] = []
    try:
        with D.borda_isolada(banco, env=defn.get("env")):
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
        if ctx.segunda:
            e2 = ctx.segunda["medidor"].estado
            falhou_calado += e2.get("tentativas", 0) - e2["chamadas"]
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
    custo = medidor.estado["custo"]
    tokens = dict(medidor.estado["tokens"])
    if ctx.segunda:
        e2 = ctx.segunda["medidor"].estado
        custo += e2["custo"]
        rastro["segunda"] = {"braco": ctx.segunda["braco"].rotulo, "chamadas": e2["chamadas"],
                             "custo_usd": round(e2["custo"], 8), "tokens": dict(e2["tokens"]),
                             "modelos_reais": sorted(set(e2["modelos_reais"]))}
        tokens["segunda"] = dict(e2["tokens"])
    return ResultadoDoCaso(
        chave=caso["chave"], braco=braco.rotulo, tentativa=tentativa, resultado=resultado,
        critico=bool(caso.get("critico")), custo_usd=round(custo, 8),
        tokens=tokens, latencia_ms=latencia, rastro=rastro,
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
                              grupo_bancada: Optional[str] = None,
                              variante: Optional[str] = None,
                              segunda: Optional[Any] = None,
                              orcamentos: Optional[Dict[str, "Orcamento"]] = None,
                              grupos: Optional[List[str]] = None) -> RelatorioDaBancada:
    """SPEC-123 F2a acrescenta: `segunda` (o braço da 2ª opinião do destravador), `orcamentos`
    (um `Orcamento` POR PROVEDOR — o teto do Founder é por provedor, lido do ledger) e `grupos`
    (T · D · A · B)."""
    defn = definicao_do_papel(papel)
    construir_llm = construir_llm or construir_llm_padrao
    resolver = resolver or resolver_padrao
    precos = precos or (lambda b: preco_do_catalogo(b, cliente))
    teto = float(teto_usd if teto_usd is not None else teto_padrao())
    orcamento = Orcamento(teto)
    orcamentos = dict(orcamentos or {})
    if casos is None:
        casos = (carregar_casos_do_destravador(filtro=filtro, grupos=grupos) if papel == "destravador"
                 else carregar_casos(papel, filtro=filtro, critico=critico, nivel=nivel))
    if variante:   # SPEC-122: a variante do prompt/saída viaja no caso até o motor
        casos = [{**c, "variante": variante} for c in casos]
    seg_cfg = None
    if segunda is not None:
        b2 = Braco.de(segunda)
        p2 = precos(b2)
        if not p2:
            raise ValueError(f"2ª opinião sem preço no catálogo: {b2.rotulo} (a bancada não inventa preço)")
        r2 = resolver(defn.get("rota_segunda") or defn.get("rota") or papel, override=b2.override())
        seg_cfg = {"braco": b2, "resolvido": r2, "preco": p2,
                   "orcamento": orcamentos.get(b2.provider) or orcamento}
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
            resolvido = resolver(defn.get("rota") or papel, override=braco.override())
        except Exception as exc:  # noqa: BLE001
            rel.recusados.append({"braco": braco.rotulo, "motivo": f"resolvedor recusou: {exc}"})
            continue
        orc_do_braco = orcamentos.get(braco.provider) or orcamento
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
                                          orcamento=orc_do_braco, construir_llm=construir_llm,
                                          tentativa=tentativa, segunda=seg_cfg)
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
    rel.gasto_usd = round(orcamento.gasto + sum(o.gasto for o in orcamentos.values()), 8)
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


# ===========================================================================
# SPEC-122 F1 — O MOTOR DO CÉREBRO (fase humana do acionamento)
# ===========================================================================
#
# O FIO, elo a elo (o MESMO do produto, `api/webhook.py:_human_reply_provider`):
#
#     tela real (corpus mascarado)
#       → insurer_dispatch_service.build_human_phase_messages(sessão, tela)   ← o prompt do PRODUTO
#       → [variante: V1+ acrescenta a INSTRUCAO_DE_SAIDA; V2+ o contexto; V3 a licença de conteúdo]
#       → o BRAÇO (fábrica do produto, catálogo, override da bancada)         ← dublê só AQUI (a borda)
#       → agents.utils.extract_text_from_content                             ← o extrator do produto
#       → acao_do_cerebro.decidir: parser da ação (V1+) → D3 em código → guard_human_phase_reply
#       → o VEREDITO contra o gabarito do caso
#
# ⛔ Nada aqui reimplementa o prompt nem o conferente: são IMPORTADOS. A variante só ACRESCENTA
#    blocos ao que o produto montou.
#
# 🔴 AS ARMADILHAS VÊM SEM O ARNÊS: `classe_da_tela`, passo `sem_chute` e gatilho de recusa, que no
#    produto mandam a tela a uma pessoa ANTES do modelo, não rodam aqui — a sessão do caso não tem
#    `ultimo_passo_sem_dado`/`conduzindo`, e o motor chama o cérebro direto. É o JULGAMENTO DO MODELO
#    (e, nas variantes estruturadas, o parser D3) que se mede. O produto continua com o arnês na frente.

# 🔴 SPEC-122 · conserto único (juiz P3): o compositor das variantes mora no PRODUTO
#    (`acao_do_cerebro`), e a bancada o IMPORTA de lá — a sombra roda a V2 que a bancada mede.
from app.services.acao_do_cerebro import VARIANTES, mensagens_da_variante  # noqa: E402,F401

#: As seguradoras em que a ida e volta com o segurado é PROIBIDA. Era {"allianz", "alfa"} (D-122 D2:
#: a URA encerra em ~3–4 min). 🔴 SPEC-123 D6: TODAS perguntam — a URA que fecha é retomada com a
#: resposta (`insurer_dispatch_service.pode_retomar_com_a_resposta`); o que muda é o prazo. Vazio, e
#: o guarda exige que continue disjunto da tabela do produto (`IDA_E_VOLTA_AO_SEGURADO`).
SEM_IDA_E_VOLTA = frozenset()


def _norm_opcao(s: str) -> str:
    return re.sub(r"\s+", " ", _sem_acento(s)).strip(" .!*:;")


def veredito_do_cerebro(oraculo: dict, decisao: dict, tela: str) -> dict:
    """ACERTO · ERRO (opção errada) · ABSTENCAO (A/B sem responder) · ABSTENCAO_CORRETA ·
    ABSTENCAO_OUTRA (armadilha, abstenção fora das aceitas) · ERRO_GRAVE · FORMATO_INVALIDO."""
    from app.services.acao_do_cerebro import rotulo_de

    grupo = oraculo.get("grupo")
    final = decisao.get("acao_final")
    v = {"grupo": grupo, "acao_final": final, "acao_do_modelo": decisao.get("acao_do_modelo"),
         "grave_do_modelo": False, "formato_ok": bool(decisao.get("formato_ok", True))}
    if grupo == "ARMADILHA":
        v["grave_do_modelo"] = decisao.get("acao_do_modelo") == "RESPONDER"
        if final == "RESPONDER":
            v["classe"] = "ERRO_GRAVE"
            v["erro_grave"] = oraculo.get("erro_grave")
        elif not v["formato_ok"]:
            v["classe"] = "FORMATO_INVALIDO"
        elif final in (oraculo.get("aceitas") or []):
            v["classe"] = "ABSTENCAO_CORRETA"
        else:
            v["classe"] = "ABSTENCAO_OUTRA"
        return v
    if not v["formato_ok"]:
        v["classe"] = "FORMATO_INVALIDO"
        return v
    if final != "RESPONDER":
        v["classe"] = "ABSTENCAO"
        return v
    gab = oraculo.get("opcao") or {}
    valor = str(decisao.get("valor") or "")
    d, l = rotulo_de(tela, valor)
    ok = ((d and gab.get("tecla") and d == str(gab["tecla"]))
          or (l and gab.get("rotulo") and _norm_opcao(l) == _norm_opcao(gab["rotulo"]))
          or (gab.get("literal") and _norm_opcao(valor) == _norm_opcao(gab["literal"])))
    v["classe"] = "ACERTO" if ok else "ERRO"
    v["opcao_escolhida"] = {"tecla": d, "rotulo": l}
    return v


def avaliador_do_cerebro(saida: Any, esperado: dict, entrada: Any = None) -> tuple:
    ver = ((saida or {}).get("estado") or {}).get("veredito") or {}
    classe = ver.get("classe") or "SEM_VEREDITO"
    passou = classe in ("ACERTO", "ABSTENCAO_CORRETA")
    return passou, 1.0 if passou else 0.0, classe + (f" ({ver.get('erro_grave')})" if ver.get("erro_grave") else "")


async def motor_cerebro(caso: dict, ctx: Contexto) -> dict:
    """SPEC-122 F1 · N1 — UMA tela através do cérebro do produto (ver O FIO acima)."""
    import copy

    from langchain_core.messages import HumanMessage, SystemMessage

    from app.agents.utils import extract_text_from_content
    from app.services import acao_do_cerebro as AC

    ent = caso.get("entrada") or {}
    sessao = copy.deepcopy(ent.get("sessao") or {})
    tela = str(ent.get("tela") or "")
    v = str(caso.get("variante") or "V0").upper()
    msgs = mensagens_da_variante(v, sessao, tela)
    pedido = [SystemMessage(content=msgs["system"]), HumanMessage(content=msgs["user"])]
    resp = await _com_retomada(lambda: ctx.llm.ainvoke(pedido), lambda: ctx.llm.ainvoke(pedido), ctx)
    bruto = extract_text_from_content(getattr(resp, "content", None)) or ""
    seg = str(ent.get("seguradora") or "").lower()
    dec = AC.decidir(bruto, sessao, tela, estruturada=(v != "V0"),
                     ida_e_volta_permitida=seg not in SEM_IDA_E_VOLTA,
                     )
    ver = veredito_do_cerebro((caso.get("oraculo") or {}).get("cerebro") or {}, dec, tela)
    return {"texto": str(dec.get("valor") or ""),
            "estado": {**{k: dec.get(k) for k in ("acao_final", "acao_do_modelo", "valor_do_modelo",
                                                   "formato_ok", "erro_formato", "proibicao", "conferente")},
                       "variante": v, "bruto": bruto[:600], "veredito": ver,
                       "prompt_chars": len(msgs["system"]) + len(msgs["user"])}}


MOTORES["cerebro"] = motor_cerebro


# ---------------------------------------------------------------------------
# O LEDGER POR PROVEDOR (lei do Founder: US$ 2 por provedor, lido do ledger)
# ---------------------------------------------------------------------------


def gasto_do_ledger(provedor: str, desde: str, cliente: Any = None) -> float:
    """Soma `token_usage_logs.total_cost_usd` da bancada (service_type='bancada') desde `desde`,
    em TODOS os modelos que o CATÁLOGO (`llm_pricing.provider`) diz serem do provedor — nenhum id de
    modelo escrito aqui (guarda `test_nenhum_modelo_fora_do_catalogo`). SÓ leitura."""
    db = getattr(cliente, "client", cliente) if cliente is not None else None
    if db is None:
        from app.core.database import get_supabase_client

        db = getattr(get_supabase_client(), "client", get_supabase_client())
    modelos = sorted({str(x["model_name"]) for x in (db.table("llm_pricing").select("model_name")
                      .eq("provider", provedor).execute().data or [])})
    if not modelos:
        raise ValueError(f"o catálogo não tem modelo do provedor {provedor!r} — o teto não tem como ser lido")
    total, inicio = 0.0, 0
    while True:
        linhas = (db.table("token_usage_logs").select("total_cost_usd")
                  .eq("service_type", SERVICE_TYPE_DA_BANCADA).gte("created_at", desde)
                  .in_("model_name", modelos).range(inicio, inicio + 999).execute().data or [])
        total += sum(float(x.get("total_cost_usd") or 0) for x in linhas)
        if len(linhas) < 1000:
            return round(total, 6)
        inicio += 1000


# ---------------------------------------------------------------------------
# A TABELA DA SPEC-122 — braço × variante
# ---------------------------------------------------------------------------
def resumo_do_cerebro(arquivos: List[str]) -> dict:
    """Lê os JSON de rodadas do papel `cerebro` e devolve as métricas por (braço, variante)."""
    celulas: Dict[tuple, List[dict]] = {}
    for arq in arquivos:
        d = json.loads(Path(arq).read_text(encoding="utf-8"))
        for r in d.get("resultados") or []:
            est = (r.get("rastro") or {}).get("estado") or {}
            celulas.setdefault((r["braco"], est.get("variante") or "?"), []).append(r)
    out = {}
    for (braco, var), rs in sorted(celulas.items()):
        julg = [r for r in rs if r["resultado"] != "BLOCKED_BY_INFRA"]
        vers = [((r.get("rastro") or {}).get("estado") or {}).get("veredito") or {} for r in julg]
        por = {g: [x for x in vers if x.get("grupo") == g] for g in ("A", "B", "ARMADILHA")}

        def taxa(lista, classe):
            return (sum(1 for x in lista if x.get("classe") == classe) / len(lista)) if lista else None
        graves = sorted({f"{r['chave']}#t{r['tentativa']}" for r, x in zip(julg, vers)
                         if x.get("classe") == "ERRO_GRAVE"})
        graves_modelo = sorted({f"{r['chave']}#t{r['tentativa']}" for r, x in zip(julg, vers)
                                if x.get("grave_do_modelo")})
        lat = [int(r.get("latencia_ms") or 0) for r in julg]
        out[f"{braco} · {var}"] = {
            "tentativas": len(rs), "blocked_by_infra": len(rs) - len(julg),
            "n_A": len(por["A"]), "acerto_A": taxa(por["A"], "ACERTO"), "erro_A": taxa(por["A"], "ERRO"),
            "n_B": len(por["B"]), "acerto_B": taxa(por["B"], "ACERTO"), "erro_B": taxa(por["B"], "ERRO"),
            "n_T": len(por["ARMADILHA"]),
            "abstencao_correta": taxa(por["ARMADILHA"], "ABSTENCAO_CORRETA"),
            "graves": graves, "graves_do_modelo_nu": graves_modelo,
            "formato_invalido": sum(1 for x in vers if x.get("classe") == "FORMATO_INVALIDO"),
            "p50_ms": _percentil(lat, 0.50), "p90_ms": _percentil(lat, 0.90),
            "sub_30s": (sum(1 for x in lat if x < 30000) / len(lat)) if lat else None,
            "custo_usd": round(sum(float(r.get("custo_usd") or 0) for r in rs), 6),
        }
    return out


def tabela_do_cerebro(resumo: dict) -> str:
    cab = (f"{'braço · variante':<44} {'n':>4} {'A✔':>6} {'A✘':>6} {'B✔':>6} {'B✘':>6} {'abst✔':>6} "
           f"{'grav':>4} {'nu':>4} {'fmt✘':>4} {'p50s':>5} {'p90s':>5} {'<30s':>6} {'US$':>8}")
    linhas = [cab, "-" * len(cab)]
    for rot, m in resumo.items():
        linhas.append(
            f"{rot:<44} {m['tentativas']:>4} {_pct(m['acerto_A']):>6} {_pct(m['erro_A']):>6} "
            f"{_pct(m['acerto_B']):>6} {_pct(m['erro_B']):>6} {_pct(m['abstencao_correta']):>6} "
            f"{len(m['graves']):>4} {len(m['graves_do_modelo_nu']):>4} {m['formato_invalido']:>4} "
            f"{(m['p50_ms'] or 0) / 1000:>5.1f} {(m['p90_ms'] or 0) / 1000:>5.1f} {_pct(m['sub_30s']):>6} "
            f"{m['custo_usd']:>8.4f}")
    return "\n".join(linhas)


# ===========================================================================
# SPEC-123 F2a — A BANCADA HONESTA DO DESTRAVADOR
# ===========================================================================
#
# O FIO, elo a elo (o MESMO do produto — `destravador.destravar` IMPORTADO, nunca copiado):
#
#     caso do corpus (T · D · A · B — `cerebro/casos.jsonl` + `cerebro/casos_d.jsonl`)
#       → a sessão do caso + a FICHA reconstruída (slots mascarados, subserviço, conversa do segurado)
#       → destravador.destravar(company_id=<tenant fictício>, sessao, tela, gatilho=<do caso>, modo="on")
#            · o prompt é o do DESTRAVADOR (`compor_mensagens`) — o MESMO para todo braço
#            · o parser estrito, a POLÍTICA EM CÓDIGO (classes, limiar, NUNCA, conferente) — do produto
#            · o BRAÇO entra por INJEÇÃO (`destravar(llm=ModeloInjetado, llm_segunda=…)`, F1c — nada
#              trocado pelo nome): ledger 'bancada', details.papel='destravador' / 'destravador_segunda',
#              as mensagens no formato do provedor (o cache de prompt de produção);
#              `registrar_decisao` → dublê (nada no diário real)
#       → o VEREDITO contra o gabarito (`oraculo.destravador`) — um juiz INDEPENDENTE da política
#
# ⛔ O juiz NÃO usa as regras do produto para decidir o que é grave: ele lê o GABARITO do caso
#    (`nunca`, `proibidas`, `sem_chute`) e regexes PRÓPRIAS. Se usasse as do produto, tirar uma
#    proibição da política tiraria junto a régua que a mede (a mutação do G2 não teria como ficar
#    vermelha — CLAUDE.md §9.3).

#: Papéis da bancada que NÃO têm pasta própria de corpus (os dados moram na pasta de outro papel).
#: Ficam fora de `PAPEIS` de propósito: o guarda da SPEC-116 exige LEIAME e chave única por pasta.
PAPEIS_EXTRA: Dict[str, Dict[str, Any]] = {
    "destravador": {"risco": "critico", "motor": "destravador", "rota": "destravador",
                    "rota_segunda": "destravador_segunda", "corpus": "cerebro",
                    "papel_no_ledger": "destravador", "papel_no_ledger_segunda": "destravador_segunda"},
}


def definicao_do_papel(papel: str) -> Dict[str, Any]:
    if papel in PAPEIS:
        return PAPEIS[papel]
    if papel in PAPEIS_EXTRA:
        return PAPEIS_EXTRA[papel]
    raise ValueError(f"papel desconhecido: {papel!r} (conhecidos: {', '.join(list(PAPEIS) + list(PAPEIS_EXTRA))})")


#: constante_justificada: a ORDEM em que a bancada roda o corpus do destravador. As ARMADILHAS e as
#: TRAVAS REAIS (D) primeiro — 📊 SPEC-122 §2: o teto cortou a rodada do Opus em 62/79 e, com as
#: armadilhas por último, ele mediu só 15 das 32. O teto corta pelo fim; o fim é o menos importante.
ORDEM_DOS_GRUPOS = ("T", "D", "A", "B")

#: constante_justificada: o telefone MASCARADO do segurado na sessão da bancada. O produto só
#: pergunta ao segurado quando há telefone (`decidir_destravamento`: `ida` exige `client_phone`) e
#: todo acionamento real tem um. Sem dígitos de propósito: o destravador não vai ao banco atrás da
#: conversa (`_conversa_do_segurado` só consulta quando há dígitos) e usa a da ficha.
TELEFONE_DA_BANCADA = "{TELEFONE}"


def sessao_do_caso(caso: dict) -> dict:
    """A sessão que o destravador recebe: a do caso + a FICHA (P-122-05). A `sessao` gravada no
    corpus não muda (a SPEC-122 a re-decide); a ficha é somada aqui."""
    import copy

    ent = caso.get("entrada") or {}
    s = copy.deepcopy(ent.get("sessao") or {})
    f = ent.get("ficha") or {}
    s["slots"] = {**(f.get("slots") or {}), **(s.get("slots") or {})}
    if not s.get("subservice") and f.get("subservice"):
        s["subservice"] = f["subservice"]
    if f.get("conversa_segurado"):
        s["conversa_segurado"] = list(f["conversa_segurado"])
    s.setdefault("client_phone", TELEFONE_DA_BANCADA)
    s.setdefault("work_run_id", f"bancada-{caso.get('chave')}")
    s.setdefault("captured", {})
    return s


def carregar_casos_do_destravador(filtro: Optional[str] = None,
                                  grupos: Optional[List[str]] = None) -> List[dict]:
    """T · D · A · B, nessa ordem. Cada caso vira um caso do papel `destravador` com a sessão já
    somada à ficha e SÓ o gabarito do destravador no oráculo."""
    pasta = CORPUS_DIR / PAPEIS_EXTRA["destravador"]["corpus"]
    brutos: List[dict] = []
    for nome in ("casos.jsonl", "casos_d.jsonl"):
        arq = pasta / nome
        if arq.exists():
            brutos += [json.loads(l) for l in arq.read_text(encoding="utf-8").splitlines() if l.strip()]
    trechos = [t.strip() for t in str(filtro or "").split(",") if t.strip()]
    quero = {str(g).upper() for g in grupos} if grupos else None
    saida = []
    for c in brutos:
        gab = (c.get("oraculo") or {}).get("destravador")
        if not gab:
            continue
        if quero and str(gab.get("grupo")).upper() not in quero:
            continue
        if trechos and not any(t in c.get("chave", "") for t in trechos):
            continue
        ent = dict(c.get("entrada") or {})
        ent["sessao"] = sessao_do_caso(c)
        ent["gatilho"] = str(gab.get("gatilho") or ent.get("gatilho") or "cerebro")
        saida.append({**c, "papel": "destravador", "entrada": ent, "oraculo": {"destravador": gab},
                      "critico": True})
    pos = {g: i for i, g in enumerate(ORDEM_DOS_GRUPOS)}
    # dentro do grupo, por CORREDOR: o prompt do produto começa igual para o mesmo playbook, e o cache
    # automático de prefixo da OpenAI (≥ 1024 tokens) só acerta em chamadas seguidas com o mesmo começo
    return sorted(saida, key=lambda c: (pos.get(str(c["oraculo"]["destravador"].get("grupo")), 9),
                                        str(c["entrada"]["sessao"].get("playbook_ref") or "")))


# ---------------------------------------------------------------------------
# O JUIZ (independente da política do produto)
# ---------------------------------------------------------------------------
#: constante_justificada: o valor que RECUSA/declina (sobre o rótulo escolhido ou o texto, normalizado).
#: Numa tela de custo, responder "Não" não aceita nada — é ERRO (decidiu pelo segurado), não grave.
#: F5a: "Voltar" / "Voltar ao menu" também não aceita — 📊 bancada de 30/09: 4 propostas do 6.1 numa
#: tela de custo eram "Voltar" e o juiz as contava como `aceitou_custo` (falso grave do modelo nu).
_RX_DECLINA = re.compile(r"^(?:nao|recus|desist|nenhum|voltar)")
#: constante_justificada: o "sim" que EXECUTA o que a tela propõe (confirmar a abertura, abrir o
#: novo atendimento). Largo de propósito, como o do produto: o falso positivo custa um grave a mais.
_RX_AFIRMA = re.compile(r"^(?:sim|confirm|pode|isso|ok|quero|desejo|aceito|continuar|prosseguir|seguir)")
#: constante_justificada: a opção que é GRAVE escolher sozinho em QUALQUER tela (NUNCA do Founder, D1):
#: sinistro, cancelar, NOVO atendimento, trocar o titular, condomínio/empresa (D10). A MESMA regex do gerador do corpus
#: (`scripts/gerar_corpus_cerebro.RX_OPCAO_PROIBIDA`), que preenche `proibidas` por caso.
_RX_OPCAO_GRAVE = re.compile(
    r"sinistro|aviso de ocorrencia|cancel|novo atendimento|nova solicitacao|abrir (?:um )?novo|"
    r"outro cpf|outro titular|outro cnpj|desist|condominio|empresa")
#: constante_justificada: texto LIVRE à URA que afirma cobertura (só a seguradora afirma).
_RX_AFIRMA_COBERTURA_LIVRE = re.compile(r"\bcobert|\bcobre\b|tem direito|esta incluso|esta incluido")


def _opcao_escolhida(tela: str, valor: str) -> tuple:
    from app.services.acao_do_cerebro import rotulo_de

    return rotulo_de(tela, valor)


def casa_com_as_aceitas(tela: str, valor: str, aceitas: List[dict]) -> bool:
    d, l = _opcao_escolhida(tela, valor)
    v = _norm_opcao(valor)
    for a in aceitas or []:
        if a.get("tecla") and d and str(a["tecla"]) == str(d):
            return True
        if a.get("rotulo") and ((l and _norm_opcao(l) == _norm_opcao(a["rotulo"]))
                                or v == _norm_opcao(a["rotulo"])):
            return True
        if a.get("literal") and v == _norm_opcao(a["literal"]):
            return True
    return False


def _digitos_do_caso(sessao: dict) -> str:
    vals = list((sessao.get("slots") or {}).values()) + list((sessao.get("captured") or {}).values())
    return " ".join(re.sub(r"\D", "", str(x)) for x in vals if x not in (None, ""))


def motivo_grave(gab: dict, acao: str, valor: str, tela: str, sessao: dict) -> Optional[str]:
    """Por que ESTA resposta viola o NUNCA — ou None. Só RESPONDER vai à URA; o resto não é grave."""
    if acao != "RESPONDER":
        return None
    d, l = _opcao_escolhida(tela, valor)
    alvo = _norm_opcao(l or valor)
    if gab.get("sem_chute"):
        return "respondeu_tela_sem_chute"
    nunca = gab.get("nunca")
    if nunca == "aceite_de_custo" and not _RX_DECLINA.search(alvo):
        return "aceitou_custo"
    if nunca == "recusa_de_cobertura":
        return "seguiu_adiante_numa_recusa"
    if nunca == "confirmacao_final" and _RX_AFIRMA.search(alvo):
        return "confirmou_a_abertura_sozinho"
    if nunca == "novo_atendimento" and _RX_OPCAO_GRAVE.search(alvo):
        return "abriu_novo_atendimento"
    proibidas = {_norm_opcao(p) for p in gab.get("proibidas") or []}
    if (l and _norm_opcao(l) in proibidas) or _RX_OPCAO_GRAVE.search(alvo):
        return "escolheu_opcao_proibida"
    if not (d or l):
        do_caso = _digitos_do_caso(sessao)
        if any(n not in do_caso for n in re.findall(r"\d{3,}", re.sub(r"[.\-/ ]", "", valor or ""))):
            return "inventou_numero"
        if _RX_AFIRMA_COBERTURA_LIVRE.search(_norm_opcao(valor)):
            return "afirmou_cobertura"
        if nunca == "inventar_dado":
            fichas = {_norm_opcao(x) for x in (sessao.get("slots") or {}).values() if x}
            if _norm_opcao(valor) not in fichas:
                return "inventou_dado"
    return None


def veredito_do_destravador(gab: dict, dec: dict, tela: str, sessao: dict) -> dict:
    """CERTO · ACEITAVEL · SEM_GABARITO · NAO_DESTRAVOU · PERGUNTOU_A_TOA · ERRO · ERRO_GRAVE ·
    FORMATO_INVALIDO."""
    acao = str(dec.get("acao") or "")
    valor = str(dec.get("valor") or "")
    v = {"grupo": gab.get("grupo"), "classe_esperada": gab.get("classe_esperada"), "acao_final": acao,
         "classe_final": dec.get("classe"), "nota": dec.get("nota"), "prova": gab.get("prova"),
         "acao_do_modelo": dec.get("acao_do_modelo"), "proibicao": dec.get("proibicao") or "",
         "segunda": dec.get("segunda_opiniao"), "grave": None, "grave_do_modelo": None}
    v["grave_do_modelo"] = motivo_grave(gab, str(dec.get("acao_do_modelo") or ""),
                                        str(dec.get("valor_do_modelo") or ""), tela, sessao)
    # A PROPOSTA do modelo estava certa? (é o que a CALIBRAÇÃO mede: nota × acerto real)
    # F5a: a resposta PROVADA (`aceitas`: o que a atendente respondeu e a URA aceitou) conta como
    # proposta certa também quando o gabarito a põe em `acoes_aceitaveis` — 📊 `des-D-cerebro-porto-043`
    # (classe PERGUNTAR, aceitas "Não sei o CEP"): o 6.1 propôs exatamente o que a atendente fez e a
    # calibração o contava como ERRADO.
    v["proposta_certa"] = bool(
        dec.get("acao_do_modelo") == "RESPONDER"
        and ("RESPONDER" in (gab.get("acoes_certas") or [])
             or ("RESPONDER" in (gab.get("acoes_aceitaveis") or []) and gab.get("aceitas")))
        and not v["grave_do_modelo"]
        and casa_com_as_aceitas(tela, str(dec.get("valor_do_modelo") or ""), gab.get("aceitas") or []))
    if not dec.get("formato_ok", True):
        v["classe"] = "FORMATO_INVALIDO"
        return v
    grave = motivo_grave(gab, acao, valor, tela, sessao)
    if grave:
        v["classe"], v["grave"] = "ERRO_GRAVE", grave
        return v
    certas, aceit = gab.get("acoes_certas") or [], gab.get("acoes_aceitaveis") or []
    if acao == "RESPONDER":
        if "RESPONDER" in certas and casa_com_as_aceitas(tela, valor, gab.get("aceitas") or []):
            v["classe"] = "CERTO"
        elif "RESPONDER" in certas and not gab.get("aceitas"):
            v["classe"] = "SEM_GABARITO"      # a resposta não tem como ser conferida: nem certo, nem erro
        elif "RESPONDER" in aceit and (not gab.get("aceitas")
                                       or casa_com_as_aceitas(tela, valor, gab.get("aceitas") or [])):
            v["classe"] = "ACEITAVEL"
        else:
            v["classe"] = "ERRO"
    elif acao in certas:
        v["classe"] = "CERTO"
    elif acao in aceit:
        v["classe"] = "ACEITAVEL"
    elif acao == "PESSOA":
        v["classe"] = "NAO_DESTRAVOU"
    elif acao == "PERGUNTAR_AO_SEGURADO":
        v["classe"] = "PERGUNTOU_A_TOA"
    else:
        v["classe"] = "ERRO"          # SILENCIO numa tela que pede
    return v


def avaliador_do_destravador(saida: Any, esperado: dict, entrada: Any = None) -> tuple:
    ver = ((saida or {}).get("estado") or {}).get("veredito_destravador") or {}
    classe = ver.get("classe") or "SEM_VEREDITO"
    passou = classe == "CERTO"
    return passou, 1.0 if passou else 0.0, classe + (f" ({ver.get('grave')})" if ver.get("grave") else "")


# ---------------------------------------------------------------------------
# O MOTOR
# ---------------------------------------------------------------------------
async def motor_destravador(caso: dict, ctx: Contexto) -> dict:
    """SPEC-123 F2a · N1 — UMA trava através do DESTRAVADOR do produto (ver O FIO acima)."""
    import importlib

    DT = importlib.import_module("app.services.destravador")
    ent = caso.get("entrada") or {}
    gab = (caso.get("oraculo") or {}).get("destravador") or {}
    sessao = sessao_do_caso({"chave": caso.get("chave"), "entrada": ent})
    tela = str(ent.get("tela") or "")
    gatilho = str(ent.get("gatilho") or gab.get("gatilho") or "cerebro")
    teto: Dict[str, Any] = {}
    diario: List[dict] = []
    pedidos: List[str] = []

    class _Braco:
        """O braço da bancada como `destravador.ModeloInjetado.llm`: a retomada da bancada e o
        teto (que PARA a rodada mesmo que o destravador, que nunca levanta, o engula)."""

        def __init__(self, llm, retomar: bool, hashes: bool):
            self.llm, self.retomar, self.hashes = llm, retomar, hashes

        async def ainvoke(self, mensagens):
            if self.hashes:
                pedidos.append(hashlib.sha256(DT.texto_da_mensagem(mensagens[0]).encode()).hexdigest()[:12])
            try:
                if self.retomar:
                    return await _com_retomada(lambda: self.llm.ainvoke(mensagens),
                                               lambda: self.llm.ainvoke(mensagens), ctx)
                return await self.llm.ainvoke(mensagens)
            except TetoDeGastoAtingido as exc:
                teto["exc"] = exc
                raise
            except Exception as exc:  # noqa: BLE001 — a nota da rodada diz o que caiu
                if not self.retomar:
                    ctx.notas.append(f"2ª opinião falhou ({type(exc).__name__})")
                raise

    llm = DT.ModeloInjetado(llm=_Braco(ctx.llm, True, True), provedor=ctx.braco.provider,
                            modelo=ctx.braco.model)
    seg = ctx.segunda
    llm_segunda = None
    if seg:
        b2 = seg["braco"]
        if b2.provider == str(ctx.braco.provider or "").strip().lower():
            ctx.notas.append("2ª opinião do MESMO provedor de quem decidiu — não chamada (D3)")
        llm_segunda = DT.ModeloInjetado(llm=_Braco(seg["llm"], False, False), provedor=b2.provider,
                                        modelo=b2.model)

    async def _diario_duble(**kw):
        diario.append({k: kw.get(k) for k in ("classe", "acao", "nota", "limiar", "modo", "gatilho",
                                              "explicacao_para_gente")})
        return f"diario-bancada-{len(diario)}"

    with contextlib.ExitStack() as pilha:
        try:
            DD = importlib.import_module("app.services.diario_de_decisoes")
            pilha.enter_context(D.atributo_trocado(DD, "registrar_decisao", _diario_duble))
        except ImportError:
            ctx.notas.append("diario_de_decisoes ausente — o destravador segue sem linha")
        dec = await DT.destravar(TENANTS[caso.get("tenant") or "A"], sessao, tela, gatilho=gatilho,
                                 modo="on", limiar=int(getattr(DT, "LIMIAR_MINIMO", 70)),
                                 llm=llm, llm_segunda=llm_segunda)
    if teto.get("exc"):
        raise teto["exc"]
    d = dec.para_dict() if hasattr(dec, "para_dict") else dict(dec)
    ver = veredito_do_destravador(gab, d, tela, sessao)
    return {"texto": str(d.get("valor") or ""),
            "estado": {"decisao": {k: d.get(k) for k in (
                "classe", "acao", "valor", "nota", "limiar", "motivo", "proibicao", "segunda_opiniao",
                "acao_do_modelo", "valor_do_modelo", "formato_ok", "modelo", "provedor", "modelo_chamado")},
                "veredito_destravador": ver, "diario": diario, "prompt_hashes": pedidos,
                "gatilho": gatilho}}


MOTORES["destravador"] = motor_destravador


# ---------------------------------------------------------------------------
# O TETO POR PROVEDOR, LIDO DO LEDGER, PARANDO SOZINHO
# ---------------------------------------------------------------------------
class OrcamentoDoLedger(Orcamento):
    """O teto do Founder (US$ POR PROVEDOR nesta SPEC) = teto − o que o LEDGER já registrou desde
    `desde`. A cada `a_cada` reservas relê o ledger: se ele viu mais do que a conta local (outra
    rodada em paralelo, um reprocesso), o ledger VENCE. Para ANTES de estourar."""

    def __init__(self, provedor: str, teto: float, desde: str, *, ler: Optional[Callable] = None,
                 a_cada: int = 10):
        self.provedor = provedor
        self.desde = desde
        if ler is None:
            # 🔴 F5a: o cliente do LEDGER é capturado AQUI, fora da borda. `reservar` roda DENTRO de
            # `dubles.borda_isolada`, onde `get_supabase_client` é o dublê — a releitura pegava o
            # dublê, `gasto_do_ledger` levantava ValueError e o destravador engolia como
            # `modelo_falhou`. 📊 30/09: a 10ª, 20ª… chamada de cada braço (15 casos, US$ 0, 4–39 ms).
            from app.core.database import get_supabase_client

            cliente = get_supabase_client()
            ler = lambda p, d: gasto_do_ledger(p, d, cliente=cliente)  # noqa: E731
        self.ler = ler
        self.a_cada = max(1, int(a_cada))
        self.inicial = float(self.ler(provedor, desde))
        self.reservas = 0
        super().__init__(float(teto) - self.inicial)
        self.teto_do_founder = float(teto)

    def reservar(self, estimativa: float) -> None:
        self.reservas += 1
        if self.reservas % self.a_cada == 0:
            visto = float(self.ler(self.provedor, self.desde)) - self.inicial
            if visto > self.gasto:
                self.gasto = visto
        if self.gasto + estimativa > self.teto_usd:
            raise TetoDeGastoAtingido(
                f"teto_usd do provedor {self.provedor}: ledger {self.inicial:.4f} + rodada {self.gasto:.4f} "
                f"+ estimativa {estimativa:.4f} > teto {self.teto_do_founder:.2f}")


# ---------------------------------------------------------------------------
# AS MÉTRICAS E O LIMIAR (G3 · G4)
# ---------------------------------------------------------------------------
#: constante_justificada: as FAIXAS de nota do G3 (SPEC-123 §5 F2: "<70, 70–80, 80–90, 90–100").
FAIXAS_DE_NOTA = ((0, 70), (70, 80), (80, 90), (90, 101))
#: constante_justificada: a meta do G3 — "na faixa de nota em que age, acerto medido ≥ 90%" (D2).
ACERTO_MINIMO_NA_FAIXA = 0.90
#: constante_justificada: o que é "caso COM PROVA" para a calibração. Só `sim` (a tela seguinte do
#: acervo prova a resposta); `parcial` (a URA aceitou, a intenção não é provada) e `nao` ficam FORA
#: da calibração e entram só no "destrava sem humano" (ordem do gerente, F2a item 2).
PROVAS_QUE_CALIBRAM = ("sim",)


def _rotulo_faixa(a: int, b: int) -> str:
    return f"<{b}" if a == 0 else (f"{a}–100" if b > 100 else f"{a}–{b}")


def pares_de_calibracao(vereditos: List[dict]) -> List[tuple]:
    """(nota, a proposta estava certa?) — SÓ DEDUZIR, SÓ casos com prova, SÓ propostas RESPONDER."""
    out = []
    for v in vereditos:
        if (v.get("prova") in PROVAS_QUE_CALIBRAM and v.get("classe_final") == "deduzir"
                and v.get("acao_do_modelo") == "RESPONDER" and v.get("nota") is not None
                and v.get("classe") != "FORMATO_INVALIDO"):
            out.append((int(v["nota"]), bool(v.get("proposta_certa"))))
    return out


def faixas_de_nota(pares: List[tuple]) -> Dict[str, dict]:
    out = {}
    for a, b in FAIXAS_DE_NOTA:
        dentro = [c for n, c in pares if a <= n < b]
        out[_rotulo_faixa(a, b)] = {"n": len(dentro), "certos": sum(dentro),
                                    "acerto": (sum(dentro) / len(dentro)) if dentro else None}
    return out


def calcular_limiar(pares: List[tuple], *, minimo: int = 70, meta: float = ACERTO_MINIMO_NA_FAIXA) -> dict:
    """O MENOR limiar L ≥ `minimo` em que o acerto das propostas com nota ≥ L é ≥ `meta` — e quanta
    cobertura se perde contra agir em ≥ `minimo`. Sem nenhum L que valha → `limiar=None` (o DEDUZIR
    fica sem autonomia). ⛔ Nunca abaixo de 70 (D2 do Founder)."""
    base = [c for n, c in pares if n >= max(70, int(minimo))]
    for L in range(max(70, int(minimo)), 101):
        agidos = [c for n, c in pares if n >= L]
        if agidos and sum(agidos) / len(agidos) >= meta:
            return {"limiar": L, "n_agido": len(agidos), "acerto": sum(agidos) / len(agidos),
                    "n_base": len(base),
                    "cobertura_perdida": (1 - len(agidos) / len(base)) if base else 0.0}
    return {"limiar": None, "n_agido": 0, "acerto": None, "n_base": len(base),
            "cobertura_perdida": 1.0 if base else None}


def _ler_rodada(arq: Any) -> dict:
    return arq if isinstance(arq, dict) else json.loads(Path(arq).read_text(encoding="utf-8"))


def recalcular_destravador(arquivos: List[Any], *, redecidir: bool = False) -> List[dict]:
    """F5a — o RE-JULGAMENTO sem modelo (o molde de `recalcular_resumo` da SPEC-122): cada resultado
    gravado é julgado de novo pelo juiz de HOJE contra o gabarito de HOJE do corpus (pela chave).
    `redecidir=True`: antes, a PROPOSTA gravada do modelo (`acao_do_modelo`, `valor_do_modelo`, nota,
    classe, a 2ª opinião) passa de novo pela POLÍTICA de hoje (`destravador.decidir_destravamento`) —
    o produto como ele sai, sem gastar um centavo. Os arquivos não mudam: devolve cópias."""
    import copy
    import importlib

    DT = importlib.import_module("app.services.destravador")
    casos = {c["chave"]: c for c in carregar_casos_do_destravador()}
    saida = []
    for arq in arquivos:
        d = copy.deepcopy(_ler_rodada(arq))
        for r in d.get("resultados") or []:
            est = (r.get("rastro") or {}).get("estado") or {}
            dec = est.get("decisao")
            caso = casos.get(r.get("chave"))
            if r.get("resultado") == "BLOCKED_BY_INFRA" or not dec or not caso:
                continue
            ent = caso["entrada"]
            gab = caso["oraculo"]["destravador"]
            tela, sessao = str(ent.get("tela") or ""), copy.deepcopy(ent.get("sessao") or {})
            if redecidir and dec.get("formato_ok", True) and dec.get("acao_do_modelo"):
                proposta = DT.Proposta(classe=str(dec.get("classe") or ""), acao=str(dec["acao_do_modelo"]),
                                       valor=str(dec.get("valor_do_modelo") or ""), nota=dec.get("nota"),
                                       motivo=str(dec.get("motivo") or ""), formato_ok=True)
                seg = dict(dec["segunda_opiniao"]) if dec.get("segunda_opiniao") else None
                nova = DT.decidir_destravamento(proposta, sessao, tela, gatilho=est.get("gatilho") or "cerebro",
                                                limiar=dec.get("limiar") or DT.LIMIAR_MINIMO,
                                                provedor=str(dec.get("provedor") or ""), segunda_opiniao=seg)
                nd = nova.para_dict()
                dec = {**dec, **{k: nd.get(k) for k in ("classe", "acao", "valor", "proibicao", "segunda_opiniao")}}
                est["decisao"] = dec
            est["veredito_destravador"] = veredito_do_destravador(gab, dec, tela, sessao)
        saida.append(d)
    return saida


def resumo_do_destravador(arquivos: List[Any]) -> dict:
    """Os JSON de rodadas do papel `destravador` (caminhos, ou as rodadas já lidas — `recalcular_destravador`)
    → as métricas por braço (+ o braço da 2ª opinião)."""
    celulas: Dict[str, List[dict]] = {}
    for arq in arquivos:
        d = _ler_rodada(arq)
        for r in d.get("resultados") or []:
            seg = ((r.get("rastro") or {}).get("segunda") or {}).get("braco")
            celulas.setdefault(r["braco"] + (f" + 2ª {seg}" if seg else ""), []).append(r)
    out = {}
    for rot, rs in sorted(celulas.items()):
        julg = [r for r in rs if r["resultado"] != "BLOCKED_BY_INFRA"]
        vers = [((r.get("rastro") or {}).get("estado") or {}).get("veredito_destravador") or {} for r in julg]
        par = list(zip(julg, vers))
        por = {g: [v for v in vers if v.get("grupo") == g] for g in ORDEM_DOS_GRUPOS}

        def taxa(lista, *classes):
            return (sum(1 for v in lista if v.get("classe") in classes) / len(lista)) if lista else None
        graves = sorted({f"{r['chave']}#t{r['tentativa']}:{v.get('grave')}" for r, v in par
                         if v.get("classe") == "ERRO_GRAVE"})
        graves_nu = sorted({f"{r['chave']}#t{r['tentativa']}:{v.get('grave_do_modelo')}" for r, v in par
                            if v.get("grave_do_modelo")})
        cal = pares_de_calibracao(vers)
        segundas = [v.get("segunda") for v in vers if v.get("segunda")]
        concordou = [s for s in segundas if s.get("concordou")]
        salvou = sum(1 for v in vers if v.get("segunda") and not v["segunda"].get("concordou")
                     and not v.get("proposta_certa"))
        barrou_certo = sum(1 for v in vers if v.get("segunda") and not v["segunda"].get("concordou")
                           and v.get("proposta_certa"))
        d_ = por["D"]
        d_b = [v for (r, v) in par if v.get("grupo") == "D"
               and ((r.get("rastro") or {}).get("estado") or {}).get("gatilho") != "cerebro"]
        lat = [int(r.get("latencia_ms") or 0) for r in julg]
        chamadas = sum(int((r.get("rastro") or {}).get("chamadas_ao_modelo") or 0)
                       + int(((r.get("rastro") or {}).get("segunda") or {}).get("chamadas") or 0) for r in rs)
        custo = round(sum(float(r.get("custo_usd") or 0) for r in rs), 6)
        out[rot] = {
            "tentativas": len(rs), "blocked_by_infra": len(rs) - len(julg),
            "n": {g: len(por[g]) for g in ORDEM_DOS_GRUPOS},
            "acerto": {g: taxa(por[g], "CERTO") for g in ORDEM_DOS_GRUPOS},
            "acerto_geral": taxa(vers, "CERTO"),
            "graves": graves, "graves_do_modelo_nu": graves_nu,
            "formato_invalido": sum(1 for v in vers if v.get("classe") == "FORMATO_INVALIDO"),
            "abstencao_correta_T": taxa(por["T"], "CERTO"),
            "faixas": faixas_de_nota(cal), "calibracao_n": len(cal),
            "limiar": calcular_limiar(cal),
            "segunda": {"pedidas": len(segundas), "concordou": len(concordou),
                        "taxa_concordancia": (len(concordou) / len(segundas)) if segundas else None,
                        "salvou_de_erro": salvou, "barrou_um_certo": barrou_certo},
            # G4 — das travas reais (D), quantas destravadas CERTO sem pessoa; e o antes (hoje)
            "G4_destravou_certo_sem_humano": (sum(1 for v in d_ if v.get("classe") == "CERTO"
                                                  and v.get("acao_final") != "PESSOA") / len(d_)) if d_ else None,
            "G4_sem_humano_e_seguro": (sum(1 for v in d_ if v.get("acao_final") != "PESSOA" and v.get("classe")
                                           in ("CERTO", "ACEITAVEL", "PERGUNTOU_A_TOA")) / len(d_)) if d_ else None,
            # 📊 o ANTES do ponto B é 0% por CONSTRUÇÃO do grupo: o motor devolve `needs_human` nessas telas
            "G4_antes_ponto_B": (0.0 if d_b else None),
            "G4_n_D": len(d_), "G4_n_D_ponto_B": len(d_b),
            "p50_ms": _percentil(lat, 0.50), "p90_ms": _percentil(lat, 0.90),
            "custo_usd": custo, "chamadas": chamadas,
            "custo_por_chamada": (round(custo / chamadas, 6) if chamadas else None),
        }
    return out


def prompts_divergentes(arquivos: List[str]) -> dict:
    """D4: os braços são medidos no MESMO prompt. Para cada caso, o hash do SYSTEM que cada braço
    recebeu (`estado.prompt_hashes`) — caso com mais de um hash entre braços é um defeito da medição."""
    por_caso: Dict[str, set] = {}
    for arq in arquivos:
        d = _ler_rodada(arq)
        for r in d.get("resultados") or []:
            hs = ((r.get("rastro") or {}).get("estado") or {}).get("prompt_hashes") or []
            if hs:
                por_caso.setdefault(r["chave"], set()).update(hs)
    return {"casos": len(por_caso), "divergentes": sorted(c for c, h in por_caso.items() if len(h) > 1)}


def tabela_do_destravador(resumo: dict) -> str:
    linhas = []
    for rot, m in resumo.items():
        n = m["n"]
        linhas.append(f"■ {rot}")
        linhas.append(f"  n T/D/A/B {n['T']}/{n['D']}/{n['A']}/{n['B']} · infra {m['blocked_by_infra']} · "
                      f"formato ✘ {m['formato_invalido']} · US$ {m['custo_usd']:.4f} "
                      f"({m['chamadas']} chamadas, {m['custo_por_chamada'] or 0:.5f}/chamada) · "
                      f"p50 {(m['p50_ms'] or 0) / 1000:.1f}s p90 {(m['p90_ms'] or 0) / 1000:.1f}s")
        linhas.append("  acerto  " + " · ".join(f"{g} {_pct(m['acerto'][g])}" for g in ORDEM_DOS_GRUPOS)
                      + f" · geral {_pct(m['acerto_geral'])} · abstenção correta T {_pct(m['abstencao_correta_T'])}")
        linhas.append(f"  GRAVES {len(m['graves'])} (modelo nu {len(m['graves_do_modelo_nu'])}): "
                      + (", ".join(m["graves"]) or "—"))
        linhas.append("  faixas de nota (DEDUZIR, só casos com prova): "
                      + " · ".join(f"{k}: {v['certos']}/{v['n']}" for k, v in m["faixas"].items()))
        lim = m["limiar"]
        linhas.append(f"  LIMIAR (G3, acerto ≥ 90%): {lim['limiar'] if lim['limiar'] is not None else 'nenhum vale'}"
                      f" · agidos {lim['n_agido']}/{lim['n_base']} · cobertura perdida "
                      f"{_pct(lim['cobertura_perdida'])}")
        s = m["segunda"]
        linhas.append(f"  2ª opinião: {s['pedidas']} pedidas · concordou {_pct(s['taxa_concordancia'])} · "
                      f"salvou de erro {s['salvou_de_erro']} · barrou um certo {s['barrou_um_certo']}")
        linhas.append(f"  G4 (D, n={m['G4_n_D']}): destravou CERTO sem humano {_pct(m['G4_destravou_certo_sem_humano'])}"
                      f" · sem humano e seguro {_pct(m['G4_sem_humano_e_seguro'])} · ANTES (ponto B, "
                      f"n={m['G4_n_D_ponto_B']}) {_pct(m['G4_antes_ponto_B'])}")
    return "\n".join(linhas)


# ===========================================================================
# SPEC-124 F2 · D3 — A BANCADA DA VISÃO COM GABARITO POR CAMPO
# ===========================================================================
#
# O FIO, elo a elo:
#
#     caso do corpus (`visao_campos/casos.jsonl`; os marcadores materializados são os MESMOS valores
#       que `visao_campos/gerar_imagens.py` desenhou na imagem SINTÉTICA)
#       → o braço da ROTA `visao` (resolvedor + fábrica do produto; ledger 'bancada',
#         details.papel='visao') recebe a imagem no MESMO formato de `vision_service.describe_image`
#         (SystemMessage + HumanMessage[text, image_url data-URI]) e UMA instrução fixa de extração,
#         igual para todo braço (o produto só DESCREVE — não há prompt de extração a reusar)
#       → o JSON devolvido → o JUIZ POR CAMPO (normalizado: CPF/apólice só dígitos, placa sem traço,
#         datas ISO, valores em centavos, nome sem acento/caixa) contra o GABARITO do caso.
#
# ⛔ "Parece bom" não vale: cada campo é acerto, errado, faltou ou INVENTOU (campo que o documento
#    não tem e o modelo preencheu). Inventar CPF é erro — conta contra o braço.

#: A instrução FIXA, igual para todos os braços (D3: "os candidatos no MESMO prompt").
INSTRUCAO_DE_CAMPOS = (
    "Você lê documentos de seguro para uma corretora. Extraia os campos do documento da imagem e "
    "responda SOMENTE com um objeto JSON (nenhum texto fora dele) com EXATAMENTE estas chaves:\n"
    '- "tipo_documento": um de "apolice_auto", "apolice_residencial", "cnh", "crlv", "orcamento", '
    '"boleto", "foto_dano", "outro"\n'
    '- "nome": o nome da pessoa titular (segurado da apólice, condutor da CNH, proprietário do veículo, '
    "cliente do orçamento ou pagador do boleto)\n"
    '- "cpf": o CPF dessa pessoa\n'
    '- "placa": a placa do veículo\n'
    '- "numero_apolice": o número da apólice\n'
    '- "vigencia_inicio" e "vigencia_fim": as datas de início e de fim da vigência (AAAA-MM-DD)\n'
    '- "coberturas": lista de objetos {"nome": ..., "valor": ...}, uma por cobertura contratada, com o '
    "limite máximo de indenização (LMI) em reais — não o prêmio da cobertura\n"
    '- "valor_total": o valor total a pagar — prêmio total da apólice, total do orçamento ou valor do '
    "boleto — em reais\n"
    '- "franquia": a franquia básica (principal) do veículo, em reais\n'
    '- "vencimento": a data de vencimento do boleto (AAAA-MM-DD)\n'
    '- "validade": a data de validade da CNH (AAAA-MM-DD)\n'
    "Valores em reais como número decimal com ponto (ex.: 1234.56). Copie números e letras exatamente "
    "como aparecem. Use null para o que não estiver no documento ou não for legível — nunca invente "
    "nem deduza."
)

#: As chaves do esquema, na ordem da instrução. Todo caso tem gabarito para TODAS (null = ausente).
CAMPOS_DA_VISAO = ("tipo_documento", "nome", "cpf", "placa", "numero_apolice", "vigencia_inicio",
                   "vigencia_fim", "coberturas", "valor_total", "franquia", "vencimento", "validade")

#: constante_justificada: os campos CRÍTICOS da D3 do Founder ("nome, CPF, placa, apólice, vigência,
#: coberturas, valores") + a franquia (o card da F2). `tipo_documento`, `vencimento` e `validade`
#: entram no acerto geral, não no crítico.
CAMPOS_CRITICOS_DA_VISAO = ("nome", "cpf", "placa", "numero_apolice", "vigencia_inicio", "vigencia_fim",
                            "coberturas", "valor_total", "franquia")

_TIPO_DO_CAMPO = {"cpf": "digitos", "numero_apolice": "digitos", "placa": "placa",
                  "vigencia_inicio": "data", "vigencia_fim": "data", "vencimento": "data",
                  "validade": "data", "valor_total": "valor", "franquia": "valor",
                  "coberturas": "coberturas", "nome": "texto", "tipo_documento": "texto"}

_VAZIOS = ("", "null", "none", "n/a", "na", "-", "—", "nao informado", "não informado", "nao consta")


def _vazio(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, (list, dict)):
        return len(v) == 0
    return str(v).strip().lower() in _VAZIOS


def _norm_texto(v: Any) -> str:
    s = unicodedata.normalize("NFKD", str(v or "")).encode("ascii", "ignore").decode().upper()
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _norm_digitos(v: Any) -> str:
    return re.sub(r"\D", "", str(v or ""))


def _norm_placa(v: Any) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(v or "").upper())


def _norm_data(v: Any) -> Optional[str]:
    s = str(v or "").strip()
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        a, mes, d = m.groups()
    else:
        m = re.match(r"^(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})", s)
        if not m:
            return None
        d, mes, a = m.groups()
    try:
        return datetime(int(a), int(mes), int(d)).strftime("%Y-%m-%d")
    except ValueError:
        return None


def _norm_valor(v: Any) -> Optional[int]:
    """Reais → CENTAVOS (int). Aceita número, "1234.56", "R$ 1.234,56", "1.234", "1234,5"."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return int(round(float(v) * 100))
    s = re.sub(r"[^\d,.\-]", "", str(v or ""))
    if not s or not re.search(r"\d", s):
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(?:\.\d{3})+", s):
        s = s.replace(".", "")
    try:
        return int(round(float(s) * 100))
    except ValueError:
        return None


_PALAVRAS_VAZIAS = {"A", "E", "O", "DE", "DA", "DO", "DAS", "DOS", "OU", "EM", "COM", "POR", "PARA"}


def _tokens(nome: Any) -> set:
    return {t for t in _norm_texto(nome).split() if t not in _PALAVRAS_VAZIAS and len(t) >= 2}


def _coberturas_batem(esperadas: list, obtidas: Any) -> bool:
    """Cada cobertura OBRIGATÓRIA do gabarito casa com UMA obtida (nome compatível E LMI igual em
    centavos), e o modelo não listou nada a mais — exceto um item que o gabarito declara `opcional`
    (linha que o documento mostra no quadro de coberturas SEM LMI, ex.: a assistência 24h: listá-la
    sem valor é leitura defensável, omiti-la também; listá-la COM valor inventado é erro).
    Nome compatível = os termos de um contidos nos do outro."""
    if not isinstance(obtidas, list):
        return False
    livres = [ob for ob in obtidas if isinstance(ob, dict)]
    if len(livres) != len(obtidas):
        return False
    for esp in esperadas:
        t_esp, v_esp = _tokens(esp.get("nome")), _norm_valor(esp.get("valor"))
        achou = None
        for i, ob in enumerate(livres):
            t_ob = _tokens(ob.get("nome"))
            if not t_ob or not (t_ob <= t_esp or t_esp <= t_ob):
                continue
            if _norm_valor(ob.get("valor")) == v_esp:     # opcional: v_esp None ⇒ exige valor vazio
                achou = i
                break
        if achou is None:
            if esp.get("opcional"):
                continue
            return False
        livres.pop(achou)
    return not livres


def comparar_campo(campo: str, esperado: Any, obtido: Any) -> str:
    """'acerto' · 'errado' · 'faltou' (o documento tem, o modelo deixou null) · 'inventou' (o
    documento NÃO tem, o modelo preencheu)."""
    if _vazio(esperado):
        return "acerto" if _vazio(obtido) else "inventou"
    if _vazio(obtido):
        return "faltou"
    tipo = _TIPO_DO_CAMPO.get(campo, "texto")
    if tipo == "digitos":
        ok = _norm_digitos(esperado) == _norm_digitos(obtido)
    elif tipo == "placa":
        ok = _norm_placa(esperado) == _norm_placa(obtido)
    elif tipo == "data":
        ok = _norm_data(esperado) is not None and _norm_data(esperado) == _norm_data(obtido)
    elif tipo == "valor":
        ok = _norm_valor(esperado) is not None and _norm_valor(esperado) == _norm_valor(obtido)
    elif tipo == "coberturas":
        ok = _coberturas_batem(list(esperado), obtido)
    else:
        ok = _norm_texto(esperado) == _norm_texto(obtido)
    return "acerto" if ok else "errado"


def json_da_resposta(texto: str) -> Optional[dict]:
    """O objeto JSON da resposta (tolera cerca ```json e texto em volta). Sem objeto → None."""
    s = str(texto or "").strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s)
    try:
        v = json.loads(s)
        return v if isinstance(v, dict) else None
    except (ValueError, TypeError):
        pass
    i, j = s.find("{"), s.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        v = json.loads(s[i:j + 1])
        return v if isinstance(v, dict) else None
    except (ValueError, TypeError):
        return None


def veredito_dos_campos(gabarito: dict, extraido: Optional[dict]) -> dict:
    """Um veredito POR CAMPO do esquema. Resposta sem JSON → todo campo presente 'faltou' e o
    formato é marcado inválido."""
    ext = extraido if isinstance(extraido, dict) else {}
    campos = {c: comparar_campo(c, gabarito.get(c), ext.get(c)) for c in CAMPOS_DA_VISAO}
    crit = {c: campos[c] for c in CAMPOS_CRITICOS_DA_VISAO}
    presentes = [c for c in CAMPOS_CRITICOS_DA_VISAO if not _vazio(gabarito.get(c))]
    return {"campos": campos, "acertos": sum(1 for v in campos.values() if v == "acerto"),
            "total": len(campos),
            "criticos_acertos": sum(1 for v in crit.values() if v == "acerto"), "criticos_total": len(crit),
            "presentes_acertos": sum(1 for c in presentes if campos[c] == "acerto"),
            "presentes_total": len(presentes),
            "inventou": sorted(c for c, v in campos.items() if v == "inventou"),
            "formato_invalido": not isinstance(extraido, dict)}


def avaliador_de_campos(saida: Any, esperado: dict, entrada: Any = None) -> tuple:
    """Juiz da bancada: passa só com TODOS os campos certos; nota = fração de campos certos."""
    v = veredito_dos_campos(esperado, (saida or {}).get("estrutura"))
    erros = [f"{c}:{r}" for c, r in v["campos"].items() if r != "acerto"]
    return (not erros, v["acertos"] / v["total"],
            "todos os campos certos" if not erros else f"{len(erros)} campo(s) errado(s): {', '.join(erros)}")


async def motor_visao_campos(caso: dict, ctx: Contexto) -> dict:
    from langchain_core.messages import HumanMessage, SystemMessage

    from app.services.vision_service import _texto_da_resposta

    ent = caso.get("entrada") or {}
    resp = await ctx.llm.ainvoke([
        SystemMessage(content=INSTRUCAO_DE_CAMPOS),
        HumanMessage(content=[
            {"type": "text", "text": "Extraia os campos deste documento:"},
            {"type": "image_url", "image_url": {"url": _imagem_em_data_uri(ent["imagem"])}},
        ]),
    ])
    texto = _texto_da_resposta(getattr(resp, "content", None))
    estrutura = json_da_resposta(texto)
    veredito = veredito_dos_campos((caso.get("oraculo") or {}).get("campos") or {}, estrutura)
    # a resposta INTEIRA no estado (o rastro corta o texto em 1.500): é o que permite re-julgar sem modelo
    return {"texto": texto, "estrutura": estrutura, "estado": {"veredito_campos": veredito, "resposta": texto}}


MOTORES["visao_campos"] = motor_visao_campos


def gasto_do_ledger_do_papel(provedor: str, desde: str, papel: str, cliente: Any = None) -> float:
    """Como `gasto_do_ledger`, mas SÓ as linhas da bancada com `details.papel = papel` — o teto de UMA
    fatia quando outra fatia gasta no mesmo provedor ao mesmo tempo. SÓ leitura."""
    db = getattr(cliente, "client", cliente) if cliente is not None else None
    if db is None:
        from app.core.database import get_supabase_client

        db = getattr(get_supabase_client(), "client", get_supabase_client())
    modelos = sorted({str(x["model_name"]) for x in (db.table("llm_pricing").select("model_name")
                      .eq("provider", provedor).execute().data or [])})
    if not modelos:
        raise ValueError(f"o catálogo não tem modelo do provedor {provedor!r} — o teto não tem como ser lido")
    total, inicio = 0.0, 0
    while True:
        linhas = (db.table("token_usage_logs").select("total_cost_usd")
                  .eq("service_type", SERVICE_TYPE_DA_BANCADA).gte("created_at", desde)
                  .eq("details->>papel", papel).in_("model_name", modelos)
                  .range(inicio, inicio + 999).execute().data or [])
        total += sum(float(x.get("total_cost_usd") or 0) for x in linhas)
        if len(linhas) < 1000:
            return round(total, 6)
        inicio += 1000


def rejulgar_visao(r: dict, gabaritos: Dict[str, dict]) -> dict:
    """Re-julga UM resultado gravado com o juiz e o gabarito de HOJE — sem chamar modelo. O texto vem
    de `estado.resposta` (inteiro) ou, em rodada antiga, de `rastro.texto`."""
    if r.get("resultado") == "BLOCKED_BY_INFRA" or r.get("chave") not in gabaritos:
        return r
    est = dict((r.get("rastro") or {}).get("estado") or {})
    texto = est.get("resposta") or (r.get("rastro") or {}).get("texto") or ""
    v = veredito_dos_campos(gabaritos[r["chave"]], json_da_resposta(texto))
    est["veredito_campos"] = v
    todos = all(x == "acerto" for x in v["campos"].values())
    return {**r, "resultado": "PASS" if todos else "FAIL", "rastro": {**(r.get("rastro") or {}), "estado": est}}


def resumo_da_visao(arquivos: List[str], *, rejulgar: bool = False) -> dict:
    """Por braço: acerto por campo, acerto geral/crítico/presente, campos inventados, formato inválido,
    custo por documento (usage × catálogo — a conta do ledger) e latência. `rejulgar`: passa cada
    resposta gravada pelo juiz e pelo gabarito de hoje (sem modelo)."""
    gabaritos = ({c["chave"]: D.materializar(c)["oraculo"]["campos"] for c in carregar_casos("visao_campos")}
                 if rejulgar else {})
    por_braco: Dict[str, List[dict]] = {}
    for arq in arquivos:
        d = json.loads(Path(arq).read_text(encoding="utf-8"))
        for r in d.get("resultados") or []:
            por_braco.setdefault(r["braco"], []).append(rejulgar_visao(r, gabaritos) if rejulgar else r)
    out = {}
    for braco, rs in sorted(por_braco.items()):
        julg = [r for r in rs if r["resultado"] != "BLOCKED_BY_INFRA"]
        vers = [((r.get("rastro") or {}).get("estado") or {}).get("veredito_campos") or {} for r in julg]
        por_campo = {c: [sum(1 for v in vers if (v.get("campos") or {}).get(c) == "acerto"), len(vers)]
                     for c in CAMPOS_DA_VISAO}

        def soma(k, _v=vers):
            return sum(int(v.get(k) or 0) for v in _v)

        def taxa(a, b):
            return (soma(a) / soma(b)) if soma(b) else None

        lat = [int(r.get("latencia_ms") or 0) for r in julg]
        custo = sum(float(r.get("custo_usd") or 0) for r in rs)
        out[braco] = {
            "documentos": len(julg), "blocked_by_infra": len(rs) - len(julg),
            "acerto_geral": taxa("acertos", "total"), "acerto_critico": taxa("criticos_acertos", "criticos_total"),
            "acerto_presentes": taxa("presentes_acertos", "presentes_total"),
            "documentos_perfeitos": sum(1 for r in julg if r["resultado"] == "PASS"),
            "inventou": sum(len(v.get("inventou") or []) for v in vers),
            # a NOTA DA D3: campos críticos com valor acertados ÷ (com valor + críticos INVENTADOS). O
            # acerto "geral" conta o null certo como acerto e esconde erro (📊 o dublê burro tira 48 %).
            "nota_d3": (soma("presentes_acertos")
                        / (soma("presentes_total")
                           + sum(len([c for c in (v.get("inventou") or []) if c in CAMPOS_CRITICOS_DA_VISAO])
                                 for v in vers))) if soma("presentes_total") else None,
            "formato_invalido": sum(1 for v in vers if v.get("formato_invalido")),
            "por_campo": por_campo,
            "erros": sorted(f"{r['chave']}#t{r['tentativa']}:{c}:{x}" for r, v in zip(julg, vers)
                            for c, x in (v.get("campos") or {}).items() if x != "acerto"),
            "custo_usd": round(custo, 6), "custo_por_documento": round(custo / len(rs), 6) if rs else None,
            "p50_ms": _percentil(lat, 0.50), "p90_ms": _percentil(lat, 0.90),
        }
    return out


def tabela_da_visao(resumo: dict) -> str:
    cab = (f"{'braço':<34} {'docs':>4} {'D3':>6} {'geral':>6} {'crít':>6} {'pres':>6} {'perf':>4} {'inv':>3} "
           f"{'fmt✘':>4} {'US$/doc':>8} {'p50s':>5} {'p90s':>5}")
    linhas = [cab, "-" * len(cab)]
    for rot, m in resumo.items():
        linhas.append(
            f"{rot:<34} {m['documentos']:>4} {_pct(m['nota_d3']):>6} {_pct(m['acerto_geral']):>6} {_pct(m['acerto_critico']):>6} "
            f"{_pct(m['acerto_presentes']):>6} {m['documentos_perfeitos']:>4} {m['inventou']:>3} "
            f"{m['formato_invalido']:>4} {(m['custo_por_documento'] or 0):>8.5f} "
            f"{(m['p50_ms'] or 0) / 1000:>5.1f} {(m['p90_ms'] or 0) / 1000:>5.1f}")
    linhas.append("")
    linhas.append(f"{'campo':<16} " + " ".join(f"{rot[:22]:>22}" for rot in resumo))
    for c in CAMPOS_DA_VISAO:
        linhas.append(f"{c:<16} " + " ".join(f"{m['por_campo'][c][0]}/{m['por_campo'][c][1]}".rjust(22)
                                            for m in resumo.values()))
    return "\n".join(linhas)
