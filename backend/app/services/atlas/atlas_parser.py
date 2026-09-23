"""SPEC-038 ATLAS — Resolvedor de IA (Bloco C+ / qualidade das rotas).

O pipeline do Tecelão é DETERMINÍSTICO (regex + eco) — cobre os cliques
estruturados e os menus digitados cujo eco a tela seguinte confirma. Sobra um
RESÍDUO ambíguo: menus DIGITADOS (Allianz "*1-*") em que a tela seguinte não
ecoa a escolha. Aí entra um modelo FORTE (founder 18/07: "não pode ter
interpretação ruim") — mas só sobre esse resíduo, em LOTE, para custo mínimo.

Modelo configurável (default forte): env ATLAS_PARSER_MODEL / ATLAS_PARSER_PROVIDER
(default claude-sonnet-5 / anthropic). Desligável: ATLAS_PARSER_ENABLED=0.

Custo: o modelo NÃO lê cada mensagem — só as arestas ambíguas do mapa FINAL
(dezenas, não centenas), uma chamada por seguradora. Independe do número de
conversas históricas (a ingestão é gratuita e determinística).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_PROMPT = """Você mapeia o menu de atendimento (URA) de uma seguradora no WhatsApp.
Em cada item abaixo há a TELA DE MENU que a URA enviou (com as opções numeradas)
e a TELA SEGUINTE que apareceu depois que o atendente escolheu uma opção.
Diga qual OPÇÃO do menu foi escolhida para chegar na tela seguinte.

Regras:
- Responda SOMENTE com o texto EXATO de uma das opções listadas, ou "NENHUMA"
  se não der para saber com segurança.
- Não invente. Na dúvida, "NENHUMA".
- Considere o significado: "enviaremos o CHAVEIRO" após um menu de serviços
  indica que a opção escolhida foi a de chaveiro.

Itens (JSON):
{items}

Responda APENAS um JSON: {{"answers": ["opção exata ou NENHUMA", ...]}} na MESMA
ordem dos itens."""


def parser_enabled() -> bool:
    return os.getenv("ATLAS_PARSER_ENABLED", "1").strip() != "0"


#: SPEC-116 U8 — o PAPEL deste trabalho no Model Router (`llm_papeis`).
#: `ATLAS_PARSER_PROVIDER/_MODEL` ficam IGNORADOS: a rota escolhe o modelo.
PAPEL = "atlas_parser"


def _model_cfg() -> Dict[str, str]:
    """O modelo que a ROTA `atlas_parser` resolve hoje (para log e estimativa).

    ⛔ Sem rota/catálogo → `ModeloNaoResolvido` (nunca um modelo por omissão).
    """
    from app.factories.llm_factory import LLMFactory

    r = LLMFactory.resolver_para({}, {}, papel=PAPEL)
    return {"provider": r.provider, "model": r.model}


def _collect_ambiguous(map_acc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Arestas sequenciais (label '→', inferred) saindo de um MENU: o humano
    escolheu algo digitando e o eco não resolveu. Uma por (origem→destino)."""
    nodes = map_acc.get("nodes") or {}
    edges = map_acc.get("edges") or {}
    items: List[Dict[str, Any]] = []
    for ekey, e in edges.items():
        if e.get("label") != "→" or e.get("echo"):
            continue
        src, dst = nodes.get(e.get("src")), nodes.get(e.get("to"))
        if not src or not dst or src.get("kind") != "menu" or not src.get("options"):
            continue
        opts = [o["label"] for o in src["options"]]
        items.append({"ekey": ekey, "src": e["src"], "to": e["to"],
                      "menu": src["text"][:280], "options": opts, "next": dst["text"][:200]})
    return items


