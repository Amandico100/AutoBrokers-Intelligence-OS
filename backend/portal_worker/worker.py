"""Poll loop do portal-worker (SPEC-020 P1): pega portal_jobs 'queued', roda a
journey Playwright determinística e grava status/evidência. Sem Redis novo (poll
na tabela, mesmo padrão do routine_scheduler_loop). Gate PORTAL_REAL_ENABLED off:
em standby o worker sobe e responde /health mas NÃO executa job nenhum."""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict
from urllib.parse import unquote, urlsplit

logger = logging.getLogger("portal_worker")

POLL_SECONDS = int(os.getenv("PORTAL_POLL_SECONDS", "30"))
# Teto duro por journey: nenhum job pode segurar o worker além disso.
JOB_TIMEOUT_SECONDS = int(os.getenv("PORTAL_JOB_TIMEOUT_SECONDS", "1200"))
# Job 'running' mais velho que timeout+margem = órfão (worker morreu/reiniciou).
STALE_MARGIN_SECONDS = 600


def portal_real_enabled() -> bool:
    return str(os.getenv("PORTAL_REAL_ENABLED", "false")).strip().lower() in ("1", "true", "yes", "on")


# --------------------------------------------------------------------------
# Pontes para a infraestrutura da SPEC-073. Import tardio dentro das funções
# NÃO serve aqui: estes módulos são puros (sem Playwright, sem rede), e o
# worker precisa deles antes de abrir o browser.
# --------------------------------------------------------------------------
from portal_worker import guardrails as _G           # noqa: E402
from portal_worker import redaction as _R            # noqa: E402
from portal_worker.runtime import (                  # noqa: E402
    kill_switch_ativo,
    kill_switch_presente,
    montar_runtime as _montar_runtime,
)


def _redigir(bloco: Any) -> Any:
    """Sanitiza a evidencia ANTES do banco — so as superficies de diagnostico.

    🔴 Ver `redaction.redigir_envelope`: envolver a evidencia INTEIRA quebrava a
    chave anti-duplicacao da cobranca. O payload de trabalho da journey sai
    intacto; profiler/trace/log/discovery passam pelo redator.
    """
    try:
        return _R.redigir_envelope(bloco)
    except Exception:  # noqa: BLE001
        # Redator quebrado não pode virar perda de evidência — mas também não
        # pode virar vazamento. Sem saber sanitizar, não grava o conteúdo.
        return {"redaction_falhou": True}


# Host de cada portal, para o profiler saber o que é primeira parte. Só isso —
# a URL de trabalho continua morando na journey, que é quem conhece o portal.
_HOSTS_DE_PORTAL: Dict[str, str] = {
    "vidros_lanternas": "abraseuatendimento.com.br",
    "allianz_corretor": "allianznet.com.br",
    "hdi_corretor": "hdi.com.br",
    "tokiomarine_corretor": "tokiomarine.com.br",
    "yelum_corretor": "yelumseguradora.com.br",
    "mapfre_corretor": "mapfre.com.br",
    "zurich_corretor": "zurich.com.br",
}


def _host_do_portal(portal_key: str) -> str:
    return _HOSTS_DE_PORTAL.get(str(portal_key or "").strip().lower(), "")


# Chromium: headless MODERNO, não o clássico.
#
# 📊 Medido em 10/08/2026 contra o portal da HDI, um fator por vez, com linha
# de CONTROLE repetida no início e no fim da bateria::
#
#     headless clássico  ...................  BLOQUEADO  "Access Denied" (Akamai)
#     + args anti-automação ................  BLOQUEADO
#     + script de stealth ..................  BLOQUEADO
#     + args E stealth .....................  BLOQUEADO
#     navegador COM janela .................  PASSOU
#     --headless=new .......................  PASSOU     ← e roda sem tela
#
# Cinco variações deram o mesmo bloqueio, então nenhuma delas era a causa: o
# fator é o MODO headless. O clássico é um binário separado, com fingerprint
# próprio, e o Akamai o reconhece. O `--headless=new` é o mesmo Chrome de
# janela rodando sem desenhar — passa, e não precisa de Xvfb no contêiner.
#
# `headless=False` + `--headless=new` é como se pede o modo novo no Playwright:
# o parâmetro precisa ficar falso para a lib não injetar o `--headless` antigo.
#
# A Allianz continua no mesmo navegador — e é ela a linha de controle desta
# mudança: se ela seguir baixando os 4 boletos, o modo novo não regrediu nada.
def _launch_kwargs() -> Dict[str, Any]:
    modo = str(os.getenv("PORTAL_HEADLESS_MODE", "new")).strip().lower()
    if modo == "classic":
        return {"headless": True}
    if modo == "headed":  # só com tela/Xvfb — último recurso
        return {"headless": False, "args": ["--no-sandbox", "--disable-dev-shm-usage"]}
    return {
        "headless": False,
        "args": [
            "--headless=new",
            "--no-sandbox",            # contêiner sem privilégio
            "--disable-dev-shm-usage",  # /dev/shm pequeno derruba aba em Docker
            "--disable-blink-features=AutomationControlled",
        ],
    }


