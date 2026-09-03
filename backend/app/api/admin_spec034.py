"""Endpoints admin das superfícies SPEC-034/036 (Etapa 1).

Alimentam as páginas novas do portal admin (design Claude Design 14/07):
Central de Agentes, Acionamentos ao vivo, Insights·Garimpo — e as ações do
Alfaiate (aprovar mapa) e do Registro de Seguradoras.

Todos exigem master admin (X-Admin-API-Key), mesmo padrão do billing_admin.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections import Counter
from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from app.core.auth import require_master_admin
# 🔴 O MASCARADOR CANÔNICO DA CASA. Ver o comentário abaixo de `router`.
from app.services.intelligence.redaction_service import redigir as _redigir

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/spec034", tags=["Admin SPEC-034"])

# 🔴 SPEC-088 §2 — E O MASCARADOR É O DA CASA, não um segundo escrito aqui.
#
# ⛔ Aqui existiam `_DIGITOS = \d{10,14}` e `_CPF_FORMATADO`, com um comentário afirmando
# que era "grosso de propósito". 📊 Medido em 03/09/2026 sobre 11 formatos reais de PII,
# ele pegava **0**: `(11) 98765-4321` (o formato que a URA devolve), `11 98765-4321`,
# `+55 11 98765-4321`, placa `ABC1D23`, placa antiga `ABC-1234`, CNPJ, e-mail e apólice
# passavam TODOS em claro — num transcript de URA que carrega exatamente isso.
#
# ⚠️ E o comentário era a parte mais cara: ele afirmava uma cobertura que o código não
# tinha, e quem lia parava de procurar. Um mascarador paralelo pior que o canônico é o
# caso literal da proibição do CLAUDE.md §5 — a lista que fica para trás é justamente a
# que deixa passar o CPF (`redaction_service`, docstring).
#
# `redigir` (importado no topo) é o único da casa: 10 padrões, testado, sem dependência
# de projeto — e 📊 pega os 11 formatos, sem tocar em `Protocolo 52955490` nem em
# `há 3 dias` (o controle do bloco [11] do guarda).
#
# ⚠️ `_mascarar_telefone` FICA: ele não redige, ele mostra os 4 últimos dígitos de um
# número que o operador precisa reconhecer (a seguradora, nunca o segurado).


def _mascarar_telefone(numero: str) -> str:
    """Só os 4 últimos dígitos, precedidos de reticências."""
    limpo = re.sub(r"\D", "", str(numero or ""))
    return f"…{limpo[-4:]}" if len(limpo) >= 4 else ("…" if limpo else "")


@router.get("/agents-status")
async def agents_status(_: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """A Central de Agentes — o contrato da §4 da SPEC-088.

    🔴 A chave `agents` do JSON antigo NÃO existe mais: a resposta é `grupos` com o
    estado de 5 cores calculado de pulso **e** produção, mais o painel de trabalho lido
    de `work_runs`/`artifacts`/`approval_requests`. Contagens, estados, ids e timestamps
    — nenhum texto de conversa atravessa.
    """
    from app.core.central_de_agentes import carregar_estado

    return await carregar_estado()


@router.get("/sessions")
async def active_sessions(_: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Sessões de acionamento ativas (Redis) com transcript para a timeline."""
    sessions: List[Dict[str, Any]] = []
    try:
        from app.core.redis import get_async_redis_client
        from app.services.dispatch_mirror import insurer_label_from_ref

        redis = await get_async_redis_client()
        async for key in redis.scan_iter(match="dispatch:active:*"):
            k = key.decode() if isinstance(key, (bytes, bytearray)) else str(key)
            raw = await redis.get(k)
            if not raw:
                continue
            try:
                s = json.loads(raw.decode() if isinstance(raw, (bytes, bytearray)) else raw)
            except Exception:  # noqa: BLE001
                continue
            parts = k.split(":")
            transcript = (s.get("transcript") or [])[-40:]
            sessions.append({
                "company_id": parts[2] if len(parts) >= 4 else "",
                # 🔴 SPEC-088 BLOCO C: o número inteiro da seguradora saía daqui em claro.
                "insurer_phone": _mascarar_telefone(parts[3]) if len(parts) >= 4 else "",
                "insurer_label": insurer_label_from_ref(s.get("playbook_ref")),
                "case_id": s.get("case_id"), "state": s.get("state"),
                "subservice": s.get("subservice"), "created_at": s.get("created_at"),
                "sentinela_attempts": s.get("sentinela_attempts") or 0,
                "reason": s.get("reason"),
                "timeline": [
                    {"at": t.get("at"), "direction": t.get("direction"),
                     # "atendente" (nunca um nome próprio: Even é só o nome que a
                     # Resulta deu — cada corretora batiza o seu).
                     "via": t.get("via") or ("seguradora" if t.get("direction") == "in" else "atendente"),
                     # 🔴 o transcript da URA carrega CPF, telefone e placa digitados
                     # pelo segurado — e o mascarador é o canônico, nunca um daqui.
                     "text": _redigir(str(t.get("text") or "")[:300])}
                    for t in transcript
                ],
            })
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ADMIN34] sessions falhou: {type(e).__name__}")
    sessions.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    return {"sessions": sessions}


