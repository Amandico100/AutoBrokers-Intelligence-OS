"""
WhatsApp Integrations API — Secret Flow seguro (39A4.2).

Recebe credenciais Z-API APENAS server-side (via chave interna Next↔Backend),
cifra token/client_token (EncryptionService) e grava em public.integrations.
NUNCA retorna/loga segredo. NÃO envia mensagem (test é validação local).
"""
import hmac
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.core.database import AsyncSupabaseClient, get_async_db
from app.services.whatsapp.integration_secrets import (
    prepare_integration_for_runtime,
    prepare_integration_for_storage,
)

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_PROVIDERS = {"z-api"}
DEFAULT_BASE_URL = "https://api.z-api.io/instances"


def _require_internal_key(provided: Optional[str]) -> None:
    """Exige a chave interna Next↔Backend (mesmo padrão de Auxiliares)."""
    expected = os.getenv("BACKEND_INTERNAL_API_KEY") or os.getenv("ADMIN_API_KEY")
    if not expected:
        logger.error("[WA INTEGRATIONS] Internal API key not configured")
        raise HTTPException(status_code=500, detail="Internal API key not configured")
    if not provided or not hmac.compare_digest(str(provided), str(expected)):
        raise HTTPException(status_code=401, detail="Unauthorized internal request")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mask(value: Optional[str]) -> Optional[str]:
    return f"...{str(value)[-4:]}" if value else None


def _sanitize(row: Dict[str, Any]) -> Dict[str, Any]:
    """Projeção SEM segredos para devolver ao Next/UI."""
    return {
        "id": row.get("id"),
        "company_id": row.get("company_id"),
        "agent_id": row.get("agent_id"),
        "provider": row.get("provider"),
        "identifier_masked": _mask(row.get("identifier")),
        "has_instance_id": bool(row.get("instance_id")),
        "has_client_token": bool(row.get("client_token")),
        "base_url": row.get("base_url"),
        "is_active": row.get("is_active"),
    }


class ConfigurePayload(BaseModel):
    company_id: str
    agent_id: str
    provider: str = "z-api"
    identifier: str
    instance_id: str
    token: str
    client_token: Optional[str] = None
    base_url: Optional[str] = None
    buffer_enabled: Optional[bool] = True
    buffer_debounce_seconds: Optional[int] = 3
    buffer_max_wait_seconds: Optional[int] = 10


class TestPayload(BaseModel):
    company_id: str
    integration_id: Optional[str] = None
    agent_id: Optional[str] = None


