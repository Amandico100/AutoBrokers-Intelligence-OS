"""SPEC-116 U9 — o modelo do PORTAL pelo MESMO catálogo e pela MESMA rota do produto.

Por que um módulo aqui, e não `app.factories`
---------------------------------------------
📊 23/09/2026: a imagem do portal-worker (`backend/portal_worker/Dockerfile`)
copia SÓ `backend/portal_worker/` e instala SÓ `portal_worker/requirements.txt`
(fastapi, playwright, supabase, httpx, redis). Não há `app/`, nem langchain,
nem pydantic-settings. Importar `app.factories` arrastaria o backend inteiro para
um contêiner de navegador. Então este é um TRANSPORTE FINO, não um motor:

  · quem ESCOLHE o modelo é a rota `portal_decisao` da tabela `llm_papeis` — a
    mesma linha que o Model Router (`app/factories/model_policy.py`) lê;
  · o que o modelo PODE (lifecycle, classes de dado, capacidades, preço) é a
    linha do `llm_pricing` — o mesmo catálogo;
  · o banco fora do ar → o SNAPSHOT versionado (`modelos_snapshot.json`, o mesmo
    arquivo gerado para o backend, copiado para a imagem pelo Dockerfile);
    sem banco e sem snapshot → ERRO explícito;
  · as regras de recusa são as do resolvedor, e o guarda
    `tests/test_spec116_f3b_portal.py` confere, papel a papel, que este leitor e
    `model_policy.resolver` devolvem o MESMO modelo e recusam os MESMOS casos.

⛔ O que morreu: `PORTAL_VISION_MODEL` (fica IGNORADO), o `gpt-4o` fixo e o
`_MODELO_DE_RESERVA = "gpt-4o-mini"` que qualquer erro >= 400 (429 e 5xx
inclusive) disparava CALADO, fora do ledger. Erro agora é erro: o
`decide_next_action` devolve `ask_human` com o motivo e o job segue o caminho de
`needs_human` que o worker já tem. Reserva só se a ROTA declarar (📊 23/09: NULA).

O uso de cada chamada vai para `token_usage_logs` (service_type='portal',
company_id do job, details com papel/resolvido/real/reserva) pelo REST do
Supabase — antes o portal não deixava uma linha sequer (📊 38 jobs, 0 linhas).
"""
from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

# ⚠️ Capturado no IMPORT, de propósito: o REST do Supabase usa SEMPRE o httpx
# real. A chamada ao PROVEDOR importa `httpx` na hora (ver `_postar_no_provedor`)
# — é por ali que a bancada (SPEC-116 F5a) desvia o tráfego para o braço.
import httpx as _httpx_real

logger = logging.getLogger(__name__)

PAPEL = "portal_decisao"
SERVICE_TYPE = "portal"
CACHE_TTL_SECONDS = 60
TIMEOUT_DO_PROVEDOR = 45.0
MAX_TOKENS_ANTHROPIC = 4096

#: As MESMAS listas de `app/factories/model_policy.py` (o guarda confere a igualdade).
LIFECYCLES_USAVEIS = ("APPROVED", "CANDIDATE", "DEPRECATED")
CLASSES_DE_DADO = ("publico", "interno", "pii")
NIVEIS_DE_ESFORCO = ("none", "low", "medium", "high", "xhigh", "max")

_COLUNAS_PAPEIS = (
    "papel,provider,modelo_primario,esforco,provider_reserva,modelo_reserva,"
    "esforco_reserva,classe_de_dado,versao"
)
_COLUNAS_CATALOGO = (
    "model_name,provider,api_surface,lifecycle,classes_de_dado,capacidades,base_url,"
    "api_key_env,input_price_per_million,output_price_per_million,input_price_long,"
    "output_price_long,limiar_contexto_longo,cache_read_multiplier,cache_write_multiplier,"
    "cached_input_multiplier,unit,is_active"
)

#: Chave por provedor quando o catálogo não declara `api_key_env`.
_CHAVE_PADRAO = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}
_URL_PADRAO = {"openai": "https://api.openai.com/v1", "anthropic": "https://api.anthropic.com/v1"}


class ModeloDoPortalIndisponivel(Exception):
    """Sem rota, rota recusada, sem chave, sem transporte ou o provedor falhou."""


