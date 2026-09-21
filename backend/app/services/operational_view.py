"""SPEC-040 Onda 2 — Visão Operacional do Chat Principal (Missão B).

Consultas DETERMINÍSTICAS e token-eficientes para o Core enxergar a operação:
- operations_summary: acionamentos ativos + desfechos do período + qualidade,
  SEMPRE escopado pela corretora (company_id vem do runtime, nunca da LLM).
- atlas_routes_summary: os mapas de rota do Atlas (estrutura GLOBAL das URAs
  das seguradoras — sem nenhum dado de cliente).

Regra de custo (SPEC-040 §5): o serviço monta o digest pronto e ENXUTO; a LLM
só formata/apresenta. Nunca devolver listas cruas nem paginação para o modelo.
Fail-soft: cada seção falha sozinha sem derrubar o resto.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_STATE_PT = {
    "ura": "navegando a URA da seguradora",
    "human_phase": "com o analista da seguradora",
    "captured": "protocolo garantido",
    "monitoring": "monitorando a chegada do prestador",
    "needs_human": "com a equipe humana (dossiê entregue)",
    "encaminhado": "resolvido por encaminhamento (formulário/orientação entregue)",
    "resolvido": "resolvido — serviço prestado e ciclo fechado",
    "test_aborted": "simulação concluída (modo teste)",
    "insurer_closed": "encerrado pela seguradora",
    "queued": "na fila (aguardando vez)",
}

_MAX_LIST = 8          # itens por seção (digest enxuto — a LLM nunca pagina)
_TEXT_CAP = 90         # corte de texto de tela do Atlas


def _insurer_label_by_phone(phone: str) -> str:
    try:
        from app.services.atlas.observer_intake import _digits, insurer_allowlist
        from app.services.insurer_registry import INSURER_REGISTRY

        key = insurer_allowlist().get(_digits(phone))
        if key:
            return str((INSURER_REGISTRY.get(key) or {}).get("label") or key.title())
    except Exception:  # noqa: BLE001
        pass
    return "Seguradora"


def _fmt_when(iso: Any) -> str:
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%d/%m %H:%M")
    except Exception:  # noqa: BLE001
        return ""


#: 🔴 SPEC-090 BLOCO D — `ontem` vira um período DE VERDADE.
#:
#: 📊 Medido em 26/08: `periodo="ontem"` caía no `else` e devolvia **"últimas
#: 24h"** — que às 10h de terça cobre metade de segunda e metade de terça.
#: ⛔ O Founder perguntava *"o que aconteceu ontem?"* e recebia outra resposta,
#: **apresentada como se fosse a que ele pediu**. É o relatório confiante e
#: falso que a SPEC-090 inteira existe para impedir.
_ONTEM = ("ontem", "yesterday", "d-1")
_SEMANA = ("semana", "7d", "7")


def _janela(periodo: str):
    """`(since, until, rotulo, dia)` — e `dia` só existe quando é UM dia.

    ⚠️ `until` importa: sem ele, *"ontem"* incluiria hoje de manhã.
    """
    p = str(periodo or "").strip().lower()
    agora = datetime.now(timezone.utc)
    if p in _SEMANA:
        return (agora - timedelta(days=7)).isoformat(), agora.isoformat(), \
            "últimos 7 dias", ""
    if p in _ONTEM:
        # ⚠️ Dia de CALENDÁRIO em UTC, e a escolha está declarada em P-090-06:
        #    o piloto é no Brasil (UTC−3), então "ontem" em Florianópolis
        #    termina às 03h00 UTC de hoje. Inventar um fuso aqui sem o Founder
        #    decidir seria trocar um erro conhecido por um escondido.
        d = (agora - timedelta(days=1)).strftime("%Y-%m-%d")
        return f"{d}T00:00:00+00:00", f"{d}T23:59:59.999999+00:00", \
            f"ontem ({d}, UTC)", d
    return (agora - timedelta(days=1)).isoformat(), agora.isoformat(), \
        "últimas 24h", ""


async def operations_summary(company_id: str, periodo: str = "hoje") -> str:
    """Digest da operação da corretora.

    `periodo`: `'hoje'` (24h) · `'ontem'` (o dia de calendário anterior, UTC) ·
    `'semana'` (7d).

    🔴 **SPEC-090 BLOCO D — é aqui que a pergunta de terça-feira encosta no
    produto**, e ela entrou nesta função em vez de numa ferramenta nova:
    `resumo_atendimentos` já está no Core, já se descreve como *"use SEMPRE que
    o corretor perguntar como estão os atendimentos"*, e 📊 o Tool Gateway tem
    teto de 12 ferramentas por execução (SPEC-053 §13.1) — o Core já carrega
    perto disso. ⛔ Uma segunda ferramenta com pergunta parecida degradaria a
    escolha do modelo em TODA conversa e seria o motor paralelo da §5.
    """
    since, until, rotulo, dia = _janela(periodo)
    lines: List[str] = [f"OPERAÇÃO DE ATENDIMENTO — período: {rotulo}"]

    # 1) Acionamentos ATIVOS agora (Redis — tempo real)
    try:
        from app.services.dispatch_router import list_active_dispatches

        active = await list_active_dispatches(company_id)
        if active:
            lines.append(f"\nACIONAMENTOS ATIVOS AGORA ({len(active)}):")
            for s in active[:_MAX_LIST]:
                label = _insurer_label_by_phone(str(s.get("insurer_phone") or ""))
                state = _STATE_PT.get(str(s.get("state") or ""), str(s.get("state") or "?"))
                cap = s.get("captured") or {}
                extra = ""
                if cap.get("protocol"):
                    extra = f" — protocolo {cap['protocol']}"
                elif cap.get("eta_minutes"):
                    extra = f" — previsão ~{cap['eta_minutes']} min"
                sub = f" ({s.get('subservice')})" if s.get("subservice") else ""
                lines.append(f"- {label}{sub}: {state}{extra}")
        else:
            lines.append("\nACIONAMENTOS ATIVOS AGORA: nenhum em andamento.")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[VISAO OPERACIONAL] ativos falhou: {type(e).__name__}")
        lines.append("\nACIONAMENTOS ATIVOS: indisponível no momento.")

    # 2) Movimento do período (Atividades — transições reais registradas)
    try:
        from app.core.database import get_supabase_client

        db = get_supabase_client()

        def _acts() -> list:
            return (db.client.table("agent_activities")
                    .select("category, title, created_at")
                    .eq("company_id", company_id)
                    .gte("created_at", since)
                    # 🔴 SPEC-090: `lte` — sem ele, "ontem" inclui HOJE.
                    #    📊 O `since` sozinho é uma janela ABERTA para a frente:
                    #    às 10h de terça, "ontem" traria as atividades da manhã
                    #    de terça junto, e o número sairia maior que o dia.
                    .lte("created_at", until)
                    .order("created_at", desc=True).limit(200).execute().data or [])

        acts = await asyncio.to_thread(_acts)
        disp = [a for a in acts if a.get("category") == "acionamentos"]
        if disp:
            started = sum(1 for a in disp if "iniciado" in str(a.get("title", "")).lower())
            protocol = sum(1 for a in disp if "protocolo" in str(a.get("title", "")).lower())
            handoff = sum(1 for a in disp if "dossiê" in str(a.get("title", "")).lower()
                          or "dossie" in str(a.get("title", "")).lower())
            lines.append(f"\nMOVIMENTO DO PERÍODO: {started} acionamentos iniciados, "
                         f"{protocol} com protocolo garantido, {handoff} entregues à equipe humana.")
            lines.append("ÚLTIMOS EVENTOS:")
            for a in disp[:_MAX_LIST]:
                lines.append(f"- {_fmt_when(a.get('created_at'))} {a.get('title')}")
        else:
            lines.append("\nMOVIMENTO DO PERÍODO: nenhum acionamento registrado.")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[VISAO OPERACIONAL] atividades falhou: {type(e).__name__}")

    # 3) Qualidade (scorecards do Auditor)
    try:
        from app.core.database import get_supabase_client

        db = get_supabase_client()

        def _scores() -> list:
            return (db.client.table("conversation_scorecards")
                    .select("score, created_at").eq("company_id", company_id)
                    # 🔴 `lte` pelo mesmo motivo do bloco acima.
                    .gte("created_at", since).lte("created_at", until)
                    .limit(200).execute().data or [])

        scores = await asyncio.to_thread(_scores)
        if scores:
            vals = [int(s.get("score") or 0) for s in scores]
            lines.append(f"\nQUALIDADE: {len(vals)} conversas auditadas, nota média "
                         f"{sum(vals) / len(vals):.0f}/100 no período.")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[VISAO OPERACIONAL] scorecards falhou: {type(e).__name__}")

    # 4) 🔴 SPEC-090 — O QUE TRAVOU, QUEM DESTRAVOU, E O QUE A REGINA ANOTOU
    #
    # ⚠️ Só para janela de UM DIA. A leitura do BLOCO D é por dia de calendário,
    # e espremer sete dias nela devolveria o número de um só — pior que não
    # devolver nada, porque pareceria completo.
    if dia:
        lines.extend(await _o_que_travou_no_dia(company_id, dia))

    lines.append("\n(Fonte: dados reais do sistema. Apresente com clareza; não invente números.)")
    return "\n".join(lines)


def _minutos(segundos: Optional[int]) -> str:
    if segundos is None:
        return "sem tempo apurado"
    if segundos < 90:
        return f"{segundos}s"
    return f"{segundos // 60} min"


async def _o_que_travou_no_dia(company_id: str, dia: str) -> List[str]:
    """As linhas do BLOCO D. ⛔ Falha sozinha, sem derrubar o resto do digest.

    ⚠️ **Cliente ASSÍNCRONO.** O resto desta função usa `get_supabase_client()`
    (síncrono) dentro de `asyncio.to_thread`. `o_que_aconteceu_ontem` faz
    `await …execute()`, então precisa do outro. ⛔ Misturar os dois produz
    *"coroutine never awaited"* — um SELECT que silenciosamente nunca acontece,
    e uma seção que sai vazia parecendo um dia tranquilo.
    """
    try:
        from app.core.database import create_async_supabase_client
        from app.services.o_dia_de_ontem import o_que_aconteceu_ontem

        db = await create_async_supabase_client()
        r = await o_que_aconteceu_ontem(db, company_id, dia)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[VISAO OPERACIONAL] travamentos falhou: {type(e).__name__}")
        # 🔴 DIZ QUE NÃO OLHOU. ⛔ Sumir com a seção seria o zero silencioso.
        return ["\nTRAVAMENTOS: não foi possível consultar agora "
                "(a resposta está incompleta)."]

    linhas: List[str] = []
    if not r["travamentos"]:
        linhas.append("\nTRAVAMENTOS: nenhum acionamento travou neste dia.")
    else:
        linhas.append(
            f"\nTRAVAMENTOS: {r['travamentos']} no dia · "
            f"{r['ainda_travados']} SEGUEM SEM DESTRAVAR · "
            f"tempo mediano {_minutos(r['segundos_mediano'])} "
            f"({r['tempos_considerados']} medidos)")
        if r["quem_destravou"]:
            quem = " · ".join(f"{k}: {v}" for k, v in
                              sorted(r["quem_destravou"].items(), key=lambda x: -x[1]))
            linhas.append(f"QUEM DESTRAVOU: {quem}")
        for t in r["telas"]:
            marca = " 🔴" if t["sem_destravar"] else ""
            linhas.append(f"- {t['rota'] or '?'} · {t['tela'] or 'tela não identificada'}: "
                          f"{t['travou']}× ({t['sem_destravar']} sem destravar){marca}")

    # 🔴 AS NOTAS DAS ATENDENTES
    if r["notas"]:
        linhas.append(f"\nANOTAÇÕES DA EQUIPE ({len(r['notas'])}):")
        for n in r["notas"][:_MAX_LIST]:
            onde = f" [{n['rota']} · {n['tela']}]" if n.get("rota") else ""
            linhas.append(f"- {str(n.get('texto') or '')[:220]}{onde}")
        # ⚠️ `whatsapp` significa que a mensagem JÁ tinha sido entregue quando o
        #    produto soube — o eco do `fromMe`. O Founder precisa saber disso.
        vazadas = int(r["notas_por_origem"].get("whatsapp", 0))
        if vazadas:
            linhas.append(
                f"⚠️ {vazadas} destas foram escritas na própria conversa do "
                "WhatsApp — o produto só as viu DEPOIS de o WhatsApp entregar. "
                "Para anotar sem que o cliente leia, use o chat do painel.")
    elif r["travamentos"]:
        linhas.append("\nANOTAÇÕES DA EQUIPE: nenhuma neste dia.")

    # 🔴 O CORTE, DECLARADO. Ver P-090-03: um relatório que trunca em silêncio
    #    conta uma história menor e parece completo.
    if r["truncado"]:
        linhas.append("⚠️ RESPOSTA INCOMPLETA: " + " · ".join(r["truncado"]))
    return linhas


# ------------------------------------------------------------------ #
# Atlas — mapas de rota (estrutura global, sem dado de cliente)
# ------------------------------------------------------------------ #
def _latest_maps_sync(insurer_key: Optional[str] = None) -> List[Dict[str, Any]]:
    from app.core.database import get_supabase_client

    db = get_supabase_client()
    q = (db.client.table("ura_maps")
         .select("insurer_key, ramo, status, map, diff_summary, created_at")
         .in_("status", ["active", "observed"])
         .order("created_at", desc=True).limit(60))
    if insurer_key:
        q = q.eq("insurer_key", insurer_key)
    rows = q.execute().data or []
    # 1 mapa por (insurer, ramo): active > observed; mais novo primeiro
    best: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        k = f"{r.get('insurer_key')}::{r.get('ramo')}"
        cur = best.get(k)
        if cur is None or (cur.get("status") != "active" and r.get("status") == "active"):
            best[k] = r
    return list(best.values())


def _trunc(text: Any, cap: int = _TEXT_CAP) -> str:
    t = " ".join(str(text or "").split())
    return t[: cap - 1] + "…" if len(t) > cap else t


def _route_to_service(map_data: Dict[str, Any], servico: str) -> List[str]:
    """BFS determinístico da raiz até a 1ª tela/aresta que casa o serviço."""
    nodes = map_data.get("nodes") or {}
    edges = (map_data.get("edges") or {}).values()
    root = map_data.get("root")
    if not root or root not in nodes:
        return []
    term = servico.strip().lower()
    adj: Dict[str, List[tuple]] = {}
    for e in edges:
        adj.setdefault(str(e.get("src")), []).append((str(e.get("label") or ""), str(e.get("to"))))
    from collections import deque

    seen = {root}
    queue = deque([(root, [])])
    while queue:
        nid, path = queue.popleft()
        for label, to in adj.get(nid, []):
            if to in seen:
                continue
            new_path = path + [(nid, label, to)]
            hit = term in label.lower() or term in str((nodes.get(to) or {}).get("text") or "").lower()
            if hit:
                out = []
                for src, lbl, dst in new_path:
                    out.append(f"[{_trunc((nodes.get(src) or {}).get('text'), 60)}] → responder \"{lbl or '(segue)'}\"")
                out.append(f"[{_trunc((nodes.get(new_path[-1][2]) or {}).get('text'), 60)}]")
                return out
            seen.add(to)
            queue.append((to, new_path))
    return []


async def atlas_routes_summary(insurer_key: Optional[str] = None, ramo: Optional[str] = None,
                               servico: Optional[str] = None) -> str:
    """Resumo dos mapas do Atlas. Sem seguradora: lista geral. Com seguradora:
    detalha (e com 'servico': mostra o caminho até o serviço)."""
    key = str(insurer_key or "").strip().lower() or None
    try:
        maps = await asyncio.to_thread(_latest_maps_sync, key)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[VISAO OPERACIONAL] atlas falhou: {type(e).__name__}")
        return "Os mapas do Atlas estão indisponíveis no momento."

    if ramo:
        maps = [m for m in maps if str(m.get("ramo") or "").lower() == str(ramo).lower()]
    if not maps:
        alvo = f" para {key or 'as seguradoras'}" + (f" ({ramo})" if ramo else "")
        return f"Ainda não há mapa de rotas observado{alvo}. O Observador constrói os mapas conforme os atendimentos acontecem."

    from app.services.insurer_registry import INSURER_REGISTRY

    if not key:
        lines = ["MAPAS DE ROTA DAS SEGURADORAS (Atlas):"]
        for m in sorted(maps, key=lambda x: str(x.get("insurer_key"))):
            label = str((INSURER_REGISTRY.get(str(m.get("insurer_key"))) or {}).get("label")
                        or str(m.get("insurer_key")).title())
            cov = ((m.get("map") or {}).get("coverage") or {})
            lines.append(f"- {label} ({m.get('ramo')}): {cov.get('nodes', '?')} telas, "
                         f"cobertura {cov.get('pct', '?')}% [{m.get('status')}]")
        lines.append("\nPara o caminho de um serviço: informe seguradora + serviço (ex.: porto + guincho).")
        return "\n".join(lines)

    m = maps[0]
    map_data = m.get("map") or {}
    cov = map_data.get("coverage") or {}
    label = str((INSURER_REGISTRY.get(key) or {}).get("label") or key.title())
    lines = [f"MAPA DA {label.upper()} ({m.get('ramo')}) — {cov.get('nodes', '?')} telas, "
             f"cobertura {cov.get('pct', '?')}% [{m.get('status')}]"]

    nodes = map_data.get("nodes") or {}
    root = map_data.get("root")
    if root and root in nodes:
        rn = nodes[root]
        lines.append(f"\nENTRADA: {_trunc(rn.get('text'))}")
        opts = [str(o.get("label") or "") for o in (rn.get("options") or []) if o.get("label")]
        if opts:
            lines.append("OPÇÕES INICIAIS: " + " · ".join(opts[:10]))

    if servico:
        path = _route_to_service(map_data, str(servico))
        if path:
            lines.append(f"\nCAMINHO ATÉ '{servico.upper()}':")
            lines.extend(f"  {i + 1}. {step}" for i, step in enumerate(path[:12]))
        else:
            lines.append(f"\nAinda não observamos o caminho de '{servico}' nesse mapa.")

    if m.get("diff_summary"):
        lines.append(f"\nRESUMO: {m['diff_summary']}")
    lines.append("(Estrutura global das URAs — sem nenhum dado de cliente.)")
    return "\n".join(lines)
