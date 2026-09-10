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
import os
import re
from typing import Any, Dict, List, Optional, Tuple

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


#: 🔴 Quanta folga o relógio do chamador ganha, em minutos.
#:
#: ⚠️ **Não é zero, e não é generoso.** Zero recusaria um desfecho legítimo por
#: um relógio 200 ms adiantado — e o `quando_iso` do corredor é gerado na
#: máquina dele, não no banco. Cinco minutos cobrem a deriva de NTP de um
#: contêiner e não cobrem nada mais: o defeito medido pelo red team era
#: `hoje + 30 DIAS`, que mantinha o atendimento dentro de `terminaram` por um
#: mês.
FOLGA_DO_RELOGIO_MIN = 5


def _recusar_futuro(quando_iso: str, agora) -> None:
    """⛔ Desfecho é **fato passado**. Uma data no futuro não é um erro do
    mundo: é um relógio errado ou um chamador inventando data — e ela
    contamina `semana.terminaram` e o estágio da tela pelos dias seguintes.

    ⚠️ **Data ILEGÍVEL passa de propósito.** Quem recusa formato é o banco
    (`timestamptz`), e duplicar o parser aqui só criaria um segundo jeito de
    discordar dele. O que esta função julga é o *momento*, não a *forma*.
    """
    from datetime import datetime, timedelta

    try:
        alvo = datetime.fromisoformat(str(quando_iso).replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return
    if alvo.tzinfo is None:
        alvo = alvo.replace(tzinfo=agora.tzinfo)
    if alvo - agora > timedelta(minutes=FOLGA_DO_RELOGIO_MIN):
        raise ValueError(
            "resolvido_em no futuro (%s > agora + %dmin) — desfecho é fato "
            "passado" % (quando_iso, FOLGA_DO_RELOGIO_MIN))


# =============================================================================
# O escritor — e ele é IDEMPOTENTE por construção
# =============================================================================

async def _episodio_e_sua_conversa(db, empresa: str, episodio: str):
    """A linha do episódio e a conversa ligada a ele — a junção R3 da SPEC-097.

    🔴 **Devolve `(None, "")` quando o episódio não é DESTA corretora.** O
    `attendance_session_id` chega da tela, e um UUID não é autorização (§7): o
    filtro por `company_id` é o que impede marcar o desfecho de um episódio de
    outra corretora.

    ⚠️ `("", …)` no segundo item é a resposta certa para 📊 42,2% dos episódios
    (E7): eles nunca terão conversa, e isso não é erro — é a vida.
    """
    try:
        achado = await (db.client.table("attendance_sessions")
                        .select("id, conversation_id")
                        .eq("company_id", empresa)          # 🔴 §7
                        .eq("id", str(episodio))
                        .limit(1).execute())
    except Exception as erro:  # noqa: BLE001
        logger.warning("[FIM] episódio não lido (%s)", type(erro).__name__)
        return None, ""
    linhas = achado.data or []
    if not linhas:
        return None, ""
    return linhas[0], str(linhas[0].get("conversation_id") or "")


async def marcar_fim(db, *, company_id: str, motivo: str,
                     conversation_id: str = "", session_id: str = "",
                     attendance_session_id: str = "",
                     quando_iso: str = "") -> Tuple[bool, str]:
    """Marca o atendimento como terminado. Devolve `(marcou, porque)`.

    🔴 **SPEC-097 U1.2 — o desfecho mora no EPISÓDIO.** 📊 Medido em 05/09/2026:
    `attendance_sessions` tem 12.755 linhas e 5,8 sessões por contato, enquanto
    `conversations` tem 728 — *o caso da operação é o episódio*, e só 57,8%
    deles casam 1:1 com uma conversa (E7). Marcar o fim **só** na conversa
    deixaria 42,2% dos atendimentos sem desfecho para sempre.

    Então: com `attendance_session_id`, grava no episódio **e espelha na
    conversa quando houver junção** (`attendance_sessions.conversation_id`);
    sem junção, o episódio recebe o desfecho sozinho.

    ⛔ **`claimed_by` não é tocado.** Encerrar não é desatribuir: quem atendeu
    continua sendo a dona do atendimento depois de ele terminar.

    ⛔ **Nunca levanta POR FALHA DO MUNDO.** Banco fora do ar, episódio de
    outra corretora, conversa já resolvida: tudo isso devolve `(False, porquê)`
    — uma falha aqui custa a marca de fim, e deixar a exceção subir custaria a
    resposta ao segurado, que vale mais.

    🔴 **As ÚNICAS exceções são dois `ValueError` de CHAMADOR ERRADO** — motivo
    fora da lista fechada e `quando_iso` no futuro. Isso não é o mundo falhando,
    é código escrito errado. Devolver `False` ali deixava o defeito passar
    calado, porque o chamador do corredor **não olha o retorno**.

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
        # 🔴 AQUI ELE LEVANTA — e é a ÚNICA coisa que este arquivo levanta.
        #
        # ⚠️ "Nunca levanta" fala do MUNDO: banco fora do ar, linha de outra
        # corretora, conversa já resolvida. Nada disso é culpa de quem chamou, e
        # engolir custa uma marca de fim. Um motivo fora da lista fechada é
        # outra coisa: é DEFEITO DE CHAMADOR, sempre — 📊 os 3 chamadores de
        # produção passam constantes deste módulo (`dispatch_router:1373`,
        # `handoff_watchdog:580`, `canario_097:187`), então esta linha só é
        # alcançável por código novo escrito errado.
        #
        # ⛔ E devolver `(False, "motivo_invalido")` era o pior dos mundos: o
        # `_marcar_fim_do_atendimento` ignora o retorno dentro de um `try` que
        # engole tudo, então o chamador seguia achando que marcou e o
        # atendimento ficava sem desfecho **em silêncio**.
        logger.error("[FIM] motivo %r não está na lista fechada %s — nada foi "
                     "gravado", motivo, MOTIVOS)
        raise ValueError(
            "motivo %r não está na lista fechada %s — o CHECK do banco recusaria"
            % (motivo, MOTIVOS))
    episodio = str(attendance_session_id or "").strip()
    if not (conversation_id or session_id):
        if not episodio:
            return False, "sem_conversa"

    agora = datetime.now(timezone.utc)
    quando = quando_iso or agora.isoformat()
    _recusar_futuro(quando, agora)
    conversa = str(conversation_id or "").strip()
    marcou_episodio = False

    # ---- ① o EPISÓDIO, quando o chamador o conhece (SPEC-097 R3/E8) --------
    if episodio:
        linha, ligada = await _episodio_e_sua_conversa(db, empresa, episodio)
        if linha is None:
            return False, "episodio_de_outra_corretora_ou_inexistente"
        if not conversa:
            conversa = ligada
        try:
            achado = await (db.client.table("attendance_sessions")
                            .update({"resolvido_em": quando,
                                     "resolucao_motivo": motivo})
                            .eq("company_id", empresa)          # 🔴 §7
                            .eq("id", episodio)
                            .is_("resolvido_em", "null")        # ⛔ idempotência
                            .execute())
            marcou_episodio = bool(achado.data)
        except Exception as erro:  # noqa: BLE001
            logger.warning("[FIM] episódio não marcado (%s) motivo=%s",
                           type(erro).__name__, motivo)
            return False, type(erro).__name__

    # ---- ② a CONVERSA, quando existe (o espelho, não a âncora) -------------
    marcou_conversa = False
    if conversa or session_id:
        try:
            consulta = (db.client.table("conversations")
                        .update({"resolvido_em": quando, "resolucao_motivo": motivo})
                        .eq("company_id", empresa)          # 🔴 §7
                        .is_("resolvido_em", "null"))       # ⛔ idempotência
            consulta = (consulta.eq("id", conversa) if conversa
                        else consulta.eq("session_id", str(session_id)))
            achado = await consulta.execute()
            marcou_conversa = bool(achado.data)
        except Exception as erro:  # noqa: BLE001
            # ⛔ NUNCA imprime telefone nem `session_id` (ele CONTÉM o telefone).
            logger.warning("[FIM] não marcado (%s) motivo=%s", type(erro).__name__, motivo)
            if not marcou_episodio:
                return False, type(erro).__name__

    if not (marcou_episodio or marcou_conversa):
        # ⚠️ Não é erro: é *"já estava resolvida"* ou *"não é desta corretora"*.
        #    Os dois terminam igual — nada muda — e o chamador não precisa
        #    distinguir para seguir trabalhando.
        return False, "ja_resolvida_ou_de_outra_corretora"
    # 🔴 SPEC-097.1 U1.2 — O DESFECHO FECHA AS ESPERAS DO ATENDIMENTO.
    #
    # ⚠️ **Em TODOS os escopos**, e é por isso que não passa por
    # `satisfazer_espera` (que filtra por escopo): quando o atendimento acaba,
    # acabou também a espera do travamento, a do pós-acionamento e qualquer
    # outra. Deixar uma ativa faria o vigia de 10 minutos cobrar uma conversa
    # ENCERRADA — e alarme sobre caso resolvido é como se ensina uma equipe a
    # ignorar alarme (a mesma razão do parágrafo do `else` no corredor).
    #
    # ⛔ Best-effort e por fora do retorno: a marca de fim vale mais que a
    # limpeza das esperas.
    if conversa:
        try:
            await (db.client.table("work_waits")
                   .update({"status": SATISFEITO,
                            "satisfeito_por": "desfecho",
                            "satisfeito_em": quando,
                            "updated_at": quando})
                   .eq("company_id", empresa)               # 🔴 §7
                   .eq("conversation_id", str(conversa))
                   .eq("status", ATIVO)
                   .execute())
        except Exception as erro:  # noqa: BLE001
            logger.warning("[FIM] esperas não fechadas (%s) — o vigia ainda pode "
                           "cobrar uma conversa encerrada", type(erro).__name__)

    logger.info("[FIM] atendimento encerrado motivo=%s episodio=%s conversa=%s",
                motivo, bool(marcou_episodio), bool(marcou_conversa))
    return True, motivo


# =============================================================================
# 🔴 SPEC-097 U2.3/E6 — A IA CALA QUANDO ALGUÉM ASSUME
# =============================================================================

#: O status que o produto grava quando o segurado pede uma pessoa.
HUMAN_REQUESTED = "HUMAN_REQUESTED"


def pausar_ia(conversa: Any) -> bool:
    """A IA tem de ficar calada nesta conversa? — **PURA**, e é UMA só.

    🔴 **Duas razões, não uma.** 📊 Medido em 05/09/2026: `webhook.py:628` e
    `chat.py:173,620` perguntavam **apenas** `status == 'HUMAN_REQUESTED'`. Uma
    conversa que a atendente ASSUMIU pela tela (`claimed_by` preenchido) segue
    com status `open` — e o robô respondia por cima dela, na frente do cliente.

    ⚠️ Este helper é **um só** de propósito (§5). Três cópias da mesma pergunta
    em dois arquivos é como uma delas fica para trás na próxima regra.

    ---------------------------------------------------------------------------
    🔴 E A PAUSA É DO ATENDIMENTO **VIVO** — ela morre com o desfecho

    ⛔ Sem esta terceira linha, o caminho feliz da Fila nova **desligava o robô
    para sempre** naquele segurado:

    ```
    a atendente ASSUME  → claimed_by preenchido        → a IA cala  ✅
    a atendente ENCERRA → resolvido_em escrito,
                          e `claimed_by` FICA (R2/U1.2:
                          encerrar não é desatribuir)  → a IA cala  ⛔ PARA SEMPRE
    ```

    📊 `webhook.py::get_or_create_conversation` reusa a MESMA linha por
    `(company, user_id, channel)` — não abre conversa nova por atendimento. Então
    a mensagem que o segurado mandar em **novembro** cai na linha encerrada em
    setembro, com o dono de setembro ainda nela, e ninguém responde. Só o
    `release` limpava o dono, e ninguém dá `release` numa conversa já encerrada.

    ⚠️ **E os DOIS motivos morrem com o desfecho, não só o dono.** Um
    `HUMAN_REQUESTED` que terminou também é passado: manter a pausa por ele
    faria o pedido de ajuda de agosto calar o robô em dezembro. Quem quiser a
    pessoa de novo pede de novo, e o pedido novo é o que pausa.

    ⛔ **A alternativa era o `close` apagar `claimed_by`** — e ela custa a
    autoria que a R2 existe para guardar (`conversas/[id]/route.ts:268-271`). O
    dado fica; o que expira é o SILÊNCIO.
    """
    linha = conversa or {}
    try:
        status = str(linha.get("status") or "").strip()
        dono = linha.get("claimed_by")
        desfecho = linha.get("resolvido_em")
    except AttributeError:                       # não é dicionário: não pausa
        return False
    if str(desfecho or "").strip():
        # 🔴 O atendimento TERMINOU. Não há mais quem calar.
        return False
    if status.upper() == HUMAN_REQUESTED:
        return True
    return bool(str(dono or "").strip())


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

#: 🔴 SPEC-097.1 U1.2 — O ESCOPO DA FASE QUE VEM DEPOIS DO PROTOCOLO.
#:
#: ⚠️ **Distinto de `'acionamento'` de propósito.** O `UNIQUE`
#: `uq_work_waits_ativo_por_escopo (company_id, conversation_id, scope) where
#: status='ativo'` permite UMA ativa **por escopo** — então o travamento do
#: corredor e a espera da seguradora convivem, que é o que a vida faz.
#: ⛔ Reusar `'acionamento'` faria a espera do pós nascer e morrer no mesmo
#: checkpoint: o ramo `else` de `_abrir_espera_do_travamento` satisfaz toda
#: fase ≠ `needs_human` naquele escopo (achado do gate zero, E4).
ESCOPO_POS_ACIONAMENTO = "pos_acionamento"

#: O escopo do travamento do corredor — o de sempre (SPEC-086 BLOCO B).
ESCOPO_ACIONAMENTO = "acionamento"

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


# ---------------------------------------------------------------------------
# 🔴 O PRAZO É UM `timestamptz` — e quem escreve nele fala DUAS línguas
# ---------------------------------------------------------------------------
#
# 📊 Achado do red team em 05/09/2026 ([3]): `vence_em` recebia o texto CRU do
# que a seguradora disse. Três desfechos, todos ruins:
#
#   'amanha de manha'  → o INSERT levanta e a espera some — e a ANTERIOR já
#                        tinha virado `'substituida'`: o caso fica SEM estado,
#                        pior do que antes da SPEC.
#   '12/09/2026'       → é EXATAMENTE o que a âncora `schedule` produz
#                        (`corridor_playbooks:1852`, grupo `(\d{1,2}/\d{1,2}/…)`).
#                        Postgres com DateStyle `ISO, MDY` lê **9 de dezembro**,
#                        três meses adiante, em silêncio; e `'29/08/2026'` — a
#                        data da cena do §0 — levanta.
#   previsão no PASSADO → a espera nasce vencida e o vigia dispara no 1º tick.
#
# ⚠️ CLAUDE.md §9.4 literal: **um padrão medido num motor e aplicado noutro é um
# padrão sobre outra coisa.** A data é escrita em Python, na língua do Brasil, e
# é em Python que ela vira instante — nunca no `DateStyle` do servidor.
#
# 🔴 E esta é a ÚNICA porta: `dispatch_router` monta o texto do agendamento e
# manda por aqui; `abrir_espera` valida por aqui **antes** de tocar na anterior.

#: O fuso da corretora. ⚠️ `'12/09/2026'` sem hora é meia-noite **em Brasília**,
#: não em UTC: em UTC seriam 21h do dia 11, e o dia mudaria na frente do cliente.
try:  # pragma: no cover - depende do tzdata do sistema
    from zoneinfo import ZoneInfo

    FUSO_DA_CORRETORA: Any = ZoneInfo("America/Sao_Paulo")
except Exception:  # noqa: BLE001  # pragma: no cover
    from datetime import timezone as _tz

    FUSO_DA_CORRETORA = _tz.utc

_DATA_BR = re.compile(
    r"^(\d{1,2})/(\d{1,2})/(\d{2,4})"
    r"(?:[\s,]+(?:[àa]s\s+)?(\d{1,2})[:h](\d{1,2})?)?\s*$", re.IGNORECASE)


def instante_br(bruto: Any) -> str:
    """Texto de prazo → ISO-8601 em UTC. `""` quando **não dá para saber**.

    Aceita ISO-8601 (com ou sem fuso) e `dd/mm/aaaa` (com ou sem hora), sempre
    lido como **dia/mês/ano**. ⛔ Recusa o resto — e recusar é a resposta certa:
    'amanhã de manhã' não é um instante, e chutar um faria o vigia cobrar numa
    data que ninguém prometeu (R3).

    🔴 **PURA.** É o guarda do `timestamptz`, e o guarda tem de conseguir
    reprovar: `instante_br('12/13/2026')` é `""` porque não existe mês 13 — é
    assim que se descobre que a leitura é BR e não MDY.
    """
    from datetime import datetime, timezone

    texto = str(bruto or "").strip()
    if not texto:
        return ""

    quando = None
    achado = _DATA_BR.match(texto)
    if achado:
        dia, mes, ano = (int(achado.group(1)), int(achado.group(2)),
                         int(achado.group(3)))
        if ano < 100:
            ano += 2000
        hora = int(achado.group(4) or 0)
        minuto = int(achado.group(5) or 0)
        try:
            quando = datetime(ano, mes, dia, hora, minuto,
                              tzinfo=FUSO_DA_CORRETORA)
        except ValueError:
            # 📊 `12/13/2026` cai aqui: mês 13 não existe. Em MDY seria 12 de
            #    dezembro, e o silêncio de três meses é o defeito [3].
            return ""
    else:
        try:
            quando = datetime.fromisoformat(texto.replace("Z", "+00:00"))
        except Exception:  # noqa: BLE001
            return ""
        if quando.tzinfo is None:
            quando = quando.replace(tzinfo=FUSO_DA_CORRETORA)
    return quando.astimezone(timezone.utc).isoformat()


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

    # 🔴 A VALIDAÇÃO VEM ANTES DE TOCAR NA ANTERIOR — achado [3] do red team.
    #
    # ⚠️ A ordem é a regra inteira: a substituição fecha a espera que existia, e
    # um INSERT que levanta DEPOIS disso deixa o caso **sem estado nenhum** —
    # pior do que antes desta SPEC. Validar aqui é o que garante que só se
    # derruba a anterior quando a nova tem como nascer.
    vence = instante_br(vence_em_iso)
    if not vence:
        logger.warning("[ESPERA] prazo ilegível (%r) — a espera NÃO foi aberta e a "
                       "anterior segue ativa. `vence_em` é timestamptz: só ISO ou "
                       "dd/mm/aaaa (R3)", str(vence_em_iso)[:40])
        return False, "vence_em_ilegivel"

    linha: Dict[str, Any] = {
        "company_id": empresa,                      # 🔴 §7
        "conversation_id": str(conversation_id),
        "kind": str(kind),
        "scope": str(scope or "default")[:120],
        "status": ATIVO,
        "vence_em": vence,
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

    # 🔴 SPEC-097.1 U1.2 — A NOVA SUBSTITUI A ANTERIOR, NO MESMO ESCOPO.
    #
    # 📊 Achado do gate zero da 097.1 ([B3p]/[K2]), e é defeito de PRODUTO, não
    # de teste: até aqui a segunda chamada batia no `UNIQUE`, voltava
    # `ja_existe_espera_ativa` — e a espera NOVA era simplesmente PERDIDA. No
    # pós-acionamento isso é a previsão que mudou de 12/09 para 19/09 e ninguém
    # nunca soube: o vigia seguiria cobrando pela data velha.
    #
    # ⚠️ **Satisfazer ANTES de inserir**, nesta ordem: o índice parcial só
    # olha `status='ativo'`, então fechar a anterior é o que abre a vaga. E o
    # motivo é `'substituida'` de propósito — quem ler o histórico precisa
    # distinguir *"o que se esperava aconteceu"* de *"a espera foi trocada por
    # uma mais nova"*.
    #
    # ⛔ O escopo do TRAVAMENTO ganha o mesmo comportamento, e é correto: dois
    # `needs_human` seguidos com prazos diferentes tinham o mesmo defeito.
    substituidas: list = []
    try:
        substituidas = await _fechar_esperas_ativas(
            db, company_id=empresa, conversation_id=str(conversation_id),
            por="substituida", scope=str(scope or "default"))
        if substituidas:
            logger.info("[ESPERA] %d espera(s) do escopo '%s' substituída(s) pela nova",
                        len(substituidas), scope)
    except Exception as erro:  # noqa: BLE001
        logger.warning("[ESPERA] substituição não feita (%s) — o INSERT ainda "
                       "pode bater no UNIQUE", type(erro).__name__)

    try:
        await db.client.table("work_waits").insert(linha).execute()
    except Exception as erro:  # noqa: BLE001
        texto = str(erro).lower()
        if "uq_work_waits_ativo_por_escopo" in texto or "duplicate key" in texto:
            await _devolver_ao_ativo(db, empresa, substituidas,
                                     conversation_id=str(conversation_id),
                                     scope=str(scope or "default"))
            return False, "ja_existe_espera_ativa"
        # 🔴 O INSERT FALHOU DEPOIS DE A ANTERIOR TER SIDO FECHADA — e é aqui
        # que o caso ficaria SEM ESTADO ([3] do red team). ⛔ Não existe
        # desfecho aceitável em que a espera antiga desapareça porque a nova
        # não conseguiu nascer: ela volta a `ativo`.
        devolvidas = await _devolver_ao_ativo(
            db, empresa, substituidas, conversation_id=str(conversation_id),
            scope=str(scope or "default"))
        # 🔴 O NÚMERO É O EFEITO, NUNCA A INTENÇÃO (§12.1). E quando ele é ZERO
        #    com esperas fechadas, o log grita: é a conversa ficando sem estado.
        if substituidas and not devolvidas:
            logger.error("[ESPERA] ❌ não aberta (%s) e a anterior NÃO voltou a "
                         "`ativo` — a conversa %s… está SEM ESPERA",
                         type(erro).__name__, str(conversation_id)[:8])
        else:
            logger.warning("[ESPERA] não aberta (%s) kind=%s — %d espera(s) "
                           "devolvida(s) a `ativo`", type(erro).__name__, kind,
                           devolvidas)
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
    fechadas = await _fechar_esperas_ativas(
        db, company_id=company_id, conversation_id=conversation_id,
        por=por, scope=scope)
    return len(fechadas)


async def _devolver_ao_ativo(db, company_id: str, linhas: Any,
                             conversation_id: str = "", scope: str = "") -> int:
    """Desfaz uma substituição que não valeu — as linhas voltam a `ativo`.

    ⛔ **Só existe para o caminho de erro de `abrir_espera`.** 📊 Sem ela, um
    INSERT recusado deixa a conversa sem espera nenhuma: o vigia não varre
    nada, o dossiê diz *"não há espera registrada"* e ninguém sabe que houve
    perda — o defeito [3] do red team, na sua forma mais silenciosa.

    ⚠️ **Devolve QUANTAS voltaram de verdade**, e o número é o que se registra.
    📊 Um contador que soma a intenção em vez do efeito foi o que fez este
    conserto quase passar num arnês em que ele não funcionava: o log dizia
    *"devolvida (1 linha)"* enquanto a linha seguia `satisfeito`.

    🔴 E há DOIS caminhos, porque o primeiro pode não ter id: o `UPDATE` devolve
    as linhas fechadas, mas nem todo cliente devolve o `id`. Sem o segundo
    caminho — por conversa e escopo, só o que foi fechado como `'substituida'` —
    o silêncio voltaria pela porta dos fundos.
    """
    empresa = str(company_id or "").strip()
    volta = {"status": ATIVO, "satisfeito_por": None, "satisfeito_em": None}
    devolvidas = 0
    for linha in (linhas or []):
        ident = str((linha or {}).get("id") or "")
        if not empresa or not ident:
            continue
        try:
            achado = await (db.client.table("work_waits").update(dict(volta))
                            .eq("company_id", empresa)     # 🔴 §7
                            .eq("id", ident).execute())
            devolvidas += len(achado.data or [])
        except Exception as erro:  # noqa: BLE001
            logger.error("[ESPERA] ❌ a espera %s NÃO voltou a ativo (%s) — esta "
                         "conversa pode ter ficado sem estado", ident[:8],
                         type(erro).__name__)

    if devolvidas or not (empresa and conversation_id and linhas):
        return devolvidas
    try:
        achado = await (db.client.table("work_waits").update(dict(volta))
                        .eq("company_id", empresa)         # 🔴 §7
                        .eq("conversation_id", str(conversation_id))
                        .eq("scope", str(scope or "default"))
                        .eq("satisfeito_por", "substituida")
                        .eq("status", SATISFEITO).execute())
        devolvidas = len(achado.data or [])
    except Exception as erro:  # noqa: BLE001
        logger.error("[ESPERA] ❌ nenhuma espera voltou a ativo (%s) — a conversa "
                     "%s… pode ter ficado SEM ESTADO", type(erro).__name__,
                     str(conversation_id)[:8])
    return devolvidas


async def _fechar_esperas_ativas(db, *, company_id: str, conversation_id: str,
                                 por: str, scope: str = "default") -> list:
    """O corpo de `satisfazer_espera`, devolvendo as LINHAS fechadas.

    ⚠️ As linhas — e não a contagem — porque `abrir_espera` precisa saber
    **quais** devolver ao ar se o INSERT novo não vingar.
    """
    from datetime import datetime, timezone

    empresa = str(company_id or "").strip()
    if not empresa or not conversation_id:
        return []
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
        return []

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
    return fechadas


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


# =============================================================================
# 🔴 A ÚLTIMA PALAVRA HUMANA DA CORRETORA MANDA
#     (PLANO-HANDOFF-E-PAUSA-2026-09-09 §2 · U3 · decisão do Founder 09/09)
# =============================================================================
#
# > *"Não é 'conversa de 15 dias'; é **quando foi a última vez que uma pessoa da
# > corretora escreveu nesta conversa**."*
#
# ```
# o agente responde ao segurado SE, E SÓ SE:
#   1. não há palavra humana da corretora nesta conversa nos últimos N dias
#      (cada nova mensagem da atendente RENOVA o prazo)
#   2. e a conversa não está reivindicada nem em HUMAN_REQUESTED  → `pausar_ia`
#   3. e o agente está ligado                                    → fora daqui
# ```
#
# ⚠️ **A regra (1) é a que faltava, e ela vale RETROATIVAMENTE.** Nenhuma coluna
# nova, nenhuma migration, nenhuma varredura: as 467 conversas antigas passam a
# obedecer no instante em que o agente liga, porque a resposta já está escrita
# em `messages`.
#
# 📊 **Por que N = 7 (nota 82/100 no plano §2):** assistência se resolve em 1–3
# dias; quem volta depois de uma semana quase sempre traz assunto novo; e o
# sinistro que a Regina conduz por semanas já está protegido pela RENOVAÇÃO a
# cada mensagem dela. N = 15 protege o caso raro do retorno em 10 dias e cala o
# agente em muitos contatos legítimos — e esse custo é invisível: segurado sem
# resposta.
#
# -----------------------------------------------------------------------------
# 🔴 O DEFEITO QUE ESTA SEÇÃO TEVE DE RESOLVER ANTES DE EXISTIR: O PRÓPRIO ECO
# -----------------------------------------------------------------------------
#
# ⛔ *"humana = `role='assistant'` com `payload.origem in ('espelho','dashboard')`"*
# **não basta**, e a ingenuidade aqui custaria o produto inteiro:
#
# ```
# webhook.py:1183   a resposta da IA é gravada com role='assistant' e SEM payload
# webhook.py:1766   a mesma resposta VOLTA como `fromMe` e o espelho a grava
#                   de novo — role='assistant', payload.origem='espelho'
# ```
#
# 📊 É o defeito que `whatsapp/voz_propria.py` documenta desde 14/08: *"o agente
# responderia UMA vez, pausaria a si mesmo e emudeceria para sempre"*. ⚠️ E o
# `voz_propria` **não serve aqui**: ele é digital em Redis, TTL de 180 s e
# consumo destrutivo — não há como perguntar a ele, sete dias depois, quem
# escreveu aquela linha.
#
# 🔴 Então o eco é reconhecido **no acervo**, e exige as DUAS coisas:
#
# ```
# A. o texto do balão está contido na fala que o agente gravou      (por balão!)
# B. e chegou dentro de _ECO_SEGUNDOS daquela fala
# ```
#
# ⚠️ Uma só não serve. Só (A): a atendente que digita *"ok"* meia hora depois
# vira eco e o robô fala por cima dela. Só (B): a atendente que responde em 40
# segundos — a corrida C'' do plano — vira eco, e é justamente ela quem mais
# precisa ser ouvida. ⛔ Exigir as duas deixa passar só o que é mesmo eco.
#
# 🔴 **E a direção da dúvida é o SILÊNCIO.** Falha de leitura, payload ilegível,
# origem desconhecida: tudo isso conta como palavra humana e o agente cala. É a
# mesma escolha de `voz_propria` e de `pode_falar_com_o_cliente`: calar é chato e
# reversível pelo botão "Devolver ao agente"; falar por cima da atendente na
# frente do segurado, não.

#: 📊 O padrão da plataforma, em dias. Ver a nota 82/100 acima.
JANELA_SILENCIO_HUMANO_DIAS = 7

#: A env que muda o padrão para a plataforma inteira.
_ENV_DA_JANELA = "JANELA_SILENCIO_HUMANO_DIAS"

#: A chave do override por corretora, em `companies.acionamento_profile`.
_CHAVE_DA_JANELA = "janela_silencio_humano_dias"

#: 🔴 As origens em que uma PESSOA da corretora escreveu.
#:
#:   `espelho`    `fromMe` pelo celular ou pelo WhatsApp Web
#:                (`espelho_chat.py:610`)
#:   `dashboard`  o painel (`app/api/dashboard/conversas/[id]/route.ts:532`)
#:
#: ⚠️ A resposta do próprio agente é gravada **sem `payload`** — é por isso que
#: a lista é fechada e por inclusão: uma origem nova e desconhecida não vira
#: "humana" por acidente, e também não vira "robô" por acidente (ver
#: `_falas_do_agente`).
ORIGENS_HUMANAS: Tuple[str, ...] = ("espelho", "dashboard")

#: Quantas linhas da conversa a janela carrega. ⚠️ É o teto do custo desta
#: regra: uma consulta por turno, servida por `idx_messages_by_conversation
#: (conversation_id, created_at)`, que já existe (`schema_completo.sql:2191`).
#: 📊 40 cobre com folga o par ida-e-volta de um atendimento inteiro; quem
#: escrever mais que isso depois da atendente já está calado por outro motivo.
_MENSAGENS_DA_JANELA = 40

#: A folga do eco. ⚠️ **O MESMO número do `voz_propria._TTL_SEGUNDOS`**, e pela
#: mesma razão: o eco volta em segundos, e o teto é folgado para um provedor
#: lento não fazer o agente se calar sozinho.
_ECO_SEGUNDOS = 180

#: Quanto do passado imediato pertence ao TURNO que está acontecendo agora.
#:
#: 🔴 `webhook.py` grava a mensagem do segurado (passo 5) **antes** de montar o
#: prompt (passo 7). Sem esta folga, "a última mensagem da conversa" seria
#: sempre a que acabou de chegar, e o reencontro nunca seria detectado.
_TURNO_SEGUNDOS = 120


def _quando(valor: Any):
    """Texto do PostgREST → `datetime` em UTC, ou `None`. **PURA.**

    ⛔ `None` é resposta, não erro: uma linha sem `created_at` legível não pode
    renovar nem vencer prazo nenhum — quem chama decide o que fazer com a
    dúvida, e nesta seção a dúvida sempre cala o agente.
    """
    from datetime import datetime, timezone

    if hasattr(valor, "tzinfo"):
        return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)
    texto = str(valor or "").strip()
    if not texto:
        return None
    try:
        quando = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return quando.replace(tzinfo=timezone.utc) if quando.tzinfo is None else quando


def _texto_normalizado(valor: Any) -> str:
    """A mesma normalização do `voz_propria._digital`: espaço colapsado, pontas
    aparadas, minúsculas. ⚠️ O WhatsApp não devolve byte a byte o que recebeu."""
    return re.sub(r"\s+", " ", str(valor or "")).strip().lower()


def janela_de_silencio_dias(companhia: Any = None) -> int:
    """N, em dias — **PURA** (lê a env, não o banco).

    ```
    padrão da plataforma   JANELA_SILENCIO_HUMANO_DIAS = 7
    env                    JANELA_SILENCIO_HUMANO_DIAS=15
    corretora              acionamento_profile.janela_silencio_humano_dias
    ```

    🔴 **`0` DESLIGA A REGRA, e é um valor legítimo** — é como uma corretora que
    não quer a janela volta ao comportamento de antes de 09/09 sem deploy. ⛔ Por
    isso o piso é `0` e não `1`: um `max(1, …)` transformaria "desligado" em
    "um dia", que é outra coisa.

    ⚠️ Valor ilegível ou negativo cai no padrão — nunca em zero. Um typo no
    `acionamento_profile` não pode DESLIGAR a proteção da atendente em silêncio.
    """
    padrao = JANELA_SILENCIO_HUMANO_DIAS
    try:
        bruto = os.environ.get(_ENV_DA_JANELA)
        if bruto is not None and str(bruto).strip():
            lido = int(float(str(bruto).strip()))
            if lido >= 0:
                padrao = lido
    except Exception:  # noqa: BLE001
        pass

    perfil = (companhia or {}).get("acionamento_profile") if isinstance(companhia, dict) else None
    perfil = perfil if isinstance(perfil, dict) else {}
    if _CHAVE_DA_JANELA not in perfil:
        return padrao
    try:
        # ⚠️ `int(float(...))` de propósito: o painel pode gravar `7.0`.
        # ⛔ Mas `bool` **não** é inteiro válido aqui: `True` viraria 1 dia.
        valor = perfil.get(_CHAVE_DA_JANELA)
        if isinstance(valor, bool):
            raise ValueError("bool nao e prazo")
        dias = int(float(str(valor).strip()))
    except Exception:  # noqa: BLE001
        logger.warning("[JANELA] `%s` ilegível no acionamento_profile — usando %d",
                       _CHAVE_DA_JANELA, padrao)
        return padrao
    return dias if dias >= 0 else padrao


# ---------------------------------------------------------------------------
# PURO — as perguntas sobre UMA linha de `messages`
# ---------------------------------------------------------------------------

def _payload(mensagem: Any) -> Dict[str, Any]:
    bruto = (mensagem or {}).get("payload") if isinstance(mensagem, dict) else None
    return bruto if isinstance(bruto, dict) else {}


def e_origem_humana(mensagem: Any) -> bool:
    """A linha nasceu de um teclado da corretora? — **PURA.**

    ⛔ `role='user'` é o segurado e nunca chega aqui. `role='assistant'` sem
    `payload` é o agente (`webhook.py:1183`).
    """
    if str((mensagem or {}).get("role") or "").strip().lower() != "assistant":
        return False
    return str(_payload(mensagem).get("origem") or "").strip().lower() in ORIGENS_HUMANAS


def e_anotacao(mensagem: Any) -> bool:
    """`#nota` — anotar **não é** assumir (SPEC-090 BLOCO C). **PURA.**

    🔴 Duas marcas, e as duas são necessárias:

    ```
    payload.nota_interna   o painel escreve (route.ts:532) — legível por máquina
    o prefixo no content   o painel TAMBÉM prefixa, e o espelho só tem isto
    ```

    ⚠️ A regra do prefixo é **uma só** e mora em `a_nota_da_atendente.e_nota`
    (§5). ⛔ Se ela não importar, a dúvida vira "é palavra humana" e o agente
    cala: uma anotação que cala o robô é um incômodo; uma intervenção lida como
    anotação é o robô falando por cima da atendente.
    """
    if _payload(mensagem).get("nota_interna") is True:
        return True
    try:
        from app.services.a_nota_da_atendente import e_nota
    except Exception as erro:  # noqa: BLE001
        logger.warning("[JANELA] regra do `#nota` indisponível (%s) — a linha "
                       "conta como palavra humana", type(erro).__name__)
        return False
    return bool(e_nota((mensagem or {}).get("content")))


def _falas_do_agente(mensagens) -> List[Tuple[Any, str]]:
    """`(instante, texto normalizado)` de cada fala que o AGENTE gravou.

    ⚠️ `role='assistant'` **sem** origem conhecida. É a linha do passo 8 do
    webhook — a única do acervo que é comprovadamente do robô.
    """
    falas: List[Tuple[Any, str]] = []
    for m in mensagens or ():
        if not isinstance(m, dict):
            continue
        if str(m.get("role") or "").strip().lower() != "assistant":
            continue
        if e_origem_humana(m):
            continue
        quando = _quando(m.get("created_at"))
        texto = _texto_normalizado(m.get("content"))
        if quando is not None and texto:
            falas.append((quando, texto))
    return falas


def e_eco_do_agente(mensagem: Any, falas_do_agente) -> bool:
    """Este `espelho` é o eco do que o próprio produto acabou de dizer? — **PURA.**

    🔴 **As duas condições, nunca uma só** (ver o cabeçalho da seção):
    o texto do balão está CONTIDO na fala gravada **e** chegou dentro de
    `_ECO_SEGUNDOS` dela.

    ⚠️ `in` e não `==` porque `whatsapp_service.send_message` quebra a resposta
    em balões (S17-9): comparar o texto inteiro reconheceria zero ecos — é o
    mesmo motivo pelo qual `voz_propria` registra a digital **por balão**.
    """
    texto = _texto_normalizado((mensagem or {}).get("content"))
    quando = _quando((mensagem or {}).get("created_at"))
    if not texto or quando is None:
        return False
    for fala_em, fala in falas_do_agente or ():
        atraso = (quando - fala_em).total_seconds()
        if -1.0 <= atraso <= _ECO_SEGUNDOS and texto in fala:
            return True
    return False


def ultima_palavra_humana(mensagens):
    """O instante da última vez que uma PESSOA da corretora escreveu — ou `None`.

    🔴 **PURA**, e é o coração da regra: cada nova mensagem dela RENOVA o prazo,
    então o que interessa é a **mais recente**, não a primeira.

    ⛔ Não conta: o segurado (`role='user'`), o próprio agente, o eco do agente
    espelhado e a anotação `#nota`.
    """
    falas = _falas_do_agente(mensagens)
    ultima = None
    for m in mensagens or ():
        if not isinstance(m, dict) or not e_origem_humana(m):
            continue
        if e_anotacao(m) or e_eco_do_agente(m, falas):
            continue
        quando = _quando(m.get("created_at"))
        if quando is not None and (ultima is None or quando > ultima):
            ultima = quando
    return ultima


def _dia_br(quando) -> str:
    """`16/09` — a data como a Regina lê. ⛔ Nunca o ISO cru na ficha."""
    from datetime import timezone

    try:
        return quando.astimezone(FUSO_DA_CORRETORA).strftime("%d/%m")
    except Exception:  # noqa: BLE001
        return quando.astimezone(timezone.utc).strftime("%d/%m")


#: 🔴 O COMEÇO DA FRASE DA JANELA — e é UMA constante de propósito.
#:
#: ⚠️ Os portões precisam separar *"calou porque alguém assumiu"* de *"calou
#: porque a atendente escreveu há pouco"*: só o segundo vira linha no feed. Um
#: terceiro elemento na tupla mudaria a assinatura que sete testes já
#: desempacotam; a frase já carrega a informação, e quem a escreve e quem a lê
#: passam pela **mesma** constante — que é o que impede o `startswith` de virar
#: regex sobre a prosa (`CLAUDE.md` §9.4).
_PREFIXO_DA_JANELA = "a atendente falou nesta conversa"


def foi_a_janela(motivo: Any) -> bool:
    """Este `motivo` de `a_ia_deve_calar` é o da JANELA? — **PURA.**"""
    return str(motivo or "").startswith(_PREFIXO_DA_JANELA)


def silenciar_por_palavra_humana(*, ultima_humana, agora=None, n_dias=None):
    """`(calar, motivo_em_portugues)` — **PURA**.

    🔴 O motivo é uma FRASE, e é de propósito: ela vai para o feed e para a
    ficha, onde quem lê é a Regina. 📊 `CLAUDE.md` §12.1 — um código de motivo
    (`janela_humana`) obrigaria a tela a traduzir, e a tradução é onde o texto
    envelhece longe do código que o produz.
    """
    from datetime import datetime, timedelta, timezone

    dias = janela_de_silencio_dias() if n_dias is None else int(n_dias)
    if dias <= 0:
        # ⚠️ A regra está desligada. Continua valendo tudo o mais.
        return False, ""
    if ultima_humana is None:
        return False, ""
    agora = agora or datetime.now(timezone.utc)
    vence = ultima_humana + timedelta(days=dias)
    if agora >= vence:
        return False, ""
    faz = max(0, int((agora - ultima_humana).total_seconds() // 86400))
    quanto = "hoje" if faz == 0 else ("há 1 dia" if faz == 1 else "há %d dias" % faz)
    return True, ("%s %s; o agente fica em silêncio até %s ou até ela devolver "
                  "a conversa" % (_PREFIXO_DA_JANELA, quanto, _dia_br(vence)))


# ---------------------------------------------------------------------------
# O ADAPTADOR — uma consulta, e ela nunca levanta
# ---------------------------------------------------------------------------

async def _executar(consulta):
    """`execute()` de PostgREST — e a casa tem os DOIS clientes.

    🔴 **Medido em 09/09/2026, e foi o que quase matou o bloco do
    reencontro em silêncio:** os serviços recebem o `AsyncSupabaseClient`
    (`database.py:235`) e escrevem `await …execute()`; o `graph.py` recebe o
    `SupabaseClient` SÍNCRONO e escreve `…execute()` sem `await`. Um `await`
    sobre a resposta síncrona levanta `TypeError`, o `except` do chamador
    engole, e o bloco **nunca aparece no prompt** — sem nada ficar vermelho
    (`CLAUDE.md` §9.1).

    ⚠️ O caminho síncrono vai para `to_thread` de propósito: `execute()` do
    cliente síncrono é `requests` puro e pararia o event loop inteiro enquanto
    uma conversa espera o PostgREST — a mesma razão do `to_thread` do envio no
    `webhook.py`.
    """
    import asyncio
    import inspect

    executar = consulta.execute
    if inspect.iscoroutinefunction(executar):
        return await executar()
    resultado = await asyncio.to_thread(executar)
    return (await resultado) if inspect.isawaitable(resultado) else resultado


def _cliente(db):
    """O PostgREST de dentro do `db`. ⚠️ Os chamadores da casa passam ora o
    wrapper (`db.client`), ora o cliente cru — `graph.py:1289` faz as duas
    coisas no mesmo arquivo."""
    return db.client if hasattr(db, "client") else db


async def janela_de_mensagens(db, conversation_id: str, *, teto: int = 0):
    """As últimas linhas da conversa, mais nova primeiro. `(linhas, erro)`.

    ⚠️ **Sem filtro JSON no banco, de propósito.** 📊 `espelho_chat` documenta
    que filtrar `payload->>origem` no PostgREST foi o que cegou o espelho; a
    marca é lida **em Python**, sobre as poucas linhas carregadas. A consulta
    usa só `conversation_id` + `created_at`, que é exatamente o índice que
    existe.

    🔴 **`messages` não tem `company_id`** (`schema_vivo.json`): quem garante o
    §7 é o `conversation_id`, e ele tem de ter sido resolvido COM a corretora.
    """
    conversa = str(conversation_id or "").strip()
    if not conversa:
        return [], "sem_conversa"
    try:
        achado = await _executar(_cliente(db).table("messages")
                                 .select("role, content, created_at, payload")
                                 .eq("conversation_id", conversa)
                                 .order("created_at", desc=True)
                                 .limit(int(teto or _MENSAGENS_DA_JANELA)))
    except Exception as erro:  # noqa: BLE001
        # ⛔ NUNCA loga conteúdo nem id de conversa — só o veredito.
        logger.warning("[JANELA] mensagens não lidas (%s)", type(erro).__name__)
        return [], type(erro).__name__
    return (achado.data or []), ""


async def a_ia_deve_calar(db, *, company_id: str, conversa: Any,
                          companhia: Any = None, agora=None, n_dias=None):
    """A porta inteira: `(calar, motivo)` — **e nunca levanta**.

    ```
    ① reivindicada / HUMAN_REQUESTED   `pausar_ia`, o helper de sempre (§5)
    ② palavra humana há menos de N     a regra nova do plano §2
    ```

    🔴 A ordem é a ordem do DANO, como em `pode_falar_com_o_cliente`: quem já
    está com a conversa no teclado vem primeiro, e nesse caso nem se paga a
    consulta.

    ⛔ **Falha de leitura CALA** (fail-closed). Não saber quem escreveu por
    último não é permissão para falar.
    """
    if not str(company_id or "").strip():
        return True, "sem corretora: o agente não fala sem saber de quem é a conversa"

    try:
        if pausar_ia(conversa or {}):
            dono = str((conversa or {}).get("claimed_by_name") or "").strip()
            if str((conversa or {}).get("claimed_by") or "").strip():
                return True, ("%s assumiu esta conversa; o agente só volta pelo "
                              "botão \"Devolver ao agente\""
                              % (dono or "Uma pessoa da corretora"))
            return True, ("o segurado pediu para falar com uma pessoa; o agente "
                          "fica em silêncio até alguém devolver a conversa")
    except Exception as erro:  # noqa: BLE001
        logger.warning("[JANELA] `pausar_ia` indisponível (%s) — calando",
                       type(erro).__name__)
        return True, "não consegui saber se alguém assumiu a conversa"

    dias = janela_de_silencio_dias(companhia) if n_dias is None else int(n_dias)
    if dias <= 0:
        # 🔴 A regra está DESLIGADA nesta corretora — e desligada é desligada:
        #    nem a consulta acontece. É o que torna `N=0` uma mutação capaz de
        #    ficar vermelha (CLAUDE.md §9.3).
        return False, ""

    linhas, erro = await janela_de_mensagens(db, str((conversa or {}).get("id") or ""))
    if erro == "sem_conversa":
        # ⚠️ Sem `id` não há como consultar. Não é falha do mundo: é chamador
        #    sem conversa, e aí a regra (2) simplesmente não se aplica.
        return False, ""
    if erro:
        return True, "não consegui ler o histórico desta conversa"

    return silenciar_por_palavra_humana(
        ultima_humana=ultima_palavra_humana(linhas), agora=agora, n_dias=dias)


# ---------------------------------------------------------------------------
# 🔴 O SILÊNCIO FICA VISÍVEL — uma linha por conversa por dia, e só isso
# ---------------------------------------------------------------------------
#
# ⚠️ **Sem tabela nova** (`CLAUDE.md` §5): o escritor é o `log_activity` que já
# alimenta a página Atividades. O que a Regina precisa ver é *"o agente ficou
# calado nesta conversa porque eu falei"* — e ela precisa ver isso UMA vez, não
# a cada mensagem do segurado.
#
# ⛔ **A memória do "uma vez por dia" é do PROCESSO, de propósito.** Guardá-la
# no banco custaria uma leitura por turno para economizar uma escrita por turno
# — e o feed é best-effort. Um contêiner novo repete a linha no máximo uma vez
# por dia por conversa, e é um preço que o feed paga sem mentir.

#: `{ "empresa:conversa:2026-09-09": True }` — e o teto existe para o dicionário
#: não virar vazamento numa instância que roda semanas.
_SILENCIO_JA_ANOTADO: Dict[str, bool] = {}
_TETO_DO_MEMO = 5000


def _chave_do_dia(company_id: str, conversation_id: str, agora=None) -> str:
    from datetime import datetime, timezone

    agora = agora or datetime.now(timezone.utc)
    try:
        dia = agora.astimezone(FUSO_DA_CORRETORA).strftime("%Y-%m-%d")
    except Exception:  # noqa: BLE001
        dia = agora.astimezone(timezone.utc).strftime("%Y-%m-%d")
    return "%s:%s:%s" % (company_id, conversation_id, dia)


async def anotar_silencio_no_feed(*, company_id: str, conversation_id: str,
                                  motivo: str, agora=None) -> bool:
    """A linha do silêncio no feed. `True` se ESCREVEU. **Nunca levanta.**

    🔴 Só o silêncio da JANELA vira linha. ⛔ Conversa reivindicada já tem o seu
    próprio registro (o takeover escreve na ficha): anotar de novo aqui encheria
    o feed de uma linha por mensagem do segurado enquanto a atendente conduz.
    """
    if not foi_a_janela(motivo):
        return False
    empresa = str(company_id or "").strip()
    conversa = str(conversation_id or "").strip()
    if not empresa or not conversa:
        return False

    chave = _chave_do_dia(empresa, conversa, agora)
    if chave in _SILENCIO_JA_ANOTADO:
        return False
    if len(_SILENCIO_JA_ANOTADO) >= _TETO_DO_MEMO:
        _SILENCIO_JA_ANOTADO.clear()
    _SILENCIO_JA_ANOTADO[chave] = True

    try:
        from app.services.activity_log import log_activity

        await log_activity(empresa, "atendimentos",
                           "O agente ficou em silêncio nesta conversa",
                           str(motivo or ""))
        return True
    except Exception as erro:  # noqa: BLE001
        logger.debug("[JANELA] feed não anotado (%s)", type(erro).__name__)
        return False


# =============================================================================
# 🔴 ASSUNTO NOVO e RELIGAMENTO — o que o agente precisa SABER antes de falar
# =============================================================================
#
# 📊 09/09/2026, produção: o robô cumprimentou *"bom dia, é bom começar o dia com
# você"* às 11:40 **na 30ª mensagem** de um sinistro com vítima. ⛔ Ele não sabia
# que já estava no meio de uma conversa, porque ninguém nunca lhe disse.
#
# ⚠️ **É DADO, nunca autorização.** O bloco descreve o que aconteceu na conversa;
# ele não muda regra protegida do prompt, não concede ferramenta e não decide
# quem fala — quem decide é `a_ia_deve_calar`, acima.

#: 💭 O texto do reencontro. ⚠️ Curto de propósito: 📊 os agentes `attendance`
#: têm prompt de ~1,5 KB, e meia página aqui competiria com as instruções da
#: dona do agente em vez de somar a elas (a mesma razão do `_FALE_COMO_CORRETOR`).
_ASSUNTO_NOVO = (
    "ESTE CONTATO VOLTA DEPOIS DE %s:\n"
    "- Trate como ASSUNTO NOVO: cumprimente e pergunte o que houve agora.\n"
    "- Não presuma que é o mesmo caso de antes.\n"
    "- Use o histórico só como MEMÓRIA (\"vi que já falamos sobre …\"), nunca "
    "como se a conversa não tivesse parado."
)

_RELIGAMENTO = (
    "ESTA CONVERSA JÁ ESTÁ EM ANDAMENTO:\n"
    "- NÃO cumprimente como se fosse o começo (nada de \"bom dia, é bom começar "
    "o dia com você\"): a última mensagem foi da própria corretora, %s.\n"
    "- Continue de onde parou, sem se reapresentar e sem repetir o que já foi "
    "perguntado."
)


def _quanto_tempo(segundos: float) -> str:
    """*"3 meses"*, *"13 dias"*, *"2 horas"* — como uma pessoa diria. **PURA.**"""
    dias = int(segundos // 86400)
    if dias >= 60:
        return "%d meses" % (dias // 30)
    if dias >= 1:
        return "1 dia" if dias == 1 else "%d dias" % dias
    horas = int(segundos // 3600)
    if horas >= 1:
        return "1 hora" if horas == 1 else "%d horas" % horas
    return "poucos minutos"


def contexto_do_reencontro(mensagens, *, agora=None, n_dias=None) -> str:
    """O bloco de prompt do reencontro, ou `""`. **PURA.**

    ⛔ **A mensagem que acabou de chegar não conta.** `webhook.py` grava o que o
    segurado escreveu (passo 5) ANTES de montar o prompt (passo 7): sem a folga
    de `_TURNO_SEGUNDOS`, "a última mensagem da conversa" seria sempre a
    própria, e o reencontro nunca seria visto.

    ⚠️ `""` é a resposta mais comum, e é a certa: no meio de um atendimento
    normal não há nada a dizer, e um bloco a mais em todo turno é token pago
    contra a atenção do modelo.
    """
    from datetime import datetime, timezone

    agora = agora or datetime.now(timezone.utc)
    dias = janela_de_silencio_dias() if n_dias is None else int(n_dias)

    anterior = None
    anterior_em = None
    for m in mensagens or ():
        if not isinstance(m, dict):
            continue
        quando = _quando(m.get("created_at"))
        if quando is None or (agora - quando).total_seconds() < _TURNO_SEGUNDOS:
            continue
        if anterior_em is None or quando > anterior_em:
            anterior, anterior_em = m, quando
    if anterior is None:
        # Primeiro contato desta conversa: não há reencontro nenhum.
        return ""

    idade = (agora - anterior_em).total_seconds()
    if dias > 0 and idade > dias * 86400:
        return _ASSUNTO_NOVO % _quanto_tempo(idade)
    if str(anterior.get("role") or "").strip().lower() == "assistant":
        return _RELIGAMENTO % ("há " + _quanto_tempo(idade))
    return ""


async def bloco_do_reencontro(db, *, company_id: str, conversation_id: str = "",
                              session_id: str = "", agora=None,
                              n_dias=None) -> str:
    """O mesmo bloco, indo buscar a conversa. **Nunca levanta**, `""` no escuro.

    🔴 O `company_id` é obrigatório e entra na resolução por `session_id` (§7):
    o backend usa service role, e uma conversa achada só pelo `session_id`
    poderia ser de outra corretora.
    """
    empresa = str(company_id or "").strip()
    if not empresa:
        return ""
    conversa = str(conversation_id or "").strip()
    if not conversa:
        sessao = str(session_id or "").strip()
        if not sessao:
            return ""
        try:
            achado = await _executar(_cliente(db).table("conversations")
                                     .select("id")
                                     .eq("company_id", empresa)   # 🔴 §7
                                     .eq("session_id", sessao)
                                     .limit(1))
            conversa = str(((achado.data or [{}])[0] or {}).get("id") or "")
        except Exception as erro:  # noqa: BLE001
            logger.warning("[REENCONTRO] conversa não resolvida (%s)",
                           type(erro).__name__)
            return ""
    linhas, erro = await janela_de_mensagens(db, conversa)
    if erro:
        # ⚠️ Aqui a dúvida NÃO cala ninguém: o pior caso é o agente falar sem
        #    esta dica, que é exatamente o comportamento de antes de 09/09.
        return ""
    return contexto_do_reencontro(linhas, agora=agora, n_dias=n_dias)