def _parse_ts(value: Any) -> datetime | None:
    """ISO tolerante (Supabase devolve '2026-07-10 04:01:46.5+00')."""
    text = str(value or "").strip().replace("Z", "+00:00")
    if not text:
        return None
    if text.endswith("+00"):
        text = text + ":00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def stale_running_patch(job: Dict[str, Any], now: datetime | None = None) -> Dict[str, Any] | None:
    """Patch de recuperação p/ job 'running' órfão; None = deixar em paz.

    1ª ocorrência → volta pra fila; reincidente → failed.
    (Um job vidros ficou 3 dias preso em running após restart do worker.)

    🔴 CORRIGIDO NA SPEC-073 (Bloco B5). A versão anterior decidia olhando
    APENAS idade e tentativas — o SELECT nem trazia `evidence`. Consequência
    medida em 16/08/2026: um job que morresse **depois** de o portal criar o
    atendimento, com o protocolo já gravado, voltava para `queued` e recomeçava
    do passo 1. O portal de vidros diz em texto que cada solicitação é um pedido
    novo; recomeçar não conserta nada, **cria um segundo atendimento na
    seguradora** — e o segurado descobre quando dois vidraceiros aparecem.

    Agora a evidência manda. A regra e o CONTROLE que a mantém honesta:

        sem efeito material ............ comportamento antigo, intacto
        efeito confirmado/incerto ...... needs_human, NUNCA de volta para a fila

    O controle é a primeira linha: um job read-only órfão continua sendo
    recuperado exatamente como antes. Sem ele, esta função poderia ter virado
    "nunca recupera nada" e ninguém perceberia.
    """
    started = _parse_ts(job.get("started_at")) or _parse_ts(job.get("created_at"))
    if started is None:
        return None
    now = now or datetime.now(timezone.utc)
    age = (now - started).total_seconds()
    return _G.decidir_recuperacao(
        job,
        idade_segundos=age,
        limite_segundos=JOB_TIMEOUT_SECONDS + STALE_MARGIN_SECONDS,
    )


async def recover_stale_jobs(supa) -> int:
    """Roda a cada tick: destrava jobs órfãos sem intervenção humana."""
    try:
        # `evidence` entra no SELECT porque é ela que responde a única pergunta
        # que importa aqui: alguma coisa já aconteceu no mundo lá fora?
        res = (supa.table("portal_jobs")
               .select("id, started_at, created_at, attempts, evidence")
               .eq("status", "running").execute())
    except Exception as e:  # noqa: BLE001
        logger.warning("[PORTAL] recover_stale_jobs indisponivel: %s", type(e).__name__)
        return 0
    recovered = 0
    for job in res.data or []:
        patch = stale_running_patch(job)
        if not patch:
            continue
        try:
            supa.table("portal_jobs").update(patch).eq("id", job["id"]).eq("status", "running").execute()
            recovered += 1
            logger.warning("[PORTAL] job orfao %s -> %s", job.get("id"), patch.get("status"))
        except Exception as e:  # noqa: BLE001
            logger.warning("[PORTAL] falha ao recuperar job orfao: %s", type(e).__name__)
    return recovered


def _supabase():
    from supabase import create_client

    url = os.getenv("SUPABASE_URL") or ""
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""
    return create_client(url, key)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _upload_portal_blob(supa, path: str, blob: bytes, content_type: str = "application/pdf") -> str | None:
    """Upload privado de evidencias/boletos do portal. Retorna storage path."""
    clean_path = str(path or "").strip().lstrip("/")
    if not clean_path or not blob:
        return None
    try:
        await asyncio.to_thread(
            lambda: supa.storage.from_("portal-evidence").upload(
                clean_path,
                blob,
                {"content-type": content_type or "application/octet-stream", "cache-control": "3600", "upsert": "true"},
            )
        )
        return clean_path
    except Exception as e:  # noqa: BLE001
        logger.warning("[PORTAL] upload portal-evidence falhou: %s", type(e).__name__)
        return None


def _session_identity(job: Dict[str, Any], account: Dict[str, Any]) -> Dict[str, str] | None:
    company_id = str(job.get("company_id") or account.get("company_id") or "").strip()
    portal_key = str(job.get("portal_key") or account.get("portal_key") or "").strip()
    account_label = str(account.get("account_label") or "default").strip() or "default"
    if not company_id or not portal_key:
        return None
    return {"company_id": company_id, "portal_key": portal_key, "account_label": account_label}


def _decode_session_blob(raw: str) -> Dict[str, Any]:
    data = json.loads(raw)
    if isinstance(data, dict) and isinstance(data.get("storage_state"), dict):
        session_storage = data.get("session_storage")
        return {
            "storage_state": data["storage_state"],
            "session_storage": session_storage if isinstance(session_storage, list) else [],
        }
    return {"storage_state": data if isinstance(data, dict) else None, "session_storage": []}