@router.get("/insights")
async def insights(_: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Ranking do Garimpo + histórico da IA de Sugestões (30 dias).

    🔴 SPEC-088 BLOCO C: os dois filtros (`"garimpo"` e `"sugestoes_ia"`) estavam escritos
    aqui, e 📊 o banco só tem `garimpo_v3` — o ranking devolvia lista vazia com 270 linhas
    no banco. Agora eles saem da MESMA `fonte_de_producao` que o registro do BLOCO A
    declara. Não é trocar a string: é matar a classe.
    """
    out: Dict[str, Any] = {"ranking": [], "sugestoes": [], "companies": {}}
    try:
        from app.core.central_de_agentes import filtro_de_fonte, linha_casa_filtro
        from app.core.database import get_supabase_client

        f_garimpo = filtro_de_fonte("garimpo", "broker_insights")
        f_sugestoes = filtro_de_fonte("sugestoes", "broker_insights")
        # Filtro ausente é lista vazia, nunca "tudo": um registro incompleto não pode
        # virar um ranking que mistura as duas fontes.
        if not f_garimpo or not f_sugestoes:
            logger.warning("[ADMIN34] insights: fonte_de_producao de broker_insights ausente")
        db = get_supabase_client()
        rows = await asyncio.to_thread(
            lambda: db.client.table("broker_insights")
            .select("company_id, kind, summary, source, status, created_at")
            .order("created_at", desc=True).limit(1000).execute()
        )
        garimpo = ([r for r in rows.data or [] if linha_casa_filtro(r, f_garimpo)]
                   if f_garimpo else [])
        counts = Counter((r["kind"], r["summary"][:80]) for r in garimpo)
        out["ranking"] = [
            {"kind": k, "summary": s, "count": c}
            for (k, s), c in counts.most_common(20)
        ]
        out["sugestoes"] = [
            {"company_id": r.get("company_id"), "summary": r.get("summary"),
             "status": r.get("status"), "created_at": r.get("created_at")}
            for r in (rows.data or []) if f_sugestoes and linha_casa_filtro(r, f_sugestoes)
        ][:20]
        comp = await asyncio.to_thread(
            lambda: db.client.table("companies").select("id, company_name").execute()
        )
        out["companies"] = {c["id"]: c["company_name"] for c in comp.data or []}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ADMIN34] insights falhou: {type(e).__name__}")
    return out


@router.get("/scorecards")
async def scorecards(_: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    out: Dict[str, Any] = {"summary": [], "recent": []}
    try:
        from app.core.database import get_supabase_client

        db = get_supabase_client()
        rows = await asyncio.to_thread(
            lambda: db.client.table("conversation_scorecards")
            .select("company_id, conversation_id, score, flags, created_at")
            .order("created_at", desc=True).limit(500).execute()
        )
        by_company: Dict[str, List[int]] = {}
        flag_counter: Counter = Counter()
        for r in rows.data or []:
            by_company.setdefault(str(r.get("company_id")), []).append(int(r.get("score") or 0))
            for f in r.get("flags") or []:
                flag_counter[f] += 1
        out["summary"] = [
            {"company_id": cid, "avg_score": round(sum(v) / len(v), 1), "audited": len(v)}
            for cid, v in by_company.items()
        ]
        out["top_flags"] = flag_counter.most_common(8)
        out["recent"] = (rows.data or [])[:30]
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ADMIN34] scorecards falhou: {type(e).__name__}")
    return out


@router.get("/registry")
async def registry(_: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    from app.services.insurer_registry import INSURER_REGISTRY

    return {"registry": INSURER_REGISTRY}


@router.get("/maps")
async def list_maps(_: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    out: Dict[str, Any] = {"maps": [], "overlays": []}
    try:
        from app.core.database import get_supabase_client

        db = get_supabase_client()
        maps = await asyncio.to_thread(
            lambda: db.client.table("ura_maps")
            .select("id, insurer_key, ramo, version, status, diff_summary, created_at")
            .order("created_at", desc=True).limit(100).execute()
        )
        overlays = await asyncio.to_thread(
            lambda: db.client.table("playbook_overlays")
            .select("id, playbook_ref, kind, note, status, created_at")
            .order("created_at", desc=True).limit(100).execute()
        )
        out["maps"] = maps.data or []
        out["overlays"] = overlays.data or []
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ADMIN34] maps falhou: {type(e).__name__}")
    return out


@router.post("/test-alert")
async def test_alert(body: Dict[str, Any], _: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Envia um alerta de TESTE pelo MESMO caminho real do Vigia (suporte humano
    da corretora) — valida o canal e a acentuação (ç, ã, õ, á, é)."""
    from app.services.dispatch_router import _support_contact
    from app.services.integration_service import get_integration_service
    from app.services.whatsapp_service import get_whatsapp_service

    company_id = str(body.get("company_id") or "")
    contact = await _support_contact(company_id)
    integration = get_integration_service().get_platform_whatsapp_integration(company_id)
    if not contact or not integration:
        return {"ok": False, "error": "sem contato de suporte ou integração",
                "contact_found": bool(contact), "integration_found": bool(integration)}
    text = ("✅ Teste do canal de alertas do Vigia\n"
            "Acentuação: ação, atenção, coração, você, análise, órgão, saúde á é í ó ú.\n"
            "Se esta mensagem chegou legível, o canal de handoff está PERFEITO. 🚨")
    try:
        get_whatsapp_service().send_message(contact, text, integration)
        return {"ok": True, "sent_to": contact[:8] + "***"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": type(e).__name__}


@router.post("/cartographer/start")
async def cartographer_start(body: Dict[str, Any], _: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Inicia UMA exploração de mapa: {company_id, insurer_key, ramo?, test_data{cpf,placa,cep}}.
    Requer CARTOGRAPHER_MODE=1 no ambiente. O founder dispara seguradora a seguradora."""
    import os as _os

    if _os.getenv("CARTOGRAPHER_MODE", "0").strip() != "1":
        return {"ok": False, "error": "CARTOGRAPHER_MODE desligado (env)"}
    from app.services.cartographer_runner import start_exploration
    from app.services.integration_service import get_integration_service
    from app.services.whatsapp_service import get_whatsapp_service

    company_id = str(body.get("company_id") or "")
    integration = get_integration_service().get_platform_whatsapp_integration(company_id)
    if not integration:
        return {"ok": False, "error": "sem integração WhatsApp para esta company"}
    wa = get_whatsapp_service()
    _ = start_exploration  # (usado em _start_with_send)
    return await _start_with_send(body, wa, integration)


async def _start_with_send(body: Dict[str, Any], wa, integration) -> Dict[str, Any]:
    from app.services.cartographer_runner import start_exploration
    from app.services.corridor_playbooks import resolve_insurer_contact
    from app.services.insurer_registry import registry_whatsapp

    insurer_key = str(body.get("insurer_key") or "")
    phone = resolve_insurer_contact(insurer_key) or registry_whatsapp(insurer_key)
    return await start_exploration(
        insurer_key=insurer_key,
        ramo=str(body.get("ramo") or "auto"),
        test_data=dict(body.get("test_data") or {}),
        send=lambda text: wa.send_message(phone, text, integration),
        company_id=str(body.get("company_id") or ""),
    )


@router.post("/cartographer/stop")
async def cartographer_stop(body: Dict[str, Any], _: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """FREIO DE EMERGÊNCIA: encerra explorações na hora. {"all": true} para todas,
    ou {"insurer_key": "porto"} para uma. O que já foi mapeado é salvo como
    'proposed' (nada se perde); nenhuma mensagem a mais é enviada."""
    stopped = []
    try:
        from app.core.redis import get_async_redis_client
        from app.services.ura_map_service import save_proposed_map
        from app.services.cartographer import exploration_to_map

        redis = await get_async_redis_client()
        target_key = str(body.get("insurer_key") or "").strip().lower()
        async for k in redis.scan_iter(match="carto:active:*"):
            kk = k.decode() if isinstance(k, (bytes, bytearray)) else str(k)
            raw = await redis.get(kk)
            exp = json.loads(raw.decode() if isinstance(raw, (bytes, bytearray)) else raw) if raw else {}
            if not body.get("all") and target_key and str(exp.get("insurer_key")) != target_key:
                continue
            try:
                map_obj = exploration_to_map(exp)
                if map_obj.get("nodes"):
                    await save_proposed_map(str(exp.get("insurer_key")), str(exp.get("ramo") or "auto"),
                                            map_obj, source="cartographer_stopped")
            except Exception:  # noqa: BLE001
                pass
            await redis.delete(kk)
            stopped.append(exp.get("insurer_key"))
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ADMIN34] carto stop falhou: {type(e).__name__}")
        return {"ok": False, "error": type(e).__name__}
    return {"ok": True, "stopped": stopped}


@router.get("/cartographer/status")
async def cartographer_status(_: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Explorações ativas + últimos mapas salvos."""
    out: Dict[str, Any] = {"active": [], "mode": None}
    import os as _os

    out["mode"] = _os.getenv("CARTOGRAPHER_MODE", "0")
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        async for k in r.scan_iter(match="carto:active:*"):
            raw = await r.get(k)
            if raw:
                exp = json.loads(raw.decode() if isinstance(raw, (bytes, bytearray)) else raw)
                out["active"].append({"insurer_key": exp.get("insurer_key"), "ramo": exp.get("ramo"),
                                      "msg_count": exp.get("msg_count"), "state": exp.get("state"),
                                      "nodes": len(exp.get("nodes") or {}),
                                      "passes": exp.get("pass_count") or 0,
                                      "tail": [str(t.get("direction")) + ": " + str(t.get("text") or "")[:120]
                                               for t in (exp.get("transcript") or [])[-6:]]})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ADMIN34] carto status falhou: {type(e).__name__}")
    return out


@router.get("/company-overview/{company_id}")
async def company_overview(company_id: str, _: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Cockpit 360º da corretora: conversas, qualidade (Auditor), insights
    (Garimpo), conhecimento e acionamentos recentes — num payload só."""
    out: Dict[str, Any] = {"company_id": company_id}
    try:
        from app.core.database import get_supabase_client

        db = get_supabase_client()

        def _q(fn):
            try:
                return fn().data or []
            except Exception:  # noqa: BLE001
                return []

        comp = await asyncio.to_thread(lambda: _q(
            lambda: db.client.table("companies")
            .select("company_name, status, plan_type, created_at, is_technical")
            .eq("id", company_id).limit(1).execute()))
        out["company"] = comp[0] if comp else {}

        convs = await asyncio.to_thread(lambda: _q(
            lambda: db.client.table("conversations")
            .select("id, session_id, user_name, last_message_at")
            .eq("company_id", company_id)
            .order("last_message_at", desc=True).limit(200).execute()))
        dispatches = [c for c in convs if str(c.get("session_id") or "").startswith("dispatch:")]
        out["conversas"] = {"total": len(convs), "acionamentos": len(dispatches),
                            "recentes": convs[:6], "acionamentos_recentes": dispatches[:6]}

        scores = await asyncio.to_thread(lambda: _q(
            lambda: db.client.table("conversation_scorecards")
            .select("score, flags, created_at").eq("company_id", company_id)
            .order("created_at", desc=True).limit(100).execute()))
        if scores:
            out["qualidade"] = {
                "nota_media": round(sum(int(s.get("score") or 0) for s in scores) / len(scores), 1),
                "auditadas": len(scores),
                "flags": Counter(f for s in scores for f in (s.get("flags") or [])).most_common(5),
            }
        else:
            out["qualidade"] = {"nota_media": None, "auditadas": 0, "flags": []}

        insights_rows = await asyncio.to_thread(lambda: _q(
            lambda: db.client.table("broker_insights")
            .select("kind, summary, source, created_at").eq("company_id", company_id)
            .order("created_at", desc=True).limit(30).execute()))
        out["insights"] = insights_rows[:10]

        docs = await asyncio.to_thread(lambda: _q(
            lambda: db.client.table("documents")
            .select("id").eq("company_id", company_id).execute()))
        out["conhecimento"] = {"documentos": len(docs)}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ADMIN34] company-overview falhou: {type(e).__name__}")
    return out


@router.post("/maps/{map_id}/activate")
async def activate_map_endpoint(map_id: str, _: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """Aprovação 1-clique do founder: promove um mapa proposto a ativo."""
    from app.services.ura_map_service import activate_map

    ok = await activate_map(map_id)
    return {"ok": ok}


# ===========================================================================
# SPEC-093-B BLOCO D — o resumo da sombra de sinistro
#
# 🔴 READ-ONLY, AGREGADO, SEM PII. A pergunta que esta rota responde é a do Founder:
# *"a sombra está de pé?"*. Ela não abre sinistro, não manda mensagem, não escreve
# uma linha — só SELECT — e **nenhum texto de conversa, nome, telefone, CPF, apólice
# ou placa atravessa**: o JSON só carrega contagem, enum, timestamp, slug e a
# assinatura (sha256) da variante. É a mesma disciplina do `/agents-status`.
#
# ⚠️ POR QUE ELA NÃO FILTRA `company_id`, E ISSO NÃO É BURACO DE TENANT
# --------------------------------------------------------------------
# Esta é a visão de PLATAFORMA, como a Central de Agentes: a barreira é
# `require_master_admin` na assinatura (SPEC-088 §4 · gate [9] do guarda da 088) mais
# o proxy Next que devolve 401 sem sessão e 403 para sessão de corretora. O agregado é
# POR `company_id`, e a corretora aparece pelo id, nunca por nome de gente.
#
# 🔴 E a segunda barreira do §7 continua aqui, invertida: um `work_event` cujo
# `company_id` NÃO bate com o da sombra é DESCARTADO. Ele não deveria existir; se
# existir, contá-lo seria misturar corretoras num número que o Founder lê como verdade.
# ===========================================================================
CLAIMS_SHADOW_CACHE_KEY = "spec093b:claims-shadow:v1"
CLAIMS_SHADOW_CACHE_S = 60
#: 📊 A janela do BLOCO D é 30 dias (a da SPEC), e é MENOR que a do digest (90). São
#: perguntas diferentes: aqui é "está funcionando agora?", lá é "qual o processo?".
CLAIMS_SHADOW_JANELA_DIAS = 30
CLAIMS_SHADOW_TOP_VARIANTES = 5
#: Quantos `work_run_id` cabem num `in_()` sem estourar a URL do PostgREST.
_CLAIMS_SHADOW_LOTE = 100

#: 🔴 O CONTRATO, FECHADO E EM CÓDIGO — não em prosa. O guarda importa estas tuplas e
#: reprova qualquer chave a mais ou a menos. Um contrato escrito só no docstring é um
#: contrato que ninguém confere (CLAUDE.md §9.3).
CLAIMS_SHADOW_CHAVES = ("gerado_em", "janela_dias", "cache_s", "corretoras",
                        "totais", "nao_instrumentado", "leitura_indisponivel")
CLAIMS_SHADOW_CHAVES_CORRETORA = ("company_id", "sombras_abertas", "sombras_encerradas",
                                  "eventos_por_tipo", "esperas_por_kind",
                                  "top_variantes", "contadores", "prazos", "sinais_30d")
CLAIMS_SHADOW_CHAVES_VARIANTE = ("assinatura", "ramo", "seguradora_slug", "n", "passos")
CLAIMS_SHADOW_CHAVES_TOTAIS = ("corretoras", "sombras", "eventos", "esperas", "sinais")

#: Só `claims.x_y` entra. ⛔ Estrutural, não confiança: um `event_type` que não case
#: com isto não vira chave do JSON — e é assim que "nenhum campo textual" deixa de
#: depender de todo escritor ter se comportado.
_RE_EVENTO_DA_SOMBRA = re.compile(r"^claims\.[a-z_]{1,60}$")
_RE_SLUG_SUJO = re.compile(r"[^a-z0-9_\-]+")


def _slug(valor: Any, padrao: str) -> str:
    """Um slug curto e sem espaço. ⛔ A última tranca antes do JSON.

    `ramo` e `seguradora_slug` nascem de `payload_redacted`, que já é filtrado pelo
    vocabulário e pelo redator. Isto aqui é a tranca de fora: mesmo que um dia entre
    algo com espaço, o que sai da rota continua sendo slug.
    """
    t = _RE_SLUG_SUJO.sub("-", str(valor or "").strip().lower()).strip("-")
    return (t or padrao)[:40]


def _iso_para_dt(valor: Any):
    from datetime import datetime

    t = str(valor or "").strip()
    if not t:
        return None
    try:
        return datetime.fromisoformat(t.replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return None


def _dias_entre(inicio: Any, fim: Any) -> float:
    a, b = _iso_para_dt(inicio), _iso_para_dt(fim)
    if a is None or b is None:
        return 0.0
    try:
        return round(max(0.0, (b - a).total_seconds() / 86400.0), 2)
    except Exception:  # noqa: BLE001
        return 0.0


def _claims_shadow_vazio(agora_iso: str, nao_instrumentado: List[str],
                         leitura_indisponivel: bool = False) -> Dict[str, Any]:
    """A resposta de banco vazio: ZEROS, contrato inteiro, e nenhum erro (gate D3)."""
    return {"gerado_em": agora_iso, "janela_dias": CLAIMS_SHADOW_JANELA_DIAS,
            "cache_s": CLAIMS_SHADOW_CACHE_S, "corretoras": [],
            "totais": {"corretoras": 0, "sombras": 0, "eventos": 0,
                       "esperas": 0, "sinais": 0},
            "nao_instrumentado": list(nao_instrumentado),
            "leitura_indisponivel": bool(leitura_indisponivel)}


def _claims_shadow_ler(cli: Any, desde: str) -> Dict[str, Any]:
    """As quatro leituras, todas paginadas. ⛔ Só SELECT.

    🔴 `ler_paginado` e não `.limit(N)`: o PostgREST entrega 1.000 e cala
    (`app/leitura_completa.py`). Quando uma leitura trunca ou falha, o nome dela entra
    em `nao_instrumentado` — um número incompleto que não se declara incompleto é o
    defeito que a SPEC-088 §4 batizou.
    """
    from app.leitura_completa import ler_paginado
    from app.services.claims_shadow_digest import SOURCE_TYPE, WORKFLOW_DA_SOMBRA

    fora: List[str] = []

    runs, cortou = ler_paginado(
        lambda: (cli.table("work_runs")
                 .select("id, company_id, created_at, status")
                 .eq("workflow_key", WORKFLOW_DA_SOMBRA)
                 .gte("created_at", desde)),
        chave_unica="id", rotulo="spec093b/work_runs")
    if cortou:
        fora.append("sombras")

    ids = [str(r.get("id")) for r in (runs or []) if r.get("id")]

    eventos: List[Dict[str, Any]] = []
    esperas: List[Dict[str, Any]] = []
    for i in range(0, len(ids), _CLAIMS_SHADOW_LOTE):
        lote = ids[i:i + _CLAIMS_SHADOW_LOTE]
        linhas, cortou = ler_paginado(
            lambda alvo=lote: (cli.table("work_events")
                               .select("id, work_run_id, event_type, "
                                       "payload_redacted, created_at, company_id")
                               .in_("work_run_id", alvo)),
            chave_unica="id", rotulo="spec093b/work_events")
        eventos.extend(linhas or [])
        if cortou and "eventos" not in fora:
            fora.append("eventos")

        linhas, cortou = ler_paginado(
            lambda alvo=lote: (cli.table("work_waits")
                               .select("id, company_id, work_run_id, kind, status, "
                                       "created_at, satisfeito_em")
                               .in_("work_run_id", alvo)),
            chave_unica="id", rotulo="spec093b/work_waits")
        esperas.extend(linhas or [])
        if cortou and "esperas" not in fora:
            fora.append("esperas")

    sinais, cortou = ler_paginado(
        lambda: (cli.table("intelligence_signals")
                 .select("id, company_id, signal_type, created_at")
                 .eq("source_type", SOURCE_TYPE)
                 .gte("created_at", desde)),
        chave_unica="id", rotulo="spec093b/intelligence_signals")
    if cortou:
        fora.append("sinais")

    return {"runs": runs or [], "eventos": eventos, "esperas": esperas,
            "sinais": sinais or [], "nao_instrumentado": fora}


def montar_resumo_claims_shadow(cli: Any, *, agora: Any = None) -> Dict[str, Any]:
    """O corpo do `GET /claims-shadow`. Recebe o cliente, devolve o contrato fechado.

    🔴 Separada da rota de propósito: é ela que o guarda chama com um cliente falso,
    porque um gate que só sabe bater na rota HTTP não roda sem servidor de pé — e um
    gate que não roda não guarda (CLAUDE.md §9.3).

    ⛔ NÃO reimplementa agregação: `trajetorias_de`, `variantes_de`, `contadores_de` e
    `esperas_vencidas` são as MESMAS do digest. Uma segunda contagem aqui divergiria
    da que escreve o sinal, e as duas mostrariam números diferentes da mesma verdade
    (CLAUDE.md §5).
    """
    from datetime import datetime, timedelta, timezone

    from app.services.claims_shadow_digest import (
        RAMO_DESCONHECIDO, SEGURADORA_DESCONHECIDA, contadores_de, esperas_vencidas,
        trajetorias_de, variantes_de,
    )

    fim = agora or datetime.now(timezone.utc)
    desde = (fim - timedelta(days=CLAIMS_SHADOW_JANELA_DIAS)).isoformat()
    agora_iso = fim.isoformat()

    try:
        cru = _claims_shadow_ler(cli, desde)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ADMIN34] claims-shadow: leitura falhou ({type(e).__name__})")
        return _claims_shadow_vazio(agora_iso, ["sombras", "eventos", "esperas",
                                                "sinais"], leitura_indisponivel=True)

    nao_instrumentado = list(cru["nao_instrumentado"])
    runs = [r for r in cru["runs"] if r.get("id") and r.get("company_id")]
    if not runs:
        return _claims_shadow_vazio(agora_iso, nao_instrumentado)

    # A corretora DONA de cada sombra — a autoridade de tenant do resto do cálculo.
    dono = {str(r["id"]): str(r["company_id"]) for r in runs}

    por_empresa: Dict[str, Dict[str, Any]] = {}
    for r in runs:
        e = por_empresa.setdefault(str(r["company_id"]),
                                   {"runs": [], "eventos": [], "esperas": [],
                                    "sinais": 0})
        e["runs"].append(str(r["id"]))

    for ev in cru["eventos"]:
        empresa = dono.get(str(ev.get("work_run_id") or ""))
        # 🔴 §7 invertido: o evento de OUTRA corretora não entra na conta desta.
        if not empresa or str(ev.get("company_id") or empresa) != empresa:
            continue
        por_empresa[empresa]["eventos"].append(ev)

    for w in cru["esperas"]:
        empresa = dono.get(str(w.get("work_run_id") or ""))
        if not empresa or str(w.get("company_id") or empresa) != empresa:
            continue
        por_empresa[empresa]["esperas"].append(w)

    for s in cru["sinais"]:
        empresa = str(s.get("company_id") or "")
        if empresa in por_empresa:
            por_empresa[empresa]["sinais"] += 1

    corretoras: List[Dict[str, Any]] = []
    for empresa, dados in por_empresa.items():
        trajs = trajetorias_de(dados["eventos"])
        # A sombra que abriu e nada mais aconteceu É o caso que mais interessa — sem
        # ela no denominador, o contador "sem documento" fica bonito onde a operação
        # está pior. Mesma linha do `digerir()`, pelo mesmo motivo.
        vistas = {t["work_run_id"] for t in trajs}
        for run in dados["runs"]:
            if run not in vistas:
                trajs.append({"work_run_id": run, "company_id": empresa,
                              "ramo": RAMO_DESCONHECIDO,
                              "seguradora_slug": SEGURADORA_DESCONHECIDA,
                              "eventos": [], "desfechos": [], "esperas": []})
        for t in trajs:
            t["company_id"] = empresa
            t["ramo"] = _slug(t.get("ramo"), RAMO_DESCONHECIDO)
            t["seguradora_slug"] = _slug(t.get("seguradora_slug"),
                                         SEGURADORA_DESCONHECIDA)
            t["eventos"] = [str(x) for x in (t.get("eventos") or ())
                            if _RE_EVENTO_DA_SOMBRA.match(str(x))]

        tipos: Counter = Counter()
        for t in trajs:
            tipos.update(t["eventos"])

        esperas_por_kind: Dict[str, Dict[str, Any]] = {}
        for w in dados["esperas"]:
            kind = _slug(w.get("kind"), "desconhecido")
            linha = esperas_por_kind.setdefault(kind, {"n": 0, "media_dias": 0.0,
                                                       "_soma": 0.0})
            linha["n"] += 1
            linha["_soma"] += _dias_entre(w.get("created_at"),
                                          w.get("satisfeito_em") or agora_iso)
        for linha in esperas_por_kind.values():
            linha["media_dias"] = round(linha.pop("_soma") / max(1, linha["n"]), 2)

        # ⚠️ `limiar=1` aqui, e 3 no digest: são perguntas diferentes. O digest só
        # emite SINAL com N>=3 (abaixo disso é anedota); esta tela mostra o que está
        # acontecendo, e com o corpus de hoje N=1 é o que existe. O `n` sai junto,
        # então ninguém cita um número sem saber de quantos ele veio (§12.1).
        variantes = variantes_de(trajs, limiar=1)[:CLAIMS_SHADOW_TOP_VARIANTES]
        encerradas = sum(1 for t in trajs if "claims.encerrado" in t["eventos"])

        corretoras.append({
            "company_id": empresa,
            "sombras_abertas": len(dados["runs"]),
            "sombras_encerradas": encerradas,
            "eventos_por_tipo": dict(sorted(tipos.items())),
            "esperas_por_kind": esperas_por_kind,
            # ⛔ `work_run_ids` de `variantes_de` NÃO sai daqui: id de execução amarra
            # a estatística a um caso, e é o oposto do agregado (referência ⑦).
            "top_variantes": [{"assinatura": v["assinatura"], "ramo": v["ramo"],
                               "seguradora_slug": v["seguradora_slug"],
                               "n": v["n"], "passos": list(v["eventos"])}
                              for v in variantes],
            "contadores": dict(contadores_de(trajs)),
            "prazos": dict(esperas_vencidas(trajs, agora=fim)),
            "sinais_30d": dados["sinais"],
        })

    corretoras.sort(key=lambda c: (-c["sombras_abertas"], c["company_id"]))
    return {"gerado_em": agora_iso, "janela_dias": CLAIMS_SHADOW_JANELA_DIAS,
            "cache_s": CLAIMS_SHADOW_CACHE_S, "corretoras": corretoras,
            "totais": {"corretoras": len(corretoras),
                       "sombras": sum(c["sombras_abertas"] for c in corretoras),
                       "eventos": sum(sum(c["eventos_por_tipo"].values())
                                      for c in corretoras),
                       "esperas": sum(sum(k["n"] for k in c["esperas_por_kind"].values())
                                      for c in corretoras),
                       "sinais": sum(c["sinais_30d"] for c in corretoras)},
            "nao_instrumentado": nao_instrumentado,
            "leitura_indisponivel": False}


def _claims_shadow_sincrono() -> Dict[str, Any]:
    """Abre o cliente e monta. ⚠️ O cliente TAMBÉM pode falhar (SPEC-088, `_cliente`):
    sem `SUPABASE_URL` ou com o Postgres fora, `get_supabase_client()` LEVANTA — e a
    rota devolveria 500 justamente quando o Founder abre a tela para ver o que quebrou.
    """
    from datetime import datetime, timezone

    try:
        from app.core.database import get_supabase_client

        cli = get_supabase_client().client
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[ADMIN34] claims-shadow sem cliente ({type(e).__name__})")
        return _claims_shadow_vazio(datetime.now(timezone.utc).isoformat(),
                                    ["sombras", "eventos", "esperas", "sinais"],
                                    leitura_indisponivel=True)
    return montar_resumo_claims_shadow(cli)


async def carregar_claims_shadow() -> Dict[str, Any]:
    """UMA chave de cache de plataforma, 60s. Sem Redis, calcula direto — o cache é
    otimização, não dependência (mesmo contrato do `carregar_estado` da 088)."""
    try:
        from app.core.redis import get_async_redis_client

        redis = await get_async_redis_client()
        cru = await redis.get(CLAIMS_SHADOW_CACHE_KEY)
        if cru:
            return json.loads(cru.decode() if isinstance(cru, (bytes, bytearray)) else cru)
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[ADMIN34] claims-shadow cache indisponível: {type(e).__name__}")

    estado = await asyncio.to_thread(_claims_shadow_sincrono)

    try:
        from app.core.redis import get_async_redis_client

        redis = await get_async_redis_client()
        await redis.set(CLAIMS_SHADOW_CACHE_KEY, json.dumps(estado),
                        ex=CLAIMS_SHADOW_CACHE_S)
    except Exception as e:  # noqa: BLE001
        logger.debug(f"[ADMIN34] claims-shadow cache não gravado: {type(e).__name__}")
    return estado


@router.get("/claims-shadow")
async def claims_shadow(_: Any = Depends(require_master_admin)) -> Dict[str, Any]:
    """O resumo da sombra de sinistro — SPEC-093-B BLOCO D. Contrato FECHADO:

    ```
    gerado_em            timestamp ISO da montagem
    janela_dias          30
    cache_s              60
    leitura_indisponivel o banco não respondeu (a tela sai zerada, com o motivo)
    nao_instrumentado    ["sombras"|"eventos"|"esperas"|"sinais"] que truncaram
    totais               {corretoras, sombras, eventos, esperas, sinais}
    corretoras[]         company_id            uuid da corretora (NUNCA nome)
                         sombras_abertas       quantas sombras na janela
                         sombras_encerradas    quantas têm `claims.encerrado`
                         eventos_por_tipo      {claims.x: n}
                         esperas_por_kind      {kind: {n, media_dias}}
                         top_variantes[]       {assinatura, ramo, seguradora_slug,
                                                n, passos[]}
                         contadores            os 5 da referência 5 + `total`
                         prazos                {vencidas, regime_nao_determinado,
                                                total}
                         sinais_30d            sinais de `claims_shadow` na janela
    ```

    ⛔ Nenhuma chave fora desta lista, e nenhum campo textual: contagem, enum,
    timestamp, uuid, slug e a assinatura sha256 da variante. Nome, telefone, CPF,
    apólice, placa e texto de conversa não têm por onde entrar — nada disso é lido.
    """
    return await carregar_claims_shadow()