@dataclass(frozen=True)
class ModeloDoPortal:
    papel: str
    provider: str
    model: str
    effort: Optional[str]
    api_surface: str
    capacidades: dict
    classe_de_dado: str
    lifecycle: str
    origem: str                      # "rota" (banco) | "snapshot"
    versao_da_rota: Optional[int]
    base_url: Optional[str] = None
    api_key_env: Optional[str] = None
    precos: dict = field(default_factory=dict)
    reserva: Optional["ModeloDoPortal"] = None


# ---------------------------------------------------------------------------
# A FONTE: banco (REST do Supabase, cache 60 s) → snapshot → erro
# ---------------------------------------------------------------------------
#: Borda dublável nos testes: `httpx.MockTransport` no lugar da rede.
transporte_do_supabase: Optional[Any] = None

_cache: Dict[str, Any] = {"dados": None, "em": 0.0}


def _supabase() -> Tuple[str, str]:
    url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
    chave = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""
    return url, chave


def _cabecalhos_supabase(chave: str) -> Dict[str, str]:
    return {"apikey": chave, "Authorization": f"Bearer {chave}"}


def _cliente_supabase() -> Any:
    kw: Dict[str, Any] = {"timeout": 10.0}
    if transporte_do_supabase is not None:
        kw["transport"] = transporte_do_supabase
    return _httpx_real.AsyncClient(**kw)


async def _ler_do_banco() -> Tuple[Dict[str, dict], Dict[str, dict]]:
    """A rota do papel + as linhas do catálogo dos modelos dela. Levanta em qualquer falha."""
    url, chave = _supabase()
    if not url or not chave:
        raise RuntimeError("SUPABASE_URL/SUPABASE_SERVICE_KEY ausentes no worker")
    async with _cliente_supabase() as c:
        r = await c.get(f"{url}/rest/v1/llm_papeis", headers=_cabecalhos_supabase(chave),
                        params={"select": _COLUNAS_PAPEIS, "papel": f"eq.{PAPEL}"})
        r.raise_for_status()
        papeis = {p["papel"]: p for p in (r.json() or [])}
        rota = papeis.get(PAPEL)
        if not rota:
            raise RuntimeError(f"rota {PAPEL!r} ausente em llm_papeis")
        nomes = [n for n in (rota.get("modelo_primario"), rota.get("modelo_reserva")) if n]
        r = await c.get(f"{url}/rest/v1/llm_pricing", headers=_cabecalhos_supabase(chave),
                        params={"select": _COLUNAS_CATALOGO,
                                "model_name": "in.(" + ",".join(f'"{n}"' for n in nomes) + ")"})
        r.raise_for_status()
        catalogo = {l["model_name"]: l for l in (r.json() or [])}
    return catalogo, papeis


def caminhos_do_snapshot() -> List[Path]:
    aqui = Path(__file__).resolve().parent
    caminhos = []
    if os.getenv("PORTAL_SNAPSHOT_DE_MODELOS"):
        caminhos.append(Path(os.environ["PORTAL_SNAPSHOT_DE_MODELOS"]))
    caminhos.append(aqui / "modelos_snapshot.json")                       # na imagem (Dockerfile)
    caminhos.append(aqui.parent / "app" / "factories" / "modelos_snapshot.json")  # no repositório
    return caminhos


def _ler_snapshot() -> Tuple[Dict[str, dict], Dict[str, dict]]:
    for p in caminhos_do_snapshot():
        if p.is_file():
            doc = json.loads(p.read_text(encoding="utf-8"))
            return doc.get("catalogo") or {}, doc.get("papeis") or {}
    raise ModeloDoPortalIndisponivel(
        "banco indisponível e nenhum modelos_snapshot.json na imagem — o portal não "
        "escolhe modelo por conta própria")


#: Ponto de troca da BORDA (banco). Produção: `_ler_do_banco`.
leitor_do_banco: Callable[[], Awaitable[Tuple[Dict[str, dict], Dict[str, dict]]]] = _ler_do_banco


def limpar_cache() -> None:
    _cache["dados"] = None
    _cache["em"] = 0.0


async def _dados() -> Tuple[Dict[str, dict], Dict[str, dict], str]:
    agora = time.monotonic()
    if _cache["dados"] is not None and (agora - float(_cache["em"])) < CACHE_TTL_SECONDS:
        return _cache["dados"]
    try:
        catalogo, papeis = await leitor_do_banco()
        dados = (catalogo, papeis, "rota")
    except ModeloDoPortalIndisponivel:
        raise
    except Exception as e:  # noqa: BLE001 — banco fora: snapshot, com aviso
        logger.warning("[PORTAL/MODELO] banco indisponível (%s) — usando o snapshot",
                       type(e).__name__)
        catalogo, papeis = _ler_snapshot()
        dados = (catalogo, papeis, "snapshot")
    _cache["dados"] = dados
    _cache["em"] = agora
    return dados


