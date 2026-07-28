"""Os grupos do WhatsApp pareado, para o corretor escolher numa lista.

O problema que isto resolve
---------------------------
Para receber o dossiê do handoff e o aviso de desconexão, a corretora precisa
apontar um grupo. Até agora a instrução era:

> "abra o grupo no WhatsApp Web e copie o ID da URL — algo como
>  `120363422850006552@g.us`"

Isso é pedir para um corretor de seguros ler a barra de endereço do navegador e
copiar dezoito dígitos sem errar. Ele vai errar, ou vai desistir — e o grupo que
não foi configurado é o alerta que não chega.

A rota existe
-------------
O Evolution Go expõe `GET /group/list` (confirmado no swagger dele em
28/07/2026, junto com `/group/myall`, `/group/info` e outras). Com o número
pareado, ela devolve os grupos.

O prazo curto não é zelo — é experiência
----------------------------------------
Ao testar contra a instância DESCONECTADA, `/group/list` devolveu 500 e
`/group/myall` **pendurou por dois minutos** até eu matar. Se a tela do
corretor chamasse isso sem prazo, ela congelaria — e o corretor não tem como
saber que o culpado é o WhatsApp desligado, não o AutoBrokers.

Por isso: prazo de 8 segundos, e a falha vira uma frase que explica o que
fazer, nunca uma tela travada.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Oito segundos. Mais que isso, o corretor acha que travou; menos, um WhatsApp
# com muitos grupos não termina de responder.
PRAZO_S = 8.0


def _jid_de_grupo(valor: Any) -> str:
    """O identificador do grupo, venha ele em que campo vier.

    O shape do Evolution Go ainda não foi confirmado com número pareado de
    verdade. Ler de vários nomes possíveis é deliberado: quando o primeiro
    pareamento acontecer amanhã, é melhor a lista aparecer do que quebrar por
    causa de uma letra maiúscula.
    """
    if isinstance(valor, str):
        return valor
    if isinstance(valor, dict):
        for k in ("JID", "jid", "Jid", "id", "ID", "groupJid", "GroupJID"):
            v = valor.get(k)
            if isinstance(v, str) and v:
                return v
            if isinstance(v, dict):
                u, s = v.get("User") or v.get("user"), v.get("Server") or v.get("server")
                if u:
                    return f"{u}@{s or 'g.us'}"
    return ""


def _nome_do_grupo(item: dict) -> str:
    for k in ("Name", "name", "subject", "Subject", "GroupName"):
        v = item.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _lista_de(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for k in ("data", "Data", "groups", "Groups", "result", "items"):
            v = payload.get(k)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
            if isinstance(v, dict):
                achou = _lista_de(v)
                if achou:
                    return achou
    return []


async def listar_grupos(company_id: str) -> dict:
    """Os grupos do WhatsApp pareado desta corretora.

    Devolve sempre um dicionário com `ok` e uma `frase` em português. Nunca
    levanta: uma tela de configuração que explode é pior que uma que diz
    "não consegui, e é por isto".
    """
    import httpx

    from app.core.database import get_supabase_client
    from app.services.whatsapp.integration_secrets import prepare_integration_for_runtime

    def _integracao() -> Optional[dict]:
        db = get_supabase_client()
        linhas = (db.client.table("integrations").select("*")
                  .eq("company_id", str(company_id))
                  .eq("provider", "evolution-go")
                  .eq("purpose", "observer")
                  .eq("is_active", True)
                  .order("last_seen_at", desc=True).limit(1).execute().data or [])
        return prepare_integration_for_runtime(linhas[0]) if linhas else None

    try:
        integracao = await asyncio.to_thread(_integracao)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Grupos] integração ilegível: %s", type(exc).__name__)
        integracao = None

    if not integracao:
        return {"ok": False, "grupos": [], "motivo": "sem_whatsapp",
                "frase": "O WhatsApp da corretora ainda não foi conectado. "
                         "Conecte em Personalização → Corretora → WhatsApp e "
                         "volte aqui."}

    estado = str(integracao.get("channel_status") or "")
    from app.services.whatsapp.channel_state import esta_conectado

    if not esta_conectado(estado):
        # Perguntar os grupos de um WhatsApp desligado devolve 500 — ou pendura.
        # Melhor dizer a verdade antes de tentar.
        return {"ok": False, "grupos": [], "motivo": "desconectado",
                "frase": f"O WhatsApp está '{estado or 'desconhecido'}'. "
                         "Reconecte em Personalização → Corretora → WhatsApp "
                         "para ver os grupos."}

    base = str(integracao.get("base_url") or "").rstrip("/")
    token = str(integracao.get("token") or "")
    if not (base and token):
        return {"ok": False, "grupos": [], "motivo": "sem_credencial",
                "frase": "A conexão do WhatsApp está incompleta. Refaça o "
                         "pareamento."}

    try:
        async with httpx.AsyncClient(timeout=PRAZO_S) as cliente:
            r = await cliente.get(f"{base}/group/list", headers={"apikey": token})
            if r.status_code >= 400:
                logger.warning("[Grupos] evolution devolveu %s", r.status_code)
                return {"ok": False, "grupos": [], "motivo": f"http_{r.status_code}",
                        "frase": "Não consegui ler os grupos agora. Se o "
                                 "WhatsApp acabou de conectar, espere um minuto "
                                 "e tente de novo."}
            bruto = r.json() if r.content else []
    except asyncio.TimeoutError:
        return {"ok": False, "grupos": [], "motivo": "demorou",
                "frase": "O WhatsApp demorou demais para responder. Tente "
                         "novamente em instantes."}
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Grupos] falha: %s", type(exc).__name__)
        return {"ok": False, "grupos": [], "motivo": type(exc).__name__,
                "frase": "Não consegui falar com o WhatsApp agora."}

    grupos: list[dict] = []
    for item in _lista_de(bruto):
        jid = _jid_de_grupo(item) or _jid_de_grupo(item.get("JID") or item.get("jid"))
        if not jid or "@g.us" not in jid:
            continue
        grupos.append({
            "jid": jid,
            "nome": _nome_do_grupo(item) or jid.split("@")[0],
            # O número de participantes ajuda o corretor a reconhecer o grupo
            # certo quando dois têm nome parecido.
            "participantes": len(item.get("Participants")
                                 or item.get("participants") or []) or None,
        })

    grupos.sort(key=lambda g: g["nome"].lower())
    return {
        "ok": True, "grupos": grupos, "total": len(grupos),
        "frase": (f"{len(grupos)} grupo(s) encontrados neste WhatsApp."
                  if grupos else
                  "Nenhum grupo neste WhatsApp. Crie o grupo no celular da "
                  "corretora, adicione quem precisa ser avisado, e recarregue "
                  "esta tela."),
    }
