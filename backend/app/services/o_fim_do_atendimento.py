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
#: 🔴 A conversa-FANTASMA de `@lid`: uma linha cujo `user_phone` é um
#: identificador interno do WhatsApp, sem telefone — que **ninguém consegue
#: abrir e para a qual ninguém consegue responder**.
#:
#: 📊 175 delas em 13/09/2026, 100% abertas (`migrar_conversas_fantasma_lid.py`).
#: ⛔ Isto **não** é o encerramento em lote que a D-PILOTO-02 proíbe: aquela
#: decisão fala das 467 conversas REAIS da AutoFleet, que o agente deve
#: continuar respondendo. Conjuntos diferentes, e o dry-run do script imprime a
#: contagem dos dois para provar que não se misturam.
#:
#: ⚠️ O valor tem de existir aqui **e** no CHECK do banco (migration
#: `20260914_07`): sem ele aqui, `marcar_fim` levanta `ValueError`; sem ele lá,
#: o banco recusa o UPDATE. Metade do conserto é conserto nenhum.
FANTASMA_LID = "fantasma_lid"

MOTIVOS: Tuple[str, ...] = (
    ACIONAMENTO_CONCLUIDO, ENCAMINHADO, RESOLVIDO_PELO_SEGURADO,
    FECHADO_POR_HUMANO, EXPIROU, FANTASMA_LID,
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


def _momento(valor: Any):
    """`datetime` com fuso a partir de um ISO-8601 do PostgREST, ou `None`.

    ⚠️ Ilegível devolve `None` de propósito: quem chama decide o lado seguro, e
    aqui adivinhar formato seria inventar uma ordem entre dois instantes.
    """
    from datetime import datetime, timezone

    texto = str(valor or "").strip()
    if not texto:
        return None
    try:
        quando = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return None
    return quando if quando.tzinfo else quando.replace(tzinfo=timezone.utc)


def _assumida_depois_do_desfecho(claimed_at: Any, resolvido_em: Any) -> bool:
    """Alguém assumiu a conversa **depois** de ela ter sido encerrada? — PURA.

    🔴 É a pergunta de P-PILOTO-15, e ela é estritamente `>`: assumir e encerrar
    no mesmo instante é o fluxo normal (a atendente conduz e fecha), e ali a
    pausa morre com o desfecho, como em 05/09/2026.
    """
    inicio = _momento(claimed_at)
    fim = _momento(resolvido_em)
    if inicio is None or fim is None:
        return False
    return inicio > fim


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

    ---------------------------------------------------------------------------
    🔴 **E A EXCEÇÃO DA EXCEÇÃO — P-PILOTO-15, 14/09/2026**

    Se alguém assumiu a conversa **depois** do desfecho (`claimed_at` posterior
    a `resolvido_em`), o atendimento recomeçou e há de novo quem calar. Sem esta
    terceira regra, a conversa encerrada em setembro e reaberta pelo segurado em
    novembro fica desprotegida **exatamente** quando a atendente está dentro
    dela — e o robô fala por cima de uma pessoa.
    """
    linha = conversa or {}
    try:
        status = str(linha.get("status") or "").strip()
        dono = linha.get("claimed_by")
        desfecho = linha.get("resolvido_em")
        assumida_em = linha.get("claimed_at")
    except AttributeError:                       # não é dicionário: não pausa
        return False
    if str(desfecho or "").strip():
        # 🔴 O atendimento TERMINOU. Não há mais quem calar — **a não ser que
        #    alguém tenha assumido DEPOIS do desfecho** (P-PILOTO-15).
        #
        # 📊 O defeito, escrito na pendência: *"`pausar_ia` devolve False quando
        # `resolvido_em` está preenchido e a pausa não limpa o campo; conversa
        # encerrada e reaberta pelo segurado com intervenção humana não fica
        # protegida"*. O segurado volta em novembro numa conversa encerrada em
        # setembro, a atendente ASSUME, e o robô fala por cima dela.
        #
        # ⚠️ **A alternativa era a pausa LIMPAR `resolvido_em`** — e ela custa
        # caro: 📊 12 leitores do campo (`atendimentos/ficha/[id]/route.ts:384`
        # desenha o FIM na linha do tempo; `:515`/`:519` decidem `pode_assumir`
        # e `pode_encerrar`; `acompanhamento.py:522`; `attendance_ficha.py:151`;
        # `saudacao_do_religamento.py:97`; `o_fim_do_atendimento` usa
        # `.is_("resolvido_em","null")` como IDEMPOTÊNCIA de `marcar_fim`).
        # Apagar o campo apagaria o fato de que o atendimento terminou — e
        # `pausar_ia` é **pura**: ela não escreve, e não deve passar a escrever.
        #
        # 🔴 A comparação é de TEXTO ISO-8601 em UTC, e é ela mesma: os dois
        # campos são `timestamptz` serializados pelo PostgREST no mesmo formato.
        # ⚠️ Ilegível ou ausente → cai no comportamento de sempre (False), que é
        # o que não reintroduz o "calado para sempre" medido em 05/09/2026.
        if not _assumida_depois_do_desfecho(assumida_em, desfecho):
            return False
        return bool(str(dono or "").strip())
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


# ---------------------------------------------------------------------------
# Números de TESTE que ficam FORA da regra (Founder, 10/09/2026)
# ---------------------------------------------------------------------------
# `JANELA_SILENCIO_EXCECOES` = telefones separados por vírgula (só dígitos,
# com ou sem o 55 e com ou sem o nono dígito). Enquanto o número estiver na
# lista, o agente trata a conversa dele como conversa NOVA: nem a janela de
# N dias nem a pausa por intervenção humana o calam. Só o piloto usa isto;
# lista vazia = ninguém é exceção. Nunca escrever números aqui: só no ambiente.
_ENV_EXCECOES_DA_JANELA = "JANELA_SILENCIO_EXCECOES"


def _variantes_do_telefone(telefone: Any) -> set:
    d = re.sub(r"\D", "", str(telefone or ""))
    if not d:
        return set()
    if d.startswith("55") and len(d) >= 12:
        d = d[2:]
    out = {d}
    if len(d) == 11 and d[2] == "9":          # DDD + 9 + 8 dígitos → sem o nono
        out.add(d[:2] + d[3:])
    elif len(d) == 10:                         # DDD + 8 dígitos → com o nono
        out.add(d[:2] + "9" + d[2:])
    return out


def telefone_e_excecao_da_janela(telefone: Any, bruto: Optional[str] = None) -> bool:
    """O telefone está na lista de exceções do ambiente? Falha para o lado do NÃO."""
    try:
        lista = os.getenv(_ENV_EXCECOES_DA_JANELA, "") if bruto is None else bruto
        alvo = _variantes_do_telefone(telefone)
        if not alvo:
            return False
        for item in str(lista or "").split(","):
            if _variantes_do_telefone(item) & alvo:
                return True
        return False
    except Exception:  # noqa: BLE001
        return False


async def a_ia_deve_calar(db, *, company_id: str, conversa: Any,
                          companhia: Any = None, agora=None, n_dias=None):
    """A porta inteira: `(calar, motivo)` — **e nunca levanta**.

    ```
    ① sem `company_id`                 fail-closed: não se fala sem saber de quem é
    ② reivindicada / HUMAN_REQUESTED   `pausar_ia`, o helper de sempre (§5)
    ③ telefone de TESTE na lista       pula SÓ a regra ④, nunca o ②
    ④ palavra humana há menos de N     a janela
    ```

    🔴 **A ORDEM MUDOU EM 14/09/2026, e a antiga era um defeito de produto.**

    📊 Até aqui a lista de exceções (`JANELA_SILENCIO_EXCECOES`) era consultada
    **antes** de `pausar_ia` — logo, um telefone na lista neutralizava
    `claimed_by` e `HUMAN_REQUESTED`: **o robô falava por cima da atendente**. O
    comentário do env já admitia a intenção ("nem a janela nem a pausa o calam"),
    o docstring desta função descrevia dois passos e **omitia a exceção**, e 📊
    `grep -rn JANELA_SILENCIO_EXCECOES` devolvia 2 linhas, ambas dentro deste
    próprio motor: **nenhum teste**.

    ⚠️ A exceção continua existindo e continua servindo ao piloto — ela só
    deixou de valer para o takeover. Um número de teste é para testar o agente,
    não para atropelar quem está atendendo.

    🔴 **E TODA SAÍDA COM SILÊNCIO ESCREVE NO FEED, aqui.** Esta é a ÚNICA
    função que decide calar, e por isso é o único lugar onde "todo silêncio tem
    motivo" pode ser garantido — em vez de depender de cada chamador lembrar.
    📊 Medido em 13/09/2026: **8.574 silêncios no meio de conversa** (26,0% dos
    turnos de cliente) e **6 motivos** escritos no banco inteiro.
    `anotar_silencio_no_feed` nunca levanta e dedupe por conversa/motivo/dia.

    ⛔ **Falha de leitura CALA** (fail-closed). Não saber quem escreveu por
    último não é permissão para falar.
    """
    # ⚠️ Em `try` próprio: esta função promete **nunca levantar**, e uma linha
    # ilegível vinda do banco não pode derrubar o portão do silêncio logo na
    # primeira instrução — é justamente o caso que termina em fail-closed.
    try:
        conversa_id = str((conversa or {}).get("id") or "")
    except Exception:  # noqa: BLE001
        conversa_id = ""

    async def _calar(motivo: str):
        await anotar_silencio_no_feed(company_id=str(company_id or ""),
                                      conversation_id=conversa_id, motivo=motivo,
                                      agora=agora)
        return True, motivo

    if not str(company_id or "").strip():
        # ⛔ Sem corretora não há feed onde escrever (o `log_activity` é por
        #    `company_id`). O motivo continua voltando ao chamador.
        return True, "sem corretora: o agente não fala sem saber de quem é a conversa"

    try:
        if pausar_ia(conversa or {}):
            dono = str((conversa or {}).get("claimed_by_name") or "").strip()
            if str((conversa or {}).get("claimed_by") or "").strip():
                return await _calar(
                    "%s assumiu esta conversa; o agente só volta pelo "
                    "botão \"Devolver ao agente\"" % (dono or "Uma pessoa da corretora"))
            return await _calar(
                "o segurado pediu para falar com uma pessoa; o agente "
                "fica em silêncio até alguém devolver a conversa")
    except Exception as erro:  # noqa: BLE001
        logger.warning("[JANELA] `pausar_ia` indisponível (%s) — calando",
                       type(erro).__name__)
        return await _calar("não consegui saber se alguém assumiu a conversa")

    if telefone_e_excecao_da_janela((conversa or {}).get("user_phone")):
        # 🔴 DEPOIS do takeover, e a NÃO-calada também vira linha no feed.
        #
        # ⚠️ Sem ela, a Regina vê o robô falando numa conversa que ela pausou e
        # não tem como saber por quê. 💭 A frase é frase, não código — quem lê é
        # ela, e a tela não traduz nada (§12.1).
        logger.info("[JANELA] telefone de teste na lista de exceções: tratado como conversa nova")
        await anotar_silencio_no_feed(
            company_id=str(company_id), conversation_id=conversa_id,
            motivo=MOTIVO_EXCECAO_DE_TESTE, agora=agora)
        return False, ""

    dias = janela_de_silencio_dias(companhia) if n_dias is None else int(n_dias)
    if dias <= 0:
        # 🔴 A regra está DESLIGADA nesta corretora — e desligada é desligada:
        #    nem a consulta acontece. É o que torna `N=0` uma mutação capaz de
        #    ficar vermelha (CLAUDE.md §9.3).
        return False, ""

    linhas, erro = await janela_de_mensagens(db, conversa_id)
    if erro == "sem_conversa":
        # ⚠️ Sem `id` não há como consultar. Não é falha do mundo: é chamador
        #    sem conversa, e aí a regra (2) simplesmente não se aplica.
        return False, ""
    if erro:
        return await _calar("não consegui ler o histórico desta conversa")

    calar, motivo = silenciar_por_palavra_humana(
        ultima_humana=ultima_palavra_humana(linhas), agora=agora, n_dias=dias)
    if calar:
        return await _calar(motivo)
    return False, ""


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


#: 💭 A frase da NÃO-calada por exceção de telefone. Ela não é um silêncio — é o
#: contrário — e por isso tem título próprio no feed.
MOTIVO_EXCECAO_DE_TESTE = ("número de teste: o agente respondeu mesmo com a "
                           "conversa pausada")

#: 🔴 As CLASSES de silêncio. Elas existem por dois motivos, e nenhum é
#: "traduzir para a tela":
#:
#:   1. a chave do memo diário precisa de um valor ESTÁVEL. A frase do takeover
#:      carrega `claimed_by_name` — NOME DE PESSOA — e usá-la na chave colocaria
#:      PII numa estrutura de processo, além de gerar uma chave nova a cada
#:      troca de atendente.
#:   2. um guarda precisa poder afirmar "os cinco motivos produziram cinco
#:      linhas" sem reimplementar as frases (CLAUDE.md §9.4).
#:
#: ⚠️ A frase continua sendo o que vai para o feed. A classe nunca aparece para
#: a Regina.
_CLASSES_POR_INICIO = (
    ("sem corretora", "sem_corretora"),
    ("o segurado pediu para falar com uma pessoa", "pedido_de_pessoa"),
    ("não consegui saber se alguém assumiu", "falha_ao_ler_o_takeover"),
    ("não consegui ler o histórico", "falha_ao_ler_o_historico"),
    (MOTIVO_EXCECAO_DE_TESTE, "excecao_de_teste"),
    (_PREFIXO_DA_JANELA, "janela"),
)


def classe_do_silencio(motivo: Any) -> str:
    """A classe estável deste motivo — **PURA**.

    Tudo que não casa com um começo conhecido é `takeover`: a frase do takeover
    **começa pelo nome de quem assumiu**, então ela não tem prefixo fixo, e ser
    o padrão é o que impede um nome de pessoa de virar chave.
    """
    texto = str(motivo or "").strip()
    if not texto:
        return "sem_motivo"
    for inicio, classe in _CLASSES_POR_INICIO:
        if texto.startswith(inicio):
            return classe
    return "takeover"


def _chave_do_dia(company_id: str, conversation_id: str, motivo: Any = "",
                  agora=None) -> str:
    from datetime import datetime, timezone

    agora = agora or datetime.now(timezone.utc)
    try:
        dia = agora.astimezone(FUSO_DA_CORRETORA).strftime("%Y-%m-%d")
    except Exception:  # noqa: BLE001
        dia = agora.astimezone(timezone.utc).strftime("%Y-%m-%d")
    return "%s:%s:%s:%s" % (company_id, conversation_id,
                            classe_do_silencio(motivo), dia)


async def anotar_silencio_no_feed(*, company_id: str, conversation_id: str,
                                  motivo: str, agora=None) -> bool:
    """A linha do silêncio no feed. `True` se ESCREVEU. **Nunca levanta.**

    🔴 **O FILTRO `if not foi_a_janela(motivo): return False` SAIU EM
    14/09/2026.** Ele deixava de fora tudo que a Regina mais precisa ver:

    ```
    o silêncio por takeover / HUMAN_REQUESTED    (era "já tem registro na ficha")
    o silêncio por falta de corretora
    as DUAS falhas fail-closed                   ("não consegui ler…")
    a NÃO-calada por exceção de telefone         (só um `logger.info`)
    ```

    📊 Medido em 13/09/2026: **8.574 silêncios no meio de conversa** (26,0% dos
    32.935 turnos de cliente; 27,7% desde 01/09) contra **6** motivos escritos no
    banco inteiro — e `conversation_logs` tem 566 linhas, **todas
    `status='success'`**: uma resposta que nunca saiu não deixava linha nenhuma.

    ⚠️ O argumento antigo ("encheria o feed") continua respeitado, e agora por
    construção: **uma linha por conversa, por CLASSE de motivo, por dia**.

    ⛔ **A frase nunca carrega narrativa do segurado** (CLAUDE.md §7). Ela diz a
    razão do silêncio; o relato do sinistro não entra em feed, log nem artifact.
    """
    empresa = str(company_id or "").strip()
    conversa = str(conversation_id or "").strip()
    if not empresa or not conversa or not str(motivo or "").strip():
        return False

    chave = _chave_do_dia(empresa, conversa, motivo, agora)
    if chave in _SILENCIO_JA_ANOTADO:
        return False
    if len(_SILENCIO_JA_ANOTADO) >= _TETO_DO_MEMO:
        _SILENCIO_JA_ANOTADO.clear()
    _SILENCIO_JA_ANOTADO[chave] = True

    e_excecao = classe_do_silencio(motivo) == "excecao_de_teste"
    titulo = ("O agente respondeu mesmo com a conversa pausada" if e_excecao
              else "O agente ficou em silêncio nesta conversa")
    try:
        from app.services.activity_log import log_activity

        await log_activity(empresa, "atendimentos", titulo, str(motivo or ""))
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


# ===========================================================================
# 🔴 A APRESENTAÇÃO SAI DO MODELO — SPEC-EXTRA-001.2 §8.1
# ===========================================================================
#
# 📊 O conflito, medido em 13/09/2026: `prompts.py` (bloco ESTÁTICO, cacheado)
# dizia `- SEMPRE se apresente com nome E corretora na primeira mensagem`, e o
# `_RELIGAMENTO` acima (bloco DINÂMICO) dizia `Continue de onde parou, sem se
# reapresentar`. Duas instruções, dois blocos, e a estática vem PRIMEIRO no
# prompt. O modelo leu "primeira mensagem" como "primeira MINHA" e cumprimentou
# na 30ª mensagem de um sinistro com vítima.
#
# ⚠️ Trocar o texto do prompt não é conserto (AAA §3). A decisão vira CÓDIGO
# puro aqui, e o prompt recebe só o resultado — UMA linha.

#: Os três modos. `""` é o mais comum, e é o certo: no meio de um atendimento
#: não há nada a dizer sobre quem é você.
MODO_PRIMEIRA = "primeira"
MODO_MUDOU_DE_NOME = "mudou_de_nome"
MODO_CALADO = ""


def nome_normalizado(nome: Any) -> str:
    """O nome sem acento, sem caixa e sem espaço duplo. **PURA.**

    ⚠️ É a mesma régua em três lugares: comparar o nome do agente com o de um
    membro da equipe (§10.5), decidir se o nome MUDOU (§10.4) e casar a
    assinatura do dossiê. Três réguas diferentes dariam três respostas para a
    mesma pergunta.
    """
    import unicodedata

    texto = str(nome or "").strip().lower()
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.split())


def deve_se_apresentar(*, assunto_novo: bool, apresentado_neste_assunto: bool,
                       nome_atual: str, nome_da_apresentacao: str) -> Tuple[bool, str]:
    """`(apresenta?, modo)` — **PURA**. modo em `{"", "primeira", "mudou_de_nome"}`.

    A ordem das três perguntas é o contrato inteiro:

    1. **assunto novo vence tudo.** A identidade da thread é reescrita (§8.3):
       quem se apresentou no caso de 22 dias atrás não se apresentou NESTE.
    2. **já se apresentou neste assunto -> cala.** Inclusive se o nome mudou no
       meio (§10.4): trocar de pessoa no meio de um acionamento é pior que
       manter o nome antigo até o assunto fechar.
    3. **o nome mudou desde a última apresentação -> diz isso UMA vez.**
    """
    novo = bool(assunto_novo)
    ja = bool(apresentado_neste_assunto) and not novo
    if ja:
        return False, MODO_CALADO

    atual = nome_normalizado(nome_atual)
    antes = nome_normalizado(nome_da_apresentacao)
    if antes and atual and antes != atual:
        return True, MODO_MUDOU_DE_NOME
    return True, MODO_PRIMEIRA


def _corretora_no_texto(corretora: Any) -> str:
    """*"da Resulta"* ou *"da corretora"*. ⛔ **NUNCA "da sua corretora"** — a
    regra já estava escrita em `prompts.py` e o agente a quebrava."""
    nome = str(corretora or "").strip()
    return "da %s" % nome if nome else "da corretora"


def linha_da_apresentacao(modo: str, *, agent_name: str = "",
                          corretora: str = "", nome_anterior: str = "") -> str:
    """A ÚNICA linha que o bloco dinâmico recebe sobre apresentação. **PURA.**

    💭 A copy é ilustrativa (o tom final vem do Jeito de atender da corretora);
    o que é contrato é **quantas vezes** ela aparece.

    ⚠️ Nome vazio -> *"a assistente virtual da {corretora}"*. Antes desta SPEC o
    bloco de identidade inteiro sumia quando o nome estava em branco, e o
    agente ficava sem identidade nenhuma (§10.2).
    """
    empresa = _corretora_no_texto(corretora)
    nome = str(agent_name or "").strip()
    if modo == MODO_CALADO:
        return ("APRESENTAÇÃO: ⛔ NÃO se apresente e NÃO cumprimente — você já "
                "está nesta conversa. Continue de onde parou.")
    if modo == MODO_MUDOU_DE_NOME:
        antes = str(nome_anterior or "").strip()
        quem = nome or "a assistente virtual"
        return ("APRESENTAÇÃO: você mudou de nome desde a última vez. Diga isso "
                "UMA vez, assim: \"Oi! Aqui é a %s, %s — antes eu me "
                "apresentava como %s.\" Depois siga direto para o que ele "
                "precisa." % (quem, empresa, antes or "outro nome"))
    if nome:
        exemplo = ("\"Oi! Aqui é a %s, assistente virtual %s. Como posso "
                   "ajudar?\"" % (nome, empresa))
    else:
        exemplo = ("\"Oi! Aqui é a assistente virtual %s. Como posso ajudar?\""
                   % empresa)
    return ("APRESENTAÇÃO: apresente-se agora, UMA vez, assim: %s — e só. "
            "Não repita isso em nenhuma mensagem seguinte deste atendimento."
            % exemplo)


# ===========================================================================
# 🔴 A HIERARQUIA DE TAMANHO — SPEC-EXTRA-001.2 §8.2
# ===========================================================================
#
# 📊 As regras JÁ existem em `prompts.py` ("frases CURTAS (1 a 3 por
# mensagem)", "máximo 4 itens", a exceção documental) — e o piloto de 10/09
# mediu mensagens de **760 caracteres**. Prosa no prompt não conserta prosa do
# modelo: é preciso MEDIR a resposta e devolvê-la ao modelo com a régua.
#
# 📊 A régua humana, medida no acervo (14/09, 6.213 rajadas >=3 respondidas):
# mediana **92 caracteres** por bloco de resposta, 1 a 2 mensagens.
#
# ⚠️ ⛔ Balões NÃO são a régua. `whatsapp/balloons.py` (300/500/4) fatia a
# resposta para ela parecer gente — é HUMANIZAÇÃO. "Uma resposta por rajada" é
# UM TURNO, nunca um balão; contar balões mediria a coisa errada.

CLASSE_CONVERSA = "conversa"
CLASSE_BLOCO = "bloco_de_ate_4"
CLASSE_LISTA_DOCUMENTAL = "lista_documental"
CLASSE_AVISAR = "avisar"

#: `0` = **sem teto**, e é a exceção DECLARADA: meia lista de documentos é pior
#: que lista nenhuma — o cliente vai ao órgão e volta sem o papel certo.
TETO_POR_CLASSE = {
    CLASSE_CONVERSA: 3,
    CLASSE_BLOCO: 4,
    CLASSE_LISTA_DOCUMENTAL: 0,
    CLASSE_AVISAR: 1,
}

#: 💭 O vocabulário do assunto DELICADO. ⚠️ Ele não decide sozinho: só conta
#: quando a resposta PERGUNTA (tem `?`). "Que bom que ninguém se feriu" é
#: acolhimento, não interrogatório.
_PALAVRAS_DELICADAS = (
    "vítima", "vitima", "ferido", "ferida", "feriu", "machucou", "machucado",
    "óbito", "obito", "faleceu", "morte", "morreu", "ambulância", "ambulancia",
    "socorro médico", "socorro medico", "hospital", "culpa", "culpado",
    "embriaguez", "alcool", "álcool",
)

#: 💭 O vocabulário DOCUMENTAL. A lista de documentos é instrução, não pergunta
#: — e tem tamanho próprio (`prompts.py`, a exceção documental).
_PALAVRAS_DOCUMENTAIS = (
    "documento", "documentos", "cnh", "rg", "cpf", "crlv",
    "boletim de ocorrência", "boletim de ocorrencia", "b.o.", "comprovante",
    "nota fiscal", "laudo", "procuração", "procuracao", "certidão", "certidao",
    "foto", "fotos", "orçamento", "orcamento", "chave reserva", "apólice",
    "apolice", "extrato",
)

_ITEM = re.compile(r"^\s*(?:\d{1,2}\s*[\).\-:]|[-*•·]|[a-z]\))\s+",
                   re.MULTILINE)
_ITEM_EM_LINHA = re.compile(r"(?<!\d)(\d{1,2})\s*\)\s+")
_FIM_DE_FRASE = re.compile(r"[.!?…]+(?:\s|$)|\n+")


def _contar_itens(texto: str) -> int:
    """Quantos itens enumerados a resposta tem — em linha ou em lista.

    ⚠️ O produto ENSINA o bloco numerado em UMA linha corrida ("me confirma: 1)
    o endereço 2) pra onde levar 3) quem estará com o carro"). Contar só início
    de linha veria 0 itens exatamente no formato que a régua existe para medir.
    """
    em_linha = len(_ITEM_EM_LINHA.findall(texto or ""))
    em_lista = len(_ITEM.findall(texto or ""))
    return max(em_linha, em_lista)


def _contar_frases(texto: str) -> int:
    limpo = str(texto or "").strip()
    if not limpo:
        return 0
    pedacos = [p.strip() for p in _FIM_DE_FRASE.split(limpo) if p and p.strip()]
    return max(1, len(pedacos))


def classe_do_tamanho(resposta: str, *, contexto: str = "") -> Tuple[str, int, int]:
    """`(classe, n_unidades, n_chars)` — **PURA**.

    `n_unidades` é o que o teto daquela classe conta: **itens** em
    `bloco_de_ate_4`, **frases** nas outras. Medir frase num bloco numerado
    reprovaria justamente o formato que o produto ensina.

    A ordem das perguntas é o contrato:

    1. **pergunta delicada?** (vítima, ferimento, culpa) -> `avisar`, teto **1**.
       ⛔ Ela nunca entra em bloco — vai sozinha, com calma.
    2. **lista documental?** -> `lista_documental`, **sem teto** (a exceção
       declarada).
    3. **bloco numerado?** -> `bloco_de_ate_4`, teto **4**.
    4. o resto é `conversa`, teto **3** frases.
    """
    texto = str(resposta or "")
    n_chars = len(texto.strip())
    baixo = texto.lower()
    pista = str(contexto or "").strip().lower()
    itens = _contar_itens(texto)
    frases = _contar_frases(texto)

    delicada = "?" in texto and any(p in baixo for p in _PALAVRAS_DELICADAS)
    if delicada or pista == CLASSE_AVISAR:
        return CLASSE_AVISAR, frases, n_chars

    documental = (pista == CLASSE_LISTA_DOCUMENTAL
                  or (itens >= 3 and any(p in baixo for p in _PALAVRAS_DOCUMENTAIS)))
    if documental:
        return CLASSE_LISTA_DOCUMENTAL, itens or frases, n_chars

    if itens >= 2 or pista == CLASSE_BLOCO:
        return CLASSE_BLOCO, itens, n_chars

    return CLASSE_CONVERSA, frases, n_chars


#: 🔴 O TETO DE CARACTERES — e ele existe porque o guarda o exigiu.
#:
#: 📊 O defeito de 10/09 tinha **760 caracteres** e apenas TRÊS frases: um
#: monólogo de três períodos longos passa inteiro por um teto de frases. Contar
#: só frase mediria pontuação, não textão.
#:
#: 📊 O número sai do acervo (14/09, 6.213 rajadas ≥3 respondidas): a resposta
#: humana tem mediana **92** caracteres e **p90 432**. O teto é 450 — o p90
#: arredondado: acima disso a mensagem já não é o que uma pessoa manda.
#: ⚠️ `0` = sem teto de caracteres (a lista documental e o bloco numerado, que
#: têm teto próprio de ITENS).
CHARS_POR_CLASSE = {
    CLASSE_CONVERSA: 450,
    CLASSE_BLOCO: 0,
    CLASSE_LISTA_DOCUMENTAL: 0,
    CLASSE_AVISAR: 300,
}


def fora_da_classe(resposta: str, *, contexto: str = "") -> Tuple[bool, str, int, int]:
    """`(estourou?, classe, n_unidades, teto)` — **PURA**.

    ⚠️ Teto `0` é sem teto: `lista_documental` **nunca** estoura. É a diferença
    entre uma régua e uma mordaça.

    🔴 Duas perguntas, não uma: **quantas unidades** (frases ou itens) e
    **quantos caracteres**. Cada uma pega o que a outra não pega — o textão de
    três períodos passa na primeira e só a segunda o vê.
    """
    classe, unidades, n_chars = classe_do_tamanho(resposta, contexto=contexto)
    teto = TETO_POR_CLASSE.get(classe, 0)
    teto_chars = CHARS_POR_CLASSE.get(classe, 0)
    if teto > 0 and unidades > teto:
        return True, classe, unidades, teto
    if teto_chars > 0 and n_chars > teto_chars:
        return True, classe, unidades, teto
    return False, classe, unidades, teto


def regua_do_tamanho(classe: str) -> str:
    """A régua EXPLÍCITA que volta ao modelo na regeneração. **PURA.**

    ⛔ Regenerar sem dizer o que estourou é torcer para o modelo adivinhar — o
    mesmo erro que o fiscal da pergunta repetida já não comete.
    """
    if classe == CLASSE_AVISAR:
        return ("Esta é uma pergunta DELICADA: ela vai SOZINHA, em UMA frase, "
                "com calma e sem mais nada junto.")
    if classe == CLASSE_BLOCO:
        return ("Você está pedindo dados em bloco: no MÁXIMO 4 itens "
                "numerados, com o porquê no fim.")
    return ("Esta é uma mensagem de conversa: no MÁXIMO 3 frases curtas e no "
            "máximo 450 caracteres. Nada de textão — 📊 a resposta humana "
            "mediana tem 92 caracteres.")


# ===========================================================================
# 🔴 "ESPECIALISTA" NOMEIA A ATENDENTE REAL, NUNCA O AGENTE — §10.3
# ===========================================================================
#
# 📊 O piloto mostrou o agente prometendo "vou passar para a especialista" sem
# dizer quem — e `prompts.py` ENSINAVA nomes inventados ("a Ana", "o Marcos",
# "o analista"). ⛔ Um nome que não existe na corretora é pior que nenhum: o
# segurado pergunta pela Ana e ninguém sabe quem é.
#
# ⚠️ **Não existe papel `attendant`** em `company_members` (📊 14/09: só
# `admin_company` e `member`) — P-PILOTO-16, decisão D-E0012-02. A regra (1),
# o PLANTÃO com horário, é do card Equipe e pertence à EXTRA-001.3 (D-PILOTO-09).

def atendente_de_plantao(company_id: str,
                         membros: Optional[List[Dict[str, Any]]] = None,
                         *, plantao: Optional[str] = None) -> Optional[str]:
    """O nome da pessoa a quem o agente vai passar o caso, ou `None`. **PURA.**

    Regra determinística, **declarada e nesta ordem**:

    1. plantão marcado, se existir -> é ela. ⚠️ Hoje o conceito de plantão não
       existe no produto (EXTRA-001.3): o parâmetro fica declarado e `None`.
    2. **exatamente um** `member` ativo não-owner na corretora -> é ela.
    3. qualquer outro caso (nenhum, ou mais de um) -> `None`.

    🔴 `None` NÃO vira nome inventado, e ⛔ **nunca** o nome do agente: o agente
    prometendo passar o caso para si mesmo é o defeito que esta função existe
    para tornar impossível.
    """
    if not str(company_id or "").strip():
        return None

    de_plantao = str(plantao or "").strip()
    if de_plantao:
        return de_plantao

    candidatos: List[str] = []
    for m in membros or ():
        if not isinstance(m, dict):
            continue
        if str(m.get("company_id") or company_id) != str(company_id):
            continue                                   # 🔴 §7: nunca outra corretora
        if str(m.get("status") or "active").strip().lower() != "active":
            continue
        if m.get("is_owner"):
            continue
        if str(m.get("role") or "").strip().lower() != "member":
            continue
        nome = str(m.get("name") or m.get("first_name") or "").strip()
        if nome:
            candidatos.append(nome)

    return candidatos[0] if len(candidatos) == 1 else None


#: 💭 As duas copies. ⛔ Nenhuma das duas contém o nome do AGENTE.
_COM_NOME = ("Vou passar seu caso para a %s, da nossa equipe. Ela te responde "
             "por aqui.")
_SEM_NOME = ("Vou passar seu caso para a nossa equipe. Uma pessoa te responde "
             "por aqui.")


def linha_de_quem_vai_atender(nome: Optional[str]) -> str:
    """A linha do prompt sobre QUEM recebe o caso. **PURA.**

    ⚠️ Ela substitui os nomes inventados que o prompt estático ensinava.
    """
    quem = str(nome or "").strip()
    if quem:
        return ("QUEM VAI ATENDER quando o caso sair da sua mão: **%s**. Diga o "
                "nome dela, assim: \"%s\"" % (quem, _COM_NOME % quem))
    return ("QUEM VAI ATENDER quando o caso sair da sua mão: ⛔ você NÃO sabe o "
            "nome. Não invente um, e NUNCA use o seu próprio nome. Diga assim: "
            "\"%s\"" % _SEM_NOME)


def colisao_com_a_equipe(nome_do_agente: str,
                         membros: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
    """O nome do membro com quem o nome do agente colide, ou `None`. **PURA.**

    📊 14/09: **0** colisões hoje nas 3 corretoras (10 membros ativos) — a
    validação nasce guardando o futuro.

    ⚠️ Compara o nome COMPLETO e o PRIMEIRO nome, normalizados. "Amanda" bate
    com "Amanda Silva": no grupo e no dossiê ninguém saberia quem falou.
    ⛔ E só membros da MESMA corretora (CLAUDE.md §7) — quem filtra é o chamador,
    que é quem tem a consulta com `company_id`.
    """
    alvo = nome_normalizado(nome_do_agente)
    if not alvo:
        return None
    primeiro_alvo = alvo.split(" ")[0]
    for m in membros or ():
        if not isinstance(m, dict):
            continue
        if str(m.get("status") or "active").strip().lower() != "active":
            continue
        nome = str(m.get("name") or "").strip()
        if not nome:
            continue
        norm = nome_normalizado(nome)
        if not norm:
            continue
        if norm == alvo or norm.split(" ")[0] == primeiro_alvo:
            return nome
    return None


async def nome_de_quem_vai_atender(db, company_id: str) -> Optional[str]:
    """O nome da atendente real desta corretora, indo buscar a equipe.

    **Nunca levanta**, `None` no escuro — e `None` é uma resposta legítima
    (§10.3): a copy sem nome existe justamente para isso.

    🔴 §7: `company_members` é filtrado por `company_id` na consulta, e o nome
    vem de `users_v2` só para os `user_id` daquela corretora.
    """
    empresa = str(company_id or "").strip()
    if not empresa:
        return None
    try:
        cli = _cliente(db)
        vinculos = await _executar(cli.table("company_members")
                                   .select("user_id, role, is_owner, status")
                                   .eq("company_id", empresa)
                                   .eq("status", "active").limit(200))
        linhas = list(vinculos.data or [])
        if not linhas:
            return None
        ids = [str(v.get("user_id")) for v in linhas if v.get("user_id")]
        if not ids:
            return None
        pessoas = await _executar(cli.table("users_v2")
                                  .select("id, first_name, last_name")
                                  .in_("id", ids).limit(200))
        por_id = {str(p.get("id")): p for p in (pessoas.data or [])}
        membros = []
        for v in linhas:
            p = por_id.get(str(v.get("user_id"))) or {}
            nome = " ".join(x for x in (p.get("first_name"), p.get("last_name"))
                            if x).strip()
            membros.append({"company_id": empresa, "status": "active",
                            "role": v.get("role"), "is_owner": v.get("is_owner"),
                            "name": nome})
        return atendente_de_plantao(empresa, membros)
    except Exception as erro:  # noqa: BLE001
        logger.warning("[QUEM ATENDE] equipe indisponível (%s)",
                       type(erro).__name__)
        return None


async def membros_da_corretora(db, company_id: str) -> List[Dict[str, Any]]:
    """A equipe ATIVA desta corretora, com o nome montado. `[]` no escuro.

    ⚠️ É a lista que `colisao_com_a_equipe` compara com o nome do agente.
    """
    empresa = str(company_id or "").strip()
    if not empresa:
        return []
    try:
        cli = _cliente(db)
        vinculos = await _executar(cli.table("company_members")
                                   .select("user_id, role, is_owner, status")
                                   .eq("company_id", empresa)
                                   .eq("status", "active").limit(500))
        linhas = list(vinculos.data or [])
        ids = [str(v.get("user_id")) for v in linhas if v.get("user_id")]
        if not ids:
            return []
        pessoas = await _executar(cli.table("users_v2")
                                  .select("id, first_name, last_name")
                                  .in_("id", ids).limit(500))
        saida = []
        for p in (pessoas.data or []):
            nome = " ".join(x for x in (p.get("first_name"), p.get("last_name"))
                            if x).strip()
            if nome:
                saida.append({"company_id": empresa, "status": "active",
                              "name": nome})
        return saida
    except Exception as erro:  # noqa: BLE001
        logger.warning("[EQUIPE] indisponível (%s)", type(erro).__name__)
        return []


# ===========================================================================
# 🔴 A IDENTIDADE DA THREAD ENTRA NO PROMPT — e é UMA linha de cada coisa
# ===========================================================================

def bloco_de_quem_fala(*, assunto_novo: bool, identidade: Dict[str, Any],
                       agent_name: str, corretora: str,
                       quem_vai_atender: Optional[str] = None,
                       agora=None) -> Tuple[str, Dict[str, Any]]:
    """`(bloco_do_prompt, identidade_nova)` — **PURA**.

    Três linhas, nunca mais: quem fala (APRESENTAÇÃO), como chamar o segurado
    (TRATAMENTO) e quem recebe o caso (QUEM VAI ATENDER).

    🔴 A linha de TRATAMENTO vem por último de propósito: ela é a ÚNICA
    autoridade sobre o nome do segurado, e o bloco de MEMÓRIA — que pode
    carregar o nome de um caso antigo — vem antes no prompt.
    """
    from datetime import datetime, timezone

    agora = agora or datetime.now(timezone.utc)
    ident = dict(identidade or {})
    apresentado = bool(ident.get("apresentado_em"))

    apresenta, modo = deve_se_apresentar(
        assunto_novo=assunto_novo, apresentado_neste_assunto=apresentado,
        nome_atual=agent_name,
        nome_da_apresentacao=str(ident.get("nome_da_apresentacao") or ""))

    linhas = [linha_da_apresentacao(
        modo if apresenta else MODO_CALADO, agent_name=agent_name,
        corretora=corretora,
        nome_anterior=str(ident.get("nome_da_apresentacao") or ""))]

    titular = str(ident.get("titular_nome") or "").strip()
    if titular:
        linhas.append("TRATAMENTO: chame o segurado de **%s** — é o nome DESTE "
                      "atendimento." % titular)
    else:
        linhas.append("TRATAMENTO: ⛔ você NÃO sabe o nome de quem está falando "
                      "neste atendimento. Não use nenhum nome que apareça na "
                      "memória, no histórico ou em documentos antigos — "
                      "pergunte, ou fale sem nome.")

    linhas.append(linha_de_quem_vai_atender(quem_vai_atender))

    if apresenta:
        ident["apresentado_em"] = agora.isoformat()
        ident["nome_da_apresentacao"] = str(agent_name or "").strip()

    return "=== 🪪 QUEM FALA NESTE TURNO ===\n" + "\n".join(linhas), ident
