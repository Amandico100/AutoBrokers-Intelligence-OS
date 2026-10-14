# -*- coding: utf-8 -*-
"""SPEC-132-C C2 — o TURNO do atalho: o MESMO agente CORE e a MESMA engine do chat principal (D-132C-04).

    agente_core(db, company_id)                          o agente CORE ativo da corretora (`agent_role='core'`)
    conversa_do_membro(db, company_id, user_id, ...)     a conversa ATIVA do canal (uma por membro por corretora)
    mensagens_de_hoje(db, company_id, user_id)           quantas o membro mandou hoje por aqui (o teto)
    async subir_midia(db, integracao, company_id, user_id, normalizado)   a mídia → Storage → `attachments`
    async rodar(db, integracao, telefone, membro, normalizado)            o turno inteiro, até a resposta enviada

O FIO deste módulo (SPEC-132-C §2): conversa do canal → a PERGUNTA gravada em `messages` como o BFF do painel grava
(`app/api/chat/stream/route.ts` §4) → anexos no prefixo `<company_id>/<user_id>/<bucket>/` → **o próprio handler
`POST /chat/stream`, em processo** (ASGI, `X-Internal-Key` = modo painel, `channel` do atalho, `options.esforco`)
→ os eventos tipados até `turn.completed` → `envio.enviar_texto` pela instância do AutoBrokers.

🔴 POR QUE O HANDLER E NÃO `stream_agent_eventos` DIRETO: o handler já é o dono de tudo o que um turno do chat tem —
a conversa conferida contra a corretora, a porteira de crédito, o guardrail (a máscara), os anexos lidos por bytes
(`chat_anexos.preparar`, com o prefixo conferido DE NOVO), o esforço, a gravação da resposta (`_persistir`, com
`payload.turn`), as peças do Artifact Hub e a junção das tool calls. Chamar o grafo direto obrigaria a copiar essas
oito coisas — e a cópia é o motor paralelo (CLAUDE.md §5). O preço: o turno passa pelo limitador do `/chat/stream`
(100/min) — com a chave do membro (`X-Forwarded-For: atalho-<user_id>`), não a de um IP compartilhado.

🔴 O membro — `company_id` E `user_id` — vem de `verificacao.membros_verificados_por_telefone` (o número VERIFICADO),
nunca do texto. Toda leitura e escrita filtra os dois (CLAUDE.md §7) e o CINTO descarta em Python a linha de outra
empresa que volte do banco.
⛔ Nenhum telefone, nome de arquivo ou conteúdo em log.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

#: 🔴 O CANAL da conversa do atalho. NÃO é `'whatsapp'`: esse valor é o do ATENDIMENTO (o segurado) — a Central de
#: Atendimento (`app/api/dashboard/conversas/route.ts:54`), a lista de segurados (`atendimentos/segurados/route.ts:31`),
#: o espelho e o histórico do segurado filtram `channel='whatsapp'`, e a conversa PRIVADA do corretor com o assistente
#: apareceria para a equipe inteira como se fosse um cliente. O Histórico do chat principal lista por `user_id`
#: (`app/api/conversations/route.ts:197`, sem filtro de canal) — é lá que ela aparece. A coluna é `text` sem CHECK
#: (`schema_completo.sql:1031`, default 'web'). D-132C-05 (proposta, nota 88 × 'whatsapp' 35).
CANAL_DO_ATALHO = "whatsapp_assistente"
#: 💭 uma conversa nova depois de 12 h de silêncio
JANELA_DA_CONVERSA = timedelta(hours=12)
#: 💭 o teto de mensagens por membro por dia (o dia de Brasília)
TETO_DE_MENSAGENS_POR_DIA = 200
#: o esforço do turno pelo WhatsApp (as escolhas são as do chat: rapido · equilibrado · maximo)
ESFORCO_DO_ATALHO = "equilibrado"
#: 💭 quanto o turno pode durar (o chat com ferramentas leva minutos nos piores casos)
TEMPO_DO_TURNO_S = 300.0
#: 💭 de quanto em quanto tempo o "digitando…" é renovado (o WhatsApp o apaga sozinho em ~25 s)
RENOVAR_DIGITANDO_S = 20.0
#: o teto de um arquivo (o mesmo do upload e do `chat_anexos`)
LIMITE_DE_BYTES = 20 * 1024 * 1024
FUSO = timezone(timedelta(hours=-3))

FRASE_SEM_AGENTE = ("O AutoBrokers da {corretora} ainda não está ligado para conversar. "
                    "Peça para quem administra a sua corretora ativar o assistente no painel.")
FRASE_SEM_RESPOSTA = "Não consegui responder agora. Pode mandar de novo daqui a pouco?"
FRASE_ARQUIVO_FALHOU = "Não consegui abrir o arquivo que você mandou. Pode mandar de novo?"
FRASE_ARQUIVO_GRANDE = "Esse arquivo passa de 20 MB e não consigo ler por aqui. Mande uma versão menor ou use o painel."

_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


@dataclass
class ResultadoDoTurno:
    """O que o turno fez — para o log e para os testes (sem conteúdo)."""
    status: str                       # respondido · sem_agente · sem_resposta · sem_chave · arquivo_falhou · erro
    company_id: str = ""
    user_id: str = ""
    conversation_id: Optional[str] = None
    enviadas: int = 0
    texto: str = ""
    entregas: List[Dict[str, Any]] = field(default_factory=list)


# =====================================================================================================================
# miúdos
# =====================================================================================================================
def _dados(r: Any) -> List[Dict[str, Any]]:
    return [x for x in list(getattr(r, "data", None) or []) if isinstance(x, dict)]


def _id(v: Any, oque: str) -> str:
    s = str(v or "").strip().lower()
    if not _UUID.match(s):
        raise ValueError(f"{oque} precisa ser um uuid")
    return s


def _mesma(a: Any, b: str) -> bool:
    return str(a or "").strip().lower() == b


def _agora(agora: Optional[datetime] = None) -> datetime:
    return (agora or datetime.now(timezone.utc)).astimezone(timezone.utc)


def _quando(v: Any) -> Optional[datetime]:
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    try:
        d = datetime.fromisoformat(str(v or "").strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _mascarar(telefone: Any) -> str:
    from app.services.canal.repositorio import mascarar

    return mascarar(telefone)


# =====================================================================================================================
# o agente e a conversa
# =====================================================================================================================
def agente_core(db: Any, company_id: Any) -> Optional[str]:
    """O agente CORE ATIVO da corretora (`agents.agent_role='core'`). Nunca o de atendimento: aquele fala com o
    SEGURADO. Nenhum → None (o turno responde a frase, sem inventar agente)."""
    cid = _id(company_id, "company_id")
    linhas = _dados(db.table("agents").select("id, company_id, is_active, agent_role")
                    .eq("company_id", cid).eq("is_active", True).eq("agent_role", "core").limit(5).execute())
    linhas = [x for x in linhas if _mesma(x.get("company_id"), cid) and x.get("is_active") is True
              and str(x.get("agent_role") or "").strip().lower() == "core" and _UUID.match(str(x.get("id") or ""))]
    return str(linhas[0]["id"]).lower() if linhas else None


def conversa_ativa(db: Any, company_id: Any, user_id: Any, *, agora: Optional[datetime] = None
                   ) -> Optional[Dict[str, Any]]:
    """A conversa ATIVA do atalho deste membro nesta corretora: canal do atalho, não encerrada e com atividade nas
    últimas 💭 12 h. Nenhuma → None."""
    cid, uid = _id(company_id, "company_id"), _id(user_id, "user_id")
    t0 = _agora(agora)
    linhas = _dados(db.table("conversations")
                    .select("id, company_id, user_id, session_id, agent_id, channel, status, last_message_at, "
                            "created_at")
                    .eq("company_id", cid).eq("user_id", uid).eq("channel", CANAL_DO_ATALHO)
                    .order("last_message_at", desc=True).limit(5).execute())
    linhas = [x for x in linhas if _mesma(x.get("company_id"), cid) and _mesma(x.get("user_id"), uid)
              and x.get("channel") == CANAL_DO_ATALHO and str(x.get("status") or "").lower() != "closed"
              and x.get("session_id")]
    for linha in linhas:
        quando = _quando(linha.get("last_message_at")) or _quando(linha.get("created_at"))
        if quando and t0 - quando <= JANELA_DA_CONVERSA:
            return linha
    return None


def conversa_do_membro(db: Any, company_id: Any, user_id: Any, agente_id: str, *, titulo: str = "",
                       agora: Optional[datetime] = None) -> Dict[str, Any]:
    """A conversa ATIVA (ou uma NOVA) do atalho: `user_id` = o membro, `company_id` = a corretora DELE, o agente CORE.
    A nova nasce com `last_message_at` = agora (o turno seguinte a acha, mesmo antes da resposta)."""
    cid, uid = _id(company_id, "company_id"), _id(user_id, "user_id")
    t0 = _agora(agora)
    linha = conversa_ativa(db, cid, uid, agora=t0)
    if linha:
        patch: Dict[str, Any] = {"last_message_at": t0.isoformat()}
        if agente_id and str(linha.get("agent_id") or "").lower() != agente_id:
            patch["agent_id"] = agente_id
            linha["agent_id"] = agente_id
        db.table("conversations").update(patch).eq("id", linha["id"]).eq("company_id", cid).execute()
        return linha
    nova = {
        "user_id": uid,
        "company_id": cid,
        "agent_id": agente_id,
        "session_id": str(uuid.uuid4()),
        "title": (titulo or "Pelo WhatsApp").strip()[:50] or "Pelo WhatsApp",
        "status": "open",
        "channel": CANAL_DO_ATALHO,
        "last_message_at": t0.isoformat(),
    }
    criadas = [x for x in _dados(db.table("conversations").insert(nova).execute()) if _mesma(x.get("company_id"), cid)]
    if not criadas or not criadas[0].get("id"):
        raise RuntimeError("conversa do atalho não criada")
    return criadas[0]


def tocar_conversa(db: Any, conversation_id: str, company_id: Any, *, agora: Optional[datetime] = None) -> None:
    """Marca a conversa como a mais recente (a escolha da corretora passa a valer por ela)."""
    cid = _id(company_id, "company_id")
    db.table("conversations").update({"last_message_at": _agora(agora).isoformat()}) \
        .eq("id", str(conversation_id)).eq("company_id", cid).execute()


def mensagens_de_hoje(db: Any, company_id: Any, user_id: Any, *, agora: Optional[datetime] = None) -> int:
    """Quantas mensagens o membro mandou HOJE (dia de Brasília) pelo atalho NESTA corretora — contadas em `messages`
    (a verdade durável; sobrevive a um Redis que reinicia). Erro de banco sobe (quem chama decide: cala)."""
    cid, uid = _id(company_id, "company_id"), _id(user_id, "user_id")
    t0 = _agora(agora)
    inicio_do_dia = datetime.combine(t0.astimezone(FUSO).date(), datetime.min.time(), tzinfo=FUSO)
    conversas = _dados(db.table("conversations").select("id, company_id, user_id, channel, last_message_at")
                       .eq("company_id", cid).eq("user_id", uid).eq("channel", CANAL_DO_ATALHO)
                       .gte("last_message_at", inicio_do_dia.astimezone(timezone.utc).isoformat()).execute())
    ids = sorted({str(x["id"]) for x in conversas if _mesma(x.get("company_id"), cid) and _mesma(x.get("user_id"), uid)
                  and x.get("channel") == CANAL_DO_ATALHO and x.get("id")})
    if not ids:
        return 0
    linhas = _dados(db.table("messages").select("id, conversation_id, role, created_at")
                    .in_("conversation_id", ids).eq("role", "user")
                    .gte("created_at", inicio_do_dia.astimezone(timezone.utc).isoformat())
                    .limit(TETO_DE_MENSAGENS_POR_DIA + 5).execute())
    return len([x for x in linhas if str(x.get("conversation_id")) in ids and x.get("role") == "user"])


# =====================================================================================================================
# a mídia
# =====================================================================================================================
_EXT_DA_IMAGEM = {"image/png": ".png", "image/webp": ".webp", "image/gif": ".gif", "image/heic": ".heic",
                  "image/heif": ".heif"}
_EXT_DO_AUDIO = {"audio/mpeg": ".mp3", "audio/mp4": ".m4a", "audio/aac": ".aac", "audio/wav": ".wav",
                 "audio/webm": ".webm"}
_EXT_DO_DOCUMENTO = {"application/pdf": ".pdf", "text/plain": ".txt", "text/csv": ".csv",
                     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
                     "application/vnd.ms-excel": ".xls",
                     "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
                     "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx"}


def _extensao(kind: str, mime: str, nome: str) -> str:
    ext = os.path.splitext(str(nome or ""))[1].lower()
    if ext and re.fullmatch(r"\.[a-z0-9]{1,8}", ext):
        return ext
    if kind == "image":
        return _EXT_DA_IMAGEM.get(mime, ".jpg")
    if kind == "audio":
        return _EXT_DO_AUDIO.get(mime, ".ogg")
    return _EXT_DO_DOCUMENTO.get(mime, ".pdf")


def _mime_padrao(kind: str) -> str:
    return {"image": "image/jpeg", "audio": "audio/ogg", "document": "application/pdf"}.get(kind, "application/octet-stream")


async def _bytes_da_midia(integracao: Dict[str, Any], normalizado: Dict[str, Any]) -> Optional[tuple]:
    """(bytes, mime): o base64 que veio no evento, senão o download do Evolution GO pelo MESMO leitor do webhook e do
    observador (`atlas.observer_media._download_media`, que exige a mensagem crua inteira). Nunca levanta."""
    media = normalizado.get("media") or {}
    bruto = str(media.get("base64") or "")
    if bruto:
        try:
            if bruto.startswith("data:") and "," in bruto[:100]:
                bruto = bruto.split(",", 1)[1]
            return base64.b64decode(bruto), str(media.get("mimetype") or "")
        except Exception:  # noqa: BLE001
            pass
    if not normalizado.get("raw_message"):
        return None
    try:
        from app.services.atlas.observer_media import _download_media

        return await _download_media(integracao, normalizado["raw_message"])
    except Exception as erro:  # noqa: BLE001 — mídia nunca derruba o turno
        logger.error("[ATALHO] mídia não baixada (%s)", type(erro).__name__)
        return None


async def subir_midia(db: Any, integracao: Dict[str, Any], company_id: Any, user_id: Any,
                      normalizado: Dict[str, Any]) -> Dict[str, Any]:
    """A mídia do WhatsApp → o Storage DA CORRETORA DO MEMBRO (`<company_id>/<user_id>/<bucket>/<uuid>.<ext>`, o
    prefixo que o upload do painel usa e que `chat_anexos` confere) → o anexo `{bucket, path, nome, mime, bytes}`.
    Imagem → `chat-media`; documento e áudio → `chat-docs`. Devolve `{"anexo": …}` ou `{"aviso": frase}`."""
    cid, uid = _id(company_id, "company_id"), _id(user_id, "user_id")
    media = normalizado.get("media") or {}
    kind = str(media.get("kind") or "")
    if kind not in ("image", "document", "audio"):
        return {}
    baixado = await _bytes_da_midia(integracao, normalizado)
    if not baixado or not baixado[0]:
        return {"aviso": FRASE_ARQUIVO_FALHOU}
    blob, mime = baixado
    if len(blob) > LIMITE_DE_BYTES:
        return {"aviso": FRASE_ARQUIVO_GRANDE}
    mime = (str(mime or media.get("mimetype") or "").split(";")[0].strip().lower()) or _mime_padrao(kind)
    nome = str(media.get("file_name") or "").strip()
    ext = _extensao(kind, mime, nome)
    if not nome:
        nome = {"image": "foto", "audio": "audio", "document": "documento"}[kind] + ext
    bucket = "chat-media" if kind == "image" else "chat-docs"
    path = f"{cid}/{uid}/{bucket}/{uuid.uuid4().hex}{ext}"

    def _subir() -> None:
        db.storage.from_(bucket).upload(path, blob, {"content-type": mime, "cache-control": "3600"})

    try:
        await asyncio.to_thread(_subir)
    except Exception as erro:  # noqa: BLE001
        logger.error("[ATALHO] mídia não gravada no storage (%s)", type(erro).__name__)
        return {"aviso": FRASE_ARQUIVO_FALHOU}
    # eslint-equivalente do BFF: sem caractere de controle, até 200
    nome_limpo = re.sub(r"[\x00-\x1f\x7f]", "", nome).strip()[:200] or "arquivo"
    return {"anexo": {"bucket": bucket, "path": path, "nome": nome_limpo, "mime": mime[:100], "bytes": len(blob)}}


# =====================================================================================================================
# a pergunta (como o BFF grava) e a chamada ao chat
# =====================================================================================================================
def gravar_pergunta(db: Any, conversa: Dict[str, Any], company_id: str, texto: str, anexos: List[Dict[str, Any]],
                    client_request_id: str) -> Optional[str]:
    """A PERGUNTA em `messages`, com a MESMA forma do BFF (`app/api/chat/stream/route.ts` §4): `role='user'`,
    `type='text'`, `payload.client_request_id` no topo (o índice único do turno), `payload.turn.submitted_at` e as
    fichas dos anexos (nunca o conteúdo). + `payload.origem` (de onde veio)."""
    cid = _id(company_id, "company_id")
    if not _mesma(conversa.get("company_id"), cid):
        raise RuntimeError("a conversa não é desta corretora")
    conteudo = texto if texto else (f"[Anexo] {', '.join(a['nome'] for a in anexos)}" if anexos else "")
    payload: Dict[str, Any] = {"client_request_id": client_request_id,
                               "turn": {"submitted_at": _agora().isoformat()},
                               "origem": CANAL_DO_ATALHO}
    if anexos:
        payload["attachments"] = [{"nome": a["nome"], "mime": a["mime"], "bytes": a["bytes"], "path": a["path"],
                                   "bucket": a["bucket"]} for a in anexos]
    linhas = _dados(db.table("messages").insert({"conversation_id": conversa["id"], "role": "user",
                                                 "content": conteudo, "type": "text", "image_url": None,
                                                 "payload": payload}).execute())
    return str(linhas[0]["id"]) if linhas and linhas[0].get("id") else None


def _chave_interna() -> Optional[str]:
    """A chave que faz o handler tratar o pedido como o BFF (modo painel) — a MESMA lista de `app.core.auth`."""
    from app.core.auth import _chaves_internas

    chaves = sorted(_chaves_internas())
    return chaves[0] if chaves else None


def _aplicacao():
    """O app ASGI do backend (o MESMO processo). Os testes trocam por um app com o router do chat."""
    import importlib

    return importlib.import_module("app.main").app


def _eventos_do_sse(texto: str) -> List[Dict[str, Any]]:
    eventos = []
    for linha in str(texto or "").splitlines():
        if not linha.startswith("data: "):
            continue
        bruto = linha[6:].strip()
        if not bruto or bruto == "[DONE]":
            continue
        try:
            ev = json.loads(bruto)
        except ValueError:
            continue
        if isinstance(ev, dict):
            eventos.append(ev)
    return eventos


@dataclass
class _Resposta:
    texto: str = ""
    aviso: str = ""
    entregas: List[Dict[str, Any]] = field(default_factory=list)
    status: str = ""


def _ler_o_turno(eventos: List[Dict[str, Any]]) -> _Resposta:
    """Os eventos tipados do turno (o contrato da SPEC-096/132-A): o conteúdo COMPLETO (ou os deltas), as peças, o
    aviso humano de política/erro e o status final."""
    r = _Resposta()
    deltas: List[str] = []
    for ev in eventos:
        tipo, carga = ev.get("type"), ev.get("payload") or {}
        if tipo == "assistant.content.delta":
            deltas.append(str(carga.get("text") or ""))
        elif tipo == "assistant.content.completed":
            r.texto = str(carga.get("content") or "")
        elif tipo == "artifact.ready":
            r.entregas.append({"title": carga.get("title"), "kind_human": carga.get("kind_human"),
                               "href": carga.get("href")})
        elif tipo in ("notice", "policy.blocked", "error"):
            r.aviso = r.aviso or str(carga.get("message_human") or "")
        elif tipo == "turn.completed":
            r.status = str(carga.get("status") or "")
    if not r.texto:
        r.texto = "".join(deltas)
    return r


async def chamar_o_chat(corpo: Dict[str, Any], *, chave: str, user_id: str) -> _Resposta:
    """O turno pela ENGINE do chat: `POST /chat/stream` no próprio processo, modo painel."""
    import httpx

    transporte = httpx.ASGITransport(app=_aplicacao())
    async with httpx.AsyncClient(transport=transporte, base_url="http://atalho.interno",
                                 timeout=TEMPO_DO_TURNO_S) as cliente:
        r = await cliente.post("/chat/stream", json=corpo,
                               headers={"X-Internal-Key": chave, "X-Forwarded-For": f"atalho-{user_id}"})
    if r.status_code >= 400:
        logger.error("[ATALHO] o chat recusou o turno (http_%s)", r.status_code)
        return _Resposta(status=f"http_{r.status_code}")
    return _ler_o_turno(_eventos_do_sse(r.text))


def _com_as_entregas(texto: str, entregas: List[Dict[str, Any]]) -> str:
    """As peças que o turno publicou viram LINK no fim (no painel elas são cartões; no WhatsApp, texto)."""
    from app.services.atalho.envio import _absoluto

    linhas = []
    for e in entregas or []:
        href = _absoluto(str(e.get("href") or ""))
        if not href or href in texto:
            continue
        titulo = str(e.get("title") or e.get("kind_human") or "Entrega").strip()
        linhas.append(f"{titulo}: {href}")
    if not linhas:
        return texto
    return (texto.rstrip() + "\n\n" if texto.strip() else "") + "\n".join(linhas)


async def _renovar_digitando(integracao: Dict[str, Any], telefone: str, parar: asyncio.Event) -> None:
    from app.services.atalho.envio import digitando

    while not parar.is_set():
        await digitando(integracao, telefone, "composing")
        try:
            await asyncio.wait_for(parar.wait(), timeout=RENOVAR_DIGITANDO_S)
        except asyncio.TimeoutError:
            continue


async def rodar(db: Any, integracao: Dict[str, Any], telefone: str, membro: Dict[str, Any],
                normalizado: Dict[str, Any], *, texto: Optional[str] = None) -> ResultadoDoTurno:
    """Um turno do CORE para o membro (company_id, user_id DELE), da mídia à resposta enviada. Nunca levanta.

    `texto` substitui o do evento (a pergunta guardada enquanto se escolhia a corretora)."""
    from app.services.atalho import envio

    cid = str(membro.get("company_id") or "").lower()
    uid = str(membro.get("user_id") or "").lower()
    res = ResultadoDoTurno(status="erro", company_id=cid, user_id=uid)
    try:
        _id(cid, "company_id"), _id(uid, "user_id")
        agente = await asyncio.to_thread(agente_core, db, cid)
        if not agente:
            await envio.enviar_texto(integracao, telefone, FRASE_SEM_AGENTE.format(
                corretora=membro.get("nome_da_corretora") or "sua corretora"), db=db)
            res.status = "sem_agente"
            return res
        chave = _chave_interna()
        if not chave:
            # ⛔ sem a chave o handler cairia no modo WIDGET (sem `userId`): o turno não roda às cegas
            logger.error("[ATALHO] sem chave interna (ADMIN_API_KEY/BACKEND_INTERNAL_API_KEY) — o turno não roda")
            await envio.enviar_texto(integracao, telefone, FRASE_SEM_RESPOSTA, db=db)
            res.status = "sem_chave"
            return res

        fala = (texto if texto is not None else str(normalizado.get("text") or "")).strip()
        midia = (normalizado.get("media") or {}) if texto is None else {}
        if not fala and midia.get("caption"):
            fala = str(midia["caption"]).strip()
        anexos: List[Dict[str, Any]] = []
        if midia:
            subida = await subir_midia(db, integracao, cid, uid, normalizado)
            if subida.get("anexo"):
                anexos.append(subida["anexo"])
            elif subida.get("aviso") and not fala:
                await envio.enviar_texto(integracao, telefone, subida["aviso"], db=db)
                res.status = "arquivo_falhou"
                return res
        if not fala and not anexos:
            res.status = "vazio"
            return res

        conversa = await asyncio.to_thread(conversa_do_membro, db, cid, uid, agente, titulo=fala[:50])
        res.conversation_id = str(conversa["id"])
        client_request_id = str(uuid.uuid4())
        user_message_id = await asyncio.to_thread(gravar_pergunta, db, conversa, cid, fala, anexos, client_request_id)
        corpo: Dict[str, Any] = {
            "chatInput": fala or None,
            "sessionId": str(conversa["session_id"]),
            "companyId": cid,
            "userId": uid,
            "agentId": agente,
            "client_request_id": client_request_id,
            "user_message_id": user_message_id,
            "assistantMessageId": str(uuid.uuid4()),
            "options": {"esforco": ESFORCO_DO_ATALHO},
            "channel": CANAL_DO_ATALHO,
        }
        if anexos:
            corpo["attachments"] = anexos

        parar = asyncio.Event()
        presenca = asyncio.ensure_future(_renovar_digitando(integracao, telefone, parar))
        try:
            resposta = await chamar_o_chat(corpo, chave=chave, user_id=uid)
        finally:
            parar.set()
            try:
                await asyncio.wait_for(presenca, timeout=2)
            except Exception:  # noqa: BLE001
                presenca.cancel()
            await envio.digitando(integracao, telefone, "paused")

        final = resposta.texto.strip() or resposta.aviso.strip()
        final = _com_as_entregas(final, resposta.entregas)
        res.entregas = list(resposta.entregas)
        if not final.strip():
            final = FRASE_SEM_RESPOSTA
            res.status = "sem_resposta"
        else:
            res.status = "respondido"
        res.texto = final
        res.enviadas = await envio.enviar_texto(integracao, telefone, final, db=db)
        logger.info("[ATALHO] turno de %s: %s, %d mensagem(ns)", _mascarar(telefone), res.status, res.enviadas)
        return res
    except Exception as erro:  # noqa: BLE001 — o atalho nunca derruba o webhook
        logger.error("[ATALHO] turno de %s não concluído (%s)", _mascarar(telefone), type(erro).__name__)
        res.status = "erro"
        return res


__all__ = ("CANAL_DO_ATALHO", "JANELA_DA_CONVERSA", "TETO_DE_MENSAGENS_POR_DIA", "ESFORCO_DO_ATALHO",
           "ResultadoDoTurno", "agente_core", "conversa_ativa", "conversa_do_membro", "tocar_conversa",
           "mensagens_de_hoje", "subir_midia", "gravar_pergunta", "chamar_o_chat", "rodar")