def _load_session_bundle(supa, job: Dict[str, Any], account: Dict[str, Any]) -> Dict[str, Any]:
    ident = _session_identity(job, account)
    if not ident:
        return {"storage_state": None, "session_storage": []}
    try:
        res = (
            supa.table("portal_sessions")
            .select("storage_state_encrypted, health")
            .eq("company_id", ident["company_id"])
            .eq("portal_key", ident["portal_key"])
            .eq("account_label", ident["account_label"])
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows or not rows[0].get("storage_state_encrypted"):
            return {"storage_state": None, "session_storage": []}
        from portal_worker import vault

        raw = vault.decrypt(rows[0]["storage_state_encrypted"])
        return _decode_session_blob(raw)
    except Exception as e:  # noqa: BLE001
        logger.warning("[PORTAL] falha ao carregar sessao persistida: %s", type(e).__name__)
        return {"storage_state": None, "session_storage": []}


def _load_session_state(supa, job: Dict[str, Any], account: Dict[str, Any]) -> Dict[str, Any] | None:
    state = _load_session_bundle(supa, job, account).get("storage_state")
    return state if isinstance(state, dict) else None


def _save_session_state(
    supa,
    job: Dict[str, Any],
    account: Dict[str, Any],
    storage_state: Dict[str, Any],
    session_storage: list | None = None,
) -> bool:
    ident = _session_identity(job, account)
    if not ident or not isinstance(storage_state, dict):
        return False
    try:
        from portal_worker import vault

        payload = {
            "version": 1,
            "storage_state": storage_state,
            "session_storage": session_storage if isinstance(session_storage, list) else [],
        }
        encrypted = vault.encrypt(json.dumps(payload, ensure_ascii=True, separators=(",", ":")))
        row = {
            **ident,
            "storage_state_encrypted": encrypted,
            "verified_at": _now(),
            "health": "ok",
        }
        (
            supa.table("portal_sessions")
            .upsert(row, on_conflict="company_id,portal_key,account_label")
            .execute()
        )
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("[PORTAL] falha ao salvar sessao persistida: %s", type(e).__name__)
        return False


async def _capture_session_storage(page) -> list:
    try:
        data = await page.evaluate(
            """() => ({
              origin: window.location.origin,
              entries: Object.fromEntries(Object.entries(window.sessionStorage || {}))
            })"""
        )
        if not isinstance(data, dict):
            return []
        entries = data.get("entries")
        origin = str(data.get("origin") or "").strip()
        if not origin or not isinstance(entries, dict) or not entries:
            return []
        return [{"origin": origin, "entries": entries}]
    except Exception as e:  # noqa: BLE001
        logger.warning("[PORTAL] falha ao capturar sessionStorage: %s", type(e).__name__)
        return []


async def _restore_session_storage(context, session_storage: list) -> bool:
    restored = False
    for item in session_storage or []:
        if not isinstance(item, dict):
            continue
        origin = str(item.get("origin") or "").strip()
        entries = item.get("entries")
        if not origin or not isinstance(entries, dict):
            continue
        payload = json.dumps({"origin": origin, "entries": entries}, ensure_ascii=True)
        await context.add_init_script(
            """(() => {
              const payload = %s;
              if (window.location.origin !== payload.origin) return;
              for (const [key, value] of Object.entries(payload.entries || {})) {
                window.sessionStorage.setItem(key, String(value));
              }
            })();""" % payload
        )
        restored = True
    return restored


def _hitl_kind(result, evidence: Dict[str, Any]) -> str:
    text = " ".join([
        str(getattr(result, "message", "") or ""),
        json.dumps(getattr(result, "captured", {}) or {}, ensure_ascii=True),
        json.dumps(evidence or {}, ensure_ascii=True),
    ]).lower()
    if any(token in text for token in ("captcha", "2fa", "mfa", "otp", "codigo de verificacao", "duas etapas")):
        return "captcha_2fa"
    return "review"


def _augment_hitl_evidence(result, evidence: Dict[str, Any]) -> Dict[str, Any]:
    message = str(getattr(result, "message", "") or "").strip()
    captured = getattr(result, "captured", {}) or {}
    kind = _hitl_kind(result, evidence)
    return {
        **(evidence or {}),
        **captured,
        "message": message,
        "hitl": {
            "required": True,
            "kind": kind,
            "resume_mode": "requeue_after_human",
            "reason": message or "portal pediu revisao humana",
        },
    }


async def _capture_hitl_screenshot(page) -> str | None:
    try:
        raw = await page.screenshot(type="jpeg", quality=60, full_page=False)
        if not raw:
            return None
        return "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii")
    except Exception as e:  # noqa: BLE001
        logger.warning("[PORTAL] falha ao capturar screenshot HITL: %s", type(e).__name__)
        return None


def proxy_do_portal(portal_key: str) -> Dict[str, str] | None:
    """A saída de rede para este portal — quando o IP do servidor não serve.

    📊 Por que isto existe. Medido em 12/08/2026 e confirmado na pesquisa
    pública: o Akamai (e o Cloudflare, e o DataDome) mantém lista de faixas de
    datacenter. AWS, GCP, Azure e hospedagens conhecidas chegam **pré-marcadas**
    — a recusa acontece antes da primeira requisição ser lida.

    E isso não é um problema de UMA corretora: com 100 corretoras entrando pelo
    mesmo servidor, o IP acumula reputação de robô e o bloqueio vira coletivo.
    A saída estrutural é a chamada sair por um IP residencial, e é por isso que
    a configuração é **por portal** — só o portal que exige paga o custo.

    Desligado por padrão. Sem a variável, nada muda::

        PORTAL_PROXY_HDI_CORRETOR = http://usuario:senha@host:porta
        PORTAL_PROXY_DEFAULT      = (vale para todos os que não têm o seu)

    Devolve `None` quando não há proxy — e `None` é o que o Playwright espera
    para "saia direto".
    """
    chave = re.sub(r"[^A-Z0-9]", "_", str(portal_key or "").upper())
    url = (os.getenv(f"PORTAL_PROXY_{chave}") or os.getenv("PORTAL_PROXY_DEFAULT") or "").strip()
    if not url:
        return None
    try:
        partes = urlsplit(url)
        if not partes.hostname:
            return None
        destino = f"{partes.scheme or 'http'}://{partes.hostname}"
        if partes.port:
            destino += f":{partes.port}"
        saida: Dict[str, str] = {"server": destino}
        if partes.username:
            saida["username"] = unquote(partes.username)
        if partes.password:
            saida["password"] = unquote(partes.password)
        return saida
    except Exception:  # noqa: BLE001
        # Proxy mal escrito não pode derrubar a colheita: sai direto e o job
        # conta a história pela evidência.
        return None


_UA_CACHE: Dict[str, str] = {}


