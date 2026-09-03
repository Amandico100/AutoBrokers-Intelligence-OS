# -*- coding: utf-8 -*-
"""O atendimento termina — e o produto sabe. SPEC-086.

> **O TESTE DO PRODUTO:** *"Sexta-feira. A Regina abre a tela e pergunta: 'dos
> atendimentos desta semana, quantos terminaram, quantos ainda esperam alguém, e
> quantos morreram esperando?' — e a tela responde, com número."*

📊 **A razão, medida em 26/08/2026:**

```
conversations ..................... 671
  com `resolvido_em` preenchido ....  0
  com `resolucao_motivo` ...........  0
status em uso ............ open=614, active=57
```

> **O produto nunca marcou uma conversa como resolvida. Nem uma, em 671.**

⚠️ **E a tubulação já estava inteira.** 📊 `attendance_ficha.gravar()` **já
escreve as duas colunas** (`attendance_ficha.py:342-344`), e a fase `resolvido`
já existe em `derivar_fase`. ⛔ Nenhum chamador jamais preencheu o campo. Esta
SPEC **liga o que existe** (§5) — não constrói escritor novo.

===============================================================================
🔴 QUANDO O ATENDIMENTO ACABA — e a SPEC errava em um dos quatro
===============================================================================

A SPEC manda marcar `acionamento_aberto` quando *"o robô conclui o
acionamento"*. 📊 **Mas "aberto" é o meio, não o fim:** `derivar_fase` chama o
estado com protocolo de `acompanhando` — *"há protocolo; espera-se o
prestador"*.

⛔ Marcar ali contaria como *"terminou"* um guincho que nunca chegou.

📊 E o produto **já sabe** o que é terminar, em
`insurer_dispatch_service.py:138`:

```
FASES_ENCERRADAS = ("needs_human", "test_aborted", "encaminhado", "resolvido")

  `resolvido`      o serviço foi prestado e o ciclo fechou
  `encaminhado`    a seguradora não abre chamado aqui: o formulário ou a
                   orientação já estão em mãos (P-46 — o SEGUNDO desfecho de
                   sucesso do produto)
```

🔴 `CLAUDE.md` §12.1: *"se o nome de um campo mente sobre o que ele guarda,
conserte o campo"*. Então `acionamento_aberto` virou **`acionamento_concluido`**,
e `encaminhado` entrou ao lado — porque são **dois** desfechos de sucesso, não
um.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# =============================================================================
# 🔴 A LISTA FECHADA — e ela é a mesma do CHECK no banco
# =============================================================================

#: O serviço foi prestado e o ciclo fechou (dispatch `state='resolvido'`).
ACIONAMENTO_CONCLUIDO = "acionamento_concluido"
#: O entregável — formulário, orientação — já está em mãos (`state='encaminhado'`).
ENCAMINHADO = "encaminhado"
#: O próprio segurado disse que resolveu.
RESOLVIDO_PELO_SEGURADO = "resolvido_pelo_segurado"
#: A atendente encerrou pela tela.
FECHADO_POR_HUMANO = "fechado_por_humano"
#: 🔴 Venceu sem resposta. É o motivo que separa *"terminou"* de *"morreu
#: esperando"* — sem ele, os dois são o mesmo estado para o banco.
EXPIROU = "expirou"

MOTIVOS: Tuple[str, ...] = (
    ACIONAMENTO_CONCLUIDO, ENCAMINHADO, RESOLVIDO_PELO_SEGURADO,
    FECHADO_POR_HUMANO, EXPIROU,
)

#: 📊 Os desfechos de SUCESSO. `expirou` não está aqui, e é esse o ponto: um
#: atendimento que venceu esperando **terminou**, mas não terminou bem.
MOTIVOS_DE_SUCESSO: Tuple[str, ...] = (
    ACIONAMENTO_CONCLUIDO, ENCAMINHADO, RESOLVIDO_PELO_SEGURADO,
    FECHADO_POR_HUMANO,
)

#: 🔴 De qual estado do dispatch nasce qual motivo. **PURO, e propositalmente
#: incompleto.**
#:
#: ⚠️ `needs_human` e `test_aborted` também estão em `FASES_ENCERRADAS`, e de
#: propósito **não** aparecem aqui:
#:
#:   `needs_human`    o acionamento parou, mas o ATENDIMENTO não acabou — tem
#:                    gente esperando. Marcar resolvido aqui é o defeito que a
#:                    SPEC-090 BLOCO B existe para medir.
#:   `test_aborted`   é simulação. 📊 O simulador usa `company_id="sim"`, e a
#:                    SPEC-087 já pagou por confiar em dado de simulador.
MOTIVO_DO_ESTADO: Dict[str, str] = {
    "resolvido": ACIONAMENTO_CONCLUIDO,
    "encaminhado": ENCAMINHADO,
}


def motivo_do_estado_do_dispatch(estado: Any) -> Optional[str]:
    """O motivo de fim que este estado de dispatch produz — ou `None`.

    🔴 FUNÇÃO PURA, e `None` é a resposta mais comum: a maioria dos estados
    não termina atendimento nenhum.
    """
    return MOTIVO_DO_ESTADO.get(str(estado or "").strip().lower())


def e_motivo_valido(motivo: Any) -> bool:
    """⛔ O banco também recusa (CHECK). Recusar aqui evita um `UPDATE` que
    estoura no meio de um turno de atendimento."""
    return str(motivo or "") in MOTIVOS


# =============================================================================
# O escritor — e ele é IDEMPOTENTE por construção
# =============================================================================

async def marcar_fim(db, *, company_id: str, motivo: str,
                     conversation_id: str = "", session_id: str = "",
                     quando_iso: str = "") -> Tuple[bool, str]:
    """Marca a conversa como terminada. Devolve `(marcou, porque)`.

    ⛔ **Nunca levanta.** Uma falha aqui custa a marca de fim; deixar a exceção
    subir custaria a resposta ao segurado, que vale mais.

    🔴 **IDEMPOTENTE PELO FILTRO, não por leitura antes.** O `UPDATE` traz
    `.is_("resolvido_em", "null")`: uma conversa já resolvida não é resolvida de
    novo, e **duas chamadas simultâneas não brigam** — a segunda simplesmente
    não casa nenhuma linha.

    ⚠️ Isso importa de verdade: o BLOCO C varre a cada 10 minutos e o dispatch
    escreve no instante do desfecho. Ler-e-depois-escrever teria janela.

    🔴 **E o filtro por corretora está em TODA chamada** (§7): o backend usa
    service role e atravessa a RLS inteira.
    """
    from datetime import datetime, timezone

    empresa = str(company_id or "").strip()
    if not empresa:
        return False, "sem_company_id"
    if not e_motivo_valido(motivo):
        logger.error("[FIM] motivo %r não está na lista fechada %s — nada foi "
                     "gravado", motivo, MOTIVOS)
        return False, "motivo_invalido"
    if not (conversation_id or session_id):
        return False, "sem_conversa"

    quando = quando_iso or datetime.now(timezone.utc).isoformat()
    try:
        consulta = (db.client.table("conversations")
                    .update({"resolvido_em": quando, "resolucao_motivo": motivo})
                    .eq("company_id", empresa)          # 🔴 §7
                    .is_("resolvido_em", "null"))       # ⛔ idempotência
        consulta = (consulta.eq("id", str(conversation_id)) if conversation_id
                    else consulta.eq("session_id", str(session_id)))
        achado = await consulta.execute()
    except Exception as erro:  # noqa: BLE001
        # ⛔ NUNCA imprime telefone nem `session_id` (ele CONTÉM o telefone).
        logger.warning("[FIM] não marcado (%s) motivo=%s", type(erro).__name__, motivo)
        return False, type(erro).__name__

    linhas = achado.data or []
    if not linhas:
        # ⚠️ Não é erro: é *"já estava resolvida"* ou *"não é desta corretora"*.
        #    Os dois terminam igual — nada muda — e o chamador não precisa
        #    distinguir para seguir trabalhando.
        return False, "ja_resolvida_ou_de_outra_corretora"
    logger.info("[FIM] atendimento encerrado motivo=%s", motivo)
    return True, motivo


# =============================================================================
# BLOCO D · a pergunta da sexta-feira
# =============================================================================

def contar_desfechos(conversas, waits=()) -> Dict[str, Any]:
    """*"Quantos terminaram, quantos ainda esperam, quantos morreram esperando?"*

    🔴 FUNÇÃO PURA. Recebe as linhas já filtradas por corretora e período.

    ⚠️ **`morreram_esperando` sai de fora de `terminaram`, e é uma escolha.**
    Tecnicamente `expirou` também é um fim; contá-lo junto faria a sexta-feira
    dizer *"12 terminaram"* num dia em que sete morreram esperando. 📊 O nome da
    coluna é a pergunta da Regina, e ela pergunta as três coisas separadas.
    """
    por_motivo: Dict[str, int] = {}
    terminaram = morreram = 0
    for c in conversas:
        m = str((c or {}).get("resolucao_motivo") or "")
        if not m:
            continue
        por_motivo[m] = por_motivo.get(m, 0) + 1
        if m == EXPIROU:
            morreram += 1
        elif m in MOTIVOS_DE_SUCESSO:
            terminaram += 1

    por_kind: Dict[str, int] = {}
    esperando = 0
    for w in waits:
        if str((w or {}).get("status") or "") != "ativo":
            continue
        esperando += 1
        k = str((w or {}).get("kind") or "?")
        por_kind[k] = por_kind.get(k, 0) + 1

    return {
        "terminaram": terminaram,
        "ainda_esperam": esperando,
        "morreram_esperando": morreram,
        "por_motivo": por_motivo,
        "por_kind": por_kind,
    }


# =============================================================================
# BLOCO B · a espera vira objeto
# =============================================================================

ESPERANDO_CLIENTE = "esperando_cliente"
ESPERANDO_SEGURADORA = "esperando_seguradora"
ESPERANDO_HUMANO = "esperando_humano"
KINDS: Tuple[str, ...] = (ESPERANDO_CLIENTE, ESPERANDO_SEGURADORA, ESPERANDO_HUMANO)

ATIVO = "ativo"
SATISFEITO = "satisfeito"
VENCIDO = "vencido"
CANCELADO = "cancelado"
STATUS_DO_WAIT: Tuple[str, ...] = (ATIVO, SATISFEITO, VENCIDO, CANCELADO)

#: Depois de quantos avisos ignorados a conversa vira `expirou`.
#:
#: ⚠️ **Três, e o número tem razão.** O vigia roda a cada 10 minutos, mas só
#: avisa a cada `HANDOFF_REALERTA_HORAS` (padrão 6). Três avisos são ~18 horas
#: de silêncio depois do vencimento — 📊 contra as **730 horas** da conversa que
#: o `handoff_watchdog.py:3` documenta. ⛔ Marcar no primeiro aviso mataria uma
#: conversa que a atendente ia responder depois do almoço.
AVISOS_ATE_EXPIRAR = 3


def e_kind_valido(kind: Any) -> bool:
    return str(kind or "") in KINDS


async def abrir_espera(db, *, company_id: str, conversation_id: str, kind: str,
                       vence_em_iso: str, scope: str = "default",
                       work_run_id: str = "") -> Tuple[bool, str]:
    """Abre uma espera. Devolve `(abriu, porque)` — e **nunca levanta**.

    ⛔ Um `UNIQUE` violado **não é erro**: significa que já havia uma espera
    ativa naquele escopo, que é exatamente o que o índice existe para garantir.
    O chamador segue trabalhando.

    ⚠️ `work_run_id` é opcional de propósito: 📊 4 `work_runs` de acionamento
    contra 671 conversas. **A âncora é a conversa.**
    """
    empresa = str(company_id or "").strip()
    if not empresa or not str(conversation_id or "").strip():
        return False, "sem_conversa_ou_corretora"
    if not e_kind_valido(kind):
        logger.error("[ESPERA] kind %r não está em %s — nada foi gravado", kind, KINDS)
        return False, "kind_invalido"

    linha: Dict[str, Any] = {
        "company_id": empresa,                      # 🔴 §7
        "conversation_id": str(conversation_id),
        "kind": str(kind),
        "scope": str(scope or "default")[:120],
        "status": ATIVO,
        "vence_em": str(vence_em_iso),
    }
    # 🔴 SPEC-093-B BLOCO B — a espera de uma conversa COM SOMBRA nasce ligada a ela.
    #
    # ⚠️ A âncora continua sendo a conversa (o parágrafo acima não mudou). O que
    # muda é que, quando existe sombra, a espera deixa de ser órfã no Work OS: sem
    # o `work_run_id`, "3 dias esperando a seguradora" não pertence a caso nenhum e
    # o digest não consegue contá-lo.
    #
    # ⛔ Só preenche o que veio VAZIO: um `work_run_id` explícito do chamador (o
    # acionamento) vence sempre — a sombra não rouba a espera de outro dono.
    if not work_run_id:
        try:
            from app.services.claims_shadow import sombra_da_conversa

            work_run_id = await sombra_da_conversa(db, empresa, conversation_id) or ""
        except Exception as erro:  # noqa: BLE001
            logger.warning("[SOMBRA] sombra da espera não consultada (%s)",
                           type(erro).__name__)
    if work_run_id:
        linha["work_run_id"] = str(work_run_id)
    try:
        await db.client.table("work_waits").insert(linha).execute()
    except Exception as erro:  # noqa: BLE001
        texto = str(erro).lower()
        if "uq_work_waits_ativo_por_escopo" in texto or "duplicate key" in texto:
            return False, "ja_existe_espera_ativa"
        logger.warning("[ESPERA] não aberta (%s) kind=%s", type(erro).__name__, kind)
        return False, type(erro).__name__

    try:
        from app.services.claims_shadow import registrar_gesto

        await registrar_gesto(db, company_id=empresa, conversation_id=conversation_id,
                              event_type="claims.espera_aberta",
                              payload={"kind": str(kind)})
    except Exception as erro:  # noqa: BLE001
        logger.warning("[SOMBRA] espera aberta não registrada (%s)", type(erro).__name__)
    return True, "aberta"


async def satisfazer_espera(db, *, company_id: str, conversation_id: str,
                            por: str, scope: str = "default") -> int:
    """O que se esperava aconteceu. Devolve **quantas** esperas foram fechadas.

    🔴 O filtro por corretora está aqui (§7), e o `status='ativo'` torna a
    operação idempotente: satisfazer duas vezes fecha uma vez.
    """
    from datetime import datetime, timezone

    empresa = str(company_id or "").strip()
    if not empresa or not conversation_id:
        return 0
    try:
        achado = await (db.client.table("work_waits")
                        .update({"status": SATISFEITO,
                                 "satisfeito_por": str(por or "?")[:120],
                                 "satisfeito_em": datetime.now(timezone.utc).isoformat(),
                                 "updated_at": datetime.now(timezone.utc).isoformat()})
                        .eq("company_id", empresa)          # 🔴 §7
                        .eq("conversation_id", str(conversation_id))
                        .eq("scope", str(scope or "default"))
                        .eq("status", ATIVO)
                        .execute())
    except Exception as erro:  # noqa: BLE001
        logger.warning("[ESPERA] não satisfeita (%s)", type(erro).__name__)
        return 0

    fechadas = list(achado.data or [])
    # 🔴 SPEC-093-B BLOCO B — quanto tempo a espera durou, em dias inteiros.
    #
    # ⛔ O `kind` e a data de abertura saem da LINHA FECHADA, nunca de um palpite
    # do chamador: `satisfazer_espera` não recebe `kind`, e inventar um encheria o
    # contador "espera de seguradora > prazo" com esperas de cliente.
    for fechada in fechadas:
        try:
            from app.services.claims_shadow import registrar_gesto

            await registrar_gesto(
                db, company_id=empresa, conversation_id=conversation_id,
                event_type="claims.espera_satisfeita",
                payload={"kind": str((fechada or {}).get("kind") or ""),
                         "dias": _dias_entre((fechada or {}).get("created_at"),
                                             (fechada or {}).get("satisfeito_em"))},
            )
        except Exception as erro:  # noqa: BLE001
            logger.warning("[SOMBRA] espera satisfeita não registrada (%s)",
                           type(erro).__name__)
    return len(fechadas)


def _dias_entre(inicio: Any, fim: Any) -> int:
    """Dias inteiros entre dois instantes ISO. `0` quando não dá para saber.

    ⛔ **Zero é a resposta honesta para "não sei", e não um dia inventado.** O
    contador que lê este campo compara com o prazo da CNSP 496/2026 — um dia
    fabricado aqui viraria um "prazo estourado" que nunca existiu.
    """
    from datetime import datetime

    try:
        a = datetime.fromisoformat(str(inicio).replace("Z", "+00:00"))
        b = datetime.fromisoformat(str(fim).replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return 0
    return max(0, int((b - a).total_seconds() // 86400))


async def esperas_da_corretora(db, company_id: str, *, status: str = ATIVO,
                               teto: int = 500):
    """As esperas de UMA corretora. 🔴 O filtro é obrigatório e não tem default.

    ⛔ Sem `company_id` devolve `[]` — **não devolve tudo**. Um repositório que
    esquece o filtro e devolve o banco inteiro é o vazamento entre corretoras
    que a RLS não impede, porque o backend usa service role (§7).
    """
    empresa = str(company_id or "").strip()
    if not empresa:
        logger.error("[ESPERA] consulta SEM corretora — devolvendo vazio. "
                     "Um SELECT sem filtro aqui vaza o banco inteiro (§7).")
        return []
    try:
        achado = await (db.client.table("work_waits")
                        .select("id, company_id, conversation_id, work_run_id, "
                                "kind, scope, status, vence_em, avisos, created_at")
                        .eq("company_id", empresa)          # 🔴 §7
                        .eq("status", str(status))
                        .order("vence_em").limit(int(teto)).execute())
    except Exception as erro:  # noqa: BLE001
        logger.warning("[ESPERA] não lidas (%s)", type(erro).__name__)
        return []
    return achado.data or []


def esperas_vencidas(waits, agora_iso: str):
    """As que já venceram — **PURA**, para o guarda rodar offline.

    ⚠️ Comparação de texto ISO-8601 em UTC é ordenação correta, e é o formato
    que o PostgREST devolve. Converter para `datetime` aqui só acrescentaria um
    jeito de errar de fuso.
    """
    agora = str(agora_iso or "")
    if not agora:
        return []
    return [w for w in waits
            if str((w or {}).get("status") or "") == ATIVO
            and str((w or {}).get("vence_em") or "") <= agora]


def deve_expirar_a_conversa(wait) -> bool:
    """Este wait já foi ignorado vezes demais? — o gate ④ do BLOCO C.

    🔴 PURA, e o `>=` importa: o contador é incrementado ANTES desta pergunta,
    então o terceiro aviso é o que fecha.
    """
    return int((wait or {}).get("avisos") or 0) >= AVISOS_ATE_EXPIRAR
