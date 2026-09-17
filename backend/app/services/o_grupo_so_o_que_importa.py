"""O GRUPO SÓ RECEBE O QUE IMPORTA — a guarda única, a porta única, o contador.

📊 10/09/2026, 17:14:18 → 18:29:59 UTC: **7 mensagens ao grupo da Resulta em
75,7 minutos, todas sobre UMA conversa** — e a Saionara já tinha digitado "1"
às 17:18:14. Seis das sete saíram DEPOIS de um humano da corretora estar
dentro daquela conversa.

```sql
-- 📊 reproduzido em 16/09/2026 (read-only, SUPABASE_DB_URL): 7 | 75,68 min
with t as (
  select created_at, title from agent_activities
   where created_at >= '2026-09-10' and created_at < '2026-09-11'
     and (title ilike 'Dossi%' or title ilike '%desconectado%')
  union all
  select created_at, event_type from work_events where event_type='espera.vencida')
select count(*), extract(epoch from (max(created_at)-min(created_at)))/60 from t;
```

⛔ **ESTE MÓDULO NÃO IMPLEMENTA REGRA NENHUMA.** Ele COMPÕE as que já existem:

```
a janela de N dias .......  o_fim_do_atendimento.janela_de_silencio_dias / ultima_palavra_humana
quem assumiu .............  conversations.claimed_by / claimed_at
o casador de telefone ....  o_fim_do_atendimento._variantes_do_telefone
o destino ................  dispatch_router.resolver_destino_de_suporte
o marcador ...............  human_handoff.reivindicar_o_aviso  (a CHAVE muda, o mecanismo não)
o ledger .................  platform_outbound.record_platform_send
o diário .................  work_events
```

🔴 **A janela do grupo é A MESMA janela do atendimento** (§7.2 do diagnóstico):
uma regra, um número, um lugar para mudar. ⛔ Criar `JANELA_DO_GRUPO_DIAS`
reprova o bloco — e o guarda `G-A3` procura por essa constante no repositório
inteiro.

⚠️ **Módulo LEVE de propósito.** `handoff_watchdog.py` registra por que:
importar `app.agents.tools.human_handoff` no topo arrasta `app.agents` →
`graph.py` → `langgraph`, e `start_buffer_scheduler()` é chamado por `main.py`
sem `try` no startup. Todo import pesado acontece DENTRO da função, sob `try`
(CLAUDE.md §9.1 — *"build verde não é prova de que a aplicação sobe"*).
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ===========================================================================
# OS TIPOS — e quais são ISENTOS da guarda
# ===========================================================================
TIPO_PEDIDO_DE_AJUDA = "pedido_de_ajuda"
TIPO_SINISTRO = "sinistro"
TIPO_CONCLUSAO = "conclusao"
TIPO_ESPERA_VENCIDA = "espera_vencida"
TIPO_VIGIA = "vigia"
TIPO_RESUMO_DIARIO = "resumo_diario"
TIPO_QUEDA_DE_CANAL = "queda_de_canal"
TIPO_COBRANCA = "cobranca"
#: 🔴 SPEC-EXTRA-001.4 C — o aviso "vi que você entrou na conversa com a
#: seguradora". É o ÚNICO que sai com a pausa aberta: ele é SOBRE a pausa.
TIPO_PAUSA_HUMANA = "pausa_humana"
#: 🔴 SPEC-EXTRA-001.4 D2 — "a seguradora respondeu, retomei". Só depois de um
#: pedido de ajuda (quem chama confere `dossier_sent`).
TIPO_RETOMADA = "retomada"

#: 🔴 O que a guarda **não** cala, e o porquê está escrito na SPEC §5.3.
#:
#: `sinistro`      é NOTÍCIA DE NEGÓCIO, não lembrete de fila. A corretora
#:                 precisa saber que existe um sinistro mesmo que alguém já
#:                 esteja conversando.
#: `conclusao`     é o fechamento, e é curto. Calar a conclusão porque um
#:                 humano participou apagaria justamente o caso em que houve
#:                 trabalho humano.
#: `resumo_diario` é uma mensagem por dia, sobre o dia, não sobre uma conversa.
#: `queda_de_canal` é sobre o CANAL da corretora, não sobre uma conversa; ele
#:                 muda de DESTINATÁRIO (§7.4), não de guarda.
#:
#: ⚠️ Uma guarda que cala tudo é tão defeituosa quanto uma que não cala nada
#: (CLAUDE.md §9.3). O gate G-A1 mede os DOIS lados.
TIPOS_ISENTOS = frozenset({
    TIPO_SINISTRO, TIPO_CONCLUSAO, TIPO_RESUMO_DIARIO, TIPO_QUEDA_DE_CANAL,
})

#: Quanto tempo a mesma (corretora, conversa, tipo) fica sem repetir — §7.5.
#: 🔴 A chave da deduplicação é a CONVERSA, não a SESSÃO: 📊 no 10/09 saíram
#: 3 dossiês em 21 min porque a sessão de acionamento reabriu três vezes e o
#: marcador vivia em `session["dossier_sent"]`.
_UM_DIA = 24 * 3600
JANELA_DE_DEDUP_S = {
    TIPO_PEDIDO_DE_AJUDA: 6 * 3600,     # a cadência de HANDOFF_REALERTA_HORAS
    TIPO_ESPERA_VENCIDA: 0,             # por VENCIMENTO — o chamador decide (§7.2)
    TIPO_SINISTRO: _UM_DIA,
    TIPO_CONCLUSAO: _UM_DIA,
    TIPO_VIGIA: _UM_DIA,
    TIPO_RESUMO_DIARIO: _UM_DIA,
    TIPO_QUEDA_DE_CANAL: 6 * 3600,
    TIPO_COBRANCA: _UM_DIA,
    # 💭 30 min: a atendente que entra e sai da conversa várias vezes não vira
    #    uma mensagem por entrada (a sessão também marca `avisou_grupo` por pausa).
    TIPO_PAUSA_HUMANA: 30 * 60,
    TIPO_RETOMADA: 6 * 3600,
}

MOTIVO_PAUSA_HUMANA = "uma pessoa da equipe está na conversa com a seguradora agora"
_CHAVE_DA_PAUSA = "pausa_humana:{empresa}:{alvo}"


async def marcar_pausa_humana(company_id: str, alvos, segundos: int) -> None:
    """Índice TRANSITÓRIO da pausa humana, por conversa e por telefone (§6: Redis).

    ⚠️ A autoridade é a SESSÃO do acionamento (`session["pausa_humana"]`); este
    índice existe para quem NÃO tem a sessão na mão (a `espera.vencida`, que só
    conhece a conversa e o telefone do segurado). Expira sozinho com a pausa.
    """
    empresa = str(company_id or "").strip()
    if not empresa or int(segundos or 0) <= 0:
        return
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        for alvo in {str(a).strip() for a in (alvos or ()) if str(a or "").strip()}:
            await r.set(_CHAVE_DA_PAUSA.format(empresa=empresa, alvo=alvo), "1",
                        ex=max(1, int(segundos)))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[GRUPO] índice da pausa humana não gravado (%s)", type(exc).__name__)


async def desmarcar_pausa_humana(company_id: str, alvos) -> None:
    empresa = str(company_id or "").strip()
    if not empresa:
        return
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        for alvo in {str(a).strip() for a in (alvos or ()) if str(a or "").strip()}:
            await r.delete(_CHAVE_DA_PAUSA.format(empresa=empresa, alvo=alvo))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[GRUPO] índice da pausa humana não apagado (%s)", type(exc).__name__)


def alvos_da_pausa(conversation_id: Any = "", telefone: Any = "") -> Set[str]:
    """As chaves do índice: `conv:<id>` e `tel:<variante>` para cada forma do número."""
    alvos = {"conv:%s" % str(conversation_id).strip()} if str(conversation_id or "").strip() else set()
    if str(telefone or "").strip():
        alvos |= {"tel:%s" % v for v in _variantes(telefone)}
    return alvos


async def _pausa_humana_na_conversa(empresa: str, sessao: Any, conversa_id: str,
                                    fone: str) -> bool:
    """A causa `pausa_humana` — pela SESSÃO quando ela veio, senão pelo índice.

    ⛔ Fail-open, como o resto da guarda: sem conseguir ler, NÃO cala."""
    if isinstance(sessao, dict):
        try:
            from app.services.insurer_dispatch_service import pausa_humana_aberta

            if pausa_humana_aberta(sessao):
                return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("[GRUPO] pausa ilegível na sessão (%s)", type(exc).__name__)
    alvos = alvos_da_pausa(conversa_id, fone)
    if not alvos:
        return False
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        for alvo in alvos:
            if await r.get(_CHAVE_DA_PAUSA.format(empresa=empresa, alvo=alvo)):
                return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("[GRUPO] índice da pausa ilegível (%s) — vou deixar avisar",
                       type(exc).__name__)
    return False

#: Os eventos contáveis deste módulo. ⛔ Nenhuma tabela de métrica nova.
EVENTO_GRUPO_ENVIADO = "grupo.enviado"
EVENTO_GRUPO_CALADO = "grupo.calado"

#: `kind` de `platform_sends`. ⚠️ O prefixo `grupo_` é só LEGIBILIDADE — quem
#: decide o que conta na cota do segurado é a allowlist
#: `platform_outbound.KINDS_QUE_CONTAM_NA_COTA_DO_SEGURADO` (§9.2).
def kind_do_grupo(tipo: str) -> str:
    return "grupo_%s" % str(tipo or "outro").strip().lower()


MOTIVO_SEM_LEITURA = "não consegui conferir se há alguém na conversa"


# ===========================================================================
# BLOCO B — os números da casa
# ===========================================================================
_TTL_DO_CACHE_S = 60
_CHAVE_DO_CACHE = "numeros_da_casa:{}"


def _variantes(telefone: Any) -> Set[str]:
    """🔴 A MESMA autoridade do `JANELA_SILENCIO_EXCECOES` (commit `05f46a9`).

    ⛔ Não escrever outro casador: com/sem `55`, com/sem nono dígito e com
    máscara já são resolvidos lá, e duas cópias é onde o conserto de um lado
    deixa o outro quebrado.
    """
    from app.services.o_fim_do_atendimento import _variantes_do_telefone

    return _variantes_do_telefone(telefone)


async def numeros_da_casa(db, company_id: str) -> Set[str]:
    """Os telefones da própria corretora, já em VARIANTES normalizadas.

    Duas fontes, uma resposta (§6.1):

    ```
    1. users_v2.phone dos membros ATIVOS daquela corretora   (já existe)
    2. company_internal_numbers                              (tabela desta SPEC)
    ```

    🔴 ⛔ **Nenhuma coluna nova em `company_members`.** 📊 16/09/2026:
    `users_v2.phone` está preenchido em **872 de 872** usuários. Acrescentar
    telefone em `company_members` criaria uma segunda verdade sobre o mesmo
    fato — exatamente o defeito de `alert_target` (três escritores, três formas).

    ⚠️ Preenchido não é utilizável: nada prova o FORMATO desses 872. É por isso
    que o casamento é por variantes e o guarda G-B1 leva um telefone de membro
    mal formatado.

    ⛔ Nunca levanta: uma lista ilegível devolve o conjunto vazio, e o efeito é
    o comportamento de hoje (o número é tratado como cliente). Falhar para o
    lado de CALAR aqui apagaria atendimento de segurado de verdade.
    """
    empresa = str(company_id or "").strip()
    if not empresa:
        return set()

    cache = await _ler_cache(empresa)
    if cache is not None:
        return cache

    numeros: Set[str] = set()
    from app.services.o_fim_do_atendimento import _cliente, _executar

    try:
        # ⚠️ `membros_da_corretora` (o_fim_do_atendimento.py:2324) devolve
        #    `{company_id, status, name}` e descarta quem não tem nome — ela
        #    existe para comparar NOMES com o do agente. O que falta aqui é
        #    outra COLUNA da mesma fonte, não outra regra: os dois `select`
        #    abaixo são os mesmos dois de lá, pedindo `phone` em vez de nome.
        cli = _cliente(db)
        vinculos = await _executar(cli.table("company_members")
                                   .select("user_id")
                                   .eq("company_id", empresa)   # 🔴 CLAUDE.md §7
                                   .eq("status", "active").limit(500))
        ids = [str(v.get("user_id")) for v in (vinculos.data or []) if v.get("user_id")]
        if ids:
            pessoas = await _executar(cli.table("users_v2")
                                      .select("id, phone").in_("id", ids).limit(500))
            for p in (pessoas.data or []):
                numeros |= _variantes((p or {}).get("phone"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[NUMEROS DA CASA] membros não lidos (%s)", type(exc).__name__)

    try:
        achado = await _executar(_cliente(db).table("company_internal_numbers")
                                 .select("phone")
                                 .eq("company_id", empresa)   # 🔴 CLAUDE.md §7
                                 .limit(500))
        for linha in (achado.data or []):
            numeros |= _variantes((linha or {}).get("phone"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[NUMEROS DA CASA] tabela não lida (%s)", type(exc).__name__)

    await _gravar_cache(empresa, numeros)
    return numeros


def e_numero_da_casa(numeros: Set[str], telefone: Any) -> bool:
    """O telefone bate com algum número da casa? — **PURA**."""
    alvo = _variantes(telefone)
    return bool(alvo and (alvo & set(numeros or ())))


async def _ler_cache(company_id: str) -> Optional[Set[str]]:
    """⚠️ O cache existe pelo CUSTO (a lista é lida em caminho quente), nunca
    pela correção. Redis mudo devolve `None` e a fonte é consultada."""
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        bruto = await r.get(_CHAVE_DO_CACHE.format(company_id))
        if bruto is None:
            return None
        texto = bruto.decode() if isinstance(bruto, (bytes, bytearray)) else str(bruto)
        return {p for p in texto.split(",") if p}
    except Exception:  # noqa: BLE001
        return None


async def _gravar_cache(company_id: str, numeros: Set[str]) -> None:
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        await r.set(_CHAVE_DO_CACHE.format(company_id), ",".join(sorted(numeros)),
                    ex=_TTL_DO_CACHE_S)
    except Exception:  # noqa: BLE001
        pass


async def esquecer_os_numeros_da_casa(company_id: str) -> None:
    """Invalida o cache. Chamado por quem ESCREVE na lista."""
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        await r.delete(_CHAVE_DO_CACHE.format(str(company_id or "")))
    except Exception:  # noqa: BLE001
        pass


# ===========================================================================
# BLOCO A — A GUARDA ÚNICA
# ===========================================================================
async def o_grupo_pode_saber(db, *, company_id: str, conversation_id: str = "",
                             telefone: str = "", tipo: str,
                             companhia: Any = None, agora=None,
                             conversa: Any = None,
                             sessao: Any = None) -> Tuple[bool, str]:
    """`(pode_falar, motivo_em_português)`.

    As quatro perguntas, **nesta ordem**, e cada uma DELEGANDO:

    ```
    1  o tipo é ISENTO?                      TIPOS_ISENTOS            → passa, antes de qualquer I/O
    2  a contraparte é NÚMERO DA CASA?       numeros_da_casa          → cala
    3  a conversa está ASSUMIDA (claim fresco)?  conversations.claimed_*  → cala
    4  um HUMANO da corretora falou nos últimos N dias?  a janela     → cala
    ```

    🔴 **FAIL-OPEN por desenho.** Se não der para ler (banco fora, timeout),
    devolve `(True, MOTIVO_SEM_LEITURA)` e loga.

    ⚠️ É o OPOSTO da `a_ia_deve_calar`, que é fail-**closed** — e a assimetria é
    deliberada: falar por cima da atendente na frente do SEGURADO é
    irreversível; mandar um aviso a mais ao GRUPO, não. O comentário de
    `handoff_watchdog.py:198-203` já escolheu assim e esta SPEC conserva a
    escolha. ⛔ Um juiz que peça fail-closed aqui está pedindo silêncio de
    atendimento por falha de infraestrutura.
    """
    empresa = str(company_id or "").strip()
    if not empresa:
        # 🔴 Sem corretora não há isolamento possível (CLAUDE.md §7). Aqui o
        #    fail-open pararia: não se resolve destino sem saber de quem é.
        return False, "não sei de que corretora é este aviso"

    # ---- 1. o tipo é isento? — atalho ANTES de qualquer I/O ---------------
    if str(tipo or "") in TIPOS_ISENTOS:
        return True, ""

    conversa_id = str(conversation_id or "").strip()
    fone = str(telefone or "").strip()

    # ---- 1-bis. 🔴 SPEC-EXTRA-001.4 C — a atendente está na URA AGORA? ------
    #    A causa que a 001.4 acrescenta (proposta §7.3: quem executa depois
    #    CHAMA a guarda e acrescenta a sua causa). Só o aviso da própria pausa
    #    passa: ele é sobre ela.
    if str(tipo or "") != TIPO_PAUSA_HUMANA and await _pausa_humana_na_conversa(
            empresa, sessao, conversa_id, fone):
        return False, MOTIVO_PAUSA_HUMANA

    # ---- 2. a contraparte é número da casa? -------------------------------
    if fone:
        try:
            casa = await numeros_da_casa(db, empresa)
            if e_numero_da_casa(casa, fone):
                return False, "é um número da própria corretora"
        except Exception as exc:  # noqa: BLE001
            logger.warning("[GRUPO] números da casa ilegíveis (%s)", type(exc).__name__)

    if not conversa_id:
        # Aviso que não é sobre uma conversa (cobrança de parcela, vigia da
        # corretora): as perguntas 3 e 4 não têm sujeito. Passa.
        return True, ""

    # ---- 3 e 4 precisam da conversa e das mensagens -----------------------
    try:
        linha = conversa if isinstance(conversa, dict) else None
        # 🔴 A LINHA RECEBIDA PODE SER PARCIAL — juiz fresco, 16/09/2026.
        #
        # 📊 `varrer_esperas_vencidas` (`handoff_watchdog.py:562-564`) seleciona
        # `id, company_id, session_id, user_name, user_phone,
        # human_handoff_reason` — **sem nenhuma coluna de claim** — e passa essa
        # linha adiante. Confiar nela fazia a pergunta 3 devolver `False` por
        # ausência de dado, não por ausência de dono:
        #
        #     linha do BANCO (claim de 30 min)  → (False, "Regina assumiu…")
        #     a MESMA conversa, linha de :562   → (True, "")   ← o grupo era avisado
        #
        # ⚠️ É o defeito do §0.3 em miniatura: o dado existia e quem perguntou
        # não o tinha na mão. O teste é pela CHAVE, não pelo valor — `None` é uma
        # resposta legítima ("ninguém assumiu"); a chave ausente é ignorância.
        if linha is not None and "claimed_by" not in linha:
            linha = None
        if linha is None:
            linha = await _ler_a_conversa(db, empresa, conversa_id)
        if linha is None:
            return True, MOTIVO_SEM_LEITURA

        agora_utc = agora or datetime.now(timezone.utc)

        # ---- 3. assumida por alguém, com claim FRESCO? --------------------
        assumida, quem = _assumida_com_claim_fresco(linha, agora_utc)
        if assumida:
            return False, "%s assumiu esta conversa" % quem

        # ---- 4. um humano da corretora falou nos últimos N dias? ----------
        from app.services.o_fim_do_atendimento import (
            janela_de_mensagens, janela_de_silencio_dias,
            silenciar_por_palavra_humana, telefone_e_excecao_da_janela,
            ultima_palavra_humana,
        )

        # ⚠️ Os números de TESTE ficam fora da regra — a mesma exceção que o
        #    atendimento já respeita (`JANELA_SILENCIO_EXCECOES`).
        alvo_fone = fone or str(linha.get("user_phone") or "")
        if alvo_fone and telefone_e_excecao_da_janela(alvo_fone):
            return True, ""

        mensagens, erro = await janela_de_mensagens(db, conversa_id)
        if erro:
            logger.warning("[GRUPO] janela ilegível (%s) — vou deixar avisar", erro)
            return True, MOTIVO_SEM_LEITURA

        # 🔴 A pergunta 4 NÃO TEM NÚMERO PRÓPRIO: chama a MESMA função que
        #    decide se o agente cala com o segurado, com a MESMA env e o MESMO
        #    override por corretora. ⛔ `JANELA_DO_GRUPO_DIAS` não existe.
        dias = janela_de_silencio_dias(companhia)
        calar, motivo = silenciar_por_palavra_humana(
            ultima_humana=ultima_palavra_humana(mensagens),
            agora=agora_utc, n_dias=dias)
        if calar:
            return False, motivo
        return True, ""
    except Exception as exc:  # noqa: BLE001
        logger.warning("[GRUPO] guarda não conseguiu ler (%s) — fail-open",
                       type(exc).__name__)
        return True, MOTIVO_SEM_LEITURA


async def _ler_a_conversa(db, company_id: str, conversation_id: str):
    from app.services.o_fim_do_atendimento import _cliente, _executar

    achado = await _executar(_cliente(db).table("conversations")
                             .select("id, company_id, user_phone, user_name, "
                                     "claimed_by, claimed_by_name, claimed_at")
                             .eq("company_id", company_id)      # 🔴 CLAUDE.md §7
                             .eq("id", conversation_id).limit(1))
    linhas = achado.data or []
    return linhas[0] if linhas else None


def _horas_do_realerta() -> int:
    try:
        return max(1, int(os.getenv("HANDOFF_REALERTA_HORAS", "6")))
    except (TypeError, ValueError):
        return 6


def _assumida_com_claim_fresco(conversa: Dict[str, Any], agora) -> Tuple[bool, str]:
    """A MESMA régua de idade de `handoff_watchdog.py:282-287` — **PURA**.

    🔴 `claimed_at` ilegível AVISA, não cala. Data que não dá para ler é dúvida,
    e a regra do módulo é "na dúvida, avisa" — senão uma data ausente calaria a
    conversa para sempre, que é o furo que este bloco existe para fechar.

    🔴 **`claimed_by` OU `claimed_by_name` — lente do dado, 16/09/2026.**

    📊 Medido em produção: `claimed_by` está preenchido em **1 linha de 938**, e
    em **0 das 259** conversas em `HUMAN_REQUESTED`. `claimed_by_name` está em
    **259 de 259**, e 63 delas têm `claimed_at` nas últimas 6 horas.

    A causa é "quem É o escritor HOJE" (§0.3): o escritor que acontece de
    verdade é `atlas/espelho_chat.py:761-764` — a atendente respondendo pelo
    celular — e ele grava `status` + `claimed_by_name` + `claimed_at`, **nunca**
    `claimed_by`. O botão *Assumir* do painel, que preenche `claimed_by`, rodou
    uma vez na história da base.

    ⚠️ Exigir só `claimed_by` fazia esta pergunta ser **inerte**: sempre `False`.
    Hoje o efeito era absorvido pela pergunta 4 — mas **por coincidência de
    escritor, não por desenho**. Numa corretora com `janela_silencio_humano_dias
    = 0` (valor legítimo e documentado) a pergunta 4 desliga, a 3 continuaria
    calada, e o grupo voltaria a receber tudo por cima de quem está atendendo.

    ⛔ `saudacao_do_religamento.py:104` já testava os dois. A guarda nova é que
    tinha ficado de fora.
    """
    if not (str(conversa.get("claimed_by") or "").strip()
            or str(conversa.get("claimed_by_name") or "").strip()):
        return False, ""
    quando = conversa.get("claimed_at")
    if not quando:
        return False, ""
    try:
        from app.services.o_fim_do_atendimento import _quando as _instante

        visto = _instante(quando)
        if visto is None:
            return False, ""
        idade_h = (agora - visto).total_seconds() / 3600.0
    except Exception:  # noqa: BLE001
        return False, ""
    if idade_h >= _horas_do_realerta():
        return False, ""
    nome = str(conversa.get("claimed_by_name") or "").strip() or "alguém da equipe"
    return True, nome


# ===========================================================================
# §7.5 — O MARCADOR, e a chave é (corretora, conversa, TIPO)
# ===========================================================================
_CHAVE_DO_ENVIO = "grupo_envio:{empresa}:{conversa}:{tipo}"


async def reivindicar_o_envio(company_id: str, conversation_id: str, tipo: str,
                              segundos: int) -> bool:
    """`True` = **já avisaram**, fique quieto. `False` = a vez é sua (reservada).

    🔴 Teste-e-marca atômico (`nx=True`) para que dois workers na mesma passada
    não avisem em dobro. Redis fora do ar devolve `False`: **avisar demais é
    melhor que calar** — a mesma escolha de `human_handoff.reivindicar_o_aviso`.

    ⛔ **Nunca com conversa vazia.** Isso gravaria uma chave global que calaria
    o grupo de TODAS as corretoras (CLAUDE.md §7); sem id, não há marcador.

    ⚠️ `company_id` vazio é aceito e vira `-`: o `conversation_id` é um uuid
    único na base inteira, então a chave continua isolada por corretora na
    prática. ⛔ O que NÃO se aceita é conversa vazia — essa sim seria global.
    """
    empresa = str(company_id or "").strip() or "-"
    conversa = str(conversation_id or "").strip()
    if not conversa or int(segundos or 0) <= 0:
        return False
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        gravou = await r.set(
            _CHAVE_DO_ENVIO.format(empresa=empresa, conversa=conversa, tipo=tipo),
            "1", ex=max(1, int(segundos)), nx=True)
        return not gravou
    except Exception as exc:  # noqa: BLE001
        logger.warning("[GRUPO] marcador indisponível (%s) — vai avisar",
                       type(exc).__name__)
        return False


async def devolver_a_vez_do_grupo(company_id: str, conversation_id: str,
                                  tipo: str) -> None:
    """Libera o marcador quando o aviso RESERVADO não saiu."""
    empresa = str(company_id or "").strip() or "-"
    conversa = str(conversation_id or "").strip()
    if not conversa:
        return
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        await r.delete(_CHAVE_DO_ENVIO.format(empresa=empresa, conversa=conversa,
                                              tipo=tipo))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[GRUPO] não consegui devolver o marcador (%s)",
                       type(exc).__name__)


# ===========================================================================
# BLOCO E — o diário: quem CALOU também deixa rastro
# ===========================================================================
async def anotar_no_diario(db, company_id: str, tipo_evento: str, mensagem: str,
                           carga: Dict[str, Any], *, severidade: str = "info") -> bool:
    """Uma linha contável em `work_events`. ⛔ **Nunca levanta.**

    🔴 **E a guarda grava quando CALA.** Um silêncio sem rastro é
    indistinguível de um job que não rodou — e é exatamente como esta SPEC
    viraria o próximo defeito invisível.

    ⚠️ `work_run_id` fica NULO, e isso só é possível desde a migration
    `20260916_02`: 📊 até 16/09/2026 a coluna era NOT NULL e TODO insert deste
    formato levantava `NotNullViolation` dentro de um `except` que engolia —
    é por isso que `handoff.realertado` tem **0 linhas** em toda a base.

    ⛔ A carga nunca leva nome, telefone ou texto de mensagem: quem guarda
    conteúdo é o Espelho, e `payload_redacted` tem esse nome por um motivo.
    """
    try:
        from app.services.o_fim_do_atendimento import _cliente, _executar

        await _executar(_cliente(db).table("work_events").insert({
            "company_id": str(company_id),          # 🔴 CLAUDE.md §7
            "event_type": str(tipo_evento),
            "actor_type": "system",
            "severity": severidade,
            "message_human": str(mensagem or "")[:400],
            "payload_redacted": carga or {},
        }))
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("[GRUPO] diário não registrado (%s)", type(exc).__name__)
        return False


def _carga(tipo: str, conversation_id: str, motivo: str, motivo_classe: str,
           extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """⛔ Sem PII. 🔴 `motivo_classe` NUNCA é omitido: `desconhecido` explícito.

    ⚠️ Um motivo desconhecido **não** cai em `regra` — se caísse, hoje (com
    zero escritores) todo pedido de ajuda sairia do denominador da eficiência
    e as 19h dariam ~100% sem medir nada (§8.1).
    """
    carga = {
        "tipo": str(tipo or ""),
        "conversa": str(conversation_id or "")[:8],
        "motivo": str(motivo or "")[:120],
        "motivo_classe": str(motivo_classe or "").strip() or "desconhecido",
    }
    if extra:
        carga.update(extra)
    return carga


# ===========================================================================
# A PORTA ÚNICA — guarda → marcador → destino → UM balão → contado
# ===========================================================================
async def enviar_ao_grupo(db, *, company_id: str, tipo: str, texto: str,
                          conversation_id: str = "", telefone: str = "",
                          companhia: Any = None, conversa: Any = None,
                          resumo: str = "", motivo: str = "",
                          motivo_classe: str = "", integration: Any = None,
                          destino: str = "", dedup: bool = True,
                          janela_s: Optional[int] = None,
                          agora=None, sessao: Any = None) -> Dict[str, Any]:
    """O ÚNICO caminho de uma mensagem para o grupo da corretora.

    ```
    guarda (§5) → marcador por (corretora, conversa, tipo) (§7.5)
                → destino (o resolvedor ÚNICO)
                → UM balão (bloco_unico)
                → platform_sends + work_events
    ```

    Devolve `{"enviado", "calado", "motivo", "destino_ok"}` — sem arredondar.

    🔴 A guarda entra no ponto mais BAIXO possível. Colocá-la no chamador é o
    que produz o 12º caminho que ninguém lembrou, e é o defeito que o guarda
    G-A2 existe para pegar.
    """
    empresa = str(company_id or "").strip()
    conversa_id = str(conversation_id or "").strip()
    resposta = {"enviado": False, "calado": False, "motivo": "", "destino_ok": False}

    # ---- ① a guarda -------------------------------------------------------
    pode, porque = await o_grupo_pode_saber(
        db, company_id=empresa, conversation_id=conversa_id, telefone=telefone,
        tipo=tipo, companhia=companhia, agora=agora, conversa=conversa,
        sessao=sessao)
    if not pode:
        resposta.update({"calado": True, "motivo": porque})
        await anotar_no_diario(
            db, empresa, EVENTO_GRUPO_CALADO,
            "O grupo não foi avisado porque a conversa já tem gente.",
            _carga(tipo, conversa_id, motivo, motivo_classe,
                   {"calou_porque": porque[:160]}))
        logger.info("[GRUPO] calado | empresa=%s | tipo=%s | porque=%s",
                    empresa, tipo, porque[:80])
        return resposta

    # ---- ② o marcador — a chave é a CONVERSA, não a sessão ----------------
    espera = JANELA_DE_DEDUP_S.get(str(tipo or ""), 0) if janela_s is None else int(janela_s)
    reservou = False
    if dedup and conversa_id and espera > 0:
        if await reivindicar_o_envio(empresa, conversa_id, tipo, espera):
            resposta.update({"calado": True,
                             "motivo": "já avisei o grupo sobre esta conversa há pouco"})
            await anotar_no_diario(
                db, empresa, EVENTO_GRUPO_CALADO,
                "O grupo não foi avisado de novo: já sabia desta conversa.",
                _carga(tipo, conversa_id, motivo, motivo_classe,
                       {"calou_porque": "repetido", "janela_s": espera}))
            return resposta
        reservou = True

    try:
        # ---- ③ o destino — o resolvedor ÚNICO -----------------------------
        alvo = str(destino or "").strip()
        if not alvo:
            from app.services.dispatch_router import resolver_destino_de_suporte

            achado = await resolver_destino_de_suporte(empresa)
            if achado.get("recusa"):
                resposta["motivo"] = str(achado["recusa"])
                raise _NaoSaiu(resposta["motivo"])
            alvo = str(achado.get("destino") or "")
        if not alvo:
            resposta["motivo"] = "a corretora não tem destino de suporte humano configurado"
            raise _NaoSaiu(resposta["motivo"])
        resposta["destino_ok"] = True

        # ---- ④ o canal ----------------------------------------------------
        integ = integration
        if integ is None:
            from app.services.integration_service import get_integration_service

            bruto = getattr(db, "client", db)
            integ = await asyncio.to_thread(
                get_integration_service(bruto).get_whatsapp_integration, empresa)
        if not integ:
            resposta["motivo"] = "a corretora não tem canal de WhatsApp conectado para avisar"
            raise _NaoSaiu(resposta["motivo"])

        # ---- ⑤ UM balão ---------------------------------------------------
        # 🔴 `bloco_unico=True` — o que vai ao grupo é DOCUMENTO, não conversa.
        #    📊 Sem isto um dossiê de 429 caracteres chega em 4 balões
        #    (136 · 16 · 69 · 201) e a atendente lê o último, que é o menos
        #    importante. E em THREAD: `send_message` faz HTTP síncrono, e
        #    direto no event loop isso trava o FastAPI a cada transferência.
        from app.services.whatsapp_service import get_whatsapp_service

        await asyncio.to_thread(
            lambda: get_whatsapp_service().send_message(alvo, texto, integ,
                                                        bloco_unico=True))
        resposta["enviado"] = True
    except _NaoSaiu:
        if reservou:
            await devolver_a_vez_do_grupo(empresa, conversa_id, tipo)
        logger.error("[GRUPO] ❌ aviso NÃO entregue | empresa=%s | tipo=%s | motivo=%s",
                     empresa, tipo, resposta["motivo"])
        return resposta
    except Exception as exc:  # noqa: BLE001
        if reservou:
            await devolver_a_vez_do_grupo(empresa, conversa_id, tipo)
        resposta["motivo"] = "falha no envio (%s)" % type(exc).__name__
        logger.error("[GRUPO] ❌ envio falhou (%s) | empresa=%s", type(exc).__name__, empresa)
        return resposta

    # ---- ⑥ contado, nos DOIS registros, com papéis diferentes -------------
    #
    # platform_sends   quantas MENSAGENS saíram        (contabilidade do canal)
    # work_events      o que cada uma SIGNIFICAVA      (a conta das 19h)
    #
    # ⚠️ Uma linha por MENSAGEM, não por intenção — e com `bloco_unico` a
    # mensagem é 1 balão por construção, então o número é 1 de verdade.
    await _contar_o_envio(empresa, alvo, tipo, resumo or motivo)
    await anotar_no_diario(
        db, empresa, EVENTO_GRUPO_ENVIADO, "O grupo da corretora foi avisado.",
        _carga(tipo, conversa_id, motivo, motivo_classe))
    return resposta


class _NaoSaiu(Exception):
    """Interno: o aviso não saiu por motivo CONHECIDO (sem destino, sem canal)."""


async def _contar_o_envio(company_id: str, destino: str, tipo: str, resumo: str) -> None:
    """Uma linha em `platform_sends`. ⛔ `phone` é o destino do GRUPO — nunca o
    telefone do segurado."""
    try:
        from app.services.platform_outbound import record_platform_send

        await record_platform_send(company_id, destino, kind_do_grupo(tipo),
                                   str(resumo or "")[:300])
    except Exception as exc:  # noqa: BLE001
        logger.warning("[GRUPO] envio não contado (%s)", type(exc).__name__)