async def resolve_typed_choices(map_acc: Dict[str, Any], insurer_key: str = "") -> int:
    """Preenche as escolhas digitadas ambíguas com o modelo forte. Muta o mapa
    (arestas viram rotuladas, confidence 'ai'). Retorna quantas resolveu."""
    if not parser_enabled():
        return 0
    items = _collect_ambiguous(map_acc)
    if not items:
        return 0

    try:
        from langchain_core.messages import HumanMessage

        from app.factories.llm_factory import LLMFactory

        # 🔴 SPEC-116 U8/G8: o Atlas era INVISÍVEL no ledger — passava
        # `company_id="atlas"` e `token_usage_logs.company_id` é uuid: o insert
        # falhava e `usage_service` engolia o erro. O Atlas é trabalho de
        # PLATAFORMA (o mapa da URA é de todas as corretoras): company_id NULO +
        # service_type "plataforma", a mesma forma das 532 linhas de plataforma
        # que o ledger já tem (📊 23/09, `group by service_type, company_id is null`).
        resolvido = LLMFactory.resolver_para({}, {}, papel=PAPEL)
        cfg = {"provider": resolvido.provider, "model": resolvido.model}
        llm = LLMFactory.create_llm(
            company_config={}, agent_data={"llm_temperature": 0},
            company_id=None, agent_id=None, service_type="plataforma",
            modelo_resolvido=resolvido)
        payload = [{"menu": it["menu"], "options": it["options"], "next": it["next"]} for it in items]
        prompt = _PROMPT.format(items=json.dumps(payload, ensure_ascii=False))
        resp = await llm.ainvoke([HumanMessage(content=prompt)])
        raw = getattr(resp, "content", "") or ""
        answers = _parse_answers(raw, len(items))
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ATLAS PARSER] modelo indisponível ({type(e).__name__}) — resíduo fica lacuna")
        return 0

    edges = map_acc.get("edges") or {}
    resolved = 0
    for it, ans in zip(items, answers):
        if not ans or ans.strip().upper() == "NENHUMA":
            continue
        match = next((o for o in it["options"] if _norm(o) == _norm(ans) or _norm(ans) in _norm(o)), None)
        if not match:
            continue
        new_key = f"{it['src']}|{match}"
        if new_key not in edges:
            old = edges.get(it["ekey"], {})
            edges[new_key] = {**old, "label": match, "inferred": False, "ai": True, "to": it["to"]}
            edges.pop(it["ekey"], None)
            resolved += 1
    if resolved:
        from app.services.atlas.weaver import compute_coverage

        compute_coverage(map_acc)
        logger.info(f"[ATLAS PARSER] {insurer_key}: {resolved} escolhas digitadas resolvidas ({cfg['model']})")
    return resolved


def _parse_answers(raw: str, n: int) -> List[str]:
    try:
        s = raw[raw.find("{"): raw.rfind("}") + 1]
        data = json.loads(s)
        ans = data.get("answers") or []
        return [str(a) for a in ans][:n]
    except Exception:  # noqa: BLE001
        return []


def _norm(s: str) -> str:
    import re
    import unicodedata

    x = unicodedata.normalize("NFKD", str(s or ""))
    x = "".join(c for c in x if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]", "", x)


def estimate_cost(nodes: int, ambiguous_edges: int) -> Dict[str, Any]:
    """Estimativa de custo por seguradora (uma chamada do resolvedor).
    Independe do nº de conversas.

    SPEC-116 U8: o modelo é o da ROTA e o preço é o do CATÁLOGO (`llm_pricing`,
    lido por `usage_service`). A tabela de preços própria que morava aqui saiu —
    ela não tinha o Opus 5 que roda em produção e cobrava-o como Sonnet.
    Preço desconhecido → custo 0 + `preco_desconhecido=True` — a MESMA regra
    do ledger (`usage_service.track_cost_sync`): nunca o preço de outro modelo.
    """
    cfg = _model_cfg()
    # ~180 tokens input por aresta ambígua + overhead; ~12 tokens output por resposta
    in_tok = 300 + ambiguous_edges * 180
    out_tok = 40 + ambiguous_edges * 12
    usd: Optional[float] = None
    try:
        from app.services.usage_service import get_usage_service

        svc = get_usage_service()
        if svc.preco_conhecido(cfg["model"]):
            usd = svc.calculate_cost(cfg["model"], in_tok, out_tok)
    except Exception as e:  # noqa: BLE001 — sem catálogo de preço, sem número
        logger.warning(f"[ATLAS PARSER] preço do catálogo indisponível ({type(e).__name__})")
    out: Dict[str, Any] = {"model": cfg["model"], "input_tokens": in_tok, "output_tokens": out_tok}
    if usd is None:
        out.update(usd_per_insurer=0.0, brl_per_insurer=0.0, preco_desconhecido=True)
    else:
        out.update(usd_per_insurer=round(usd, 4), brl_per_insurer=round(usd * 6.0, 3))
    return out