# ---------------------------------------------------------------------------
# As regras de recusa — as do resolvedor (model_policy._validar)
# ---------------------------------------------------------------------------
def _classe(rota: dict) -> str:
    c = rota.get("classe_de_dado")
    if c is None:
        return "pii"  # sem declaração = o mais restritivo
    if c not in CLASSES_DE_DADO:
        raise ModeloDoPortalIndisponivel(f"classe de dado desconhecida: {c!r}")
    return c


def _validar(provider: Optional[str], model: Optional[str], effort: Optional[str],
             classe: str, cat: Dict[str, dict]) -> dict:
    if not model:
        raise ModeloDoPortalIndisponivel(f"papel {PAPEL!r}: nenhum modelo declarado")
    linha = cat.get(model)
    if linha is None:
        raise ModeloDoPortalIndisponivel(f"papel {PAPEL!r}: modelo {model!r} fora do catálogo")
    if provider is not None and provider != linha.get("provider"):
        raise ModeloDoPortalIndisponivel(
            f"papel {PAPEL!r}: provedor {provider!r} diverge do catálogo "
            f"({linha.get('provider')!r}) para {model!r}")
    if linha.get("lifecycle") not in LIFECYCLES_USAVEIS:
        raise ModeloDoPortalIndisponivel(
            f"papel {PAPEL!r}: {model!r} tem lifecycle {linha.get('lifecycle')!r} (recusado)")
    if classe not in (linha.get("classes_de_dado") or []):
        raise ModeloDoPortalIndisponivel(f"papel {PAPEL!r}: {model!r} não pode ver dado {classe!r}")
    if effort is not None:
        niveis = (linha.get("capacidades") or {}).get("niveis_de_esforco")
        if effort not in NIVEIS_DE_ESFORCO or (niveis is not None and effort not in niveis):
            raise ModeloDoPortalIndisponivel(f"papel {PAPEL!r}: {model!r} não aceita esforço {effort!r}")
    return linha


def _montar(linha: dict, effort: Optional[str], classe: str, origem: str,
            versao: Optional[int], reserva: Optional[ModeloDoPortal]) -> ModeloDoPortal:
    return ModeloDoPortal(
        papel=PAPEL, provider=linha["provider"], model=linha["model_name"], effort=effort,
        api_surface=linha.get("api_surface") or "", capacidades=dict(linha.get("capacidades") or {}),
        classe_de_dado=classe, lifecycle=linha["lifecycle"], origem=origem, versao_da_rota=versao,
        base_url=linha.get("base_url"), api_key_env=linha.get("api_key_env"),
        precos=dict(linha), reserva=reserva)


async def resolver_rota() -> ModeloDoPortal:
    """O modelo do portal, segundo a rota `portal_decisao`. ⛔ Nunca um modelo por omissão."""
    cat, papeis, origem = await _dados()
    rota = papeis.get(PAPEL)
    if not rota:
        raise ModeloDoPortalIndisponivel(f"rota {PAPEL!r} ausente")
    classe = _classe(rota)
    versao = int(rota["versao"]) if rota.get("versao") is not None else None
    reserva = None
    if rota.get("modelo_reserva"):
        lr = _validar(rota.get("provider_reserva"), rota["modelo_reserva"],
                      rota.get("esforco_reserva"), classe, cat)
        reserva = _montar(lr, rota.get("esforco_reserva"), classe, origem, versao, None)
    linha = _validar(rota.get("provider"), rota.get("modelo_primario"), rota.get("esforco"),
                     classe, cat)
    return _montar(linha, rota.get("esforco"), classe, origem, versao, reserva)


