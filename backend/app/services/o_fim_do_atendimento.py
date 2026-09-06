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
    try:
        substituidas = await satisfazer_espera(
            db, company_id=empresa, conversation_id=str(conversation_id),
            por="substituida", scope=str(scope or "default"))
        if substituidas:
            logger.info("[ESPERA] %d espera(s) do escopo '%s' substituída(s) pela nova",
                        substituidas, scope)
    except Exception as erro:  # noqa: BLE001
        logger.warning("[ESPERA] substituição não feita (%s) — o INSERT ainda "
                       "pode bater no UNIQUE", type(erro).__name__)

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
