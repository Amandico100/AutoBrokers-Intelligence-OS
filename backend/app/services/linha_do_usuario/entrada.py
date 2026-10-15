# -*- coding: utf-8 -*-
"""SPEC-131-0-B2 · L2 — a ENTRADA da linha do usuário: o que chega do aparelho do corretor, o que passa, e a saída.

    desviar(db, integration, body, background_tasks, dedupe)   o webhook (`evolution_go_webhook_token`) delega TUDO da
                                                              integração `purpose='linha_do_usuario'` para cá
    filtrar(linha, envelope_v2, *, db=None)                   (normalizado | None, motivo) — o portão da privacidade
    async turno_da_linha(db, integration, envelope)           o turno inteiro (2º plano): o MESMO `atalho.turno.rodar`
    async enviar_pela_linha(db, linha, texto_markdown)        a ÚNICA saída da linha: "▸ AutoBrokers\\n…" à PRÓPRIA conta,
                                                              anti-eco gravado ANTES, pelo cinto `atalho.envio.enviar`
    descarregar_descartadas(db)                               o contador `descartadas_total` (só o número) para o banco

🔴 O PORTÃO DA PRIVACIDADE (D-1310B2-05, nota 95) — a linha é o WhatsApp INTEIRO da pessoa: o Evolution entrega TODAS
as conversas do aparelho. Só passa a mensagem em que o CHAT é a própria conta (JID `@s.whatsapp.net` e/ou LID `@lid`,
Chat/ChatAlt) E `fromMe` E que NÃO é eco do sistema. Todo o resto — outra conversa, grupo, status, broadcast,
newsletter, history sync, evento sem `Message` — morre AQUI, antes de gravar, logar, chamar modelo ou Storage. A
ordem importa e é testada: as checagens PURAS (sem banco, sem normalizador, sem log) vêm primeiro; a mensagem de outra
conversa nunca passa nem pelo normalizador. Dela sobra só +1 num contador em memória por linha.

🔴 O ANTI-ECO (D-1310B2-04) — a resposta do sistema volta pelo webhook como `fromMe` NA MESMA conversa. Três camadas,
qualquer uma cala: (1) o PREFIXO "▸ AutoBrokers" (toda mensagem do sistema o leva) · (2) o SHA-256 do texto enviado
nos últimos 💭 10 min (`linha_mensagens_do_sistema`, gravado ANTES do envio: o eco pode chegar antes da linha
seguinte) · (3) o id da mensagem que o provedor devolve no envio (`evolution_go._post` → `SendResult.
provider_message_id` → `whatsapp_service.coletar_ids_enviados`), gravado DEPOIS do envio (M6, L4-B).
Banco ilegível na checagem → CALA (uma pergunta perdida é melhor que um laço robô↔robô na conta da pessoa).

🔴 O `descartadas_total` NÃO tem incremento atômico no banco. Ler-e-gravar por mensagem descartada custaria DUAS idas ao
banco por mensagem de QUALQUER conversa do aparelho (centenas por dia por pessoa). Decisão: contar EM MEMÓRIA por linha
e descarregar em lote (a cada 💭 50 por linha ou 💭 60 s), num 2º plano SERIALIZADO por uma trava do processo (o backend
roda em UM processo uvicorn — `backend/Dockerfile:27`): nenhuma descarga disputa com outra, então o ler-e-gravar não
perde soma. O preço: um restart perde até 49 contagens por linha — é um contador de transparência, não um saldo.

⛔ Nenhum telefone, JID, LID, texto ou nome em log — só o MOTIVO e a CONTAGEM (CLAUDE.md §13.3).
⛔ Nenhum cliente HTTP novo: o envio é o cinto `atalho.envio.enviar` (whatsapp_service), o turno é `atalho.turno.rodar`.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from app.services.linha_do_usuario import estado as E

logger = logging.getLogger(__name__)

PURPOSE = E.PURPOSE
#: a ORIGEM do turno (o `payload.origem` da pergunta em `messages` — é ela que diz por onde a cotação volta)
ORIGEM = "linha_do_usuario"
#: o prefixo de TODA mensagem do sistema pela linha (a conta é a mesma: é ele que separa "sou eu" de "é você")
PREFIXO = "▸ AutoBrokers"
PREFIXO_DA_MENSAGEM = PREFIXO + "\n"
#: 💭 quanto tempo o hash de uma mensagem enviada cala o eco dela
JANELA_DO_ECO = timedelta(minutes=10)
#: 💭 a descarga do contador de descartadas: a cada N por linha, ou depois de S segundos com algo pendente
DESCARREGAR_A_CADA = 50
DESCARREGAR_APOS_S = 60.0

#: os motivos que são PRIVACIDADE (o aparelho inteiro) — só estes contam em `descartadas_total`
MOTIVOS_DE_OUTRA_CONVERSA = frozenset({"outra_conversa", "grupo_ou_status", "sem_mensagem", "history_sync",
                                       "sem_chat"})
_SUFIXOS_QUE_NAO_SAO_CONVERSA = ("@g.us", "@broadcast", "@newsletter", "@call")
_SERVIDORES_DE_TELEFONE = ("s.whatsapp.net", "c.us")

_DESCARTADAS: Dict[str, Dict[str, Any]] = {}
_TRAVA_DO_CONTADOR = threading.Lock()
_TRAVA_DA_DESCARGA = threading.Lock()
_IGNORADAS_DESLIGADA = {"n": 0}
_TRAVAS_DO_TURNO: Dict[Tuple[int, str], asyncio.Lock] = {}


def ligada() -> bool:
    """Existe alguém com a linha ligada? (só informativo — a decisão é sempre por DONO: `ligada_para`)."""
    return E.ligada()


def ligada_para(dono: Any) -> bool:
    """A chave liga a linha DESTE dono? (`estado.ligada_para` — o ponto único)."""
    return E.ligada_para(dono)


def _dados(r: Any) -> List[Dict[str, Any]]:
    return [x for x in list(getattr(r, "data", None) or []) if isinstance(x, dict)]


def _t(db: Any, tabela: str) -> Any:
    cliente = db if hasattr(db, "table") else getattr(db, "client", db)
    return cliente.table(tabela)


def _sha(texto: Any) -> str:
    return hashlib.sha256(str(texto or "").strip().encode("utf-8")).hexdigest()


def _low(v: Any) -> str:
    return str(v or "").strip().lower()


# =====================================================================================================================
# a linha confirmada (o webhook e o turno) — FALHA FECHADA
# =====================================================================================================================
def linha_confirmada(db: Any, integration: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """A linha do evento SE ela é exatamente esta integração (id, corretora, DONO), ativa, e o dono é membro ATIVO da
    corretora. Qualquer dúvida → None (o webhook cala; nunca cai no observer, no QCM nem no atendimento)."""
    try:
        integ = integration or {}
        if _low(integ.get("purpose")) != PURPOSE:
            return None
        nome = str(integ.get("instance_id") or integ.get("identifier") or "").strip()
        linha = E.linha_da_instancia(db, nome)
        if not linha:
            return None
        if (str(linha.get("integration_id") or "") != str(integ.get("id") or "")
                or _low(linha.get("company_id")) != _low(integ.get("company_id"))
                or _low(linha.get("owner_user_id")) != _low(integ.get("owner_user_id"))
                or not linha.get("ativa")):
            return None
        if not E.membro_ativo(db, linha["company_id"], linha["owner_user_id"]):
            return None
        return linha
    except Exception as erro:  # noqa: BLE001
        logger.warning("[LINHA] linha nao confirmada (%s) — ignorada", type(erro).__name__)
        return None


# =====================================================================================================================
# o portão da privacidade
# =====================================================================================================================
def _partes(jid: Any) -> Tuple[str, str]:
    """`5511…:12@s.whatsapp.net` → ('5511…', 's.whatsapp.net'). O `:12` é o DISPOSITIVO, não a pessoa."""
    s = _low(jid)
    if "@" not in s:
        return "", ""
    usuario, servidor = s.split("@", 1)
    return usuario.split(":", 1)[0], servidor


def _casa_a_propria_conta(linha: Dict[str, Any], jid: Any) -> Optional[bool]:
    """True = este JID/LID é a PRÓPRIA conta da linha · False = é de outra pessoa · None = não dá para dizer (LID que
    a linha ainda não conhece)."""
    from app.services.canal.repositorio import canonico, formas

    usuario, servidor = _partes(jid)
    if not usuario:
        return False
    if servidor in _SERVIDORES_DE_TELEFONE:
        meu_jid, _ = _partes(linha.get("jid"))
        if meu_jid and meu_jid == usuario:
            return True
        meu_numero = formas(linha.get("numero_e164"))
        return bool(meu_numero) and canonico(usuario) in meu_numero
    if servidor == "lid":
        meu_lid, _ = _partes(linha.get("lid"))
        if not meu_lid:
            return None
        return meu_lid == usuario
    return False


def _conversa_consigo_mesmo(linha: Dict[str, Any], chave: Dict[str, Any]) -> bool:
    """O CHAT do evento é a conversa da pessoa consigo mesma ("Mensagem para você")?

    `remoteJid` decide. Só quando ele é um `@lid` que a linha ainda NÃO conhece, o `remoteJidAlt` (o mesmo chat
    endereçado pelo telefone — `evolution_go_events` só o guarda quando é `@s.whatsapp.net`) pode confirmar.
    LID conhecido e diferente → NÃO é (mesmo que o alternativo diga que sim: contradição = fecha)."""
    principal = _casa_a_propria_conta(linha, chave.get("remoteJid"))
    if principal is not None:
        return principal
    alt = chave.get("remoteJidAlt")
    return bool(alt) and _partes(alt)[1] in _SERVIDORES_DE_TELEFONE and _casa_a_propria_conta(linha, alt) is True


def _eco_no_banco(db: Any, linha: Dict[str, Any], message_id: Optional[str], texto: str) -> Optional[str]:
    """'eco_id' · 'eco_hash' · None. Erro de banco SOBE (quem chama cala)."""
    iid, cid = str(linha.get("integration_id") or ""), _low(linha.get("company_id"))
    if message_id:
        r = _dados(_t(db, "linha_mensagens_do_sistema").select("id, integration_id, company_id, message_id")
                   .eq("integration_id", iid).eq("company_id", cid).eq("message_id", str(message_id))
                   .limit(1).execute())
        if any(str(x.get("integration_id")) == iid and str(x.get("message_id")) == str(message_id) for x in r):
            return "eco_id"
    if texto:
        desde = (datetime.now(timezone.utc) - JANELA_DO_ECO).isoformat()
        h = _sha(texto)
        r = _dados(_t(db, "linha_mensagens_do_sistema").select("id, integration_id, company_id, hash_texto, enviada_em")
                   .eq("integration_id", iid).eq("company_id", cid).eq("hash_texto", h)
                   .gte("enviada_em", desde).limit(1).execute())
        if any(str(x.get("integration_id")) == iid and x.get("hash_texto") == h for x in r):
            return "eco_hash"
    return None


def _corpo_go_sem_chat(corpo: Any) -> bool:
    """O corpo CRU do Evolution GO é uma mensagem (`data.Info`) SEM o `Chat`? (SPEC-131-0-B2, conserto P1)

    O conversor comum (`evolution_go_events.go_event_to_v2_envelope`) faz `remoteJid = Chat or Sender`. Numa mensagem
    `fromMe`, o `Sender` é a PRÓPRIA conta — então um evento sem `Chat` (para quem quer que tenha ido) viraria "a
    conversa consigo mesmo" e passaria no portão. A linha não usa esse fallback: sem `Chat` explícito, não passa."""
    if not isinstance(corpo, dict):
        return False
    dados = corpo.get("data")
    info = dados.get("Info") if isinstance(dados, dict) else None
    if not isinstance(info, dict):
        info = dados.get("info") if isinstance(dados, dict) else None
    if not isinstance(info, dict):
        return False
    return not str(info.get("Chat") or info.get("chat") or "").strip()