# ---------------------------------------------------------------------------
# O PEDIDO — capacidades do catálogo → corpo do provedor
# ---------------------------------------------------------------------------
def montar_pedido(modelo: ModeloDoPortal, system: str, user: str) -> Dict[str, Any]:
    """O pedido ao provedor, sem segredo: {provider, api_surface, model, url, corpo}.

    ⛔ Sampling (temperature) só onde o catálogo diz que o modelo aceita
    (`sampling_ok`); Claude 5 dá 400 com ele.
    """
    caps = modelo.capacidades or {}
    amostra_ok = caps.get("sampling_ok") is not False
    base = (modelo.base_url or _URL_PADRAO.get(modelo.provider) or "").rstrip("/")
    mensagens = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    prov, sup, eff = modelo.provider, modelo.api_surface, modelo.effort
    if prov == "openai" and sup == "chat_completions":
        corpo: Dict[str, Any] = {"model": modelo.model, "messages": mensagens,
                                 "response_format": {"type": "json_object"}}
        if amostra_ok:
            corpo["temperature"] = 0
        if eff and caps.get("reasoning_param") in ("reasoning_effort", "reasoning.effort"):
            corpo["reasoning_effort"] = eff
        url = f"{base}/chat/completions"
    elif prov == "openai" and sup == "responses":
        corpo = {"model": modelo.model, "input": mensagens, "store": False,
                 "text": {"format": {"type": "json_object"}}}
        if amostra_ok:
            corpo["temperature"] = 0
        if eff:
            corpo["reasoning"] = {"effort": eff}
        url = f"{base}/responses"
    elif prov == "anthropic" and sup == "messages":
        corpo = {"model": modelo.model, "max_tokens": MAX_TOKENS_ANTHROPIC, "system": system,
                 "messages": [{"role": "user", "content": user}]}
        if amostra_ok:
            corpo["temperature"] = 0
        if eff and caps.get("reasoning_param") == "output_config.effort":
            corpo["output_config"] = {"effort": eff}
        url = f"{base}/messages"
    else:
        raise ModeloDoPortalIndisponivel(
            f"o portal não tem transporte para {prov!r}/{sup!r} ({modelo.model!r}) — "
            f"trocar a rota para um provedor sem transporte é ERRO, não queda para outro modelo")
    return {"papel": PAPEL, "provider": prov, "api_surface": sup, "model": modelo.model,
            "url": url, "corpo": corpo}


def _cabecalhos_do_provedor(modelo: ModeloDoPortal) -> Dict[str, str]:
    env = modelo.api_key_env or _CHAVE_PADRAO.get(modelo.provider) or ""
    chave = os.getenv(env) if env else ""
    if not chave:
        raise ModeloDoPortalIndisponivel(f"sem chave do provedor {modelo.provider!r} no worker ({env})")
    if modelo.provider == "anthropic":
        return {"x-api-key": chave, "anthropic-version": "2023-06-01",
                "content-type": "application/json"}
    return {"Authorization": f"Bearer {chave}"}


async def _postar_no_provedor(pedido: Dict[str, Any], cabecalhos: Dict[str, str]) -> Dict[str, Any]:
    import httpx  # ⚠️ na hora: é o ponto que a bancada desvia (dubles.httpx_do_portal)

    async with httpx.AsyncClient(timeout=TIMEOUT_DO_PROVEDOR) as c:
        r = await c.post(pedido["url"], headers=cabecalhos, json=pedido["corpo"])
        if r.status_code >= 400:
            raise ModeloDoPortalIndisponivel(f"o provedor respondeu HTTP {r.status_code}")
        return r.json()


# ---------------------------------------------------------------------------
# A RESPOSTA — texto e uso, em qualquer das três formas
# ---------------------------------------------------------------------------
def texto_da_resposta(dados: Any) -> str:
    if not isinstance(dados, dict):
        raise ModeloDoPortalIndisponivel("resposta do provedor ilegível")
    if dados.get("choices"):                                   # chat_completions
        return str(((dados["choices"][0] or {}).get("message") or {}).get("content") or "")
    if isinstance(dados.get("content"), list):                 # anthropic messages
        return "".join(str(b.get("text") or "") for b in dados["content"]
                       if isinstance(b, dict) and b.get("type") == "text")
    if dados.get("output_text"):                               # responses (atalho)
        return str(dados["output_text"])
    partes = []
    for item in dados.get("output") or []:                     # responses
        if isinstance(item, dict) and item.get("type") == "message":
            for b in item.get("content") or []:
                if isinstance(b, dict) and b.get("type") in ("output_text", "text"):
                    partes.append(str(b.get("text") or ""))
    return "".join(partes)


