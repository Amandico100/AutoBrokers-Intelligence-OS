"""Canal WhatsApp da corretora — setup Evolution + QR + status (SPEC-017 P1.2).

Endpoints internos (chave interna Next↔Backend, mesmo padrão do InfoCap):
  POST /api/whatsapp-channel/setup   — garante instância Evolution da corretora,
                                       gera token de webhook e configura o webhook.
  GET  /api/whatsapp-channel/qr      — QR code (base64) para conectar no dashboard.
  GET  /api/whatsapp-channel/status  — estado da conexão (instância + integração).

Plataforma Evolution (global, EasyPanel): EVOLUTION_BASE_URL + EVOLUTION_API_KEY.
Instância por corretora: `ab-<8 primeiros do company_id>`. O token plaintext do
webhook aparece UMA vez (na URL configurada na instância); no banco só o hash.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.core.database import get_supabase_client
from app.services.whatsapp.channel_security import (
    build_webhook_url,
    corpo_do_connect,
    new_webhook_credentials,
)
from app.services.whatsapp.pairing_orchestrator import instancia_ja_existe

logger = logging.getLogger(__name__)
router = APIRouter()

_TIMEOUT = 20.0


def _require_internal_key(provided: Optional[str]) -> None:
    expected = os.getenv("BACKEND_INTERNAL_API_KEY") or os.getenv("ADMIN_API_KEY")
    if not expected or not provided or provided != expected:
        raise HTTPException(status_code=401, detail="unauthorized")


def _evolution_platform() -> Dict[str, str]:
    base_url = (os.getenv("EVOLUTION_BASE_URL") or "").rstrip("/")
    api_key = os.getenv("EVOLUTION_API_KEY") or ""
    if not base_url or not api_key:
        raise HTTPException(status_code=503, detail="evolution_not_configured")
    return {"base_url": base_url, "api_key": api_key}


def _instance_name(company_id: str, purpose: str = "attendance") -> str:
    """Nome de instância do **Evolution v2** — NÃO do Evolution GO.

    ⚠️ Não confundir com `_go_instance_name`, logo abaixo. São dois provedores
    diferentes, dois servidores diferentes e dois espaços de nomes diferentes;
    parecerem-se é acidente de prefixo, não parentesco.

    Só o GO indexa acervo pelo nome (`observer_number` = dígitos do nome), e por
    isso só o GO tem gerador canônico em `channel_identity`. Trazer esta função
    para lá renomearia instâncias de um provedor que não tem esse problema — o
    tipo de "consolidação" que cria o defeito que pretendia evitar.

    S17-12 multi-número: uma instância Evolution POR PROPÓSITO por corretora.
    'attendance' mantém o nome curto (compat); demais ganham sufixo.
    """
    base = f"ab-{str(company_id).replace('-', '')[:12]}"
    p = str(purpose or "attendance").strip().lower()
    if p in ("", "attendance"):
        return base
    suffix = "".join(ch for ch in p if ch.isalnum())[:10] or "aux"
    return f"{base}-{suffix}"


def _public_backend_url() -> str:
    return (os.getenv("PUBLIC_BACKEND_URL") or os.getenv("BACKEND_PUBLIC_URL") or "").rstrip("/")


# ------------------------------------------------------------------ #
# Evolution GO (SPEC-034 — founder 14/07: "transferir tudo de uma vez").
# Liga com WHATSAPP_CHANNEL_PROVIDER=evolution-go + os envs EVOLUTION_GO_*.
#
# SPEC-047 MULTI-CORRETORA: uma instância GO POR corretora (ab-<company>),
# criada via EVOLUTION_GO_GLOBAL_KEY com token próprio (mesmo padrão do
# onboarding do Atlas) e persistida em integrations — QR/status/desconectar
# resolvem a instância DA corretora pela linha do banco, nunca por env.
# A instância única por env (EVOLUTION_GO_INSTANCE_TOKEN) vira fallback
# legado para quem já estava pareado por ela.
# ------------------------------------------------------------------ #
def _go_enabled() -> bool:
    return (os.getenv("WHATSAPP_CHANNEL_PROVIDER") or "").strip().lower() == "evolution-go"


def _go_base() -> str:
    base = (os.getenv("EVOLUTION_GO_BASE_URL") or "").rstrip("/")
    if not base:
        raise HTTPException(status_code=503, detail="evolution_go_not_configured")
    return base


def _go_env_fallback() -> Optional[Dict[str, str]]:
    """APOSENTADO em 04/08/2026 (SPEC-065). NÃO voltar a chamar.

    Devolve a instância GLOBAL do ambiente. Era usada como rede quando a
    corretora não tinha linha ativa — e essa rede cruzava tenant:

    📊 `EVOLUTION_GO_INSTANCE_NAME` tem como padrão `autobrokers-go-teste`, que é
    o nome da linha de attendance **da Resulta** (criada 15/07). A **AutoFleet
    não tem linha de attendance nenhuma** — que é o estado natural de qualquer
    corretora antes do primeiro pareamento.

    Resultado: a tela de WhatsApp de uma corretora resolvia para a instância de
    outra. Status, QR e **disconnect** inclusos.

    A função continua aqui, e só isso, porque o teste da SPEC-047 verifica o
    NOME dela para afirmar que o `env` de instância única virou legado. Apagá-la
    deixaria aquele teste verde por ausência — que é a pior forma de verde.
    O guarda de verdade é o `test_o_canal_de_uma_corretora_nao_e_de_outra`, que
    exige que ninguém a CHAME.
    """
    itoken = os.getenv("EVOLUTION_GO_INSTANCE_TOKEN") or ""
    iname = os.getenv("EVOLUTION_GO_INSTANCE_NAME") or "autobrokers-go-teste"
    if not itoken:
        return None
    return {"instance_name": iname, "instance_token": itoken}


def _go_instance_name(company_id: str, purpose: str) -> str:
    """Delega para `channel_identity` — o nome nasce num lugar só.

    📊 A versão anterior usava base de **12** caracteres e prefixo `ab-`, contra
    a base de **10** e o prefixo `ab-obs-` do orquestrador. As duas rodaram, e as
    duas instâncias existiam ao mesmo tempo para a mesma corretora:

        ab-obs-04b5cdbc04-1   (orquestrador — pareada, com acervo)
        ab-04b5cdbc04cd       (esta função — nunca pareada por ninguém)

    Nome de instância é identidade de acervo: `observer_number` é `_digits()` do
    nome. Dois nomes para uma corretora é um acervo esperando para se partir ao
    meio.
    """
    from app.services.whatsapp.channel_identity import nome_da_instancia

    return nome_da_instancia(company_id, purpose)


async def _go_company_channel(company_id: str, purpose: str = "attendance") -> Optional[Dict[str, str]]:
    """Instância GO DA corretora (linha ativa em integrations)."""
    supabase = get_supabase_client()

    def _q() -> list:
        return (
            supabase.client.table("integrations")
            .select("instance_id, token")
            .eq("company_id", company_id).eq("provider", "evolution-go")
            .eq("purpose", str(purpose or "attendance").strip().lower())
            .eq("is_active", True)
            .order("last_seen_at", desc=True).limit(1).execute().data or []
        )

    rows = await asyncio.to_thread(_q)
    if rows and rows[0].get("token"):
        from app.services.whatsapp.integration_secrets import prepare_integration_for_runtime

        row = prepare_integration_for_runtime(rows[0]) or rows[0]
        return {"instance_name": row["instance_id"], "instance_token": row["token"]}
    return None


async def _go_resolve(company_id: str, purpose: str = "attendance") -> Dict[str, str]:
    """Resolve a instância DA corretora. Sem linha ativa, ninguém é atendido.

    🔴 SPEC-065 — aqui morava um cruzamento de tenant, e ele estava armado.

    O código caía num `_go_env_fallback()` que devolve a instância GLOBAL
    (`EVOLUTION_GO_INSTANCE_NAME`, padrão `autobrokers-go-teste`) com o token do
    ambiente. 📊 Medido em 04/08/2026: esse nome é o da linha de **attendance da
    Resulta**, criada em 15/07. E a **AutoFleet não tem linha de attendance
    nenhuma**.

    Ou seja: abrir a tela de WhatsApp da AutoFleet resolvia para a instância da
    Resulta. Status, QR e — o pior — **disconnect** de um tenant operando o canal
    de outro. Bastava uma corretora sem linha ativa, que é o estado natural de
    toda corretora nova.

    CLAUDE.md §7 não admite exceção: nenhum dado atravessa tenants. Um fallback
    que escolhe a instância de outra empresa quando não acha a sua não é
    tolerância a falha — é a falha.

    Sem linha ativa agora é 404 explícito, para os dois propósitos. A tela lê
    isso como "não pareado" e oferece o QR, que é exatamente o que deve
    acontecer com quem ainda não pareou.
    """
    row = await _go_company_channel(company_id, purpose)
    if row:
        return row
    # Os códigos vão LITERAIS, não montados por f-string: é por eles que se
    # procura num log de produção às duas da manhã, e string que só existe
    # depois de interpolada não aparece em busca nenhuma.
    if str(purpose or "attendance").strip().lower() == "observer":
        raise HTTPException(status_code=404, detail="observer_channel_not_paired")
    raise HTTPException(status_code=404, detail="attendance_channel_not_paired")


async def _go_get(company_id: str, path: str, purpose: str = "attendance") -> Dict[str, Any]:
    cfg = await _go_resolve(company_id, purpose)
    async with httpx.AsyncClient(timeout=_TIMEOUT, base_url=_go_base()) as client:
        res = await client.get(path, headers={"apikey": cfg["instance_token"]})
        if res.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"evolution_go_http_{res.status_code}")
        return res.json() if res.content else {}


async def _go_status_payload(company_id: str, purpose: str = "attendance") -> Dict[str, Any]:
    j = await _go_get(company_id, "/instance/status", purpose)
    data = j.get("data") if isinstance(j.get("data"), dict) else {}
    logged_in = bool(data.get("LoggedIn") or data.get("loggedIn"))
    connected_ws = bool(data.get("Connected") or data.get("connected"))
    state = "open" if logged_in else ("connecting" if connected_ws else "close")
    return {"state": state, "connected": logged_in}


async def _go_setup(company_id: str, payload: "ChannelSetupPayload", public_url: str) -> Dict[str, Any]:
    """Setup do canal via Evolution GO — POR corretora.

    1) Reusa a instância da corretora se já existir (linha em integrations);
    2) senão CRIA `ab-<company>` via EVOLUTION_GO_GLOBAL_KEY com token próprio
       e modo cofre (readMessages/alwaysOnline/rejectCall off, ignora grupos/status);
    3) senão (sem global key) cai no fallback legado por env.
    Sempre reconfigura o webhook via /instance/connect; HISTORY_SYNC assinado —
    no pareamento fresco o histórico alimenta o Espelho/Atlas.
    """
    import secrets

    base = _go_base()
    purpose = str(payload.purpose or "attendance").strip().lower()
    existing = await _go_company_channel(company_id, purpose)
    global_key = os.getenv("EVOLUTION_GO_GLOBAL_KEY") or ""

    async def _go_find_by_name(client: httpx.AsyncClient, name: str) -> Optional[Dict[str, Any]]:
        if not global_key:
            return None
        r = await client.get("/instance/all", headers={"apikey": global_key})
        for row in (r.json() or {}).get("data", []) if r.status_code < 400 and r.content else []:
            if str(row.get("name") or "") == name:
                return row
        return None

    async def _go_create(client: httpx.AsyncClient, name: str, tok: str) -> Optional[str]:
        """Cria a instância. Devolve o token REAL se reusou uma que já existia.

        🔴 O DEFEITO QUE ISTO CONSERTA — medido em 17/08/2026.

        Quando a instância já existe COM telefone, este método (corretamente)
        não recria: apagar despareia a corretora. Mas ele devolvia `None`, e
        quem chamou seguia gravando no banco o `tok` que acabara de sortear —
        um token que **a instância nunca conheceu**.

        📊 A consequência, medida na Resulta: `integrations.token` tinha um
        valor e o Evolution GO tinha outro. Todo envio devolvia **HTTP 401**.
        O Auxiliar de Cobrança baixou 3 boletos reais três vezes seguidas e
        não conseguiu mandar nenhum. A tela de "Buscar grupos" falhava pelo
        mesmo motivo — mesma chave, mesmo 401.

        E o defeito é invisível pelo caminho normal: o INBOUND autentica pelo
        NOSSO webhook token, não por este. O canal parece "conectado", recebe
        mensagem, espelha conversa — e não consegue falar. Só quem tenta
        ENVIAR descobre, e até hoje ninguém tinha tentado (o agente de
        atendimento nunca foi ligado).
        """
        cr = await client.post(
            "/instance/create",
            headers={"apikey": global_key, "Content-Type": "application/json"},
            json={
                "name": name, "token": tok,
                "advancedSettings": {"readMessages": False, "alwaysOnline": False,
                                     "rejectCall": False, "ignoreGroups": True, "ignoreStatus": True},
            },
        )
        if instancia_ja_existe(cr.status_code, getattr(cr, "text", "")):
            # Instância existe no GO sem linha no banco (setup interrompido).
            # AUTO-CURA: apaga e recria limpa — sem beco sem saída pro corretor.
            ghost = await _go_find_by_name(client, name)
            # ⚠️ SÓ casca vazia. Até 06/08/2026 esta condição era
            # `if ghost and ghost.get("id")` — sem olhar o `jid`. Um DELETE numa
            # instância COM telefone **despareia a corretora**: o WhatsApp perde
            # o dispositivo vinculado, a captura morre e a atendente precisa
            # escanear QR de novo, sem ninguém ter pedido isso.
            #
            # A bomba nunca explodiu por sorte de código de status: 📊 o provedor
            # devolve 500 para nome repetido, e o `in (409, 422)` acima nunca era
            # verdadeiro. Corrigir o status SEM corrigir a guarda teria armado o
            # gatilho — por isso as duas mudanças andam juntas, nesta linha.
            #
            # Quem tem telefone e precisa trocar usa o caminho explícito:
            # `PairingOrchestrator.liberar_para_novo_numero`, que preserva o NOME
            # (e portanto o acervo) e é acionado por uma pessoa, não por retry.
            if ghost and ghost.get("id") and not str(ghost.get("jid") or "").strip():
                await client.delete(f"/instance/delete/{ghost['id']}", headers={"apikey": global_key})
                cr = await client.post(
                    "/instance/create",
                    headers={"apikey": global_key, "Content-Type": "application/json"},
                    json={"name": name, "token": tok,
                          "advancedSettings": {"readMessages": False, "alwaysOnline": False,
                                               "rejectCall": False, "ignoreGroups": True, "ignoreStatus": True}},
                )
            elif ghost:
                # Existe E tem telefone: é a instância CERTA desta corretora, já
                # pareada. Não é erro — é o caso normal de quem volta à tela.
                # Tratar como falha dava o beco sem saída de 03/08 (§6 do
                # relatório): "Desconectado" na tela e `configuration_error` em
                # todo retry, com o próprio código recusando a única saída.
                #
                # 🔴 E o TOKEN DELA VOLTA JUNTO. Reusar a instância e gravar um
                # token novo no banco é o que produzia o HTTP 401 em todo envio
                # (ver a docstring). O token da instância é a única chave que o
                # Evolution aceita; gerar outro não a substitui, só a perde.
                token_real = str(ghost.get("token") or "").strip()
                if token_real:
                    logger.info("[WA CHANNEL GO] instancia %s reusada — adotando o "
                                "token DELA (o gerado aqui seria recusado)", name)
                    return token_real
                # Sem o token na resposta do provedor não há como falar com ela.
                # Falhar aqui é melhor que gravar uma chave que não abre nada e
                # descobrir três semanas depois, no primeiro envio.
                logger.error("[WA CHANNEL GO] instancia %s existe mas o provedor nao "
                             "devolveu o token dela — o canal ficaria mudo", name)
                raise HTTPException(
                    status_code=502,
                    detail="evolution_go_instancia_sem_token:"
                           "a instancia ja existe e o provedor nao devolveu a chave dela")
        if cr.status_code >= 400:
            raise HTTPException(status_code=502,
                                detail=f"evolution_go_create_failed:http_{cr.status_code}:{(cr.text or '')[:100]}")
        return None

    token, token_hash, token_prefix = new_webhook_credentials()
    webhook_url = build_webhook_url(public_url, "evolution-go", token)
    # Eventos do GO são UPPERCASE (event_types.go) — "Message" era descartado em
    # silêncio e a instância ficava SEM inscrição. HISTORY_SYNC: no pareamento
    # fresco o histórico vira matéria-prima do Espelho (SPEC-040) e do Atlas.
    #
    # A lista mora em `corpo_do_connect` porque quatro lugares a montavam e os
    # quatro discordavam — este mandava três eventos, o orquestrador quatro, e o
    # reconector nenhum. Divergência em corpo que o provedor GRAVA POR CIMA não é
    # estilo: é o canal de uma corretora perdendo inscrição sem ninguém saber.
    connect_body = corpo_do_connect(webhook_url)

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, base_url=base) as client:
            if existing:
                instance, inst_token = existing["instance_name"], existing["instance_token"]
            elif global_key:
                instance = _go_instance_name(company_id, purpose)
                inst_token = secrets.token_hex(16)
                # 🔴 Se a instancia ja existia, o token DELA volta aqui e
                # substitui o que sorteamos. Gravar o sorteado seria gravar
                # uma chave que o Evolution recusa (HTTP 401 em todo envio).
                _token_da_instancia = await _go_create(client, instance, inst_token)
                if _token_da_instancia:
                    inst_token = _token_da_instancia
            else:
                # 🔴 SPEC-065 — aqui o attendance caía na instância GLOBAL do
                # ambiente e, logo abaixo, esse nome era GRAVADO na linha da
                # corretora. Duas corretoras diferentes acabariam apontando para
                # a MESMA instância do Evolution Go — um WhatsApp só, servindo
                # dois tenants, com as conversas de ambos no mesmo lugar.
                #
                # Sem a chave global não há como criar instância própria, e
                # instância própria é a única forma correta. Então é 503 para os
                # DOIS propósitos, e a mensagem diz o que configurar.
                raise HTTPException(
                    status_code=503,
                    detail="evolution_go_not_configured (defina EVOLUTION_GO_GLOBAL_KEY)",
                )

            res = await client.post("/instance/connect",
                                    headers={"apikey": inst_token, "Content-Type": "application/json"},
                                    json=connect_body)
            if res.status_code in (401, 404) and existing and global_key:
                # Linha aponta p/ instância que não existe mais no GO (zumbi).
                # AUTO-CURA: recria com token novo e reconecta.
                logger.warning(f"[WA CHANNEL GO] linha zumbi (instance={instance}) — recriando")
                inst_token = secrets.token_hex(16)
                # 🔴 Se a instancia ja existia, o token DELA volta aqui e
                # substitui o que sorteamos. Gravar o sorteado seria gravar
                # uma chave que o Evolution recusa (HTTP 401 em todo envio).
                _token_da_instancia = await _go_create(client, instance, inst_token)
                if _token_da_instancia:
                    inst_token = _token_da_instancia
                res = await client.post("/instance/connect",
                                        headers={"apikey": inst_token, "Content-Type": "application/json"},
                                        json=connect_body)
            if res.status_code >= 400:
                logger.error(f"[WA CHANNEL GO] connect failed http={res.status_code} body={(res.text or '')[:120]}")
                raise HTTPException(status_code=502, detail=f"evolution_go_connect_failed:http_{res.status_code}")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"evolution_go_unreachable:{type(e).__name__}") from e

    supabase = get_supabase_client()

    def _attendant_id() -> Optional[str]:
        if payload.agent_id:
            return payload.agent_id
        try:
            res = (
                supabase.client.table("agents").select("id").eq("company_id", company_id)
                .eq("agent_role", "attendance").limit(1).execute()
            )
            return str(res.data[0]["id"]) if res.data else None
        except Exception:  # noqa: BLE001
            return None

    agent_id = _attendant_id()

    def _upsert() -> None:
        from app.services.whatsapp.integration_secrets import prepare_integration_for_storage

        record = prepare_integration_for_storage({
            "company_id": company_id,
            "identifier": instance,
            "purpose": purpose,
            "provider": "evolution-go",
            "base_url": base,
            "instance_id": instance,
            "token": inst_token,
            "webhook_token_hash": token_hash,
            "webhook_token_prefix": token_prefix,
            "alert_target": {"number": payload.alert_number} if payload.alert_number else None,
            "channel_status": "connecting",
            "is_active": True,
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
        })
        if agent_id:
            record["agent_id"] = agent_id
        existing = (
            supabase.client.table("integrations").select("id").eq("company_id", company_id)
            .eq("provider", "evolution-go").eq("instance_id", instance).limit(1).execute()
        )
        if existing.data:
            supabase.client.table("integrations").update(record).eq("id", existing.data[0]["id"]).execute()
        else:
            supabase.client.table("integrations").insert(record).execute()
        # Uma função = um canal ativo: instâncias GO antigas desta mesma função
        # saem de cena (evita rotear/enviar por dois números ao mesmo tempo).
        supabase.client.table("integrations").update({"is_active": False}) \
            .eq("company_id", company_id).eq("provider", "evolution-go") \
            .eq("purpose", purpose).neq("instance_id", instance).execute()

    try:
        await asyncio.to_thread(_upsert)
    except Exception as e:  # noqa: BLE001
        logger.error(f"[WA CHANNEL GO] integração NÃO gravada: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Webhook configurado no GO, mas a integração não foi gravada no banco.")
    logger.info(f"[WA CHANNEL GO] setup ok instance={instance} token_prefix={token_prefix}")
    return {"ok": True, "instance": instance, "webhook_token_prefix": token_prefix, "status": "connecting", "provider": "evolution-go"}


class ChannelSetupPayload(BaseModel):
    company_id: str
    agent_id: Optional[str] = None
    alert_number: Optional[str] = None  # S17-3: destino do alerta de desconexão
    purpose: str = "attendance"  # S17-12: multi-número por corretora (attendance | auxiliary:<slug> | dispatch)


class PairingPayload(BaseModel):
    company_id: str
    purpose: str = "observer"
    method: str = "qr"
    phone_number: Optional[str] = None
    correlation_id: Optional[str] = None


def _pairing_http_error(exc: Exception) -> HTTPException:
    from app.services.whatsapp.pairing_orchestrator import (
        PairingConflictError,
        PairingNotFoundError,
    )

    if isinstance(exc, PairingNotFoundError):
        return HTTPException(status_code=404, detail="pairing_not_found")
    if isinstance(exc, PairingConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=503, detail="pairing_unavailable")


@router.post("/api/whatsapp-channel/pairing")
async def whatsapp_channel_pairing(
    payload: PairingPayload,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
    x_correlation_id: Optional[str] = Header(default=None, alias="X-Correlation-ID"),
) -> Dict[str, Any]:
    """Inicia uma única tentativa explícita de QR ou código de pareamento."""
    _require_internal_key(x_autobrokers_internal_key)
    from app.services.whatsapp.pairing_orchestrator import get_pairing_orchestrator

    try:
        return await get_pairing_orchestrator().start(
            payload.company_id,
            payload.purpose,
            correlation_id=x_correlation_id or payload.correlation_id,
            method=payload.method,
            phone_number=payload.phone_number,
        )
    except Exception as exc:  # noqa: BLE001
        raise _pairing_http_error(exc) from exc


@router.get("/api/whatsapp-channel/pairing/{attempt_id}")
async def whatsapp_channel_pairing_state(
    attempt_id: str,
    company_id: str,
    purpose: str = "observer",
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
) -> Dict[str, Any]:
    _require_internal_key(x_autobrokers_internal_key)
    from app.services.whatsapp.pairing_orchestrator import get_pairing_orchestrator

    try:
        return await get_pairing_orchestrator().get(company_id, purpose, attempt_id)
    except Exception as exc:  # noqa: BLE001
        raise _pairing_http_error(exc) from exc


@router.post("/api/whatsapp-channel/pairing/{attempt_id}/retry")
async def whatsapp_channel_pairing_retry(
    attempt_id: str,
    payload: PairingPayload,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
    x_correlation_id: Optional[str] = Header(default=None, alias="X-Correlation-ID"),
) -> Dict[str, Any]:
    _require_internal_key(x_autobrokers_internal_key)
    from app.services.whatsapp.pairing_orchestrator import get_pairing_orchestrator

    try:
        return await get_pairing_orchestrator().retry(
            payload.company_id,
            payload.purpose,
            attempt_id,
            x_correlation_id or payload.correlation_id or str(__import__("uuid").uuid4()),
        )
    except Exception as exc:  # noqa: BLE001
        raise _pairing_http_error(exc) from exc


@router.post("/api/whatsapp-channel/pairing/{attempt_id}/cancel")
async def whatsapp_channel_pairing_cancel(
    attempt_id: str,
    payload: PairingPayload,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
) -> Dict[str, Any]:
    _require_internal_key(x_autobrokers_internal_key)
    from app.services.whatsapp.pairing_orchestrator import get_pairing_orchestrator

    try:
        return await get_pairing_orchestrator().cancel(
            payload.company_id, payload.purpose, attempt_id
        )
    except Exception as exc:  # noqa: BLE001
        raise _pairing_http_error(exc) from exc


@router.post("/api/whatsapp-channel/pairing/liberar-numero")
async def whatsapp_channel_liberar_numero(
    payload: PairingPayload,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
) -> Dict[str, Any]:
    """Solta a linha do telefone atual para que OUTRO possa parear.

    ⚠️ Encerra a sessão do número que está pareado agora. É o "trocar número" da
    tela, e exige confirmação lá — aqui não há como saber se o clique foi
    consciente.

    Existe porque não havia saída: 📊 nada no Evolution Go limpa o `jid` de uma
    instância, e com `jid` preenchido o whatsmeow reconecta em vez de emitir QR.
    A corretora ficava presa ao primeiro número que pareou, para sempre.

    O nome da instância é preservado — é dele que sai o `observer_number`, metade
    da chave de deduplicação de 69.150 transcrições. Ver
    `PairingOrchestrator.liberar_para_novo_numero`.
    """
    _require_internal_key(x_autobrokers_internal_key)
    from app.services.whatsapp.pairing_orchestrator import get_pairing_orchestrator

    try:
        return await get_pairing_orchestrator().liberar_para_novo_numero(
            payload.company_id, payload.purpose
        )
    except Exception as exc:  # noqa: BLE001
        raise _pairing_http_error(exc) from exc


@router.get("/api/admin/whatsapp-channel/diagnostics")
async def whatsapp_pairing_admin_diagnostics(
    company_id: str,
    purpose: str = "observer",
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
) -> Dict[str, Any]:
    """Diagnóstico sem credenciais para suporte de uma tentativa específica."""
    _require_internal_key(x_autobrokers_internal_key)
    from app.services.whatsapp.pairing_orchestrator import (
        get_pairing_orchestrator,
        public_pairing_state,
    )

    orchestrator = get_pairing_orchestrator()
    redis = await orchestrator._redis()  # noqa: SLF001 - superfície admin interna
    current = orchestrator._decode(await redis.get(orchestrator._key(company_id, purpose)))  # noqa: SLF001
    health: Dict[str, Any] = {"reachable": False, "version": None}
    try:
        async with httpx.AsyncClient(timeout=10.0, base_url=orchestrator.base_url) as client:
            response = await client.get("/server/ok")
            payload = response.json() if response.status_code < 400 and response.content else {}
            health = {
                "reachable": response.status_code < 500,
                "version": payload.get("version"),
                "http_status": response.status_code,
            }
    except httpx.HTTPError:
        health["error"] = "provider_unavailable"
    integration = await orchestrator._integration(company_id, purpose)  # noqa: SLF001
    return {
        "ok": True,
        "provider": health,
        "integration_present": bool(integration),
        "purpose": purpose,
        "attempt": public_pairing_state(current or {}),
    }


@router.get("/api/whatsapp-channel/diagnostics")
async def whatsapp_channel_diagnostics(
    company_id: str,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
) -> Dict[str, Any]:
    """Diagnóstico transparente do canal (SPEC-017): mostra EXATAMENTE o que
    falta/quebrou, sem expor segredos. Usado pelo card do dashboard em erro."""
    _require_internal_key(x_autobrokers_internal_key)
    base_url = (os.getenv("EVOLUTION_BASE_URL") or "").rstrip("/")
    api_key = os.getenv("EVOLUTION_API_KEY") or ""
    public_url = _public_backend_url()
    out: Dict[str, Any] = {
        "evolution_base_url_set": bool(base_url),
        "evolution_api_key_set": bool(api_key),
        "public_backend_url_set": bool(public_url),
        "evolution_reachable": False,
        "evolution_http_status": None,
        "instance": _instance_name(company_id),
        "instance_state": None,
        "error": None,
    }
    if not base_url or not api_key:
        out["error"] = "envs_ausentes"
        return out
    headers = {"apikey": api_key}
    try:
        async with httpx.AsyncClient(timeout=10.0, base_url=base_url) as client:
            root = await client.get("/", headers=headers)
            out["evolution_http_status"] = root.status_code
            out["evolution_reachable"] = root.status_code < 500
            try:
                info = root.json() if root.content else {}
                out["evolution_version"] = str(info.get("version") or "")[:20]
            except Exception:  # noqa: BLE001
                pass
            state_res = await client.get(f"/instance/connectionState/{out['instance']}", headers=headers)
            if state_res.status_code < 400 and state_res.content:
                data = state_res.json()
                inner = data.get("instance") if isinstance(data.get("instance"), dict) else data
                out["instance_state"] = str(inner.get("state") or inner.get("connectionStatus") or "")[:30]
            else:
                out["instance_state"] = f"http_{state_res.status_code}"
    except httpx.HTTPError as e:
        out["error"] = f"evolution_unreachable:{type(e).__name__}"

    # Sem linha em integrations o webhook NÃO roteia — o diagnóstico tem que
    # gritar isso (foi o que escondeu o canal mudo por 2 dias).
    try:
        from app.core.database import get_supabase_client

        supabase = get_supabase_client()

        def _row():
            return (
                supabase.client.table("integrations")
                .select("id, agent_id, is_active, webhook_token_prefix")
                .eq("company_id", company_id)
                .eq("provider", "evolution")
                .eq("instance_id", out["instance"])
                .limit(1)
                .execute()
            )

        res = await asyncio.to_thread(_row)
        row = res.data[0] if res.data else None
        out["integration_row"] = bool(row)
        out["integration_agent_bound"] = bool(row and row.get("agent_id"))
        if not row:
            out["error"] = out["error"] or "integracao_ausente_no_banco"
    except Exception as e:  # noqa: BLE001
        out["integration_row"] = None
        logger.warning(f"[WA CHANNEL] diagnostics row check failed: {type(e).__name__}")
    return out


@router.post("/api/whatsapp-channel/setup")
async def whatsapp_channel_setup(
    payload: ChannelSetupPayload,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
) -> Dict[str, Any]:
    _require_internal_key(x_autobrokers_internal_key)
    company_id = (payload.company_id or "").strip()
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id required")
    public_url = _public_backend_url()
    if not public_url:
        raise HTTPException(status_code=503, detail="public_backend_url_not_configured")

    if _go_enabled():
        return await _go_setup(company_id, payload, public_url)

    platform = _evolution_platform()
    instance = _instance_name(company_id, payload.purpose)
    token, token_hash, token_prefix = new_webhook_credentials()
    webhook_url = build_webhook_url(public_url, "evolution", token)

    def _safe_snippet(res: httpx.Response) -> str:
        try:
            return (res.text or "")[:120].replace("\n", " ")
        except Exception:  # noqa: BLE001
            return ""

    headers = {"apikey": platform["api_key"], "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, base_url=platform["base_url"]) as client:
            # 1) Garante a instância (idempotente: 403/409 = já existe).
            create = await client.post(
                "/instance/create",
                headers=headers,
                json={
                    "instanceName": instance,
                    "qrcode": True,
                    "integration": "WHATSAPP-BAILEYS",
                    # Cinto e suspensório (v2.3.x): webhook já na criação.
                    "webhook": {
                        "url": webhook_url,
                        "byEvents": False,
                        "base64": True,  # F1: midia decodificada no proprio webhook
                        "events": ["MESSAGES_UPSERT", "CONNECTION_UPDATE"],
                    },
                },
            )
            if create.status_code >= 400 and create.status_code not in (403, 409):
                logger.error(f"[WA CHANNEL] instance create failed http={create.status_code} body={_safe_snippet(create)}")
                raise HTTPException(
                    status_code=502,
                    detail=f"evolution_instance_create_failed:http_{create.status_code}:{_safe_snippet(create)}",
                )

            # 2) Configura o webhook da instância para a NOSSA rota com token.
            webhook_body = {
                "webhook": {
                    "enabled": True,
                    "url": webhook_url,
                    "events": ["MESSAGES_UPSERT", "CONNECTION_UPDATE"],
                    "byEvents": False,
                    "base64": True,  # F1: midia decodificada no proprio webhook
                }
            }
            wh = await client.post(f"/webhook/set/{instance}", headers=headers, json=webhook_body)
            if wh.status_code >= 400:
                # fallback formato flat (versões antigas do Evolution)
                wh2 = await client.post(
                    f"/webhook/set/{instance}",
                    headers=headers,
                    json={"enabled": True, "url": webhook_url, "events": ["MESSAGES_UPSERT", "CONNECTION_UPDATE"]},
                )
                if wh2.status_code >= 400:
                    logger.error(f"[WA CHANNEL] webhook set failed http={wh.status_code}/{wh2.status_code} body={_safe_snippet(wh2)}")
                    raise HTTPException(
                        status_code=502,
                        detail=f"evolution_webhook_set_failed:http_{wh.status_code}/{wh2.status_code}:{_safe_snippet(wh2)}",
                    )
    except httpx.HTTPError as e:
        logger.error(f"[WA CHANNEL] evolution unreachable: {type(e).__name__}")
        raise HTTPException(status_code=502, detail=f"evolution_unreachable:{type(e).__name__}") from e

    # 3) Upsert da integração (hash do token; plaintext NUNCA persiste).
    supabase = get_supabase_client()

    def _resolve_attendant_agent_id() -> Optional[str]:
        """SPEC-017 P2: sem agent_id explícito, vincula o ATENDENTE da corretora
        (role attendance) — nunca o Core — para o canal do segurado."""
        if payload.agent_id:
            return payload.agent_id
        try:
            res = (
                supabase.client.table("agents")
                .select("id, is_active")
                .eq("company_id", company_id)
                .eq("agent_role", "attendance")
                .eq("is_active", True)
                .limit(1)
                .execute()
            )
            if res.data:
                return str(res.data[0]["id"])
            # fallback: atendente existe mas está inativo — ainda assim é o correto
            res2 = (
                supabase.client.table("agents")
                .select("id")
                .eq("company_id", company_id)
                .eq("agent_role", "attendance")
                .limit(1)
                .execute()
            )
            return str(res2.data[0]["id"]) if res2.data else None
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[WA CHANNEL] attendant agent lookup failed: {type(e).__name__}")
            return None

    attendant_agent_id = _resolve_attendant_agent_id()

    def _upsert() -> None:
        record = {
            "company_id": company_id,
            # NOT NULL no schema; telefone real só existe após parear — a
            # instância identifica o canal até lá.
            "identifier": instance,
            "purpose": str(payload.purpose or "attendance").strip().lower(),
            "provider": "evolution",
            "base_url": platform["base_url"],
            "instance_id": instance,
            "token": platform["api_key"],
            "webhook_token_hash": token_hash,
            "webhook_token_prefix": token_prefix,
            "alert_target": {"number": payload.alert_number} if payload.alert_number else None,
            "channel_status": "connecting",
            "is_active": True,
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
        }
        if attendant_agent_id:
            record["agent_id"] = attendant_agent_id
        existing = (
            supabase.client.table("integrations")
            .select("id")
            .eq("company_id", company_id)
            .eq("provider", "evolution")
            .eq("instance_id", instance)
            .limit(1)
            .execute()
        )
        if existing.data:
            supabase.client.table("integrations").update(record).eq("id", existing.data[0]["id"]).execute()
        else:
            supabase.client.table("integrations").insert(record).execute()

    # FAIL-LOUD: sem a linha em integrations o webhook não roteia NADA — se o
    # banco recusar (coluna/constraint), o setup TEM que falhar visível, nunca
    # deixar a instância de pé sem rota (bug que escondeu o canal por 2 dias).
    try:
        await asyncio.to_thread(_upsert)
    except Exception as e:  # noqa: BLE001
        logger.error(f"[WA CHANNEL] integração NÃO gravada: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Instância criada, mas a integração não foi gravada no banco ({type(e).__name__}). O canal NÃO vai responder até corrigir.",
        )
    logger.info(f"[WA CHANNEL] setup ok instance={instance} token_prefix={token_prefix}")
    return {"ok": True, "instance": instance, "webhook_token_prefix": token_prefix, "status": "connecting"}


@router.get("/api/whatsapp-channel/qr")
async def whatsapp_channel_qr(
    company_id: str,
    purpose: str = "attendance",
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
) -> Dict[str, Any]:
    _require_internal_key(x_autobrokers_internal_key)
    if _go_enabled():
        cfg = await _go_resolve(company_id, purpose)
        j = await _go_get(company_id, "/instance/qr", purpose)
        d = j.get("data") if isinstance(j.get("data"), dict) else j
        raw = str(d.get("QRCode") or d.get("qrcode") or d.get("qr") or d.get("base64") or "")
        return {
            "ok": bool(raw), "instance": cfg["instance_name"],
            "qr_base64": raw or None, "qr_text": d.get("code") if not raw else None,
            "raw_state": d.get("state"), "error_code": d.get("errorCode"),
            "passkey_stage": d.get("passkeyStage"),
            "passkey_open_url": d.get("passkeyOpenUrl"),
            "passkey_code": d.get("passkeyCode"),
            "passkey_error": d.get("passkeyError"),
            "expires_at": d.get("expiresAt"),
        }
    platform = _evolution_platform()
    instance = _instance_name(company_id)
    headers = {"apikey": platform["api_key"]}
    async with httpx.AsyncClient(timeout=_TIMEOUT, base_url=platform["base_url"]) as client:
        res = await client.get(f"/instance/connect/{instance}", headers=headers)
        if res.status_code >= 400:
            raise HTTPException(status_code=502, detail="evolution_qr_failed")
        data = res.json() if res.content else {}
    qr = data.get("base64") or (data.get("qrcode") or {}).get("base64")
    qr_text = data.get("code") or (data.get("qrcode") or {}).get("code")
    # v2.3.x: base64 é a imagem; 'code' é o TEXTO do QR (não renderizável como img).
    return {
        "ok": bool(qr or qr_text),
        "instance": instance,
        "qr_base64": qr,
        "qr_text": qr_text if not qr else None,
        "raw_state": data.get("state"),
    }


@router.post("/api/whatsapp-channel/disconnect")
async def whatsapp_channel_disconnect(
    payload: Dict[str, Any],
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
) -> Dict[str, Any]:
    """Desconecta (logout) a instância Evolution da corretora — founder 14/07:
    sem este botão não há como tirar o número da Evolution pelo dashboard.
    Logout preserva a instância (reconectar = novo QR); não deleta nada."""
    _require_internal_key(x_autobrokers_internal_key)
    company_id = str(payload.get("company_id") or "").strip()
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id_required")
    if _go_enabled():
        # SPEC-050: desconectar DE VERDADE. O logout do GO nem sempre limpa a
        # sessão registrada (jid fica; "Reconnecting") — e sessão registrada
        # NUNCA emite QR novo (foi o "Gerar QR não gera" do founder). Se a
        # sessão persistir, apagamos a instância no GO (chave global) e
        # desativamos a linha: o próximo "Gerar QR" cria instância limpa.
        purpose = str(payload.get("purpose") or "attendance").strip().lower()
        cfg = await _go_resolve(company_id, purpose)
        global_key = os.getenv("EVOLUTION_GO_GLOBAL_KEY") or ""
        async with httpx.AsyncClient(timeout=_TIMEOUT, base_url=_go_base()) as client:
            try:
                await client.delete("/instance/logout", headers={"apikey": cfg["instance_token"]})
            except httpx.HTTPError:
                pass  # a limpeza abaixo resolve mesmo sem logout
            still_registered = False
            if global_key:
                try:
                    r = await client.get("/instance/all", headers={"apikey": global_key})
                    for row in (r.json() or {}).get("data", []) if r.status_code < 400 and r.content else []:
                        if str(row.get("name") or "") == cfg["instance_name"] and str(row.get("jid") or ""):
                            still_registered = True
                            if row.get("id"):
                                await client.delete(f"/instance/delete/{row['id']}", headers={"apikey": global_key})
                            break
                except httpx.HTTPError:
                    pass
        # 🔴 SPEC-065 — a gravação SAIU de dentro do `if still_registered`.
        #
        # Ela estava lá dentro, e por isso o botão "Desconectar" mentia: quando o
        # `logout` já tinha limpado a sessão antes do `GET /instance/all`,
        # `still_registered` era False, **o banco não era tocado**, e a linha
        # continuava `is_active=True` — com o webhook aceitando evento de um
        # canal que a tela dizia estar desligado.
        #
        # 📊 Medido em 04/08/2026, depois de o Founder clicar em desconectar em
        # tudo: AMANDUS e AutoFleet ficaram `retired`+`is_active=false`; a
        # Resulta ficou `disconnected`+`is_active=TRUE`. **Mesmo botão, dois
        # resultados** — e o dele foi o que continuou capturando.
        #
        # Apagar a instância no provedor É condicional (só existe o que existe).
        # Aposentar a linha, não: o usuário mandou desligar. Se o provedor já
        # tinha esquecido a sessão, com mais razão ainda.
        supabase = get_supabase_client()

        def _retire() -> None:
            supabase.client.table("integrations").update({
                "is_active": False,
                "channel_status": "retired",
                # `updated_at` não tem trigger nesta tabela (medido), e sem ele
                # a data da linha continua sendo a do PAREAMENTO. Foi por isso
                # que a reconstrução do incidente de 29/07 leu a data errada.
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("company_id", company_id).eq("provider", "evolution-go") \
                .eq("instance_id", cfg["instance_name"]).execute()

        try:
            await asyncio.to_thread(_retire)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[WA CHANNEL GO] retire falhou: {type(e).__name__}")
        logger.info("[WA CHANNEL GO] instância %s desligada (sessão no provedor: %s)",
                    cfg["instance_name"], "removida" if still_registered else "já não existia")
        return {"ok": True, "instance": cfg["instance_name"], "state": "close"}
    platform = _evolution_platform()
    instance = _instance_name(company_id)
    headers = {"apikey": platform["api_key"]}
    async with httpx.AsyncClient(timeout=_TIMEOUT, base_url=platform["base_url"]) as client:
        res = await client.delete(f"/instance/logout/{instance}", headers=headers)
        if res.status_code >= 400:
            # v2 usa DELETE /instance/logout/{instance}; se indisponível, tenta restart-less close
            raise HTTPException(status_code=502, detail="evolution_logout_failed")
    return {"ok": True, "instance": instance, "state": "close"}


async def _numero_pareado_da_linha(company_id: str, purpose: str = "observer") -> Optional[str]:
    """QUAL número está pareado nesta linha — mascarado. ``None`` se nenhum.

    Pedido do Founder, 06/08/2026: *"é importante que apareça pra nunca mais
    gerar confusão do número que está pareado"*.

    A confusão foi real e cara: a linha da Resulta esteve pareada com um DDD 47
    (o celular do Founder) enquanto todos acreditavam ser o da atendente, que é
    DDD 48 — e passaram-se dias de investigação sem que nada na tela pudesse
    desmentir isso. 📊 O dado já estava no banco (`paired_phone_e164`); só não
    tinha por onde sair.

    Lê a linha DESLIGADA também: quem desconectou continua tendo o direito de
    saber qual número estava ali. Desconectar é pausa, não amnésia.

    Mascarado sempre — é a linha de trabalho de uma pessoa real (CLAUDE.md
    §13.3). Quem já conhece o número o reconhece; quem não conhece não passa a
    conhecer.
    """
    from app.services.whatsapp.numero_pareado import mascarar

    supabase = get_supabase_client()

    def _q() -> list:
        return (
            supabase.client.table("integrations").select("paired_phone_e164")
            .eq("company_id", company_id).eq("purpose", purpose)
            .eq("provider", "evolution-go")
            .order("last_seen_at", desc=True).limit(1).execute().data or []
        )

    try:
        rows = await asyncio.to_thread(_q)
    except Exception:  # noqa: BLE001 — a tela não cai por causa do número
        return None
    bruto = str((rows[0] if rows else {}).get("paired_phone_e164") or "").strip()
    return mascarar(bruto) if bruto else None


async def _channel_alert_info(company_id: str, purpose: str = "attendance") -> Dict[str, Any]:
    """Config atual do AVISO de queda (SPEC-049) — número próprio ou o mesmo
    destino do suporte humano/dossiês."""
    supabase = get_supabase_client()

    def _q() -> list:
        return (
            supabase.client.table("integrations").select("alert_target")
            .eq("company_id", company_id).eq("purpose", purpose).eq("is_active", True)
            .order("last_seen_at", desc=True).limit(1).execute().data or []
        )

    rows = await asyncio.to_thread(_q)
    target = rows[0].get("alert_target") if rows else None
    if isinstance(target, str):
        import json as _json

        try:
            target = _json.loads(target)
        except Exception:  # noqa: BLE001
            target = {"number": target}
    if not isinstance(target, dict):
        return {"mode": None, "number": None}
    if target.get("use_support_destination"):
        return {"mode": "support", "number": None}
    number = str(target.get("number") or "").strip()
    return {"mode": "number" if number else None, "number": number or None}


class ChannelAlertPayload(BaseModel):
    company_id: str
    purpose: str = "attendance"
    # mode: 'number' (alert_number obrigatório) | 'support' (grupo/nº do
    # suporte humano — o mesmo dos dossiês) | 'off'
    mode: str
    alert_number: Optional[str] = None


@router.post("/api/whatsapp-channel/set-alert")
async def whatsapp_channel_set_alert(
    payload: ChannelAlertPayload,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
) -> Dict[str, Any]:
    """SPEC-049 — configura/edita o AVISO de queda a qualquer momento (a opção
    nunca some do dashboard). O número de aviso NUNCA pode ser o número pareado."""
    _require_internal_key(x_autobrokers_internal_key)
    company_id = (payload.company_id or "").strip()
    mode = (payload.mode or "").strip().lower()
    if not company_id or mode not in ("number", "support", "off"):
        raise HTTPException(status_code=400, detail="parametros_invalidos")

    target: Optional[Dict[str, Any]] = None
    if mode == "number":
        digits = "".join(ch for ch in str(payload.alert_number or "") if ch.isdigit())
        if len(digits) < 10 or len(digits) > 15:
            raise HTTPException(status_code=400, detail="numero_invalido")
        target = {"number": digits}
    elif mode == "support":
        target = {"use_support_destination": True}

    supabase = get_supabase_client()
    purpose = (payload.purpose or "attendance").strip().lower()

    def _rows() -> list:
        return (
            supabase.client.table("integrations").select("id, identifier")
            .eq("company_id", company_id).eq("purpose", purpose).eq("is_active", True)
            .limit(5).execute().data or []
        )

    rows = await asyncio.to_thread(_rows)
    if not rows:
        raise HTTPException(status_code=404, detail="canal_nao_configurado (gere o QR primeiro)")
    if mode == "number" and target:
        for row in rows:
            paired = "".join(ch for ch in str(row.get("identifier") or "") if ch.isdigit())
            if paired and paired == target["number"]:
                raise HTTPException(status_code=400, detail="numero_igual_ao_pareado (use OUTRO número)")

    def _update() -> None:
        for row in rows:
            supabase.client.table("integrations").update({"alert_target": target}).eq("id", row["id"]).execute()

    await asyncio.to_thread(_update)
    return {"ok": True, "alert": await _channel_alert_info(company_id, purpose)}


@router.get("/api/whatsapp-channel/status")
async def whatsapp_channel_status(
    company_id: str,
    purpose: str = "attendance",
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
) -> Dict[str, Any]:
    _require_internal_key(x_autobrokers_internal_key)
    alert = await _channel_alert_info(company_id, purpose)
    numero = await _numero_pareado_da_linha(company_id, purpose)
    if _go_enabled():
        if str(purpose or "attendance").strip().lower() == "observer":
            company_channel = await _go_company_channel(company_id, purpose)
            if not company_channel:
                return {
                    "ok": True,
                    "instance": None,
                    "state": "close",
                    "connected": False,
                    "unpaired": True,
                    "alert": alert,
                    "paired_phone": numero,
                }
        cfg = await _go_resolve(company_id, purpose)
        st = await _go_status_payload(company_id, purpose)
        return {"ok": True, "instance": cfg["instance_name"], "alert": alert,
                "paired_phone": numero, **st}
    platform = _evolution_platform()
    instance = _instance_name(company_id)
    headers = {"apikey": platform["api_key"]}
    state = "unknown"
    async with httpx.AsyncClient(timeout=_TIMEOUT, base_url=platform["base_url"]) as client:
        res = await client.get(f"/instance/connectionState/{instance}", headers=headers)
        if res.status_code < 400 and res.content:
            data = res.json()
            inner = data.get("instance") if isinstance(data.get("instance"), dict) else data
            state = str(inner.get("state") or inner.get("connectionStatus") or "unknown").lower()
    return {"ok": True, "instance": instance, "state": state, "connected": state in ("open", "connected"), "alert": alert}


@router.post("/api/whatsapp-channel/espelho/trazer-conversas")
async def espelho_trazer_conversas(
    company_id: str,
    dias: int = 2,
    limite: int = 3000,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
) -> Dict[str, Any]:
    """Leva ao chat as conversas que o Observador JÁ capturou.

    A ponte do espelho só age quando chega mensagem nova. 📊 No dia em que ela
    subiu, a AutoFleet tinha 32.128 mensagens capturadas em 7 dias e o chat
    abriu VAZIO — a última mensagem tinha entrado 22 minutos antes do deploy. A
    corretora ficaria olhando uma tela vazia sobre um acervo cheio, esperando um
    cliente escrever.

    Idempotente: usa a mesma `espelhar_no_chat`, que deduplica por `message_id`.
    Rodar duas vezes não duplica nada.

    ⚠️ NÃO envia nada pelo WhatsApp e NÃO liga agente nenhum. Só lê o acervo e
    escreve no chat.
    """
    _require_internal_key(x_autobrokers_internal_key)
    from app.services.atlas.espelho_chat import trazer_conversas_ja_capturadas

    return await trazer_conversas_ja_capturadas(
        company_id=company_id, dias=dias, limite=limite)


@router.get("/api/whatsapp-channel/grupos")
async def whatsapp_channel_grupos(
    company_id: str,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
) -> Dict[str, Any]:
    """Os grupos do WhatsApp pareado, para o corretor escolher numa lista.

    Existe para substituir a instrucao "abra o WhatsApp Web e copie dezoito
    digitos da barra de enderecos" — que e onde a configuracao do suporte
    humano morria antes de comecar.

    Nunca levanta: devolve `ok=false` com uma frase que diz o que fazer.
    """
    _require_internal_key(x_autobrokers_internal_key)
    from app.services.whatsapp.grupos import listar_grupos

    return await listar_grupos(company_id)


@router.post("/api/whatsapp-channel/reparar-token")
async def whatsapp_channel_reparar_token(
    company_id: str,
    purpose: str = "observer",
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
) -> Dict[str, Any]:
    """Adota o token REAL da instância do Evolution GO — o reparo do HTTP 401.

    🔴 POR QUE ESTA ROTA EXISTE, e por que ela não deveria precisar existir.

    📊 Medido em 17/08/2026 na Resulta Seguros: `integrations.token` guardava um
    valor que a instância do Evolution nunca conheceu. Todo envio devolvia
    **HTTP 401**. O Auxiliar de Cobrança entrou no portal da Allianz três vezes,
    baixou 3 boletos reais em cada, e não conseguiu mandar nenhum.

    A causa está em `_go_create`: quando a instância JÁ EXISTE com telefone, o
    código (corretamente) não a recria — apagar despareia a corretora. Só que
    ele seguia gravando no banco um token recém-sorteado, e a instância
    continuava com o dela. Duas chaves, uma fechadura.

    O defeito é INVISÍVEL pelo caminho normal: o inbound autentica pelo NOSSO
    webhook token, não por este. O canal aparece "conectado", recebe mensagem,
    espelha conversa — e é mudo. Só quem tenta ENVIAR descobre.

    `_go_create` já foi consertado e adota o token certo dos pareamentos daqui
    em diante. Esta rota conserta quem já está no banco com a chave errada, sem
    despareamento e sem QR novo.

    Idempotente: se o token já bate, não escreve nada e diz isso.
    """
    _require_internal_key(x_autobrokers_internal_key)

    global_key = os.getenv("EVOLUTION_GO_GLOBAL_KEY") or ""
    if not global_key:
        return {"ok": False, "motivo": "sem_chave_global",
                "frase": "EVOLUTION_GO_GLOBAL_KEY não está configurada no backend."}

    supabase = get_supabase_client()
    alvo = str(purpose or "observer").strip().lower()

    def _linha() -> Optional[Dict[str, Any]]:
        r = (supabase.client.table("integrations")
             .select("id, instance_id, token")
             .eq("company_id", company_id).eq("provider", "evolution-go")
             .eq("purpose", alvo).eq("is_active", True)
             .order("last_seen_at", desc=True).limit(1).execute().data or [])
        return r[0] if r else None

    linha = await asyncio.to_thread(_linha)
    if not linha:
        return {"ok": False, "motivo": "sem_linha",
                "frase": f"Nenhuma integração evolution-go ativa com purpose={alvo}."}

    nome = str(linha.get("instance_id") or "")
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, base_url=_go_base()) as client:
            r = await client.get("/instance/all", headers={"apikey": global_key})
            if r.status_code >= 400:
                return {"ok": False, "motivo": f"http_{r.status_code}",
                        "frase": f"O Evolution recusou listar as instâncias (HTTP {r.status_code})."}
            achada = next((row for row in (r.json() or {}).get("data", [])
                           if str(row.get("name") or "") == nome), None)
    except Exception as exc:  # noqa: BLE001
        logger.error("[REPARAR TOKEN] falha ao falar com o GO: %s", type(exc).__name__)
        return {"ok": False, "motivo": type(exc).__name__,
                "frase": f"Não consegui falar com o Evolution ({type(exc).__name__})."}

    if not achada:
        return {"ok": False, "motivo": "instancia_nao_encontrada",
                "frase": f"A instância '{nome}' não existe no Evolution GO."}

    token_real = str(achada.get("token") or "").strip()
    if not token_real:
        return {"ok": False, "motivo": "provedor_sem_token",
                "frase": "O Evolution não devolveu o token desta instância."}

    # Compara o DECIFRADO, nunca o cru — senão a comparação diria "diferente"
    # sempre, e a rota reescreveria o token a cada chamada.
    from app.services.whatsapp.integration_secrets import (
        encrypt_integration_secret,
        prepare_integration_for_runtime,
    )

    atual = (prepare_integration_for_runtime(dict(linha), tolerar_perda=True) or {}).get("token")
    if atual and str(atual) == token_real:
        return {"ok": True, "mudou": False, "instancia": nome,
                "frase": "O token já era o certo. Nada foi alterado."}

    def _gravar() -> None:
        supabase.client.table("integrations").update({
            "token": encrypt_integration_secret(token_real),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", linha["id"]).execute()

    await asyncio.to_thread(_gravar)
    logger.info("[REPARAR TOKEN] instancia %s: token adotado do provedor", nome)
    return {"ok": True, "mudou": True, "instancia": nome,
            "frase": "Token corrigido — o canal volta a poder enviar. "
                     "Nenhum despareamento, nenhum QR novo."}