async def user_agent_sem_headless(browser) -> str:
    """O User-Agent do navegador, sem a palavra que o entrega.

    📊 Medido em 12/08/2026 contra a HDI, do MESMO IP, com CONTROLE nas duas
    pontas — variando SÓ o User-Agent::

        UA limpo (Chrome/…)          PASSOU
        UA padrão (HeadlessChrome/…) BLOQUEADO
        UA limpo                     PASSOU

    O `--headless=new` conserta a impressão digital em JavaScript, mas **não**
    tira `HeadlessChrome` do cabeçalho. São dois fatores independentes, e os
    dois precisam ser corrigidos: um filtro que só lê o header derruba o
    navegador antes de qualquer JS rodar.

    Trocamos só a palavra, mantendo versão e plataforma exatamente como o
    binário as reporta. Escrever um UA à mão criaria a inconsistência que se
    quer evitar — um UA de Windows saindo de um contêiner Linux é mais
    denunciador que o `Headless` original.
    """
    versao = str(getattr(browser, "version", "") or "")
    if versao in _UA_CACHE:
        return _UA_CACHE[versao]
    ctx = await browser.new_context()
    try:
        page = await ctx.new_page()
        ua = str(await page.evaluate("() => navigator.userAgent") or "")
    finally:
        await ctx.close()
    limpo = ua.replace("HeadlessChrome", "Chrome")
    _UA_CACHE[versao] = limpo
    return limpo