@router.post("/configure")
async def configure(
    payload: ConfigurePayload,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
    db: AsyncSupabaseClient = Depends(get_async_db),
):
    _require_internal_key(x_autobrokers_internal_key)

    company_id = (payload.company_id or "").strip()
    agent_id = (payload.agent_id or "").strip()
    provider = (payload.provider or "z-api").lower().strip()
    identifier = (payload.identifier or "").strip()
    instance_id = (payload.instance_id or "").strip()
    token = (payload.token or "").strip()
    client_token = (payload.client_token or "").strip() or None
    base_url = (payload.base_url or DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL

    if provider not in ALLOWED_PROVIDERS:
        raise HTTPException(status_code=400, detail="provider not allowed")
    if not company_id or not agent_id:
        raise HTTPException(status_code=400, detail="company_id and agent_id are required")
    if not identifier or not instance_id or not token:
        raise HTTPException(status_code=400, detail="identifier, instance_id and token are required")

    # Valida que o agente pertence à empresa (anti-IDOR), sem maybe_single (evita 406).
    try:
        ag = (
            await db.client.table("agents")
            .select("id, company_id")
            .eq("id", agent_id)
            .eq("company_id", company_id)
            .limit(1)
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        logger.error(f"[WA INTEGRATIONS] agent lookup failed: {type(e).__name__}")
        raise HTTPException(status_code=500, detail="Failed to validate agent")
    if not ag.data:
        raise HTTPException(status_code=404, detail="agent not found for this company")

    # Cifra token/client_token (39A4.1) ANTES de gravar — erro de cripto isolado (nunca loga valor).
    try:
        secrets_enc = prepare_integration_for_storage({"token": token, "client_token": client_token})
    except Exception as e:  # noqa: BLE001
        logger.error(f"[WA INTEGRATIONS] encryption failed: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=f"Encryption unavailable ({type(e).__name__})")

    record = {
        "company_id": company_id,
        "agent_id": agent_id,
        "provider": provider,
        "identifier": identifier,
        "instance_id": instance_id,
        "token": secrets_enc.get("token"),
        "client_token": secrets_enc.get("client_token"),
        "base_url": base_url,
        "is_active": True,
        "buffer_enabled": bool(payload.buffer_enabled) if payload.buffer_enabled is not None else True,
        "buffer_debounce_seconds": payload.buffer_debounce_seconds or 3,
        "buffer_max_wait_seconds": payload.buffer_max_wait_seconds or 10,
        "updated_at": _now(),
    }

    # Upsert manual (evita on_conflict no client async): procura por (provider, identifier).
    try:
        existing = (
            await db.client.table("integrations")
            .select("id")
            .eq("provider", provider)
            .eq("identifier", identifier)
            .limit(1)
            .execute()
        )
        if existing.data:
            row_id = existing.data[0]["id"]
            upd = await db.client.table("integrations").update(record).eq("id", row_id).execute()
            row = upd.data[0] if upd.data else {"id": row_id, **record}
        else:
            ins = await db.client.table("integrations").insert(record).execute()
            row = ins.data[0] if ins.data else None
    except Exception as e:  # noqa: BLE001
        logger.error(f"[WA INTEGRATIONS] store failed: {type(e).__name__}")
        raise HTTPException(status_code=500, detail=f"Failed to store integration ({type(e).__name__})")

    if not row:
        raise HTTPException(status_code=500, detail="Integration not stored")

    logger.info(
        f"[WA INTEGRATIONS] ✅ stored integration for company {company_id} | agent {agent_id} | provider {provider}"
    )
    return {"success": True, "integration": _sanitize(row)}


@router.post("/test")
async def test_configuration(
    payload: TestPayload,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
    db: AsyncSupabaseClient = Depends(get_async_db),
):
    """Valida a configuração localmente (descriptografa em memória). NÃO envia mensagem."""
    _require_internal_key(x_autobrokers_internal_key)

    company_id = (payload.company_id or "").strip()
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id is required")

    try:
        query = (
            db.client.table("integrations")
            .select("*")
            .eq("company_id", company_id)
            .eq("is_active", True)
        )
        if payload.integration_id:
            query = query.eq("id", payload.integration_id)
        elif payload.agent_id:
            query = query.eq("agent_id", payload.agent_id)
        resp = await query.limit(1).execute()
    except Exception as e:  # noqa: BLE001
        logger.error(f"[WA INTEGRATIONS] test lookup failed: {type(e).__name__}")
        raise HTTPException(status_code=500, detail="Failed to load integration")

    if not resp.data:
        raise HTTPException(status_code=404, detail="integration not found")

    runtime = prepare_integration_for_runtime(resp.data[0]) or {}
    ok = bool(runtime.get("instance_id") and runtime.get("token") and runtime.get("identifier"))

    # NUNCA chama a Z-API. NUNCA retorna token.
    return {
        "success": ok,
        "dry_run": True,
        "message": (
            "Configuração local válida. Nenhuma mensagem foi enviada."
            if ok
            else "Configuração incompleta. Revise os campos."
        ),
    }


@router.get("/health")
async def health(
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
):
    """Diagnóstico Web→Backend (sem segredo): confirma rota viva e cripto disponível."""
    _require_internal_key(x_autobrokers_internal_key)
    encryption_configured = False
    try:
        from app.services.whatsapp.integration_secrets import encrypt_integration_secret

        probe = encrypt_integration_secret("healthcheck")
        encryption_configured = bool(probe) and probe != "healthcheck"
    except Exception:  # noqa: BLE001
        encryption_configured = False
    return {
        "success": True,
        "service": "whatsapp-integrations",
        "encryption_configured": encryption_configured,
    }


class ProvaDeFormularioPayload(BaseModel):
    company_id: str
    para: str
    integration_id: Optional[str] = None


@router.post("/prova-de-formulario")
async def prova_de_formulario(
    payload: ProvaDeFormularioPayload,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
    db: AsyncSupabaseClient = Depends(get_async_db),
):
    """Prova que este canal consegue RESPONDER um formulário nativo.

    Envia, de um número nosso para outro número nosso, exatamente o tipo de
    mensagem que o telefone de uma pessoa produz ao preencher um formulário
    dentro do WhatsApp e tocar enviar. **Manda de verdade** — não é dry-run.

    Existe porque a coisa que pode estar errada só aparece no ar. O
    codificador já é provado por teste em Go dentro do build; o que nenhum
    teste alcança é a rede: se o WhatsApp aceita a mensagem, entrega, e se do
    outro lado ela volta a ser lida como resposta de formulário.

    Por que um endpoint, e não um comando de terminal: a chave da instância é
    cifrada em repouso e só se abre dentro do processo. Um teste que exija
    alguém colar a chave em algum lugar não é um teste — é um vazamento com
    hora marcada. Aqui a chave é aberta em memória, usada, e nunca sai na
    resposta.

    Fica como diagnóstico permanente: qualquer corretora pode conferir o
    próprio canal sem depender de quem escreveu o código.
    """
    _require_internal_key(x_autobrokers_internal_key)

    company_id = (payload.company_id or "").strip()
    para = "".join(ch for ch in str(payload.para or "") if ch.isdigit())
    if not company_id:
        raise HTTPException(status_code=400, detail="company_id is required")
    if not para:
        raise HTTPException(status_code=400, detail="para (numero de destino) is required")

    try:
        query = (
            db.client.table("integrations")
            .select("*")
            .eq("company_id", company_id)
            .eq("provider", "evolution-go")
            .eq("is_active", True)
        )
        if payload.integration_id:
            query = query.eq("id", payload.integration_id.strip())
        resp = await query.limit(1).execute()
    except Exception as e:  # noqa: BLE001
        logger.error(f"[PROVA FORMULARIO] lookup falhou: {type(e).__name__}")
        raise HTTPException(status_code=500, detail="Failed to load integration") from e

    if not resp.data:
        raise HTTPException(status_code=404, detail="Nenhuma integracao evolution-go ativa para esta corretora")

    runtime = prepare_integration_for_runtime(resp.data[0]) or {}
    base_url = str(runtime.get("base_url") or "").rstrip("/")
    token = runtime.get("token")
    if not base_url or not token:
        raise HTTPException(status_code=422, detail="Integracao sem base_url ou sem chave utilizavel")

    # A forma vem da ÚNICA captura real que temos de um humano respondendo este
    # formulário (18/07/2026, família HDI). O flow_token guarda os dois
    # telefones dentro dele — por isso é montado, e nunca inventado solto.
    from app.services.whatsapp.providers.evolution_go import montar_nfm_reply

    origem = "".join(ch for ch in str(runtime.get("identifier") or "") if ch.isdigit()) or "0"
    flow_token = f"00000000-0000-0000-0000-000000000000:{origem}:{para}"
    try:
        mensagem = montar_nfm_reply(
            flow_token=flow_token,
            params={"prova_de_canal": "1"},
            nome_do_envelope="galaxy_message",
            flow_response_params={
                "title": "Prova de canal",
                "flow_id": "0",
                "flow_name": "AutoBrokers — prova de envio de formulario",
            },
            body_text="Prova tecnica do AutoBrokers. Pode ignorar.",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"montagem recusada: {exc}") from exc

    envelope = mensagem["interactiveResponseMessage"]
    nfm = envelope["nativeFlowResponseMessage"]
    params_json = nfm["paramsJSON"]
    texto = (envelope.get("body") or {}).get("text")

    # A BATERIA. O WhatsApp recusou a primeira tentativa com 479, que o próprio
    # whatsmeow documenta como "Invalid stanza sent (smax-invalid)": recusa do
    # ENVELOPE da mensagem, não do conteúdo. O paramsJSON estava certo; o que
    # está em dúvida é a estrutura em volta dele.
    #
    # Só existe uma captura real deste tipo de mensagem, e ela não registra o
    # envelope inteiro — então a diferença não dá para deduzir por leitura. Dá
    # para MEDIR: variar um fator por vez e ver qual o servidor aceita.
    #
    # Para a primeira e a última mensagem chegarem, quem decide são elas.
    tentativas = [
        {"nome": "como a captura (sem version, sem nos biz)", "version": 0, "biz": False, "body": True},
        {"nome": "com os nos biz", "version": 0, "biz": True, "body": True},
        {"nome": "com version 1", "version": 1, "biz": False, "body": True},
        {"nome": "version 1 + nos biz", "version": 1, "biz": True, "body": True},
        {"nome": "sem body", "version": 0, "biz": False, "body": False},
    ]

    import asyncio

    import requests

    url = f"{base_url}/send/interactiveResponse"
    resultados = []
    vencedora = None

    for t in tentativas:
        corpo: Dict[str, Any] = {"number": para, "name": nfm["name"], "paramsJSON": params_json}
        if t["version"]:
            corpo["version"] = int(t["version"])
        if t["body"] and texto:
            corpo["body"] = texto
        if t["biz"]:
            corpo["withBizNodes"] = True

        def _enviar(c=corpo):
            return requests.post(
                url, json=c,
                headers={"Content-Type": "application/json", "apikey": str(token)},
                timeout=30,
            )

        try:
            r = await asyncio.to_thread(_enviar)
        except Exception as e:  # noqa: BLE001
            resultados.append({"tentativa": t["nome"], "http": None, "erro": type(e).__name__})
            continue

        # 404 é conclusivo e não adianta insistir: a imagem no ar é anterior ao
        # patch 0005 e não tem a porta de saída.
        if r.status_code == 404:
            return {
                "success": False,
                "diagnostico": "rota_ausente",
                "explicacao": (
                    "Este Evolution GO nao tem POST /send/interactiveResponse. "
                    "A imagem precisa ser 0.7.2-autobrokers.2 ou mais nova."
                ),
            }

        try:
            devolvido = r.json()
        except Exception:  # noqa: BLE001
            devolvido = (r.text or "")[:300]

        ok = 200 <= r.status_code < 300
        resultados.append({
            "tentativa": t["nome"],
            "http": r.status_code,
            "aceito": ok,
            "resposta": devolvido,
        })
        logger.info("[PROVA FORMULARIO] company=%s '%s' http=%s", company_id, t["nome"], r.status_code)

        if ok:
            vencedora = t["nome"]
            break

    return {
        "success": vencedora is not None,
        "vencedora": vencedora,
        "para": para,
        "envelope": nfm["name"],
        "tamanho_paramsJSON": len(params_json),
        "tentativas": resultados,
        "leitura": (
            f"O WhatsApp ACEITOU: {vencedora}. Esta e a forma a usar."
            if vencedora
            else (
                "Nenhuma forma foi aceita. 479 = 'Invalid stanza sent' — o servidor "
                "recusa o envelope, nao o conteudo. O proximo passo e no Go: embrulhar "
                "em DocumentWithCaptionMessage, como /send/button ja faz."
            )
        ),
    }


class SendDryRunPayload(BaseModel):
    company_id: str
    integration_id: str
    to_number: str
    message: str


@router.post("/send-dry-run")
async def send_dry_run(
    payload: SendDryRunPayload,
    x_autobrokers_internal_key: Optional[str] = Header(default=None, alias="X-AutoBrokers-Internal-Key"),
    db: AsyncSupabaseClient = Depends(get_async_db),
):
    """
    Execução de envio em DRY-RUN FORÇADO. NUNCA chama a Z-API real (force_dry_run=True),
    independente do env global. Valida que a integração existe e descriptografa em memória.
    """
    _require_internal_key(x_autobrokers_internal_key)

    company_id = (payload.company_id or "").strip()
    integration_id = (payload.integration_id or "").strip()
    to_number = (payload.to_number or "").strip()
    message = (payload.message or "").strip()

    if not company_id or not integration_id:
        raise HTTPException(status_code=400, detail="company_id and integration_id are required")
    if not to_number or not message:
        raise HTTPException(status_code=400, detail="to_number and message are required")

    try:
        resp = (
            await db.client.table("integrations")
            .select("*")
            .eq("company_id", company_id)
            .eq("id", integration_id)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
    except Exception as e:  # noqa: BLE001
        logger.error(f"[WA INTEGRATIONS] dry-run lookup failed: {type(e).__name__}")
        raise HTTPException(status_code=500, detail="Failed to load integration")

    if not resp.data:
        raise HTTPException(status_code=404, detail="integration not found")

    runtime = prepare_integration_for_runtime(resp.data[0]) or {}
    if not (runtime.get("instance_id") and runtime.get("token") and runtime.get("identifier")):
        raise HTTPException(status_code=400, detail="integration not fully configured")

    # FORÇA dry-run no provider — não chama a Z-API real, não toca a internet.
    from app.services.whatsapp.zapi_provider import get_zapi_provider

    result = get_zapi_provider().send_text(to_number, message, runtime, force_dry_run=True)
    if not result.success:
        raise HTTPException(status_code=502, detail=f"dry-run failed ({result.error or 'unknown'})")

    logger.info(
        f"[WA INTEGRATIONS] 🧪 dry-run OK for company {company_id} | to ...{to_number[-4:]} | provider {result.provider}"
    )
    return {
        "success": True,
        "provider": result.provider,
        "dry_run": True,
        "message": "Simulação executada. Nenhuma mensagem foi enviada.",
    }