def filtrar(linha: Optional[Dict[str, Any]], envelope: Any, *, db: Any = None, corpo: Any = None
            ) -> Tuple[Optional[Dict[str, Any]], str]:
    """`(normalizado, "")` quando a mensagem é da pessoa, na conversa consigo mesma, e não é eco do sistema;
    `(None, motivo)` quando morre aqui. NUNCA loga, NUNCA grava; para outra conversa não passa nem pelo normalizador.

    O normalizado devolvido leva `phone` = o número da PRÓPRIA linha (o destino da resposta é sempre a conta dela).
    Com `db`: as camadas de banco do anti-eco (id e hash); banco ilegível → `(None, 'eco_nao_conferido')`.

    `corpo` = o corpo CRU do Evolution GO (o webhook o passa): mensagem sem `Info.Chat` → `(None, 'sem_chat')`. O
    `envelope` também pode ser o próprio corpo cru do GO (`data.Info`): o portão confere o `Chat` e converte aqui."""
    if not linha:
        return None, "linha_nao_confirmada"
    if isinstance(envelope, dict) and isinstance(envelope.get("data"), dict) and (
            isinstance(envelope["data"].get("Info"), dict) or isinstance(envelope["data"].get("info"), dict)):
        from app.services.whatsapp.evolution_go_events import go_event_to_v2_envelope

        corpo = envelope if corpo is None else corpo
        envelope = go_event_to_v2_envelope(envelope)
    if _corpo_go_sem_chat(corpo):
        return None, "sem_chat"
    if not isinstance(envelope, dict) or str(envelope.get("event") or "") != "messages.upsert":
        return None, "sem_mensagem"
    dados = envelope.get("data")
    if not isinstance(dados, dict):
        return None, "sem_mensagem"
    chave, mensagem = dados.get("key"), dados.get("message")
    if not isinstance(chave, dict) or not isinstance(mensagem, dict) or not mensagem:
        return None, "sem_mensagem"
    remoto = _low(chave.get("remoteJid"))
    if remoto.endswith(_SUFIXOS_QUE_NAO_SAO_CONVERSA) or remoto.startswith("status@") or chave.get("participant"):
        return None, "grupo_ou_status"
    if chave.get("fromMe") is not True:
        # na conversa consigo mesmo TODA mensagem é fromMe; a que não é veio de outra pessoa
        return None, "outra_conversa"
    if not _conversa_consigo_mesmo(linha, chave):
        return None, "outra_conversa"

    # ---- daqui para baixo, SÓ a conversa consigo mesmo ----------------------------------------------------------
    from app.services.canal.repositorio import canonico
    from app.services.whatsapp.evolution_inbound import normalize_evolution_inbound

    try:
        bruto = normalize_evolution_inbound(envelope)
    except Exception:  # noqa: BLE001 — formato que o normalizador não conhece
        return None, "ilegivel"
    texto = str(bruto.get("text") or "")
    midia = bruto.get("media") if isinstance(bruto.get("media"), dict) else None
    legenda = str((midia or {}).get("caption") or "")
    if not texto.strip() and not midia:
        return None, "vazia"
    if texto.lstrip().startswith(PREFIXO) or legenda.lstrip().startswith(PREFIXO):
        return None, "eco_prefixo"
    numero = canonico(linha.get("numero_e164"))
    if not numero:
        return None, "linha_sem_numero"
    if db is not None:
        try:
            eco = _eco_no_banco(db, linha, bruto.get("message_id"), texto or legenda)
        except Exception as erro:  # noqa: BLE001
            logger.warning("[LINHA] anti-eco nao conferido (%s) — cala", type(erro).__name__)
            return None, "eco_nao_conferido"
        if eco:
            return None, eco
    normalizado = {**bruto, "skip": False, "skip_reason": None, "from_me": True, "is_group": False,
                   "phone": "+" + numero}
    return normalizado, ""