def uso_da_resposta(dados: Any) -> Dict[str, int]:
    u = (dados or {}).get("usage") or {} if isinstance(dados, dict) else {}

    def _i(v: Any) -> int:
        try:
            return int(v or 0)
        except (TypeError, ValueError):
            return 0

    if "prompt_tokens" in u:                                   # chat_completions
        return {"input": _i(u.get("prompt_tokens")), "output": _i(u.get("completion_tokens")),
                "cached": _i((u.get("prompt_tokens_details") or {}).get("cached_tokens")),
                "cache_read": 0, "cache_write": 0,
                "reasoning": _i((u.get("completion_tokens_details") or {}).get("reasoning_tokens"))}
    if "cache_read_input_tokens" in u or "cache_creation_input_tokens" in u:  # anthropic
        lidos, escritos = _i(u.get("cache_read_input_tokens")), _i(u.get("cache_creation_input_tokens"))
        return {"input": _i(u.get("input_tokens")) + lidos + escritos,
                "output": _i(u.get("output_tokens")), "cached": 0,
                "cache_read": lidos, "cache_write": escritos, "reasoning": 0}
    return {"input": _i(u.get("input_tokens")), "output": _i(u.get("output_tokens")),  # responses
            "cached": _i((u.get("input_tokens_details") or {}).get("cached_tokens")),
            "cache_read": 0, "cache_write": 0,
            "reasoning": _i((u.get("output_tokens_details") or {}).get("reasoning_tokens"))}


def custo_usd(precos: dict, uso: Dict[str, int]) -> Optional[float]:
    """A MESMA conta de `usage_service.calculate_cost` (o guarda compara). None = sem preço."""
    pin, pout = precos.get("input_price_per_million"), precos.get("output_price_per_million")
    if pin is None or pout is None or precos.get("is_active") is False:
        return None
    pin, pout = float(pin), float(pout)
    if not pin and not pout:
        return None  # 0/0 no catálogo = desconhecido, não "de graça"
    limiar = precos.get("limiar_contexto_longo")
    if limiar and uso["input"] > int(limiar):
        pin = float(precos.get("input_price_long") or pin)
        pout = float(precos.get("output_price_long") or pout)

    def _m(chave: str, padrao: float) -> float:
        v = precos.get(chave)
        return padrao if v is None else float(v)

    regular = max(0, uso["input"] - uso["cached"] - uso["cache_read"] - uso["cache_write"])
    return ((regular / 1e6) * pin
            + (uso["cached"] / 1e6) * pin * _m("cached_input_multiplier", 0.50)
            + (uso["cache_write"] / 1e6) * pin * _m("cache_write_multiplier", 1.25)
            + (uso["cache_read"] / 1e6) * pin * _m("cache_read_multiplier", 0.10)
            + (uso["output"] / 1e6) * pout)


# ---------------------------------------------------------------------------
# O LEDGER — token_usage_logs pelo REST
# ---------------------------------------------------------------------------
def _uuid_ou_none(v: Any) -> Optional[str]:
    try:
        return str(uuid.UUID(str(v))) if v else None
    except (ValueError, TypeError, AttributeError):
        return None


def linha_do_ledger(modelo: ModeloDoPortal, dados: Any, *, company_id: Any, job_id: Any,
                    reserva_usada: bool, motivo_reserva: Optional[str]) -> Dict[str, Any]:
    uso = uso_da_resposta(dados)
    custo = custo_usd(modelo.precos, uso)
    detalhes: Dict[str, Any] = {
        "papel": modelo.papel, "modelo_pedido": None,
        "modelo_resolvido": modelo.model, "provedor_resolvido": modelo.provider,
        "modelo_real": (dados or {}).get("model") if isinstance(dados, dict) else None,
        "esforco": modelo.effort, "origem_da_rota": modelo.origem,
        "versao_da_rota": modelo.versao_da_rota, "reserva_usada": bool(reserva_usada),
        "reasoning_tokens": uso["reasoning"], "job_id": str(job_id) if job_id else None,
    }
    if motivo_reserva:
        detalhes["motivo_reserva"] = motivo_reserva
    if custo is None:
        detalhes["preco_desconhecido"] = True
    linha: Dict[str, Any] = {
        "service_type": SERVICE_TYPE, "model_name": modelo.model,
        "input_tokens": uso["input"], "output_tokens": uso["output"],
        "total_cost_usd": float(custo or 0.0), "details": detalhes,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cache_creation_tokens": uso["cache_write"], "cache_read_tokens": uso["cache_read"],
        "cached_tokens": uso["cached"],
    }
    cid = _uuid_ou_none(company_id)
    if cid:
        linha["company_id"] = cid
    elif company_id:
        detalhes["company_id_invalido"] = str(company_id)[:64]
    return linha


