"""BLOCO F — o gate de LIGAR o agente de atendimento.

📊 O DEFEITO, MEDIDO. Até 16/09/2026 ligar o agente era um `PATCH` genérico e a
**única** validação era de prompt. A checagem de destino existia, mas era
**posterior e passiva**: `main.py:874-921` conta
`corretoras_ligadas_sem_destino_de_suporte` no `/health` — e a docstring de lá
registra o incidente que a criou:

> *"09/09/2026, primeiro dia de piloto real. A AutoFleet passou o dia com o
> agente ligado e zero destinos de suporte: a ferramenta de handoff rodou 5
> vezes, recusou mentir e ninguém foi avisado — e não havia onde olhar."*

🔴 Um painel que só **conta** o problema depois de ele acontecer não é um
porteiro. Este módulo responde a pergunta **antes**: *"posso ligar?"*

⛔ E ele NÃO reimplementa a resolução de destino (CLAUDE.md §5): chama
`resolver_destino_de_suporte`, o mesmo motor por onde o handoff sai. Uma
consulta "parecida" aqui decidiria uma coisa e o handoff faria outra
(CLAUDE.md §9.4).

⚠️ **A trava é no ato de LIGAR, não no runtime.** `attendance_agent_active`
(`atlas/attendance_capture.py:267`) continua sendo o portão fail-closed de
execução e não muda. Misturar os dois é como se cria o produto que se desliga
sozinho no meio de um atendimento porque o heartbeat piscou.

⚠️ **E DESLIGAR nunca é bloqueado.** Uma trava que impede desligar é um produto
que não obedece — o botão de desligar é a saída de emergência da atendente.
Este endpoint só é consultado quando o pedido é LIGAR.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, Query

from app.core.auth import require_internal_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/atendimento", tags=["Atendimento"])

#: 🔴 As frases são o produto, e ficam AQUI, ao lado da regra que as escolhe.
#: ⛔ Nunca `destination_not_configured` na tela (CLAUDE.md §12.1 e a régua de
#: língua humana de `test_o_caso_se_explica_sozinho.py`).
SEM_DESTINO = ("Antes de ligar o agente, diga para onde ele pede ajuda. "
               "Cadastre o grupo da equipe em Personalização → Suporte humano.")
DESTINO_COMPARTILHADO = ("O destino de suporte que está cadastrado pertence a "
                         "outra corretora. Cadastre um grupo só desta corretora "
                         "em Personalização → Suporte humano.")
SEM_CANAL = ("O WhatsApp da corretora está desconectado. Conecte o número em "
             "Conectores → WhatsApp e tente de novo.")

#: Os valores de `integrations.channel_status` que significam "fora do ar".
#: 📊 Medido em 16/09/2026: os valores vivos na base são
#: `connected`, `disconnected`, `retired`, `close`.
CANAL_FORA_DO_AR = {"disconnected", "close", "closed", "retired"}


async def pode_ligar_o_atendimento(company_id: str) -> Dict[str, Any]:
    """`{"pode": bool, "motivo": str, "falta": "destino"|"canal"|""}`.

    ⚠️ **A assimetria é deliberada.** *Sem destino* é uma RECUSA dura: é o
    incidente medido, e é irreversível para o segurado que pede uma pessoa.
    *Canal em estado desconhecido* NÃO bloqueia — só o estado explicitamente
    desconectado bloqueia. Recusar por não saber transformaria uma leitura
    falha de metadado numa corretora impedida de trabalhar.
    """
    empresa = str(company_id or "").strip()
    if not empresa:
        return {"pode": False, "motivo": SEM_DESTINO, "falta": "destino"}

    from app.core.database import get_supabase_client
    from app.services.dispatch_router import resolver_destino_de_suporte

    # ---- ① destino de suporte, pelo MOTOR ---------------------------------
    try:
        alvo = await resolver_destino_de_suporte(empresa)
    except Exception as exc:  # noqa: BLE001
        # ⚠️ Não conseguir PERGUNTAR não é o mesmo que não ter destino. Aqui a
        # falha é de infraestrutura, e bloquear por ela deixaria a corretora
        # sem agente por uma indisponibilidade de leitura.
        logger.error("[PORTEIRO] resolvedor de destino indisponível (%s) — deixo ligar",
                     type(exc).__name__)
        return {"pode": True, "motivo": "", "falta": ""}

    if alvo.get("recusa"):
        # 🔴 AUSENTE ≠ RECUSADO, e as instruções são OPOSTAS:
        #    ausente  → CADASTRE um destino
        #    recusado → PARE DE COMPARTILHAR o que você já tem
        return {"pode": False, "motivo": DESTINO_COMPARTILHADO, "falta": "destino"}
    if not str(alvo.get("destino") or "").strip():
        return {"pode": False, "motivo": SEM_DESTINO, "falta": "destino"}

    # ---- ② canal conectado ------------------------------------------------
    try:
        db = get_supabase_client()
        linhas = (db.client.table("integrations")
                  .select("channel_status, is_active, provider")
                  .eq("company_id", empresa)          # 🔴 CLAUDE.md §7
                  .eq("is_active", True)
                  .limit(20).execute().data or [])
    except Exception as exc:  # noqa: BLE001
        logger.error("[PORTEIRO] canais ilegíveis (%s) — deixo ligar", type(exc).__name__)
        return {"pode": True, "motivo": "", "falta": ""}

    if not linhas:
        return {"pode": False, "motivo": SEM_CANAL, "falta": "canal"}

    estados = {str((l or {}).get("channel_status") or "").strip().lower()
               for l in linhas}
    # Basta UM canal fora da lista de "fora do ar" para o agente poder falar.
    # ⚠️ O vazio entra aqui de propósito: `channel_status` nulo é canal antigo,
    # não canal caído.
    vivos = [e for e in estados if e not in CANAL_FORA_DO_AR]
    if not vivos:
        return {"pode": False, "motivo": SEM_CANAL, "falta": "canal"}

    return {"pode": True, "motivo": "", "falta": ""}


@router.post("/esquecer-numeros-da-casa")
async def esquecer_numeros(company_id: str = Query(..., min_length=1),
                           _: bool = Depends(require_internal_key)) -> Dict[str, Any]:
    """O painel avisa que a lista mudou; o cache de 60 s cai na hora.

    ⚠️ O cache existe pelo CUSTO (a lista é lida em caminho quente, todo
    inbound), nunca pela correção. Sem esta rota a corretora cadastraria o fixo
    da loja e veria o agente respondendo a ele por mais um minuto — e um minuto
    é o suficiente para a pessoa achar que não funcionou.
    """
    from app.services.o_grupo_so_o_que_importa import esquecer_os_numeros_da_casa

    await esquecer_os_numeros_da_casa(company_id)
    return {"ok": True}


@router.get("/pode-ligar")
async def pode_ligar(company_id: str = Query(..., min_length=1),
                     _: bool = Depends(require_internal_key)) -> Dict[str, Any]:
    """O painel pergunta ANTES de escrever `is_active = true`.

    ⛔ Nada de PII, nada de destino, nada de segredo na resposta: só o veredito
    e a frase que a corretora lê.
    """
    return await pode_ligar_o_atendimento(company_id)