async def _run_job(supa, job: Dict[str, Any]) -> None:
    from portal_worker.journeys import get_journey, motivo_para_barrar

    job_id = job["id"]
    journey_fn = get_journey(str(job.get("portal_key")), str(job.get("journey")))
    if journey_fn is None:
        supa.table("portal_jobs").update({
            "status": "failed",
            "error": f"journey desconhecida: {job.get('portal_key')}.{job.get('journey')}",
            "finished_at": _now(),
        }).eq("id", job_id).execute()
        return

    # 🔴 O FREIO POR CLASSE DE EFEITO — 18/08/2026.
    #
    # Aqui, e não no `poll_loop`, porque a pergunta é sobre ESTE job: uma
    # varredura de cobrança (READ_ONLY) tem de rodar enquanto um pedido de
    # vidro (MATERIAL_SIDE_EFFECT) fica barrado. Parar o laço inteiro,
    # que foi a primeira ideia, derrubava a cobrança junto.
    #
    # E aqui além do ponto de criação: job já enfileirado antes de alguém
    # apertar o freio não pode rodar depois. Freio que só vale para o que
    # ainda não entrou na fila não freia nada numa emergência.
    barrado = motivo_para_barrar(str(job.get("portal_key")), str(job.get("journey")))
    if barrado:
        logger.warning("[PORTAL] job %s barrado — %s", job_id, barrado)
        supa.table("portal_jobs").update({
            "status": "failed",
            "error": f"barrado pelo freio de efeito material: {barrado}",
            "finished_at": _now(),
        }).eq("id", job_id).execute()
        return

    params = dict(job.get("params") or {})
    # Credencial: se há account_id, decifra a senha do cofre (NUNCA em log/LLM).
    account_id = job.get("account_id")
    account_row: Dict[str, Any] | None = None
    if account_id:
        acc = (
            supa.table("portal_accounts")
            .select("username, secret_encrypted, account_label, portal_key, company_id")
            # 🔴 Defesa em profundidade (SPEC-073 §6.2). A busca era só por `id`,
            # e o `company_id` da conta vinha no SELECT e NUNCA era comparado com
            # o do job. O banco também não impede o cruzamento: a FK de
            # `20260706_03_spec020_portal.sql:48` é simples, não composta.
            # Filtrar aqui faz o mismatch devolver zero linhas em vez de devolver
            # a credencial da outra corretora.
            .eq("id", account_id)
            .eq("company_id", str(job.get("company_id") or ""))
            .limit(1)
            .execute()
        )
        if not acc.data:
            # Fail-closed ANTES do browser e ANTES de decifrar qualquer segredo.
            # Sem esta porta, um job da corretora A apontando para a conta da B
            # abriria o portal como B — e `_session_identity` gravaria a sessão
            # autenticada de B sob o `company_id` de A, transformando um erro
            # pontual em acesso persistente.
            logger.error("[PORTAL] job %s: conta %s nao pertence a company %s",
                         job_id, account_id, job.get("company_id"))
            supa.table("portal_jobs").update({
                "status": "failed",
                "error": "tenant_or_portal_mismatch: conta de portal nao pertence "
                         "a esta corretora — credencial NAO foi usada",
                "evidence": {"security_stop": {
                    "classe": "tenant_or_portal_mismatch",
                    "checou": ["job.company_id == account.company_id"],
                    "browser_aberto": False,
                    "credencial_usada": False,
                }},
                "finished_at": _now(),
            }).eq("id", job_id).execute()
            return

        account_row = dict(acc.data[0] or {})

        # Segunda tranca: o portal do job tem de ser o portal da conta. Uma conta
        # da Allianz não abre a HDI, mesmo sendo da corretora certa.
        if str(account_row.get("portal_key") or "") != str(job.get("portal_key") or ""):
            logger.error("[PORTAL] job %s: conta %s e do portal %s, job pede %s",
                         job_id, account_id, account_row.get("portal_key"),
                         job.get("portal_key"))
            supa.table("portal_jobs").update({
                "status": "failed",
                "error": "tenant_or_portal_mismatch: conta pertence a outro portal "
                         "— credencial NAO foi usada",
                "evidence": {"security_stop": {
                    "classe": "tenant_or_portal_mismatch",
                    "checou": ["job.portal_key == account.portal_key"],
                    "browser_aberto": False,
                    "credencial_usada": False,
                }},
                "finished_at": _now(),
            }).eq("id", job_id).execute()
            return

        from portal_worker import vault

        params.setdefault("username", account_row.get("username") or "")
        enc = account_row.get("secret_encrypted")
        if enc:
            try:
                params["password"] = vault.decrypt(enc)
            except Exception:  # noqa: BLE001
                logger.error("[PORTAL] falha ao decifrar credencial da conta")

    # 🔴 Começa do que JÁ ESTÁ no banco, não do vazio.
    #
    # `update({"evidence": ...})` substitui a coluna `jsonb` inteira — não
    # mescla. Começar em `{}` significa apagar tudo que foi gravado ali antes de
    # o worker pegar o job. E a SPEC-075 passou a gravar coisas ali antes:
    #
    #   `gateway.linhagem` / `gateway_fingerprint`  no insert do Gateway
    #   `gateway_sombra`                            logo após o insert legado
    #
    # O estrago seria silencioso e no pior lugar: o diff de sombra existe para
    # decidir o cutover, e sumiria exatamente dos jobs CONCLUÍDOS — os únicos
    # que interessa avaliar. E `gateway_fingerprint` some, o que faz
    # `IdempotencyRecord.conflita_com` tratar como "nunca conflita" (impressão
    # vazia) qualquer job que já passou pelo worker — desligando a conferência
    # do Stripe justamente para o histórico.
    #
    # 📊 Achado por juiz crítico em 16/08/2026, e confirmado no código.
    evidence: Dict[str, Any] = dict(job.get("evidence") or {}) \
        if isinstance(job.get("evidence"), dict) else {}

    # ----------------------------------------------------------------------
    # Runtime da SPEC-073 — ADITIVO. Journey antiga nunca lê `_runtime` e segue
    # funcionando igual; journey nova pega guard/profiler/checkpoint sem que a
    # assinatura `journey_fn(page, params, evidence)` mude uma vírgula.
    # ----------------------------------------------------------------------
    async def _gravar_checkpoint(patch: Dict[str, Any]) -> None:
        """Escreve em `portal_jobs.evidence` NO MEIO da execução.

        🔴 É o ponto do Bloco B6: o que a perda causa repetição material precisa
        estar no banco antes do próximo clique perigoso. Esperar o
        `JourneyResult` é o que transforma uma queda em um segundo atendimento.
        """
        atual = {**evidence, **(patch or {})}
        await asyncio.to_thread(
            lambda: supa.table("portal_jobs")
            .update({"evidence": _redigir(atual)})
            .eq("id", job_id).execute()
        )

    runtime = _montar_runtime(
        job,
        account_label=str((account_row or {}).get("account_label") or ""),
        account_id=str(account_id) if account_id else None,
        evidence=evidence,
        checkpoint=_gravar_checkpoint,
        host_portal=_host_do_portal(str(job.get("portal_key") or "")),
    )
    params["_runtime"] = runtime

    from playwright.async_api import async_playwright

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(**_launch_kwargs())
            # Locale/fuso do corretor real: apps legados Allianz derivam nomes
            # de atributos de strings localizadas e QUEBRAM no boot com en-US
            # (InvalidCharacterError em setAttribute — job c17fc7db).
            context_kwargs: Dict[str, Any] = {
                "accept_downloads": True,
                "locale": "pt-BR",
                "timezone_id": "America/Sao_Paulo",
                # Sem isto o navegador se anuncia como HeadlessChrome no
                # cabeçalho, e portal com filtro de bot recusa antes de rodar
                # uma linha de JS. Ver `user_agent_sem_headless`.
                "user_agent": await user_agent_sem_headless(browser),
                # Uma janela de tamanho plausível. O padrão do headless é
                # 800x600, que praticamente não existe em desktop real.
                "viewport": {"width": 1366, "height": 768},
            }
            evidence["user_agent_limpo"] = "HeadlessChrome" not in context_kwargs["user_agent"]
            proxy = proxy_do_portal(str(job.get("portal_key") or ""))
            if proxy:
                context_kwargs["proxy"] = proxy
                # Só o HOST, nunca usuário e senha — credencial de proxy é
                # segredo, e evidência é lida por gente.
                evidence["saida_de_rede"] = proxy.get("server")
            else:
                evidence["saida_de_rede"] = "direta (IP do servidor)"
            session_storage: list = []
            if account_row:
                session_bundle = _load_session_bundle(supa, job, account_row)
                storage_state = session_bundle.get("storage_state")
                session_storage = session_bundle.get("session_storage") or []
                if storage_state:
                    context_kwargs["storage_state"] = storage_state
                    params["session_loaded"] = True
                    evidence["session_reused"] = True
            context = await browser.new_context(**context_kwargs)
            # A Ficha de Gestão (ngx-file-management) morre no boot com
            # InvalidCharacterError ao chamar setAttribute('-') — fatal no
            # Chromium headless, inofensivo no Chrome do corretor. O shim
            # engole SÓ o atributo inválido; o app continua montando.
            await context.add_init_script(
                """(() => {
                  const orig = Element.prototype.setAttribute;
                  Element.prototype.setAttribute = function (name, value) {
                    try { return orig.call(this, name, value); }
                    catch (e) { /* atributo inválido de app legado — ignora */ }
                  };
                })();"""
            )
            if session_storage:
                evidence["session_storage_restored"] = await _restore_session_storage(context, session_storage)
            page = await context.new_page()
            # Profiler PASSIVO: só escuta eventos. Não intercepta, não altera,
            # não repete request — se ele quebrasse tráfego, o dia em que uma
            # cobrança falhasse ninguém suspeitaria do observador.
            if runtime.profiler is not None:
                runtime.profiler.attach(page)
            # Que navegador subiu, de fato. Sem isto, um portal que recusa o
            # acesso deixa duas explicações igualmente plausíveis — "o modo
            # errado" e "o IP do servidor" — e nenhuma forma de separá-las
            # sem outro deploy. A evidência tem de trazer o que foi usado.
            params["_launch_mode"] = _launch_kwargs()
            evidence["launch_mode"] = params["_launch_mode"]
            params["_job_id"] = str(job_id)
            params["_company_id"] = str(job.get("company_id") or "")
            params["_portal_key"] = str(job.get("portal_key") or "")
            # 🔴 O rótulo da conta é DADO DE TRABALHO, não enfeite de tela.
            # Na MAPFRE, um login enxerga DUAS corretoras e o `account_label`
            # guarda qual delas esta conta deve varrer — sem ele a journey não
            # tem como conferir de quem é o dado, e varrer "o que estiver
            # selecionado" é como um inadimplente de uma empresa entra no
            # cadastro da outra (CLAUDE.md §7).
            if account_row:
                params.setdefault("account_label",
                                  str(account_row.get("account_label") or ""))
            params["_upload_blob"] = lambda path, blob, content_type="application/pdf": _upload_portal_blob(
                supa, path, blob, content_type
            )
            try:
                result = await asyncio.wait_for(journey_fn(page, params, evidence), timeout=JOB_TIMEOUT_SECONDS)
            except asyncio.TimeoutError:
                raise RuntimeError(
                    f"journey excedeu o teto de {JOB_TIMEOUT_SECONDS}s (PORTAL_JOB_TIMEOUT_SECONDS)"
                ) from None
            if account_row and result.status == "done" and (result.captured or {}).get("logged_in"):
                state = await context.storage_state()
                session_storage = await _capture_session_storage(page)
                evidence["session_storage_captured"] = bool(session_storage)
                evidence["session_saved"] = _save_session_state(
                    supa, job, account_row, state, session_storage=session_storage
                )
            screenshots = list(result.screenshots or [])
            if result.status == "needs_human":
                hitl_shot = await _capture_hitl_screenshot(page)
                if hitl_shot:
                    screenshots.insert(0, hitl_shot)
                evidence = _augment_hitl_evidence(result, evidence)
            await browser.close()
    except Exception as e:  # noqa: BLE001
        # 🔴 Falhar DEPOIS de um efeito material não é a mesma coisa que falhar
        # antes. Se a journey armou um efeito e o processo caiu no meio, o
        # desfecho honesto é "não sei", e `unknown` é o estado que impede o
        # recovery de recomeçar do passo 1.
        if _G.fase_do_efeito(evidence) in (_G.FASE_ARMED, _G.FASE_SUBMITTED):
            ef = dict(_G.efeito_critico(evidence) or {})
            ef["phase"] = _G.FASE_UNKNOWN
            ef["reason"] = f"excecao apos armar o efeito: {type(e).__name__}"
            evidence[_G.CHAVE_EFEITO] = ef
        evidence.update(runtime.selar_evidencia())

        # 🔴 `failed` NÃO é um status neutro: é a válvula de escape do dedup.
        # `portal_tool._buscar_pedido_vivo` filtra com `.neq("status","failed")`,
        # e o índice único parcial `idx_portal_jobs_pedido_vivo` usa o MESMO
        # predicado. Ou seja: gravar `failed` aqui APAGA a chave de idempotência
        # deste pedido, e o próximo `portal_action` com a mesma chave entra.
        #
        # Isso era correto enquanto `failed` só acontecia antes de qualquer
        # escrita — a premissa que a SPEC-065 §7.2 escreveu. A SPEC-074 quebrou
        # essa premissa: agora existe efeito material dentro da journey, e o
        # bloco logo acima já rebaixou a fase para `unknown` justamente porque
        # SABE que houve. Gravar `failed` sabendo disso é liberar o segundo
        # pedido, pago, no nome do mesmo segurado.
        #
        # `needs_human` mantém o pedido VIVO para o dedup e é o único status que
        # o botão de retry do dashboard aceita — onde `pode_retentar_pelo_
        # dashboard` já faz a conferência de efeito antes de deixar repetir.
        houve_efeito = not _G.pode_repetir_com_seguranca(evidence)
        status_final = "needs_human" if houve_efeito else "failed"

        supa.table("portal_jobs").update({
            "status": status_final,
            "error": f"{type(e).__name__}: {str(e)[:300]}",
            "evidence": _redigir(evidence),
            "finished_at": _now(),
        }).eq("id", job_id).execute()
        return

    # O envelope da SPEC-073 H1 é ADITIVO: journey antiga continua gravando a
    # evidência menor que sempre gravou, e ganha `runtime`/`execution` por cima.
    evidence.update(runtime.selar_evidencia())
    final = (evidence if result.status == "needs_human"
             else {**evidence, **(result.captured or {}), "message": result.message})
    supa.table("portal_jobs").update({
        "status": result.status,
        "evidence": _redigir(final),
        "screenshots": screenshots,
        "error": None,  # limpa nota de requeue de tentativa anterior
        "finished_at": _now(),
    }).eq("id", job_id).execute()
    logger.info("[PORTAL] %s", _R.linha_de_log(
        job=job_id, portal=job.get("portal_key"), journey=job.get("journey"),
        status=result.status,
        layer=runtime.escada.resumo().get("layer_final") or "dom",
        fallback=runtime.escada.resumo().get("fallback_count"),
        efeito=_G.fase_do_efeito(evidence) or None,
    ))