async def _gravar_no_banco(linha: Dict[str, Any]) -> bool:
    url, chave = _supabase()
    if not url or not chave:
        logger.error("[PORTAL/MODELO] uso NÃO gravado: SUPABASE_URL/SUPABASE_SERVICE_KEY ausentes")
        return False
    async with _cliente_supabase() as c:
        r = await c.post(f"{url}/rest/v1/token_usage_logs",
                         headers={**_cabecalhos_supabase(chave), "Content-Type": "application/json",
                                  "Prefer": "return=minimal"},
                         json=linha)
        if r.status_code >= 400:
            logger.error("[PORTAL/MODELO] uso NÃO gravado: HTTP %s", r.status_code)
            return False
    return True


#: Borda dublável do ledger (produção: `_gravar_no_banco`).
gravador_de_uso: Callable[[Dict[str, Any]], Awaitable[bool]] = _gravar_no_banco


async def _gravar(linha: Dict[str, Any]) -> None:
    try:
        await gravador_de_uso(linha)
    except Exception as e:  # noqa: BLE001 — perder a medição não derruba o acionamento
        logger.error("[PORTAL/MODELO] uso NÃO gravado: %s", type(e).__name__)


# ---------------------------------------------------------------------------
# A DECISÃO
# ---------------------------------------------------------------------------
ChamarModelo = Callable[[Dict[str, Any]], Any]


async def _uma_chamada(modelo: ModeloDoPortal, system: str, user: str,
                       chamar_modelo: Optional[ChamarModelo]) -> Dict[str, Any]:
    pedido = montar_pedido(modelo, system, user)
    if chamar_modelo is not None:
        try:
            dados = chamar_modelo(pedido)
            if inspect.isawaitable(dados):
                dados = await dados
        except ModeloDoPortalIndisponivel:
            raise
        except Exception as e:  # noqa: BLE001
            raise ModeloDoPortalIndisponivel(f"o provedor falhou ({type(e).__name__})") from e
        if isinstance(dados, dict) and dados.get("error"):
            raise ModeloDoPortalIndisponivel("o provedor devolveu erro")
        return dados
    cabecalhos = _cabecalhos_do_provedor(modelo)
    try:
        return await _postar_no_provedor(pedido, cabecalhos)
    except ModeloDoPortalIndisponivel:
        raise
    except (asyncio.TimeoutError, Exception) as e:  # noqa: BLE001 — rede, timeout, JSON
        raise ModeloDoPortalIndisponivel(f"o provedor falhou ({type(e).__name__})") from e


async def decidir(system: str, user: str, *, company_id: Any = None, job_id: Any = None,
                  chamar_modelo: Optional[ChamarModelo] = None,
                  rota: Optional[ModeloDoPortal] = None) -> Dict[str, Any]:
    """Uma decisão do cérebro do portal. Devolve {texto, modelo, reserva_usada}.

    Levanta `ModeloDoPortalIndisponivel` com o MOTIVO — nunca troca de modelo
    calado. `chamar_modelo` (injeção da BANCADA) recebe o pedido montado e
    devolve a resposta crua do provedor; com ele o ledger do produto NÃO é
    escrito (a bancada mede o próprio custo em `eval_case_results`, e o
    processo dela não pode gravar linha no ledger de produção).

    `rota` (SPEC-116 F6, só a BANCADA passa): o `ModeloDoPortal` do braço medido
    — o corpo do pedido sai no formato do provedor DELE (`montar_pedido`). Sem
    ele, o modelo é o da rota `portal_decisao`, como sempre.
    """
    modelo = rota if rota is not None else await resolver_rota()
    try:
        dados = await _uma_chamada(modelo, system, user, chamar_modelo)
        usado, reserva_usada, motivo = modelo, False, None
    except ModeloDoPortalIndisponivel as falha:
        if modelo.reserva is None:
            logger.error("[PORTAL/MODELO] %s/%s falhou e a rota não declara reserva: %s",
                         modelo.provider, modelo.model, falha)
            raise
        motivo = str(falha)[:200]
        logger.warning("[PORTAL/MODELO] %s/%s falhou (%s) — RESERVA declarada na rota: %s/%s",
                       modelo.provider, modelo.model, motivo, modelo.reserva.provider,
                       modelo.reserva.model)
        dados = await _uma_chamada(modelo.reserva, system, user, chamar_modelo)
        usado, reserva_usada = modelo.reserva, True
    if chamar_modelo is None:
        await _gravar(linha_do_ledger(usado, dados, company_id=company_id, job_id=job_id,
                                      reserva_usada=reserva_usada, motivo_reserva=motivo))
    return {"texto": texto_da_resposta(dados), "modelo": usado, "reserva_usada": reserva_usada}
