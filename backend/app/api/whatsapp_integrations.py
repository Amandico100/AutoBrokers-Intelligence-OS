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


#: Teto da varredura de numeros nossos. Bater nele RECUSA — ver `_destino_e_nosso`.
_TETO_DE_NUMEROS_NOSSOS = 500


def _chave_de_telefone(bruto: Any) -> str:
    """A forma comparavel de um telefone brasileiro: **DDD + o numero inteiro**.

    🔴 A PRIMEIRA VERSAO DESTA FUNCAO COMPARAVA `DDD + os 8 FINAIS`, E ISSO
    COLIDIA. Medido pelo painel, em duas formas:

        movel  47 9 3333-4444  ->  chave 4733334444
        FIXO   47   3333-4444  ->  chave 4733334444     COLIDIAM
        +55 12 92555-0147      ->  chave 1225550147
        +1 212 555-0147        ->  chave 1225550147     COLIDIAM

    ⚠️ Numa lista de PERMISSAO que autoriza envio real sem freio, colisao e'
    autorizacao indevida. E a docstring antiga afirmava *"na pratica e' a mesma
    linha"* — falso justamente para o par fixo/movel que a migracao do nono
    digito criou.

    Agora: tira o `55` **so** quando o que sobra tem 10 ou 11 digitos (DDD +
    numero), e compara o numero INTEIRO. Duas linhas so' colidem se forem a
    mesma.
    """
    d = "".join(ch for ch in str(bruto or "") if ch.isdigit())
    if not d:
        return ""
    if d.startswith("55") and len(d) in (12, 13):
        d = d[2:]
    return d