def _marcar_lease_perdida(supa, job: dict) -> None:
    """O job foi abortado por perda de posse da conta. Ele NÃO volta para a fila.

    🔴 `queued` seria a resposta errada e a mais tentadora: o job "não terminou",
    então parece natural devolvê-lo. Mas ele foi cancelado no meio, e ninguém
    sabe onde — pode ter clicado, pode não ter. Requeue de um job que talvez
    tenha tocado o portal é o mesmo defeito que a SPEC-074 fechou: a segunda
    operação, no nome do mesmo segurado.

    `needs_human` mantém o pedido vivo para o dedup de idempotência e é o único
    status que o botão de retry do dashboard aceita — onde
    `pode_retentar_pelo_dashboard` confere a evidência antes de deixar repetir.
    """
    try:
        supa.table("portal_jobs").update({
            "status": "needs_human",
            "error": ("lease da conta perdida durante a execucao: outro worker "
                      "pode ter assumido a mesma sessao. NAO reexecute sem "
                      "conferir o que ficou no portal."),
            "finished_at": _now(),
        }).eq("id", job["id"]).execute()
    except Exception:  # noqa: BLE001
        logger.error("[PORTAL] nao consegui marcar o job %s como lease perdida",
                     job.get("id"))


def _candidatos_da_fila(supa, limite: int) -> list:
    """Os próximos jobs da fila, na melhor ordem que o schema permitir.

    🔴 Esta função tem de funcionar ANTES e DEPOIS da migration da SPEC-075.
    O portal-worker é um serviço separado que sobe com a imagem nova enquanto o
    banco ainda pode não ter as colunas novas — é o desalinhamento que a
    CLAUDE.md §9.1 registra como causa real de queda. Então: tenta a ordenação
    por prioridade; se o banco recusar (coluna inexistente), cai para a
    ordenação de sempre e segue trabalhando.

    A ordem nova é `priority ASC, created_at ASC`, e `available_at` no passado
    ou nulo. 📊 Hoje o worker é FIFO puro, o que significa que uma varredura de
    cobrança de 200 apólices enfileirada às 3h fica na frente do acionamento de
    um segurado com o carro parado às 9h.
    """
    agora = _now()
    try:
        r = (supa.table("portal_jobs").select("*")
             .eq("status", "queued")
             .or_(f"available_at.is.null,available_at.lte.{agora}")
             .order("priority").order("created_at")
             .limit(limite).execute())
        return list(r.data or [])
    except Exception:  # noqa: BLE001
        # Banco ainda sem as colunas da 075. Comportamento de ontem, intacto.
        r = (supa.table("portal_jobs").select("*")
             .eq("status", "queued").order("created_at")
             .limit(limite).execute())
        return list(r.data or [])