# =====================================================================================================================
# o contador de descartadas (só o número; em lote)
# =====================================================================================================================
def contar_descartada(linha: Dict[str, Any]) -> bool:
    """+1 em memória para esta linha. True = está na hora de descarregar (o webhook agenda em 2º plano)."""
    iid = str(linha.get("integration_id") or "")
    if not iid:
        return False
    with _TRAVA_DO_CONTADOR:
        d = _DESCARTADAS.setdefault(iid, {"n": 0, "company_id": _low(linha.get("company_id")),
                                          "owner_user_id": _low(linha.get("owner_user_id")),
                                          "desde": time.monotonic()})
        d["n"] += 1
        return d["n"] >= DESCARREGAR_A_CADA or (time.monotonic() - d["desde"]) >= DESCARREGAR_APOS_S


def descarregar_descartadas(db: Any) -> int:
    """Soma o que está em memória a `integrations.descartadas_total` (filtrando id, corretora, purpose e DONO).
    Serializado pela trava do processo: duas descargas nunca leem-e-gravam a mesma linha ao mesmo tempo. Falha →
    a contagem volta para a memória. Devolve quantas foram gravadas. Nunca levanta."""
    with _TRAVA_DA_DESCARGA:
        with _TRAVA_DO_CONTADOR:
            pendentes = dict(_DESCARTADAS)
            _DESCARTADAS.clear()
        gravadas = 0
        for iid, d in pendentes.items():
            try:
                linhas = _dados(_t(db, "integrations").select("id, company_id, owner_user_id, purpose, descartadas_total")
                                .eq("id", iid).eq("company_id", d["company_id"]).eq("purpose", PURPOSE)
                                .eq("owner_user_id", d["owner_user_id"]).limit(1).execute())
                row = next((x for x in linhas if str(x.get("id")) == iid and _low(x.get("company_id")) == d["company_id"]
                            and _low(x.get("owner_user_id")) == d["owner_user_id"]), None)
                if not row:
                    continue    # a linha sumiu: a contagem morre com ela
                (_t(db, "integrations").update({"descartadas_total": int(row.get("descartadas_total") or 0) + d["n"]})
                 .eq("id", iid).eq("company_id", d["company_id"]).eq("purpose", PURPOSE)
                 .eq("owner_user_id", d["owner_user_id"]).execute())
                gravadas += d["n"]
            except Exception as erro:  # noqa: BLE001
                logger.warning("[LINHA] descartadas nao gravadas (%s) — ficam para a proxima", type(erro).__name__)
                with _TRAVA_DO_CONTADOR:
                    atual = _DESCARTADAS.setdefault(iid, {**d, "n": 0})
                    atual["n"] += d["n"]
        if gravadas:
            logger.info("[LINHA] %d mensagem(ns) de outras conversas descartada(s) na entrada", gravadas)
        return gravadas