async def _destino_e_nosso(db: AsyncSupabaseClient, company_id: str,
                           destino: str) -> tuple:
    """O destino da prova e' um aparelho **DESTA** corretora? 🔴 Na duvida, NAO.

    Devolve `(permitido, numero_a_usar)`. 🔴 **O numero devolvido e' o que esta'
    GRAVADO**, nunca o que o chamador mandou — ver o fim desta docstring.

    ⛔ **SPEC-092 F.2, corrigido pelo painel.** Esta rota **envia de verdade** e
    nao passa por freio nenhum: nao consulta `dispatch_live_enabled()` nem o
    freio de emergencia, so' a chave interna.

    > **Uma premissa de seguranca que existe so' na docstring nao e' uma trava:
    > e' uma esperanca.**

    🔴 E A PRIMEIRA VERSAO DESTA TRAVA ERA ELA MESMA UM VAZAMENTO. Ela
    consultava `integrations` **sem filtro de `company_id`** — a lista de
    permissao era GLOBAL. Medido pelo painel, ponta a ponta:

        um usuario logado da Corretora A posta {"para": "<pareado da B>"}
        a lista aceita, porque o numero e' "nosso"
        o backend carrega a integracao DE A e dispara de verdade
        -> mensagem real saindo do aparelho de A para o aparelho de B

    E ela virava **oraculo de pertencimento**: `400` significava *"esse numero
    nao e' de ninguem da plataforma"*, e qualquer outra resposta significava
    *"e'"*. Qualquer corretora logada descobria quais aparelhos sao de clientes
    AutoBrokers — inclusive de concorrentes — **sem enviar nada**.

    `CLAUDE.md` §7: *"RLS + filtro obrigatorio no repository/service"*. O
    backend usa service role; sem o `.eq("company_id", …)` aqui nao havia nem um
    nem outro.

    ## 🔴 E O NUMERO QUE VAI AO FIO E' O GRAVADO, NAO O DIGITADO

    A versao anterior **comparava normalizado e enviava o cru**: `corpo["number"]
    = para`, os digitos que o chamador mandou. Bastava uma colisao de chave para
    a trava aprovar um numero e o produto entregar noutro. Devolvendo o valor
    GRAVADO, a colisao deixa de ser explorave l: o pior caso vira "mandou para
    outro aparelho NOSSO da mesma corretora".

    ⚠️ Falha FECHADO em quatro caminhos: consulta que levanta, varredura que
    bate no teto (truncar nao e' provar), destino vazio, e `company_id` vazio.
    """
    alvo = _chave_de_telefone(destino)
    empresa = str(company_id or "").strip()
    if not alvo or not empresa:
        return (False, "")
    try:
        r = await (db.client.table("integrations")
                   .select("paired_phone_e164")
                   .eq("company_id", empresa)
                   .eq("is_active", True)
                   .limit(_TETO_DE_NUMEROS_NOSSOS).execute())
    except Exception as e:  # noqa: BLE001
        logger.error("[PROVA FORMULARIO] nao foi possivel conferir se o destino "
                     "e' desta corretora (%s) — recusando por seguranca",
                     type(e).__name__)
        return (False, "")
    linhas = r.data or []
    if len(linhas) >= _TETO_DE_NUMEROS_NOSSOS:
        logger.error("[PROVA FORMULARIO] a varredura de numeros da corretora bateu "
                     "no teto de %s — nao provou nada, recusando",
                     _TETO_DE_NUMEROS_NOSSOS)
        return (False, "")
    for linha in linhas:
        gravado = str(linha.get("paired_phone_e164") or "").strip()
        if gravado and _chave_de_telefone(gravado) == alvo:
            return (True, "".join(ch for ch in gravado if ch.isdigit()))
    return (False, "")


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

    # ⛔ SPEC-092 F.2 — O DESTINO TEM DE SER NOSSO.
    #
    # Esta rota manda DE VERDADE e nao passa por freio nenhum. Ate' aqui, o
    # unico motivo de ela ser segura era a docstring dizer que o destino e'
    # nosso. Agora o codigo confere.
    permitido, numero_gravado = await _destino_e_nosso(db, company_id, para)
    if not permitido:
        logger.error("[PROVA FORMULARIO] destino RECUSADO: nao e' um aparelho "
                     "desta corretora (empresa=%s)", company_id)
        raise HTTPException(
            status_code=400,
            detail=("destino recusado: a prova de formulario so' envia para um "
                    "aparelho desta corretora. Nenhuma mensagem foi enviada."))
    # 🔴 O QUE VAI AO FIO E' O GRAVADO. Ver `_destino_e_nosso`.
    para = numero_gravado

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

    # 🔴 A PROVA MEDE O CAMINHO DA PRODUÇÃO — as MESMAS funções, não cópias.
    #
    # A forma vem da ÚNICA captura real que temos de um humano respondendo este
    # formulário (18/07/2026, família HDI). O flow_token guarda os dois
    # telefones dentro dele — por isso é montado, e nunca inventado solto.
    #
    # ⚠️ Aqui já houve DOIS montadores: esta rota remontava o corpo plano à mão
    # (`{number, name, paramsJSON, ...}`) ao lado de `corpo_do_flow_reply`, que é
    # quem o motor de envio usa. Dois montadores do mesmo corpo divergem um dia,
    # e a divergência só aparece numa seguradora descartando a resposta em
    # silêncio — com a prova dizendo "está tudo bem" sobre outra coisa
    # (CLAUDE.md §5 e §9.4).
    from app.services.whatsapp.providers.evolution_go import (
        ENV_ROTA_FLOW_REPLY,
        ROTA_DE_FLOW_REPLY_PROVADA,
        corpo_do_flow_reply,
        rota_de_flow_reply,
    )

    origem = "".join(ch for ch in str(runtime.get("identifier") or "") if ch.isdigit()) or "0"
    flow_token = f"00000000-0000-0000-0000-000000000000:{origem}:{para}"

    #: O que a prova varia por cima do corpo de produção — um fator por vez.
    _PARAMS_DA_PROVA: Dict[str, Any] = {"prova_de_canal": "1"}
    _IDENTIDADE_DA_PROVA: Dict[str, Any] = {
        "title": "Prova de canal",
        "flow_id": "0",
        "flow_name": "AutoBrokers — prova de envio de formulario",
    }
    _TEXTO_DA_PROVA = "Prova tecnica do AutoBrokers. Pode ignorar."

    def _corpo_da_prova(*, version: int) -> Dict[str, Any]:
        """O corpo plano do envio REAL, montado por quem monta em produção."""
        return corpo_do_flow_reply(
            to=para,
            flow_token=flow_token,
            params=_PARAMS_DA_PROVA,
            nome_do_envelope="galaxy_message",
            flow_response_params=_IDENTIDADE_DA_PROVA,
            body_text=_TEXTO_DA_PROVA,
            version=version,
        )

    try:
        # A primeira montagem também serve de relatório (envelope e tamanho do
        # paramsJSON na resposta) — e recusa cedo, antes de tocar a rede.
        corpo_base = _corpo_da_prova(version=0)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"montagem recusada: {exc}") from exc

    params_json = str(corpo_base.get("paramsJSON") or "")
    nome_do_envelope_ecoado = str(corpo_base.get("name") or "")

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
    # RODADA 2. A primeira rodada mediu os fatores de PAYLOAD — version, nós biz,
    # body — e os cinco deram 479 igual. Fator que não muda o resultado não é a
    # causa: isso descarta o conteúdo e aponta para a FORMA.
    #
    # Sobraram as duas coisas que /send/button faz em todas as suas variantes e
    # que nós não fazíamos: o embrulho DocumentWithCaptionMessage e os 32 bytes
    # de MessageSecret. Viraram bandeiras no patch 0006.
    #
    # A primeira linha é controle: se ela parar de dar 479, quem mudou foi outra
    # coisa, e o resto da leitura não vale.
    tentativas = [
        {"nome": "controle — como na rodada 1", "version": 0, "biz": False, "body": True,
         "embrulho": False, "segredo": False},
        {"nome": "embrulho DocumentWithCaption", "version": 0, "biz": False, "body": True,
         "embrulho": True, "segredo": False},
        {"nome": "MessageSecret", "version": 0, "biz": False, "body": True,
         "embrulho": False, "segredo": True},
        {"nome": "embrulho + MessageSecret", "version": 0, "biz": False, "body": True,
         "embrulho": True, "segredo": True},
        {"nome": "embrulho + segredo + nos biz (igual ao botao)", "version": 0, "biz": True,
         "body": True, "embrulho": True, "segredo": True},
    ]

    import asyncio

    import requests

    # 🔴 A ROTA SAI DA MESMA FUNÇÃO QUE O ENVIO REAL — nunca de uma string daqui.
    #
    # ⚠️ Esta linha já foi `f"{base_url}/send/interactiveResponse"` fixo. Hoje as
    # duas coisas coincidem, e é justamente por isso que o defeito era
    # SILENCIOSO: no dia em que alguém escrever `EVOLUTION_GO_FLOW_REPLY_PATH`
    # para corrigir o caminho, a prova continuaria dizendo "tudo bem" sobre uma
    # rota que a produção não usa mais (CLAUDE.md §9.4 — *um padrão medido com um
    # motor e aplicado com outro é um padrão sobre outra coisa*).
    rota = rota_de_flow_reply()
    if not rota:
        # 🔴 Desligado é uma RECUSA, não um caminho. Sem esta guarda o `f-string`
        # abaixo montaria `{base_url}` + "" e a prova bateria na raiz do serviço,
        # medindo o que não se quis medir.
        logger.warning(
            "[PROVA FORMULARIO] company=%s a rota de resposta de interativa esta "
            "DESLIGADA por configuracao (%s) — nada foi enviado", company_id,
            ENV_ROTA_FLOW_REPLY)
        return {
            "success": False,
            "diagnostico": "rota_desligada_por_configuracao",
            "explicacao": (
                f"O envio de resposta de formulario esta DESLIGADO nesta instalacao: "
                f"a variavel {ENV_ROTA_FLOW_REPLY} esta em 'off'. Nenhuma mensagem "
                f"foi enviada, e o produto tambem nao envia enquanto estiver assim. "
                f"Para religar, apague o valor da variavel (o padrao volta a ser a "
                f"rota provada {ROTA_DE_FLOW_REPLY_PROVADA}) e rode esta prova de novo."
            ),
        }

    url = f"{base_url}{rota}"
    resultados = []
    vencedora = None

    for t in tentativas:
        # 🔴 O corpo NASCE do montador de produção e a prova só TIRA o fator que
        # está medindo. Começar de um dicionário próprio é ter dois montadores.
        corpo: Dict[str, Any] = _corpo_da_prova(version=int(t["version"]))
        if not t.get("embrulho"):
            corpo.pop("wrapInDocumentWithCaption", None)
        if not t["body"]:
            corpo.pop("body", None)
        if t["biz"]:
            corpo["withBizNodes"] = True
        if t.get("segredo"):
            corpo["withMessageSecret"] = True

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

        # 404 é conclusivo e não adianta insistir — mas o que ele SIGNIFICA
        # mudou, e dizer o antigo custou um rebuild que não era necessário.
        #
        # 🔴 O TEXTO DE ANTES DIZIA QUE FALTAVA VERSÃO DE IMAGEM, e isso é FALSO
        # desde 26/09/2026: 📊 a rota respondeu HTTP 200 (`vencedora: "embrulho
        # DocumentWithCaption"`, servidor devolveu
        # `Type: "InteractiveResponseMessage"`, ID 3EB02C9B1BFC57E46E3136) na
        # imagem que está no ar. Quem leu aquele texto pediu autorização para
        # reconstruir a imagem à toa. CLAUDE.md §9.3: verdade vencida é pior que
        # teste nenhum — e este texto é lido às três da manhã, por quem está com
        # um acionamento parado.
        #
        # ⛔ E ele NÃO promete versão de imagem nenhuma. Foi a promessa que
        # enganou: a rota não aparece no `swagger/doc.json` nem na imagem em que
        # ela FUNCIONA, então número de versão aqui é palpite com cara de
        # instrução.
        if r.status_code == 404:
            return {
                "success": False,
                "diagnostico": "rota_nao_respondeu_mais",
                "explicacao": (
                    f"Este Evolution GO devolveu 404 em POST {rota}. 📊 Essa mesma "
                    f"rota FOI PROVADA no ar em 26/09/2026 (HTTP 200, o servidor "
                    f"respondeu Type: \"InteractiveResponseMessage\"). Um 404 agora "
                    f"significa que ela MUDOU DE CAMINHO ou foi DESLIGADA no "
                    f"servico — nao que falte versao de imagem. Confira: (1) a "
                    f"variavel {ENV_ROTA_FLOW_REPLY}, que e o que corrige o caminho "
                    f"(vazia = usa {ROTA_DE_FLOW_REPLY_PROVADA}); (2) se o servico "
                    f"em {base_url} e o mesmo de antes; (3) rode esta prova de novo "
                    f"depois de corrigir — ela e a unica coisa que decide, e o "
                    f"swagger/doc.json NAO lista esta rota nem quando ela funciona."
                ),
                "rota_tentada": rota,
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
        "envelope": nome_do_envelope_ecoado,
        "tamanho_paramsJSON": len(params_json),
        # 🔴 A rota vai NA RESPOSTA: quem lê a prova precisa saber em que caminho
        # ela bateu, senão um dia ela prova um caminho e o produto usa outro.
        "rota": rota,
        "tentativas": resultados,
        "leitura": (
            f"O WhatsApp ACEITOU: {vencedora}. Esta e a forma a usar."
            if vencedora
            else (
                "Nenhuma forma foi aceita. Se ate 'embrulho + segredo + nos biz' — que e "
                "exatamente a forma dos botoes, que FUNCIONAM — deu 479, entao o servidor "
                "nao recusa a forma: recusa o TIPO. Ou seja, uma conta comum nao pode "
                "ORIGINAR uma resposta de formulario sem ter recebido o formulario antes. "
                "Nesse caso o proximo teste tem de ser com um flow de verdade chegando, e "
                "nao com um fabricado por nos."
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