def _tentar_claim(supa, job: dict) -> bool:
    """Claim atômico `queued -> running`. `False` = outro worker levou."""
    claim = supa.table("portal_jobs").update({
        "status": "running", "started_at": _now(),
        "attempts": int(job.get("attempts") or 0) + 1,
    }).eq("id", job["id"]).eq("status", "queued").execute()
    return bool(claim.data)


async def run_once(supa) -> int:
    """Pega 1 job queued (claim atômico queued->running) e roda. Retorna 0 ou 1.

    Mantida com o mesmo nome e o mesmo contrato: é o caminho de
    `concurrency=1`, e Gate D da SPEC-075 exige que ele continue **idêntico**
    ao baseline. Quem quer paralelismo chama `run_lote`.
    """
    jobs = _candidatos_da_fila(supa, 1)
    if not jobs:
        return 0
    job = jobs[0]
    if not _tentar_claim(supa, job):
        return 0  # outro worker levou
    await _run_job(supa, job)
    return 1


async def run_lote(supa, concorrencia: int) -> int:
    """Roda até `concorrencia` jobs em paralelo, um por conta.

    🔴 A regra que não pode ser afrouxada: **a mesma conta nunca roda duas
    vezes ao mesmo tempo.** Cada conta tem uma sessão de navegador persistida
    (`portal_sessions.storage_state_encrypted`); dois jobs da mesma conta em
    paralelo se sobrescrevem, e o resultado é uma sessão corrompida que derruba
    a corretora do portal — não um job perdido.

    Contas DIFERENTES podem rodar juntas, e é daí que vem o ganho: seis
    seguradoras varridas em paralelo em vez de em fila.

    Sem Redis não há lease, e sem lease não há como garantir a regra acima
    entre processos. Nesse caso a concorrência **cai para 1** e o `UPDATE`
    condicional do Supabase volta a ser suficiente — ver
    `leases.politica_com_redis_fora`. Redis fora nunca vira paralelismo sem
    trava.
    """
    from portal_worker import leases as _L

    efetiva, motivo = _L.politica_com_redis_fora(concorrencia) \
        if not _L.redis_disponivel() else (concorrencia, "")
    if motivo:
        logger.warning("[PORTAL] %s", motivo)
    if efetiva <= 1:
        return await run_once(supa)

    # Busca mais candidatos que slots: alguns vão cair no lease de conta.
    candidatos = _candidatos_da_fila(supa, efetiva * 3)
    if not candidatos:
        return 0

    lease = _L.LeaseDePortal()
    dono = _L.identidade_do_worker()
    escolhidos: list = []
    contas_tomadas: list = []

    for job in candidatos:
        if len(escolhidos) >= efetiva:
            break
        chave = _L.chave_de_conta(job.get("company_id"), job.get("portal_key"),
                                  job.get("account_id") or "")
        if chave in contas_tomadas:
            continue  # já peguei um job desta conta neste lote
        if not lease.adquirir(chave, dono, _L.LEASE_DURACAO_SEGUNDOS):
            continue  # outro worker está nesta conta
        if not _tentar_claim(supa, job):
            lease.liberar(chave, dono)  # perdi a corrida do claim; devolvo a conta
            continue
        escolhidos.append((job, chave))
        contas_tomadas.append(chave)

    if not escolhidos:
        return 0

    async def _rodar(job: dict, chave: str) -> None:
        # A renovação corre em paralelo: um job pode levar até
        # JOB_TIMEOUT_SECONDS (1200s) e a lease dura 120s. Sem heartbeat, a
        # conta seria liberada no meio do trabalho e um segundo worker entraria
        # na mesma sessão — exatamente o que a lease existe para impedir.
        parar = asyncio.Event()
        perdeu_a_posse = asyncio.Event()

        async def _bater():
            while not parar.is_set():
                try:
                    await asyncio.wait_for(parar.wait(),
                                           timeout=_L.HEARTBEAT_INTERVALO_SEGUNDOS)
                except asyncio.TimeoutError:
                    # 🔴 O RETORNO IMPORTA, e a primeira versão deste bloco o
                    # descartava.
                    #
                    # `renovar()` devolve `False` quando a lease já **não é
                    # mais desta** worker: ela venceu e outro processo assumiu
                    # a conta. Ignorar esse `False` deixa este job continuar
                    # clicando numa sessão que outro worker já tomou — que é
                    # exatamente a colisão que o Bloco N foi escrito para
                    # impedir, agora com dois navegadores sobrescrevendo o
                    # mesmo `portal_sessions.storage_state_encrypted`.
                    #
                    # E o cenário não é exótico: a lease dura 120s e o job pode
                    # levar 1200s. Basta o event loop ficar sem ceder controle
                    # por mais que o TTL — uma etapa síncrona longa, um GC
                    # pause, contenção de CPU no contêiner — para a chave
                    # expirar com o job vivo.
                    if not lease.renovar(chave, dono, _L.LEASE_DURACAO_SEGUNDOS):
                        logger.error(
                            "[PORTAL] perdi a lease da conta durante o job %s "
                            "— abortando para nao colidir com outro worker",
                            job.get("id"))
                        perdeu_a_posse.set()
                        return

        batida = asyncio.create_task(_bater())
        tarefa = asyncio.create_task(_run_job(supa, job))
        try:
            aguardar_perda = asyncio.create_task(perdeu_a_posse.wait())
            feito, _pendentes = await asyncio.wait(
                {tarefa, aguardar_perda}, return_when=asyncio.FIRST_COMPLETED)
            if tarefa not in feito:
                # Perdemos a conta antes de o job terminar. Cancelar é a única
                # saída segura — mas o job pode já ter tocado o portal, então
                # ele NÃO volta para `queued`: vai para `needs_human` com a
                # fase de efeito preservada, e quem decide é gente.
                tarefa.cancel()
                try:
                    await tarefa
                except (asyncio.CancelledError, Exception):  # noqa: BLE001
                    pass
                _marcar_lease_perdida(supa, job)
            else:
                aguardar_perda.cancel()
                await tarefa  # propaga exceção, se houver
        finally:
            parar.set()
            batida.cancel()
            # Só libera se ainda formos donos — `liberar` já confere por dentro,
            # e liberar lease de outro é o bug clássico do lock distribuído.
            lease.liberar(chave, dono)

    await asyncio.gather(*[_rodar(j, c) for j, c in escolhidos],
                         return_exceptions=True)
    return len(escolhidos)


