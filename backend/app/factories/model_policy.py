"""SPEC-116 U3 — o Model Router (SPEC-052 §14): UM resolvedor por PAPEL.

Todo trabalho que chama um modelo pede um PAPEL ("atendimento", "memoria",
"portal_decisao"...). Este módulo responde QUAL modelo faz esse papel, lendo UM
catálogo governado (`llm_pricing` expandido) e UMA tabela de rotas
(`llm_papeis`). Nenhum model id mora no código de negócio.

Precedência de `resolver()`:
  1. `override`  — só a BANCADA passa ({provider, model, effort});
  2. ROTA do papel (`llm_papeis`);
  3. `agente.llm_model` (ou `corretora.llm_model`) — SOMENTE para papel SEM
     rota, e só se o modelo está no catálogo com lifecycle usável;
  4. os dados vêm do banco (cache de 60 s) e, quando o banco não responde, do
     SNAPSHOT versionado `modelos_snapshot.json`;
  5. nada disso → `ModeloNaoResolvido`. ⛔ Nunca "cai no mini".

Sempre recusa: modelo fora do catálogo · lifecycle BLOCKED/HISTORICAL ·
provedor desconhecido ou divergente do catálogo · classe de dado da rota que o
modelo não pode ver (D-116-10) · esforço fora dos níveis do modelo. A reserva é
resolvida pelas MESMAS regras.

🔴 PRODUÇÃO × BANCADA (Founder 24/09/2026 — conclusão da Onda A):
  · PRODUÇÃO (rota, reserva, modelo do agente, snapshot) aceita SÓ `APPROVED`
    (`LIFECYCLES_DE_PRODUCAO`) e recusa esforço abaixo de
    `capacidades.esforco_minimo_producao` quando o modelo o declara (esforço
    NULO também é recusado: o mínimo obriga a declarar). É a MESMA regra do
    trigger `llm_papeis_so_modelo_governado` (migration 20260924_01).
  · BANCADA (`override=`) continua aceitando APPROVED · CANDIDATE · DEPRECATED
    (`LIFECYCLES_DA_BANCADA`) — medir desafiante e baseline histórico é o ofício
    dela — e não impõe o mínimo de produção (medir a Luna em `low` é legítimo).

`resolve_chat_model` e `is_core_chat_role` ficam como SHIM da fábrica de hoje
(a F2 troca a fábrica para `resolver`). O shim NÃO promove mais para gpt-4o.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

SNAPSHOT_PATH = Path(__file__).resolve().parent / "modelos_snapshot.json"
CACHE_TTL_SECONDS = 60

#: o que a BANCADA pode medir (override explícito) — e o que a tela de config lista.
LIFECYCLES_USAVEIS = ("APPROVED", "CANDIDATE", "DEPRECATED")
LIFECYCLES_DA_BANCADA = LIFECYCLES_USAVEIS
#: o que uma rota/agente/snapshot de PRODUÇÃO pode usar (Founder 24/09/2026).
LIFECYCLES_DE_PRODUCAO = ("APPROVED",)
LIFECYCLES_PROIBIDOS = ("BLOCKED", "HISTORICAL")
NIVEIS_DE_ESFORCO = ("none", "low", "medium", "high", "xhigh", "max")
#: ordem de sensibilidade — a classe efetiva de uma chamada é a MAIS sensível
#: entre a da rota e a que o chamador declarou.
CLASSES_DE_DADO = ("publico", "interno", "pii")
PROVEDORES_CONHECIDOS = frozenset({
    "openai", "anthropic", "google", "openrouter", "xai", "xiaomi", "deepseek",
    "zai", "cohere", "groq", "mistral",
})

_COLUNAS_CATALOGO = (
    "model_name,provider,tipo,api_surface,lifecycle,classes_de_dado,capacidades,"
    "base_url,api_key_env,substituido_por,retirada_em"
)
_COLUNAS_PAPEIS = (
    "papel,provider,modelo_primario,esforco,provider_reserva,modelo_reserva,"
    "esforco_reserva,classe_de_dado,risco,versao,motivo"
)


class ModeloNaoResolvido(Exception):
    """Papel/modelo/provedor desconhecido, lifecycle proibido ou classe de dado recusada."""


@dataclass(frozen=True)
class ModeloResolvido:
    papel: str
    provider: str
    model: str
    effort: Optional[str]
    api_surface: str
    capacidades: dict
    classe_de_dado: str
    lifecycle: str
    reserva: Optional["ModeloResolvido"]
    origem: str
    versao_da_rota: Optional[int]
    motivo: str
    base_url: Optional[str] = None
    api_key_env: Optional[str] = None


# ---------------------------------------------------------------------------
# Fonte dos dados: banco (cache) → snapshot
# ---------------------------------------------------------------------------
_lock = threading.Lock()
_cache: Dict[str, object] = {"dados": None, "em": 0.0}


def _ler_banco() -> Tuple[Dict[str, dict], Dict[str, dict]]:
    """Lê catálogo + rotas pelo MESMO cliente do UsageService (usage_service.py).

    Levanta em qualquer falha — quem chama cai no snapshot.
    """
    from app.core.database import get_supabase_client  # import tardio: módulo puro nos testes

    cli = get_supabase_client().client
    cat = cli.table("llm_pricing").select(_COLUNAS_CATALOGO).execute().data or []
    pap = cli.table("llm_papeis").select(_COLUNAS_PAPEIS).execute().data or []
    if not cat or not pap:
        raise RuntimeError("catálogo/rotas vazios no banco (migration 20260923_01 aplicada?)")
    return {r["model_name"]: r for r in cat}, {r["papel"]: r for r in pap}


def _ler_snapshot() -> Tuple[Dict[str, dict], Dict[str, dict]]:
    doc = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    return doc.get("catalogo") or {}, doc.get("papeis") or {}


#: Ponto de troca da BORDA (banco). Testes substituem por um dublê; produção usa
#: `_ler_banco`. Nada além disto é dublável.
leitor_do_banco: Callable[[], Tuple[Dict[str, dict], Dict[str, dict]]] = _ler_banco


def _dados() -> Tuple[Dict[str, dict], Dict[str, dict], str]:
    agora = time.monotonic()
    with _lock:
        dados = _cache["dados"]
        if dados is not None and (agora - float(_cache["em"])) < CACHE_TTL_SECONDS:
            return dados  # type: ignore[return-value]
    try:
        catalogo, papeis = leitor_do_banco()
        dados = (catalogo, papeis, "rota")
    except Exception as e:  # noqa: BLE001 — banco fora: snapshot, com aviso
        logger.warning("[ModelRouter] banco indisponível (%s) — usando snapshot", type(e).__name__)
        catalogo, papeis = _ler_snapshot()
        dados = (catalogo, papeis, "snapshot")
    with _lock:
        _cache["dados"] = dados
        _cache["em"] = agora
    return dados


def limpar_cache() -> None:
    with _lock:
        _cache["dados"] = None
        _cache["em"] = 0.0


def catalogo() -> Dict[str, dict]:
    return dict(_dados()[0])


def papeis_conhecidos() -> list:
    return sorted(_dados()[1].keys())


# ---------------------------------------------------------------------------
# Papel do agente
# ---------------------------------------------------------------------------
def papel_do_agente(agent_role: Optional[str]) -> str:
    r = str(agent_role or "").strip().lower()
    if r in ("", "core"):
        return "chat_principal"
    if r in ("attendance", "insured_external"):
        return "atendimento"
    return "subagente"


def is_core_chat_role(agent_role) -> bool:
    """Core = role 'core' ou legado/sem papel (chat principal interno)."""
    return papel_do_agente(agent_role) == "chat_principal"


# ---------------------------------------------------------------------------
# Validação
# ---------------------------------------------------------------------------
def _classe_mais_sensivel(*classes: Optional[str]) -> str:
    validas = [c for c in classes if c]
    for c in validas:
        if c not in CLASSES_DE_DADO:
            raise ModeloNaoResolvido(f"classe de dado desconhecida: {c!r}")
    if not validas:
        return "pii"  # sem declaração = o mais restritivo
    return max(validas, key=CLASSES_DE_DADO.index)


def esforco_abaixo_do_minimo(effort: Optional[str], linha: dict) -> Optional[str]:
    """O mínimo de produção que `effort` não atinge (ou None se atinge / não há mínimo).

    Esforço NULO com mínimo declarado NÃO atinge: o default do provedor pode
    mudar sem aviso, e a rota de produção tem de dizer o que roda.
    """
    minimo = (linha.get("capacidades") or {}).get("esforco_minimo_producao")
    if not minimo:
        return None
    if minimo not in NIVEIS_DE_ESFORCO:
        return minimo  # mínimo mal declarado no catálogo: recusa (não adivinha)
    if effort not in NIVEIS_DE_ESFORCO:
        return minimo
    return minimo if NIVEIS_DE_ESFORCO.index(effort) < NIVEIS_DE_ESFORCO.index(minimo) else None


def _validar(papel: str, provider: Optional[str], model: Optional[str], effort: Optional[str],
             classe: str, cat: Dict[str, dict], *, producao: bool = True) -> dict:
    if not model:
        raise ModeloNaoResolvido(f"papel {papel!r}: nenhum modelo declarado")
    linha = cat.get(model)
    if linha is None:
        raise ModeloNaoResolvido(f"papel {papel!r}: modelo {model!r} fora do catálogo")
    prov_cat = linha.get("provider")
    if prov_cat not in PROVEDORES_CONHECIDOS:
        raise ModeloNaoResolvido(f"papel {papel!r}: provedor desconhecido {prov_cat!r} para {model!r}")
    if provider is not None and provider != prov_cat:
        if provider not in PROVEDORES_CONHECIDOS:
            raise ModeloNaoResolvido(f"papel {papel!r}: provedor desconhecido {provider!r}")
        raise ModeloNaoResolvido(
            f"papel {papel!r}: provedor {provider!r} diverge do catálogo ({prov_cat!r}) para {model!r}")
    ciclo = linha.get("lifecycle")
    aceitos = LIFECYCLES_DE_PRODUCAO if producao else LIFECYCLES_DA_BANCADA
    if ciclo not in aceitos:
        onde = "produção só aceita APPROVED" if producao else "recusado"
        raise ModeloNaoResolvido(f"papel {papel!r}: {model!r} tem lifecycle {ciclo!r} ({onde})")
    permitidas = linha.get("classes_de_dado") or []
    if classe not in permitidas:
        raise ModeloNaoResolvido(
            f"papel {papel!r}: {model!r} não pode ver dado {classe!r} (permite {sorted(permitidas)})")
    if effort is not None:
        if effort not in NIVEIS_DE_ESFORCO:
            raise ModeloNaoResolvido(f"papel {papel!r}: esforço {effort!r} fora da escala canônica")
        niveis = (linha.get("capacidades") or {}).get("niveis_de_esforco")
        if niveis is not None and effort not in niveis:
            raise ModeloNaoResolvido(f"papel {papel!r}: {model!r} não aceita esforço {effort!r}")
    if producao:
        minimo = esforco_abaixo_do_minimo(effort, linha)
        if minimo is not None:
            raise ModeloNaoResolvido(
                f"papel {papel!r}: {model!r} exige esforço >= {minimo!r} em produção (recebeu {effort!r})")
    return linha


def _montar(papel: str, linha: dict, effort: Optional[str], classe: str, origem: str,
            versao: Optional[int], motivo: str, reserva: Optional[ModeloResolvido]) -> ModeloResolvido:
    return ModeloResolvido(
        papel=papel, provider=linha["provider"], model=linha["model_name"], effort=effort,
        api_surface=linha.get("api_surface") or "", capacidades=dict(linha.get("capacidades") or {}),
        classe_de_dado=classe, lifecycle=linha["lifecycle"], reserva=reserva, origem=origem,
        versao_da_rota=versao, motivo=motivo, base_url=linha.get("base_url"),
        api_key_env=linha.get("api_key_env"),
    )


# ---------------------------------------------------------------------------
# O resolvedor
# ---------------------------------------------------------------------------
def resolver(papel: str, *, agente: Optional[dict] = None, corretora: Optional[dict] = None,
             classe_de_dado: Optional[str] = None, override: Optional[dict] = None) -> ModeloResolvido:
    cat, rotas, fonte = _dados()
    rota = rotas.get(papel)

    classe = _classe_mais_sensivel(rota.get("classe_de_dado") if rota else None, classe_de_dado)
    versao = int(rota["versao"]) if rota and rota.get("versao") is not None else None

    reserva: Optional[ModeloResolvido] = None
    if rota and rota.get("modelo_reserva"):
        lr = _validar(papel, rota.get("provider_reserva"), rota["modelo_reserva"],
                      rota.get("esforco_reserva"), classe, cat)
        reserva = _montar(papel, lr, rota.get("esforco_reserva"), classe, fonte, versao,
                          "reserva declarada na rota", None)

    # 1. bancada
    if override:
        linha = _validar(papel, override.get("provider"), override.get("model"),
                         override.get("effort"), classe, cat, producao=False)
        return _montar(papel, linha, override.get("effort"), classe, "bancada", versao,
                       "override da bancada", reserva)

    # 2. rota do papel
    if rota:
        linha = _validar(papel, rota.get("provider"), rota.get("modelo_primario"),
                         rota.get("esforco"), classe, cat)
        return _montar(papel, linha, rota.get("esforco"), classe, fonte, versao,
                       rota.get("motivo") or "rota do papel", reserva)

    # 3. papel sem rota: o modelo do agente (ou da corretora), se governado
    for dono in (agente, corretora):
        if dono and dono.get("llm_model"):
            effort = dono.get("reasoning_effort")
            linha = _validar(papel, dono.get("llm_provider"), dono["llm_model"], None, classe, cat,
                             producao=False)  # lifecycle/mínimo conferidos abaixo, já com o esforço
            niveis = (linha.get("capacidades") or {}).get("niveis_de_esforco")
            if effort not in NIVEIS_DE_ESFORCO or (niveis is not None and effort not in niveis):
                effort = None  # esforço gravado que o modelo não aceita: default do provedor
            # produção: o modelo do agente também só roda se APPROVED e no mínimo
            _validar(papel, dono.get("llm_provider"), dono["llm_model"], effort, classe, cat)
            return _montar(papel, linha, effort, classe, "agente", None,
                           "papel sem rota: modelo do agente", None)

    # 4. nada — erro explícito. ⛔ nunca um modelo por omissão.
    raise ModeloNaoResolvido(f"papel {papel!r} sem rota e sem modelo governado do agente")


# ---------------------------------------------------------------------------
# SHIM da fábrica de hoje (F2 troca por `resolver`)
# ---------------------------------------------------------------------------
def resolve_chat_model(agent_role, configured_model):
    """Modelo efetivo para a fábrica atual.

    Papel com rota → o modelo da ROTA, desde que a rota seja do MESMO provedor
    do modelo configurado (a fábrica de hoje escolhe o cliente pelo provedor do
    agente: devolver um Claude para um `ChatOpenAI` quebraria a chamada).
    Papel sem rota, rota inválida ou provedor divergente → o configurado, como
    hoje. ⛔ Não promove mais nada para gpt-4o.
    """
    papel = papel_do_agente(agent_role)
    try:
        r = resolver(papel)
    except ModeloNaoResolvido as e:
        logger.error("[ModelRouter] shim: %s — mantendo o modelo configurado", e)
        return configured_model
    if r.origem not in ("rota", "snapshot"):
        return configured_model
    if configured_model:
        prov_config = (catalogo().get(configured_model) or {}).get("provider")
        if prov_config != r.provider:
            logger.warning(
                "[ModelRouter] shim: rota de %r é %s/%s mas o agente usa %r (provedor %r) — "
                "mantido o do agente até a F2 ligar a fábrica ao resolvedor",
                papel, r.provider, r.model, configured_model, prov_config)
            return configured_model
    return r.model