# =====================================================================================================================
# a saída — a ÚNICA porta por onde a linha fala
# =====================================================================================================================
def _metades_do_reenvio(texto: str) -> List[str]:
    """As duas metades que `whatsapp_service.send_message` manda quando um balão > 400 falha duas vezes (o último
    recurso dele). Elas também voltam como eco, SEM o prefixo na 2ª — então o hash delas é gravado junto."""
    if len(texto) <= 400:
        return []
    linhas = texto.splitlines()
    meio = max(1, len(linhas) // 2)
    return [p for p in ("\n".join(linhas[:meio]).strip(), "\n".join(linhas[meio:]).strip()) if p]


def _registrar_anti_eco(db: Any, row: Dict[str, Any], textos: List[str],
                        message_id: Optional[str] = None) -> None:
    """Grava o SHA-256 de cada mensagem (e das metades do reenvio) ANTES de enviar. Erro SOBE (nada sai sem ele)."""
    hashes: List[str] = []
    for t in textos:
        for h in [_sha(t)] + [_sha(m) for m in _metades_do_reenvio(t)]:
            if h not in hashes:
                hashes.append(h)
    agora = datetime.now(timezone.utc).isoformat()
    linhas = [{"integration_id": str(row["id"]), "company_id": _low(row["company_id"]), "message_id": None,
               "hash_texto": h, "enviada_em": agora} for h in hashes]
    if message_id and linhas:
        linhas[0]["message_id"] = str(message_id)
    if linhas:
        _t(db, "linha_mensagens_do_sistema").insert(linhas).execute()


def _registrar_ids_enviados(db: Any, row: Dict[str, Any], enviados: List[Tuple[str, str]]) -> None:
    """M6 — a 3ª camada do anti-eco: o id que o PROVEDOR deu a cada balão que saiu (`whatsapp_service.
    coletar_ids_enviados`), gravado DEPOIS do envio (antes não existe). Uma linha por id, com o hash do balão; o
    único (integration_id, message_id) recusa repetido. Falha de um não impede os outros e nunca sobe: o hash,
    gravado ANTES, já cala o eco do mesmo texto — o id cobre o eco cujo texto o aparelho mudou."""
    agora = datetime.now(timezone.utc).isoformat()
    for texto, mid in enviados:
        try:
            _t(db, "linha_mensagens_do_sistema").insert({
                "integration_id": str(row["id"]), "company_id": _low(row["company_id"]), "message_id": str(mid),
                "hash_texto": _sha(texto), "enviada_em": agora}).execute()
        except Exception as erro:  # noqa: BLE001
            logger.warning("[LINHA] id do envio nao gravado (%s) — o hash cobre o eco", type(erro).__name__)


def _em_mensagens_com_prefixo(texto_markdown: Any) -> List[str]:
    from app.services.atalho import envio as AENV

    corpo = AENV.para_whatsapp(texto_markdown)
    if corpo.lstrip().startswith(PREFIXO):
        corpo = corpo.lstrip()[len(PREFIXO):].lstrip("\n").lstrip()
    pedacos = AENV.em_mensagens(corpo, teto=AENV.TETO_DE_UMA_MENSAGEM - len(PREFIXO_DA_MENSAGEM))
    return [PREFIXO_DA_MENSAGEM + p for p in pedacos]


async def enviar_pela_linha(db: Any, linha: Optional[Dict[str, Any]], texto_markdown: Any) -> Dict[str, Any]:
    """Manda `texto_markdown` pela PRÓPRIA linha à PRÓPRIA conta ("Mensagem para você"), cada mensagem com
    "▸ AutoBrokers\\n", o hash gravado em `linha_mensagens_do_sistema` ANTES, pelo cinto `atalho.envio.enviar` (a
    exceção EXATA do anti-laço: destino == o número desta linha). `linha` = o dict de `estado.linha_do_dono`.

    Devolve `{enviadas, ids, motivo?}`. `ids` = os ids que o provedor deu aos balões que saíram (M6), cada um gravado
    em `linha_mensagens_do_sistema` DEPOIS do envio (o hash vai ANTES); provedor que não devolve id → `ids` vazio.
    Chave desligada para o DONO, linha inativa/de outro dono, sem número → nada sai. Nunca levanta."""
    vazio: Dict[str, Any] = {"enviadas": 0, "ids": []}
    try:
        if not ligada_para((linha or {}).get("owner_user_id")):
            return {**vazio, "motivo": "desligada"}
        linha = linha or {}
        cid, uid = _low(linha.get("company_id")), _low(linha.get("owner_user_id"))
        iid = str(linha.get("integration_id") or "")
        row = await asyncio.to_thread(E.linha_crua_do_dono, db, cid, uid)
        if not row or str(row.get("id")) != iid or row.get("is_active") is not True:
            return {**vazio, "motivo": "linha_inativa"}
        from app.services.canal.repositorio import canonico

        numero = canonico(row.get("paired_phone_e164"))
        if not numero:
            return {**vazio, "motivo": "linha_sem_numero"}
        textos = _em_mensagens_com_prefixo(texto_markdown)
        if not textos:
            return {**vazio, "motivo": "vazio"}
        try:
            await asyncio.to_thread(_registrar_anti_eco, db, row, textos)
        except Exception as erro:  # noqa: BLE001 — sem o anti-eco gravado a resposta voltaria como pergunta
            logger.error("[LINHA] anti-eco nao gravado (%s) — nada sai", type(erro).__name__)
            return {**vazio, "motivo": "anti_eco_nao_gravado"}
        from app.services.atalho import envio as AENV
        from app.services.whatsapp.integration_secrets import prepare_integration_for_runtime
        from app.services.whatsapp_service import coletar_ids_enviados

        integracao = prepare_integration_for_runtime(row)
        with coletar_ids_enviados() as enviados:
            n = await AENV.enviar(integracao, numero, textos, db=db)
        if enviados:
            await asyncio.to_thread(_registrar_ids_enviados, db, row, enviados)
        return {"enviadas": int(n or 0), "ids": [mid for _, mid in enviados]}
    except Exception as erro:  # noqa: BLE001
        logger.error("[LINHA] envio pela linha falhou (%s)", type(erro).__name__)
        return {**vazio, "motivo": "erro"}


# =====================================================================================================================
# o turno (2º plano)
# =====================================================================================================================
def _trava_do_turno(chave: str) -> asyncio.Lock:
    k = (id(asyncio.get_running_loop()), chave)
    trava = _TRAVAS_DO_TURNO.get(k)
    if trava is None:
        if len(_TRAVAS_DO_TURNO) > 2000:
            for x in [x for x, v in _TRAVAS_DO_TURNO.items() if not v.locked()][:1000]:
                _TRAVAS_DO_TURNO.pop(x, None)
        trava = _TRAVAS_DO_TURNO[k] = asyncio.Lock()
    return trava


def _aprender_o_lid(db: Any, linha: Dict[str, Any], envelope: Dict[str, Any]) -> None:
    """A conversa consigo mesmo veio por um `@lid` que a linha ainda não conhecia (confirmada pelo JID alternativo):
    guarda o LID (só quando ainda vazio). Falha não importa."""
    try:
        remoto = str(((envelope.get("data") or {}).get("key") or {}).get("remoteJid") or "")
        if linha.get("lid") or not remoto.lower().endswith("@lid"):
            return
        (_t(db, "integrations").update({"linha_lid": remoto})
         .eq("id", str(linha["integration_id"])).eq("company_id", _low(linha["company_id"])).eq("purpose", PURPOSE)
         .eq("owner_user_id", _low(linha["owner_user_id"])).is_("linha_lid", "null").execute())
    except Exception as erro:  # noqa: BLE001
        logger.debug("[LINHA] lid nao gravado (%s)", type(erro).__name__)


def _nome_da_corretora(db: Any, company_id: str) -> str:
    try:
        from app.services.atalho.verificacao import _nomes_das_corretoras

        return _nomes_das_corretoras(db, [company_id]).get(company_id) or "sua corretora"
    except Exception:  # noqa: BLE001
        return "sua corretora"


async def turno_da_linha(db: Any, integration: Dict[str, Any], envelope: Dict[str, Any]) -> Dict[str, Any]:
    """Uma mensagem da pessoa na conversa consigo mesma → o MESMO turno do atalho (`atalho.turno.rodar`, origem
    `linha_do_usuario`) com o DONO da linha como identidade, na corretora em que a linha mora (D-1310B2-02: sem
    perguntar "qual corretora?" — essa pergunta é do central). Reconfere tudo (o cinto). Nunca levanta."""
    from app.services.atalho import entrada as AE
    from app.services.atalho import turno as T
    from app.services.whatsapp.integration_secrets import prepare_integration_for_runtime

    try:
        if not ligada_para((integration or {}).get("owner_user_id")):
            return {"status": "ignorado", "motivo": "desligada"}
        linha = await asyncio.to_thread(linha_confirmada, db, integration)
        if not linha:
            return {"status": "ignorado", "motivo": "linha_nao_confirmada"}
        normalizado, motivo = await asyncio.to_thread(filtrar, linha, envelope, db=db)
        if normalizado is None:
            return {"status": "ignorado", "motivo": motivo}
        await asyncio.to_thread(_aprender_o_lid, db, linha, envelope)
        cid, uid = _low(linha["company_id"]), _low(linha["owner_user_id"])
        membro = {"company_id": cid, "user_id": uid, "nome_da_corretora": await asyncio.to_thread(
            _nome_da_corretora, db, cid), "linha": linha}
        telefone = normalizado["phone"]
        cortado = AE._cortar(normalizado)

        async with _trava_do_turno(f"linha:{linha['integration_id']}"):
            feitas = await asyncio.to_thread(T.mensagens_de_hoje, db, cid, uid)
            if feitas > T.TETO_DE_MENSAGENS_POR_DIA:
                return {"status": "silencio", "motivo": "teto"}
            if feitas == T.TETO_DE_MENSAGENS_POR_DIA:
                agente = await asyncio.to_thread(T.agente_core, db, cid)
                if agente:
                    conversa = await asyncio.to_thread(T.conversa_do_membro, db, cid, uid, agente)
                    await asyncio.to_thread(T.gravar_pergunta, db, conversa, cid,
                                            str(normalizado.get("text") or "") or "[Mensagem]", [],
                                            f"teto-{time.time_ns():x}", origem=ORIGEM)
                await enviar_pela_linha(db, linha, AE.FRASE_DO_TETO)
                return {"status": "teto", "company_id": cid}
            if cortado:
                await enviar_pela_linha(db, linha, AE.FRASE_TEXTO_LONGO)
            row = await asyncio.to_thread(E.linha_crua_do_dono, db, cid, uid)
            if not row or str(row.get("id")) != str(linha["integration_id"]):
                return {"status": "ignorado", "motivo": "linha_nao_confirmada"}
            integracao = prepare_integration_for_runtime(row)
            r = await T.rodar(db, integracao, telefone, membro, normalizado, origem=ORIGEM)
            return {"status": r.status, "company_id": r.company_id, "user_id": r.user_id,
                    "conversation_id": r.conversation_id, "enviadas": r.enviadas}
    except Exception as erro:  # noqa: BLE001
        logger.error("[LINHA] mensagem nao tratada (%s)", type(erro).__name__)
        return {"status": "erro"}


# =====================================================================================================================
# o desvio do webhook
# =====================================================================================================================
_EVENTOS_DE_QR = ("qrcode", "qr", "qrtimeout", "qrcode.updated", "qr.updated", "pairerror", "qrscannedwithoutmultidevice")


def tipo_do_evento(body: Dict[str, Any], envelope: Dict[str, Any]) -> Tuple[str, str]:
    """('qr'|'conexao'|'desconexao'|'history_sync'|'mensagem'|'outro', motivo). O QR é da API (L1), não do webhook;
    `QRTimeout` NÃO é desconexão de linha conectada (é o fim de uma rodada de QR)."""
    bruto = _low(body.get("event") or body.get("type") or body.get("Type")).replace("_", "")
    if bruto in _EVENTOS_DE_QR or bruto.startswith("qr"):
        return "qr", ""
    if "historysync" in bruto or "history.sync" in bruto:
        return "history_sync", ""
    if bruto == "pairsuccess":
        return "conexao", ""
    ev = str(envelope.get("event") or "")
    if ev == "connection.update":
        dados = envelope.get("data") or {}
        estado = _low(dados.get("state"))
        if estado in ("open", "connected"):
            return "conexao", ""
        if estado in ("close", "closed", "disconnected", "logout"):
            return "desconexao", _low(dados.get("reason")) or estado
        return "outro", ""
    if ev == "messages.upsert":
        return "mensagem", ""
    return "outro", ""


async def _boas_vindas_em_2o_plano(db: Any, linha: Dict[str, Any]) -> None:
    from app.services.linha_do_usuario import boas_vindas

    await boas_vindas.enviar_boas_vindas(db, linha)


async def desviar(db: Any, integration: Dict[str, Any], body: Dict[str, Any], background_tasks: Any,
                  dedupe: Callable[[str, Optional[str]], Awaitable[bool]]) -> Dict[str, Any]:
    """TUDO da integração `purpose='linha_do_usuario'` no webhook. Responde sempre (nunca levanta) e NUNCA devolve
    para o resto do webhook: nada desta linha chega ao observer, ao QCM ou ao pipeline de atendimento."""
    from app.services.whatsapp.evolution_go_events import go_event_to_v2_envelope

    try:
        # a chave decide pelo DONO da integração: dono fora da lista = como a chave ausente (conta e cala)
        if not ligada_para((integration or {}).get("owner_user_id")):
            _IGNORADAS_DESLIGADA["n"] += 1
            if _IGNORADAS_DESLIGADA["n"] % 100 == 1:
                logger.info("[LINHA] desligada (LINHA_DO_USUARIO_LIGADA) — %d evento(s) ignorado(s)",
                            _IGNORADAS_DESLIGADA["n"])
            return {"status": "ignored", "reason": "linha_desligada"}
        linha = await asyncio.to_thread(linha_confirmada, db, integration)
        if not linha:
            logger.warning("[LINHA] evento de uma linha sem dono/inativa/nao confirmada — ignorado")
            return {"status": "ignored", "reason": "linha_nao_confirmada"}
        corpo = body if isinstance(body, dict) else {}
        envelope = go_event_to_v2_envelope(corpo)
        tipo, motivo = tipo_do_evento(corpo, envelope)

        if tipo == "qr":
            return {"status": "ignored", "reason": "linha_qr"}
        if tipo == "conexao":
            r = await asyncio.to_thread(E.registrar_conexao, db, integration, corpo)
            if r.get("ok"):
                atual = await asyncio.to_thread(E.linha_da_instancia, db,
                                                integration.get("instance_id") or integration.get("identifier"))
                if atual:
                    background_tasks.add_task(_boas_vindas_em_2o_plano, db, atual)
            return {"status": "ok", "event": "linha_conexao"}
        if tipo == "desconexao":
            await asyncio.to_thread(E.registrar_desconexao, db, integration, motivo)
            return {"status": "ok", "event": "linha_desconexao"}
        if tipo == "history_sync":
            if contar_descartada(linha):
                background_tasks.add_task(descarregar_descartadas, db)
            return {"status": "ignored", "reason": "linha_history_sync"}
        if tipo != "mensagem":
            return {"status": "ignored", "reason": "linha_evento_ignorado"}

        normalizado, motivo = await asyncio.to_thread(filtrar, linha, envelope, db=db, corpo=corpo)
        if normalizado is None:
            if motivo in MOTIVOS_DE_OUTRA_CONVERSA and contar_descartada(linha):
                background_tasks.add_task(descarregar_descartadas, db)
            return {"status": "ignored", "reason": f"linha_{motivo}"}
        if await dedupe("evolution-go", normalizado.get("message_id")):
            return {"status": "ignored", "reason": "duplicate"}
        background_tasks.add_task(turno_da_linha, db, integration, envelope)
        return {"status": "accepted", "reason": "linha"}
    except Exception as erro:  # noqa: BLE001 — falha FECHADA: nunca segue para o resto do webhook
        logger.error("[LINHA] evento nao tratado (%s) — ignorado", type(erro).__name__)
        return {"status": "ignored", "reason": "linha_erro"}


__all__ = ("PURPOSE", "ORIGEM", "PREFIXO", "PREFIXO_DA_MENSAGEM", "JANELA_DO_ECO", "MOTIVOS_DE_OUTRA_CONVERSA",
           "ligada", "ligada_para", "linha_confirmada", "filtrar", "contar_descartada", "descarregar_descartadas",
           "enviar_pela_linha", "turno_da_linha", "tipo_do_evento", "desviar")