async def poll_loop() -> None:
    """Loop principal. Nunca derruba o processo. Standby se o gate estiver off."""
    if not portal_real_enabled():
        logger.info("[PORTAL] standby (PORTAL_REAL_ENABLED=false) — não executa jobs")
        return
    logger.info("[PORTAL] worker iniciado (poll %ss)", POLL_SECONDS)
    # 🔴 Dito UMA vez, no boot, e não a cada volta: se a variável não existe
    # neste processo, o freio de emergência não está ligado na roda. Sem esta
    # linha a ausência é indistinguível de "desligado de propósito" — ver
    # `runtime.kill_switch_ativo`.
    if not kill_switch_presente():
        logger.warning(
            "[PORTAL] GLOBAL_KILL_SWITCH AUSENTE do ambiente — o freio de "
            "emergencia NAO alcanca este worker. Defina a variavel (mesmo que "
            "como 'false') para que apertar o freio funcione."
        )
    while True:
        try:
            # 🔴 O freio que não estava ligado na roda (SPEC-073, achado de
            # auditoria). `GLOBAL_KILL_SWITCH` existia, estava `true` no
            # ambiente e era lido SÓ pelo Next.js — `grep GLOBAL_KILL_SWITCH
            # backend/` devolvia vazio. Quem apertasse numa emergência veria a
            # tela dizer "parado" com o worker ainda entrando em portal.
            #
            # Ele é checado DENTRO do laço, não na entrada: um freio que só vale
            # no boot obriga a reiniciar o serviço para frear, e é justamente na
            # emergência que ninguém quer reiniciar nada.
            if kill_switch_ativo():
                logger.warning("[PORTAL] GLOBAL_KILL_SWITCH ativo — nenhum job sera pego")
                await asyncio.sleep(POLL_SECONDS)
                continue
            supa = _supabase()
            await recover_stale_jobs(supa)
            # SPEC-075 Bloco N. `concorrencia_configurada()` é lida A CADA VOLTA,
            # não no boot: subir a concorrência numa emergência não pode exigir
            # reiniciar o serviço, pela mesma razão que o kill switch é lido
            # aqui dentro e não na entrada.
            from portal_worker.leases import concorrencia_configurada

            n = await run_lote(supa, concorrencia_configurada())
            if n:
                logger.info(f"[PORTAL] processou {n} job(s)")
        except Exception as e:  # noqa: BLE001
            logger.error(f"[PORTAL] loop falhou: {type(e).__name__}: {str(e)[:200]}")
        await asyncio.sleep(POLL_SECONDS)
