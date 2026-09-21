# -*- coding: utf-8 -*-
"""O DONO DA CORRETORA SABE QUANDO A FILA DELE ESTÁ LONGA — uma vez, não dez.

> **O TESTE DO PRODUTO:** a corretora está com mais conversas ao mesmo tempo do
> que a cota permite, e ninguém do lado de lá sabe disso. Os segurados são
> atendidos por ordem de chegada — **nada se perde** —, mas quem responde por
> aquela corretora merece saber que hoje está mais devagar.

```
⛔ NASCE DESLIGADO          `ISOLAMENTO_AVISO_AO_DONO` ausente = não avisa
⛔ NENHUM CANAL NOVO        o caminho é `enviar_ao_grupo`, o único da casa
⛔ NENHUM DESTINO NOVO      quem resolve é `resolver_destino_de_suporte`
🔴 UM POR JANELA            trava `SET NX EX` por corretora — uma réplica só avisa
🔴 SEM REDIS, NÃO AVISA     é ENVIO: fail-closed (CLAUDE.md §3.2 piso CRÍTICO)
```

🔴 **POR QUE A JANELA É A REGRA INTEIRA.** 📊 DIAGNÓSTICO §1.5: o grupo da
corretora virou ruído porque um aviso saía de 10 em 10 minutos. Um aviso que se
repete deixa de ser lido, e o dia em que ele importar ninguém vai ver. A trava é
de REDIS, e não de memória do processo, porque duas réplicas do mesmo produto
avisariam duas vezes sobre a mesma coisa.

⛔ **Este módulo não decide nada sobre o atendimento.** Ele não adia, não
cancela e não reordena conversa nenhuma: ele só CONTA o que já está
acontecendo. Falhar aqui nunca custa uma resposta ao segurado.

⚠️ O texto é escrito para gente, sem jargão, e **sem nome de corretora fixo**
(CLAUDE.md §13.9): quem é a corretora já é o destino para onde a mensagem vai.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

#: 🔴 FAIL-CLOSED. Ausente, vazia ou qualquer coisa fora desta lista = NÃO avisa.
#: ⚠️ É o mesmo desenho de `ISOLAMENTO_ATRASO_ALLOWLIST` (§11.2): o default de um
#: mecanismo que produz efeito externo é "ninguém", nunca "todos".
FLAG_DO_AVISO = "ISOLAMENTO_AVISO_AO_DONO"
_LIGADO = {"1", "true", "on", "sim", "yes"}

#: Quanto tempo a corretora precisa estar esperando para valer um aviso.
#: 💭 60 s (ilustrativo, da proposta §8.3): abaixo disso é a rajada normal de
#: debounce (8–25 s) mais um turno, e avisar seria avisar do funcionamento.
ESPERA_MINIMA_S = "ISOLAMENTO_AVISO_ESPERA_S"
_ESPERA_PADRAO_S = 60

#: 💭 30 min entre dois avisos para a MESMA corretora.
JANELA_DO_AVISO_S = "ISOLAMENTO_AVISO_JANELA_S"
_JANELA_PADRAO_S = 1800

#: A trava, por corretora. ⚠️ O TTL da chave É a janela: ela solta sozinha.
CHAVE_DA_JANELA = "isolamento_aviso_dono:{company_id}"

#: Desde quando este escopo está esperando. 🔴 Vive AQUI, e não no
#: `message_buffer_service`: os contadores dele guardam QUANTAS estão esperando,
#: nunca DESDE QUANDO — e acrescentar um campo lá seria mexer num arquivo que
#: tem outro dono. `SET NX` faz o primeiro a chegar mandar no relógio.
CHAVE_DA_ESPERA = "isolamento_espera_desde:{escopo}"

#: 24 h, o mesmo prazo dos contadores: uma espera mais velha que isso não é
#: espera, é lixo de uma corretora que parou de falar.
_TTL_DA_ESPERA_S = 24 * 3600


def _env_int(nome: str, padrao: int) -> int:
    try:
        valor = int(str(os.getenv(nome, "")).strip() or padrao)
    except (TypeError, ValueError):
        return padrao
    return valor if valor >= 0 else padrao


def aviso_ligado() -> bool:
    """A flag. ⛔ Ausente é DESLIGADO — nunca "provavelmente sim"."""
    return str(os.getenv(FLAG_DO_AVISO, "")).strip().lower() in _LIGADO


def limiar_de_espera_s() -> int:
    """Quantos segundos de espera valem um aviso — **UMA grafia do número**.

    🔴 Existe para o chamador (`buffer_processor.avisar_os_donos_da_fila`) poder
    filtrar quem ainda nem chegou ao limiar SEM ir ao banco resolver de quem é a
    fila — e sem reescrever o `60` do outro lado. Duas grafias do mesmo número é
    como uma das duas nasce errada (CLAUDE.md §5); a porta ④ de
    `avisar_dono_se_fila_longa` continua conferindo o limiar por conta própria.
    """
    return _env_int(ESPERA_MINIMA_S, _ESPERA_PADRAO_S)


def texto_do_aviso(em_espera: int, em_execucao: Optional[int] = None) -> str:
    """A frase que vai ao grupo — **PURA**, para o guarda poder lê-la.

    ⛔ Sem jargão ("cota", "escopo", "buffer"), sem número de telefone, sem nome
    de corretora e sem promessa que o produto não cumpre. Ela diz o que é
    verdade: está mais cheio do que o normal, e ninguém foi perdido.
    """
    quantas = max(0, int(em_espera or 0))
    plural = "conversas estão" if quantas != 1 else "conversa está"
    agora = ""
    if em_execucao is not None:
        agora = (" Estamos respondendo %d ao mesmo tempo agora."
                 % max(0, int(em_execucao)))
    return (
        "Aviso rápido do atendimento automático: neste momento %d %s esperando a "
        "vez para receber resposta.%s Ninguém foi perdido — elas vão sendo "
        "respondidas por ordem de chegada, e isso costuma se resolver sozinho em "
        "alguns minutos. Se quiser, entrem na conversa normalmente: quando uma "
        "pessoa responde, o atendimento automático cala naquela conversa."
        % (quantas, plural, agora)
    )


# --------------------------------------------------------------------------- #
# AS DUAS COSTURAS — trocadas pelo guarda, nunca reimplementadas
# --------------------------------------------------------------------------- #
async def _redis():
    from app.core.redis import get_async_redis_client

    return await get_async_redis_client()


async def _enviar_ao_grupo(db, **kwargs):
    """O ÚNICO caminho de uma mensagem para o grupo da corretora (EXTRA-001.3).

    ⛔ Não se reimplementa aqui: é ele que traz a guarda "uma pessoa da equipe
    já está nesta conversa", o resolvedor único de destino (com a recusa de
    destino compartilhado entre corretoras) e o registro em `platform_sends`.
    """
    from app.services.o_grupo_so_o_que_importa import enviar_ao_grupo

    return await enviar_ao_grupo(db, **kwargs)


def _tipo_do_aviso() -> str:
    """`espera_vencida` — o tipo que a casa já tem para "isto está esperando".

    ⛔ Um tipo NOVO exigiria editar `o_grupo_so_o_que_importa.py`, que tem outro
    dono, e criaria um 12º caminho de aviso. ⚠️ A janela dele é 0 de propósito
    (*"por VENCIMENTO — o chamador decide"*), e quem decide aqui é a trava de
    Redis abaixo.
    """
    from app.services.o_grupo_so_o_que_importa import TIPO_ESPERA_VENCIDA

    return TIPO_ESPERA_VENCIDA


# --------------------------------------------------------------------------- #
# DESDE QUANDO ESTA CORRETORA ESTÁ ESPERANDO
# --------------------------------------------------------------------------- #
async def marcar_espera(escopo: str, *, agora_s: float) -> None:
    """Primeira varredura que viu este escopo esperando manda no relógio.

    `SET NX`: as varreduras seguintes não reescrevem o instante, senão a espera
    reiniciaria a cada 20 s e nunca passaria do limiar.
    """
    alvo = str(escopo or "").strip()
    if not alvo:
        return
    try:
        cliente = await _redis()
        await cliente.set(CHAVE_DA_ESPERA.format(escopo=alvo), str(int(agora_s)),
                          nx=True, ex=_TTL_DA_ESPERA_S)
    except Exception as erro:  # noqa: BLE001
        logger.debug("[AVISO-FILA] espera não marcada (%s)", type(erro).__name__)


async def esquecer_espera(escopo: str) -> None:
    """A fila desta corretora esvaziou: o relógio zera para a próxima vez."""
    alvo = str(escopo or "").strip()
    if not alvo:
        return
    try:
        cliente = await _redis()
        await cliente.delete(CHAVE_DA_ESPERA.format(escopo=alvo))
    except Exception as erro:  # noqa: BLE001
        logger.debug("[AVISO-FILA] espera não esquecida (%s)", type(erro).__name__)


async def esperando_ha(escopo: str, *, agora_s: float) -> Optional[float]:
    """Há quantos segundos este escopo está esperando. `None` = não dá para saber."""
    alvo = str(escopo or "").strip()
    if not alvo:
        return None
    try:
        cliente = await _redis()
        bruto = await cliente.get(CHAVE_DA_ESPERA.format(escopo=alvo))
        if bruto is None:
            return None
        texto = bruto.decode() if isinstance(bruto, (bytes, bytearray)) else str(bruto)
        return max(0.0, float(agora_s) - float(int(texto)))
    except Exception as erro:  # noqa: BLE001
        logger.debug("[AVISO-FILA] espera não lida (%s)", type(erro).__name__)
        return None


# --------------------------------------------------------------------------- #
# O AVISO
# --------------------------------------------------------------------------- #
async def avisar_dono_se_fila_longa(
    db, *, company_id: str, em_espera: int,
    esperando_ha_s: Optional[float] = None,
    em_execucao: Optional[int] = None,
) -> bool:
    """Manda UM aviso ao suporte desta corretora, se for o caso. `True` = saiu.

    🔴 **As quatro portas, nesta ordem, e todas fecham por padrão:**

    ```
    ① a flag está ligada?         ausente → não avisa
    ② a fila está longa E esperando há mais que o limiar?
    ③ o Redis deu a trava da janela?   sem Redis → não avisa
    ④ a guarda do grupo deixou?   (dentro de `enviar_ao_grupo`)
    ```

    ⛔ **Nunca levanta.** Um aviso perdido é ruim; derrubar a varredura de
    buffers por causa de um aviso é pior — e a varredura é o que responde ao
    segurado.
    """
    empresa = str(company_id or "").strip()
    quantas = max(0, int(em_espera or 0))
    if not empresa or quantas <= 0:
        return False

    # ① a flag
    if not aviso_ligado():
        return False

    # ② o limiar de espera. ⛔ `None` (não sei há quanto tempo) NÃO passa: sem
    #    saber, avisar seria avisar a cada varredura.
    limiar = _env_int(ESPERA_MINIMA_S, _ESPERA_PADRAO_S)
    if esperando_ha_s is None or float(esperando_ha_s) < limiar:
        return False

    # ③ a trava da janela — é ela que faz "um por janela", e é de Redis porque
    #    duas réplicas avisariam duas vezes sobre a mesma fila.
    janela = _env_int(JANELA_DO_AVISO_S, _JANELA_PADRAO_S)
    try:
        cliente = await _redis()
        reservou = await cliente.set(CHAVE_DA_JANELA.format(company_id=empresa),
                                     "1", nx=True, ex=max(1, janela))
    except Exception as erro:  # noqa: BLE001
        # 🔴 FAIL-CLOSED. Sem trava não existe "um por janela" — existe "um por
        # varredura", que é exatamente como o grupo virou ruído.
        logger.warning("[AVISO-FILA] sem trava, nenhum aviso sai (%s)",
                       type(erro).__name__)
        return False
    if not reservou:
        return False

    # ④ o caminho único, com a guarda de "já tem gente na conversa" dentro dele
    try:
        saida = await _enviar_ao_grupo(
            db, company_id=empresa, tipo=_tipo_do_aviso(),
            texto=texto_do_aviso(quantas, em_execucao),
            resumo="fila de atendimento acima do normal",
            motivo="fila_longa", dedup=False)
        enviou = bool((saida or {}).get("enviado"))
        # ⛔ Só contagens no log. Nome de corretora, telefone e texto ficam fora.
        logger.info("[AVISO-FILA] aviso ao dono | em_espera=%d | enviado=%s",
                    quantas, enviou)
        return enviou
    except Exception as erro:  # noqa: BLE001
        logger.warning("[AVISO-FILA] aviso não saiu (%s)", type(erro).__name__)
        return False


async def avisar_pelos_escopos(db, resumo: Any, escopo_para_corretora) -> int:
    """A porta que o processador de buffers chama — devolve quantos avisos saíram.

    `resumo` é o dicionário que `processar_buffers_prontos` já devolve; o que
    esta função usa dele é `adiadas` (por motivo) e nada mais.
    ⚠️ **Hoje o resumo NÃO é por escopo** — ele soma a varredura inteira. Ligar
    esta porta sem essa quebra avisaria a corretora errada, então ela só aceita
    o mapa `escopo → (company_id, em_espera)` que o chamador montar.
    """
    saíram = 0
    for escopo, dados in dict(escopo_para_corretora or {}).items():
        empresa, quantas = dados[0], dados[1]
        if await avisar_dono_se_fila_longa(
                db, company_id=empresa, em_espera=quantas,
                esperando_ha_s=dados[2] if len(dados) > 2 else None):
            saíram += 1
    return saíram
