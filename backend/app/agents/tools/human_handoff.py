"""Devolver para humano — e o humano precisa FICAR SABENDO.

O que esta ferramenta fazia, medido em 02/08/2026
-------------------------------------------------
Um `UPDATE conversations SET status='HUMAN_REQUESTED'`. Só isso.

    sem envio         nenhum import de WhatsApp, e-mail ou push
    sem contexto      o humano teria de reconstruir a conversa sozinho
    sem company_id    `.eq("session_id", …)` — viola CLAUDE.md §7
    e mentia          "Um atendente foi solicitado." era devolvido TAMBÉM
                      quando o UPDATE não achava a conversa E quando
                      estourava exceção

A última é a pior. O segurado ouvia que um humano viria, o humano nunca soube,
e ninguém no sistema ficou sabendo que a promessa não foi cumprida. **Falha
declarando sucesso é pior que falha.**

E havia um segundo defeito, na direção oposta: o prompt do atendimento MANDA
chamar humano em sinistro e em risco grave — mas a ferramenta só era anexada
se `tools_config.human_handoff.enabled` fosse verdadeiro, e 📊 `tools_config`
estava vazio nos agentes de atendimento. **O prompt prometia o que a ferramenta
não tinha como cumprir.**

O que ela faz agora
-------------------
1. Exige `company_id` — sem ele não escreve nada e diz por quê.
2. Filtra a conversa por `company_id` **e** `session_id`.
3. Resolve o destino pelo resolvedor canônico, que **recusa destino
   compartilhado entre corretoras** (o dossiê leva CPF do segurado).
4. Monta um dossiê com as últimas mensagens e envia.
5. **Devolve ao segurado o que de fato aconteceu.** Se ninguém foi avisado, a
   resposta não promete atendente. Nunca inventa uma transferência que não houve.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any, ClassVar, Dict, Optional, Type

from langchain_core.tools import BaseTool

from app.agents.honestidade_do_handoff import (
    FALHA_DO_HANDOFF,
    JA_ESTAVA_COM_A_EQUIPE,
    SUCESSO_DO_HANDOFF,
)
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ===========================================================================
# O MARCADOR DE "JÁ AVISAMOS" — UMA definição, dois donos
# ===========================================================================
#
# 🔴 Ele mora aqui, e não no Vigia, porque agora são DOIS os que avisam o
# grupo sobre a mesma conversa:
#
#   esta ferramenta          quando a atendente pede um humano
#   handoff_watchdog         quando ninguém respondeu depois de um tempo
#
# Duas cópias do mesmo marcador seriam duas chaves diferentes no Redis, e cada
# um silenciaria só a si mesmo — o grupo receberia o dobro. É o mesmo defeito
# que o próprio código já registra sobre normalizador copiado
# (`insurer_dispatch_service._norm_text`): "cópia é onde o conserto de um lado
# deixa o outro quebrado".
#
# O Vigia importa daqui. A direção já existe: ele importa `HumanHandoffTool`
# deste módulo desde que foi escrito.
# 🔴 SPEC-EXTRA-001.3 §7.5 — A CHAVE MUDOU; O MECANISMO, NÃO.
#
# 📊 10/09/2026: saíram 3 dossiês sobre a MESMA conversa em 21 minutos (17:14,
# 17:21, 17:35) porque a sessão de acionamento reabriu três vezes e o marcador
# de "já entreguei" vivia na SESSÃO. A unidade certa é a CONVERSA, e o tipo de
# aviso entra na chave para que um sinistro não cale um pedido de ajuda.
#
# ⛔ Nada de tabela de dedup nova e nada de segundo marcador: as funções abaixo
# DELEGAM para `o_grupo_so_o_que_importa`, que é o módulo leve que o agendador
# também usa (importar daqui arrastaria `langgraph` para dentro do scheduler).
_CHAVE_DO_MARCADOR = "handoff_realerta:{}"   # 🔴 histórico — ver `_chave` do módulo novo
HORAS_ENTRE_AVISOS_PADRAO = 6


def _env_int(nome: str, padrao: int, minimo: int = 1) -> int:
    try:
        return max(minimo, int(os.getenv(nome, str(padrao))))
    except (TypeError, ValueError):
        return padrao


# ===========================================================================
# O RASTRO DURÁVEL DO HANDOFF — 09/09/2026
# ===========================================================================
#
# 📊 Medido em 09/09/2026 (primeiro dia de piloto real da AutoFleet): esta
# ferramenta rodou **5 vezes**, `_avisar_suporte` devolveu
# `{"avisado": False, "motivo": "a corretora não tem destino de suporte humano
# configurado"}` nas 5, e o único vestígio foi um `logger.error`. O log do
# contêiner some no próximo deploy. **Nada ficou no banco.**
#
# 🔴 E O `claims.handoff_pedido` NÃO ERA O RASTRO — nunca foi, por construção.
#
# `claims_shadow.registrar_evento` grava em `work_events`, e `work_events`
# tem `work_run_id` **NOT NULL** com FK para `work_runs`. A função resolve
# esse run por `sombra_da_conversa(...)` e, quando não existe,
# `if not run_id: return False` — sai ANTES do INSERT, sem levantar nada. O
# `except` do `registrar_gesto` e o `try` do chamador não engoliram exceção
# nenhuma: **não houve exceção**. 📊 4 de 729 conversas têm sombra de sinistro
# (a sombra só abre quando o detector reconhece sinistro), então o caminho
# normal de um handoff é "sem sombra → `False` silencioso".
#
# ⛔ Por isso o rastro do handoff NÃO pode morar em `work_events`: ele
# precisaria de um `work_run` que a conversa não tem, e abrir sombra
# retroativa está fora desta unidade (e fora deste arquivo).
#
# ✅ Ele mora em `agent_activities`, pelo escritor que já existe
# (`activity_log.log_activity`, o mesmo feed de Atividades que o acionamento
# usa): tem `company_id`, não exige run nenhum e é o lugar onde a corretora
# já olha o que o robô fez. Nenhum escritor novo (CLAUDE.md §5).
#
# ⚠️ Os nomes de máquina abaixo existem para o log e para os guardas. O que
# vai para o feed é FRASE, em português — a atendente lê o feed.
EVENTO_HANDOFF_FALHOU = "handoff.falhou"
EVENTO_HANDOFF_ENTREGUE = "handoff.entregue"
_CATEGORIA_DA_ATIVIDADE = "atendimentos"

TITULO_HANDOFF_FALHOU = "Pedido de ajuda humana sem ninguém para receber"
TITULO_HANDOFF_ENTREGUE = "Atendimento entregue a uma pessoa da equipe"
FRASE_DA_FALHA = ("O agente pediu ajuda humana e ninguém foi avisado: %s.")
FRASE_DA_ENTREGA = ("O agente entregou o atendimento à equipe e o dossiê do caso "
                    "foi enviado ao destino de suporte da corretora.")

#: 🔴 O motivo NUNCA vai vazio — e nunca vai em código de máquina.
#: 📊 09/09/2026: `human_handoff_reason` ficou NULL em **4 das 5** conversas do
#: piloto, mesmo depois do conserto da 097.1. A causa: aquele conserto só
#: preenche o silêncio **quando o caso já foi acionado**
#: (`_e_pos_acionamento`), e as 5 conversas do dia eram sinistros NOVOS, sem
#: acionamento nenhum. Fora daquele ramo, `if motivo_gravado:` simplesmente
#: não escrevia — e a Fila mostrava "precisa de você" sem uma palavra sobre
#: por quê. Agora existe um terceiro degrau, que vale para TODO handoff.
MOTIVO_SEM_DECLARACAO = "o agente pediu ajuda humana sem dizer o motivo"

_LIMITE_DO_MOTIVO = 300


def _motivo_em_portugues(motivo: Optional[str]) -> str:
    """O `reason` da ferramenta virado frase legível — **PURA**.

    ⚠️ Ela NÃO reescreve o que o modelo disse: o texto do modelo já vem em
    português e reescrevê-lo seria inventar motivo. O que ela faz é o que a
    atendente precisa para ler a linha da Fila:

        espaços e quebras colapsados      "pediu\\n  humano" → "pediu humano"
        slug vira frase                   "cliente_pediu_humano" → "cliente pediu humano"
        teto de 300 caracteres            a Fila mostra uma linha, não um parágrafo

    ⛔ Não capitaliza: `human_handoff_reason` é comparado por igualdade em
    guardas existentes, e mudar a primeira letra quebraria a promessa de que
    *"o motivo explícito é preservado, não sobrescrito"*.
    """
    texto = " ".join(str(motivo or "").split())
    if texto and " " not in texto and "_" in texto:
        # 🔴 `cliente_pediu_humano` é nome de variável, não frase. A regra da
        #    097 ([13], R11) é língua humana em tudo que a corretora lê.
        texto = texto.replace("_", " ")
    return texto[:_LIMITE_DO_MOTIVO]


# ===========================================================================
# 🔴 O ESCRITOR DE `motivo_classe` — SPEC-EXTRA-001.3 BLOCO D
# ===========================================================================
#
# 📊 Medido em 16/09/2026, antes de escrever: `grep -rn "motivo_classe"
# backend/app` → **0**; `human_handoff_reason` preenchido em **2 de 254**
# conversas `HUMAN_REQUESTED`, e as duas em prosa livre. O campo não existia e
# não tinha escritor designado. A conta das 19h depende dele.
#
# ⚠️ **E um motivo desconhecido NÃO cai em `regra`.** Se caísse, hoje — com
# zero escritores — TODO pedido de ajuda sairia do denominador e a eficiência
# das 19h daria ~100% sem medir nada. `desconhecido` fica fora do numerador E
# do denominador, com LINHA PRÓPRIA no resumo (SPEC §8.1).
#
# 🔴 A busca é por PALAVRA, sobre o texto sem acento e em minúsculas — o
# `reason` chega em prosa do modelo, não em chave. ⛔ Nada de `in` sobre a
# string crua: "vitima" dentro de "revitimizacao" não é vítima.

#: `incapacidade` — o agente NÃO CONSEGUIU. Entra no denominador da eficiência.
_MOTIVOS_DE_INCAPACIDADE = {
    "ura_travou": ("ura", "travou", "travei", "menu", "nao consegui", "não consegui",
                   "formulario_incompleto", "formulario", "opcao", "tentei"),
    "dado_faltante": ("falta", "faltou", "faltando", "nao tenho", "não tenho",
                      "sem o dado", "nao sei", "não sei", "dado"),
    "sentinela_esgotou": ("sentinela", "esgotou", "recuperacao", "recuperação",
                          "stall", "tempo limite", "timeout"),
}

#: `regra` — o agente PODIA, mas o produto manda passar. 🔴 Fica FORA do
#: denominador: contar contra puniria o agente por obedecer (D-PILOTO-13).
_MOTIVOS_DE_REGRA = {
    "vitima": ("vitima", "vitimas", "vítima", "vítimas", "ferido", "feridos",
               "machucado", "ambulancia", "ambulância"),
    "cliente_pediu_humano": ("pediu humano", "pediu atendente", "pediu pessoa",
                             "quer falar com", "falar com alguem", "falar com alguém",
                             "cliente_pediu_humano", "pediu para falar"),
    "valor_acima_do_limite": ("valor", "limite", "alcada", "alçada", "aprovacao",
                              "aprovação"),
    "fora_do_escopo": ("fora do escopo", "nao atendo", "não atendo", "nao e comigo",
                       "não é comigo", "assunto novo"),
    "segurado_irritado": ("irritado", "nervoso", "reclamacao", "reclamação",
                          "insatisfeito", "xingou", "bravo"),
}

CLASSE_INCAPACIDADE = "incapacidade"
CLASSE_REGRA = "regra"
CLASSE_DESCONHECIDA = "desconhecido"


def _sem_acento_minusculo(texto: str) -> str:
    import unicodedata

    plano = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(c for c in plano if not unicodedata.combining(c)).lower()


def classificar_o_motivo(motivo: Optional[str]) -> tuple:
    """`(classe, chave)` — **PURA**. `('desconhecido', 'desconhecido')` no escuro.

    🔴 A ordem importa: `regra` é conferida ANTES de `incapacidade`. Um pedido
    com vítima que TAMBÉM menciona a URA é, antes de tudo, um caso de regra —
    e classificá-lo como incapacidade colocaria no denominador da eficiência um
    caso em que o agente fez exatamente o que devia.

    🔴 **POR PALAVRA INTEIRA (`\\b`), e não por substring** — juiz fresco,
    16/09/2026. O docstring já prometia "a busca é por PALAVRA" e o código fazia
    `alvo in texto`. 📊 O que isso classificava errado:

    ```
    'a seguradora não respondeu'                  → incapacidade/ura_travou   ("ura" ⊂ segURAdora)
    'falar da apólice com a seguradora'           → incapacidade/ura_travou
    'sentinela esgotou o tempo limite'            → regra/valor_acima_do_limite
    'cuidado com o valor'                         → regra
    ```

    ⚠️ Não é cosmético: `motivo_classe` decide o DENOMINADOR da eficiência das
    19h, e um `regra` a mais tira um caso da conta que a corretora lê.

    ⚠️ E as EXPRESSÕES de duas palavras são conferidas antes das soltas: *"tempo
    limite"* é incapacidade; *"limite"* sozinho é alçada.
    """
    texto = _sem_acento_minusculo(_motivo_em_portugues(motivo))
    if not texto.strip():
        return CLASSE_DESCONHECIDA, CLASSE_DESCONHECIDA

    #: Duas passadas. Na 1ª só as EXPRESSÕES (duas palavras ou mais), com
    #: INCAPACIDADE na frente — "tempo limite" tem de ganhar de "limite". Na 2ª
    #: as palavras soltas, com REGRA na frente, como a SPEC manda.
    passadas = (
        (True, ((_MOTIVOS_DE_INCAPACIDADE, CLASSE_INCAPACIDADE),
                (_MOTIVOS_DE_REGRA, CLASSE_REGRA))),
        (False, ((_MOTIVOS_DE_REGRA, CLASSE_REGRA),
                 (_MOTIVOS_DE_INCAPACIDADE, CLASSE_INCAPACIDADE))),
    )
    for so_compostas, tabelas in passadas:
        for tabela, classe in tabelas:
            for chave, palavras in tabela.items():
                for p in palavras:
                    alvo = _sem_acento_minusculo(p)
                    if so_compostas != (" " in alvo or "_" in alvo):
                        continue
                    if re.search(r"\b%s\b" % re.escape(alvo), texto):
                        return classe, chave
    return CLASSE_DESCONHECIDA, CLASSE_DESCONHECIDA


async def registrar_o_desfecho_do_handoff(company_id: str, evento: str,
                                          motivo: str, conversa_id: str = "") -> None:
    """UMA linha durável em `agent_activities` para o desfecho do handoff.

    ⛔ **Nunca levanta** e nunca leva PII: o `session_id` do WhatsApp carrega o
    TELEFONE do segurado (`whatsapp:5547…:<empresa>`), então o que identifica o
    caso aqui é o `conversations.id` (uuid) — e mais nada.
    """
    entregue = evento == EVENTO_HANDOFF_ENTREGUE
    titulo = TITULO_HANDOFF_ENTREGUE if entregue else TITULO_HANDOFF_FALHOU
    detalhe = FRASE_DA_ENTREGA if entregue else (FRASE_DA_FALHA % (motivo or "motivo desconhecido"))
    if conversa_id:
        detalhe = "%s Conversa %s." % (detalhe, str(conversa_id)[:8])
    try:
        from app.services.activity_log import log_activity

        await log_activity(str(company_id or ""), _CATEGORIA_DA_ATIVIDADE,
                           titulo, detalhe)
        logger.info("[HumanHandoff] %s registrado no feed | empresa=%s", evento, company_id)
    except Exception as exc:  # noqa: BLE001
        # ⚠️ O rastro é o conserto do silêncio; ele não pode virar a causa de
        #    um handoff que não acontece.
        logger.error("[HumanHandoff] rastro '%s' NÃO registrado (%s)",
                     evento, type(exc).__name__)


async def reivindicar_o_aviso(conversa_id: str, horas: int, *,
                              company_id: str = "", tipo: str = "") -> bool:
    """Alguém já avisou o grupo sobre esta conversa nas últimas `horas`?

    `True` = já avisaram, **fique quieto**. `False` = a vez é sua, e este
    retorno JÁ RESERVOU o direito — é teste-e-marca atômico (`nx=True`), para
    que dois workers na mesma passada não avisem em dobro.

    🔴 Redis fora do ar devolve `False`: **avisar demais é melhor que calar.**
    O defeito grave é o silêncio; a repetição é só incômodo.

    🔴 SPEC-EXTRA-001.3 §7.5 — a chave é `(corretora, conversa, tipo)`. UMA
    implementação, em `o_grupo_so_o_que_importa`; aqui ficou só a assinatura
    que os chamadores antigos já usam.
    """
    from app.services.o_grupo_so_o_que_importa import (
        TIPO_PEDIDO_DE_AJUDA, reivindicar_o_envio,
    )

    return await reivindicar_o_envio(company_id, conversa_id,
                                     tipo or TIPO_PEDIDO_DE_AJUDA,
                                     max(1, int(horas or 1)) * 3600)


#: Quantas vezes o Vigia lembra a equipe da MESMA conversa antes de parar.
#: 📊 Com a cadência de 6h, quatro lembretes cobrem 24 horas. Depois disso o
#: problema não é mais falta de aviso — é falta de gente, e mais mensagem não
#: resolve, só ensina a ignorar o grupo.
MAX_LEMBRETES_POR_CONVERSA = 4


async def contar_lembrete(conversa_id: str) -> int:
    """Soma 1 ao contador de lembretes desta conversa e devolve o total.

    🔴 Sem teto, uma conversa esquecida vira um alarme a cada 6 horas, para
    sempre. E alarme que chega para sempre deixa de ser alarme: 📊 foi
    exatamente assim que uma conversa ficou 730 horas sem ninguém olhar — não
    por falta de aviso, mas por excesso.

    Erro de Redis devolve 0: **na dúvida, avisa.** O contador é um freio
    contra repetição, e freio quebrado não pode virar mordaça.
    """
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        chave = f"handoff_lembretes:{conversa_id}"
        n = await r.incr(chave)
        # 7 dias: mais que isso e a conversa ja nao e a mesma historia.
        await r.expire(chave, 7 * 24 * 3600)
        return int(n or 0)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Handoff] contador de lembretes indisponível (%s) — "
                       "não vou usar o teto", type(exc).__name__)
        return 0


async def devolver_a_vez(conversa_id: str, *, company_id: str = "",
                         tipo: str = "") -> None:
    """Libera o marcador. Chamado quando o aviso RESERVADO não saiu.

    🔴 Sem isto, uma falha de envio silenciaria o grupo pelas horas inteiras
    do marcador: quem reservou não avisou, e ninguém mais pode. Reserva que
    não virou aviso tem de ser devolvida — é o mesmo princípio de "flag que
    mente é pior que flag ausente", aplicado a uma reserva.
    """
    from app.services.o_grupo_so_o_que_importa import (
        TIPO_PEDIDO_DE_AJUDA, devolver_a_vez_do_grupo,
    )

    await devolver_a_vez_do_grupo(company_id, conversa_id,
                                  tipo or TIPO_PEDIDO_DE_AJUDA)

# Quantas mensagens vão no dossiê. Suficiente para o humano entrar sabendo,
# curto o bastante para caber num WhatsApp sem virar parede de texto.
_MSGS_NO_DOSSIE = 12

# ===========================================================================
# AS PEÇAS DO DOSSIÊ — puras, testáveis sem banco e sem rede.
#
# Estão fora da classe de propósito: o que decide COMO a atendente lê a
# situação não deve precisar de um cliente de Supabase para ser provado.
# ===========================================================================

# Linguagem humana. 🔴 O dossiê antigo escrevia `assistencia.residencial.
# encanador` para uma pessoa ler no WhatsApp — nome de chave interna vazando
# para a tela de quem trabalha.
_TITULOS = {
    "guincho": ("🚗", "GUINCHO"), "pneu": ("🛞", "PNEU"),
    "bateria": ("🔋", "BATERIA"), "chaveiro": ("🔑", "CHAVEIRO"),
    "vidros": ("🪟", "VIDROS"), "eletricista": ("💡", "ELETRICISTA"),
    "encanador": ("🔧", "ENCANADOR"), "desentupimento": ("🚿", "DESENTUPIMENTO"),
    "eletrodomestico": ("🧊", "ELETRODOMÉSTICO"),
    "sinistro": ("🚨", "SINISTRO"), "consulta": ("💬", "DÚVIDA"),
}


# ===========================================================================
# 🔴 SPEC-097.1 R5/U2 — O CASO JÁ ACIONADO É OUTRO CASO.
#
# 📊 Medido em 05/09/2026: `_TITULOS` não tem uma entrada de pós-acionamento,
# então um segurado que pergunta pela previsão do vidro chegava à atendente
# como `🪟 ASSISTÊNCIA · VIDROS` — o mesmo cabeçalho de quem acabou de bater o
# carro — com a recomendação *"conclua o acionamento"* de um acionamento que
# já tinha sido feito seis dias antes.
#
# ⚠️ As três coisas que o dossiê de hoje não diz e a atendente precisa:
#   1. que é PÓS-acionamento (senão ela reabre um caso que já anda);
#   2. **de quem** se está esperando — cliente, oficina e seguradora são
#      ações OPOSTAS;
#   3. o que fazer AGORA, e nunca "concluir" o que já foi concluído.
# ===========================================================================

#: As fases do corredor em que o acionamento JÁ FOI ENTREGUE.
#: ⚠️ `encaminhado` entra: o entregável está em mãos, e a pergunta que vem
#: depois dele é pós-acionamento igual.
# ⛔ `encaminhado` NÃO está aqui (red team 097.1 [8]): é a seguradora dizendo "aqui não
#    se abre chamado, vá pelo link" — o checkpoint ENCERRA o atendimento (MOTIVO_DO_ESTADO)
#    e a R4 o exclui da espera. Dar a esse caso o título de pós (o 🔁) seria dossiê
#    de um caso que não foi acionado. ⚠️ Esta prosa NÃO repete o literal do título de
#    propósito: a mutação U2 troca a 1ª ocorrência dele no arquivo (juiz 097.1, P0).
FASES_JA_ACIONADAS = ("captured", "monitoring")


def _e_pos_acionamento(conversa: Dict[str, Any],
                       espera: Optional[Dict[str, Any]] = None) -> bool:
    """O acionamento deste atendimento já saiu? — **PURA** (o ESTADO, nunca
    o texto: `dispatch_state` e a espera escrita, não uma palavra na conversa).
    """
    ficha = conversa.get("ficha_atendimento") or {}
    if isinstance(ficha, dict):
        if str(ficha.get("dispatch_state") or "") in FASES_JA_ACIONADAS:
            return True
        if str(ficha.get("protocolo") or "").strip():
            return True
    if isinstance(espera, dict) and str(espera.get("scope") or "") == "pos_acionamento":
        return True
    return False


def _quem_fala(conversa: Dict[str, Any]) -> str:
    """Segurado, parceiro ou indefinido — e **honesto quando não sabe**.

    📊 62 % do tráfego pós-acionamento do acervo NÃO é do segurado (parceiro e
    oficina somam 673 mensagens contra 254). ⛔ E reconhecer por identidade
    ficou de FORA da SPEC (não há cadastro de parceiros): então quando a
    heurística não decide, a resposta é *"não dá para saber"* — nunca um chute
    que faz a atendente tratar a oficina como se fosse a segurada.
    """
    nome = str(conversa.get("user_name") or "").strip()
    texto = str(conversa.get("last_message_preview") or "").lower()
    marcas_de_parceiro = ("aquele caso do", "meu cliente", "o segurado de",
                          "estamos com o veículo", "a loja aqui", "oficina aqui")
    if any(m in texto for m in marcas_de_parceiro):
        return "um parceiro ou a oficina (pelo jeito de escrever)"
    marcas_de_segurado = ("meu carro", "meu veículo", "minha apólice", "meu vidro",
                          "estou", "fiquei", "meu caso")
    if any(m in texto for m in marcas_de_segurado):
        return "o próprio segurado%s" % (" (%s)" % nome if nome else "")
    return "não dá para saber pelo texto — confirme antes de tratar por nome"


def _com_a_espera(conversa: Dict[str, Any],
                  espera: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """O MESMO caso, com a espera lida pendurada nele — uma CÓPIA.

    🔴 Achado [J-4] do juiz (06/09/2026): as peças puras do dossiê recebiam só
    a conversa, e `_e_pos_acionamento` sem a espera devolvia `False` para todo
    caso cujo lastro mora **só** em `work_waits` — que é a cena do §0 (a ficha
    do acervo não tem `dispatch_state`). O título vinha certo, porque
    `_montar_dossie` passa a espera; a recomendação vinha do ramo de ANTES do
    acionamento. ⚠️ *Não trava, responde errado, chega à atendente* (§9.5).

    ⛔ E é cópia, nunca mutação: a linha lida do banco não ganha chave que o
    banco não tem.
    """
    caso = dict(conversa or {})
    if isinstance(espera, dict) and espera:
        caso["espera"] = dict(espera)
    return caso


def _a_espera_do_caso(conversa: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """A espera pendurada por `_com_a_espera`. `None` quando não há."""
    espera = (conversa or {}).get("espera")
    return espera if isinstance(espera, dict) and espera else None


def _ultimas_do_cliente(conversa: Dict[str, Any]) -> list:
    """O que o cliente disse por último — a base do rótulo do turno.

    ⚠️ `mensagens` (a rajada real do turno) tem prioridade sobre
    `last_message_preview` porque a prévia guarda UMA linha e o turno costuma
    ter mais de uma: 📊 no acervo, *"muito abuso"* + *"disseram que o prestador
    foi ao local mas não foi"* chegam juntas, e só a segunda diz o que houve.
    """
    msgs = (conversa or {}).get("mensagens")
    if isinstance(msgs, (list, tuple)) and msgs:
        return [str(m or "") for m in msgs][-4:]
    return [str((conversa or {}).get("last_message_preview") or "")]


#: 🔴 A recomendação de um caso já acionado cuja situação a R9 **não conhece**.
#: ⚠️ Ela é uma CONSTANTE de propósito, e a régua sabe disso: um dossiê cujo
#: *"O que fazer"* é esta linha **não conta** como dossiê completo (R8). Sem
#: essa distinção, esvaziar `SITUACOES_PARA_HUMANO` deixaria os dossiês
#: "completos" do mesmo jeito e a R9 seria inerte — foi o [J-4] do juiz.
RECOMENDACAO_SEM_SITUACAO = (
    "Cobrar quem está devendo (a seguradora ou a loja) e responder aqui.")


def _o_que_ele_quer(conversa: Dict[str, Any]) -> str:
    """O rótulo do turno, em português — do MESMO motor da régua (§9.4)."""
    try:
        from app.atendimento.pos_acionamento import CATEGORIAS, classificar_turno

        rotulo = classificar_turno(_ultimas_do_cliente(conversa))
        return CATEGORIAS.get(rotulo) or "não deu para entender o que ele quer"
    except Exception as exc:  # noqa: BLE001
        logger.warning("[HumanHandoff] rótulo do turno indisponível (%s)",
                       type(exc).__name__)
        return "não deu para entender o que ele quer"


def _onde_parou(conversa: Dict[str, Any], espera: Optional[Dict[str, Any]]) -> str:
    """De quem se espera e desde quando — **só do que está ESCRITO** (R3)."""
    try:
        from app.atendimento.pos_acionamento import texto_da_espera

        frase = texto_da_espera(espera)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[HumanHandoff] estado da espera indisponível (%s)",
                       type(exc).__name__)
        frase = ""
    if frase:
        return "o caso está %s." % frase
    # ⛔ Sem linha de espera não se inventa de quem se espera (R3). Dizer que
    #    não se sabe é informação; dizer "esperando a seguradora" sem lastro é
    #    mandar a atendente cobrar quem talvez não deva nada.
    return ("não há espera registrada para este caso — confira no corredor de "
            "quem se está esperando antes de cobrar.")


def _texto_do_caso(conversa: Dict[str, Any], motivo: str) -> str:
    """Tudo que se sabe do caso, junto e minúsculo — para procurar palavra."""
    ficha = conversa.get("ficha_atendimento") or {}
    partes = [str(motivo or ""), str(conversa.get("human_handoff_reason") or ""),
              str(conversa.get("last_message_preview") or "")]
    if isinstance(ficha, dict):
        partes += [str(v) for v in ficha.values() if isinstance(v, (str, int, float))]
    return " ".join(partes).lower()


def _titulo_humano(conversa: Dict[str, Any], motivo: str) -> str:
    """A primeira linha. Ela tem de dizer O QUE É antes de qualquer outra coisa."""
    # 🔴 SPEC-121 · conserto único (B1): com a MARCA do motor, o título vem dela —
    #    a prosa do motivo ("…falta o número do sinistro") não vira 🚨 SINISTRO.
    marca = codigo_do_pedido(conversa)
    if marca and _e_carro_reserva(conversa):
        return "🚙 *CARRO RESERVA*"
    texto = _texto_do_caso(conversa, motivo)
    for chave, (emoji, nome) in _TITULOS.items():
        if chave == "sinistro" and _marca_nao_e_sinistro(conversa):
            continue
        if chave in texto:
            # Sinistro e dúvida não são "assistência de alguma coisa" — são a
            # coisa inteira. `SINISTRO · SINISTRO` é ruído que o primeiro
            # render mostrou na cara.
            if chave in ("sinistro", "consulta"):
                return f"{emoji} *{'SINISTRO' if chave == 'sinistro' else 'DÚVIDA DO CLIENTE'}*"
            return f"{emoji} *ASSISTÊNCIA · {nome}*"
    return "🔔 *ATENDIMENTO PRECISA DE VOCÊ*"


# 🔴 DEZ caracteres, nao 22 -- 18/08/2026.
#
# 📊 O separador de 22 nao cabia na largura do balao no celular e quebrava em
# DUAS linhas, deixando um traco longo seguido de um toco. Na foto do grupo
# TESTE SUPORTE HUMANO aparecem tres desses tocos.
#
# Separador que precisa de duas linhas nao separa nada: vira sujeira.
_TRACO = "━━━━━━━━━━"


def _fone_bonito(bruto: Any) -> str:
    """(47) 90000-0000 em vez de 5547996274743.

    Não é enfeite: a atendente compara este número com o que está na tela do
    celular dela, e comparar 13 dígitos colados é onde o olho erra.
    """
    d = "".join(ch for ch in str(bruto or "") if ch.isdigit())
    if len(d) >= 12 and d.startswith("55"):
        d = d[2:]
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    return str(bruto or "")


def _linha_da_apolice(conversa: Dict[str, Any]) -> str:
    """Seguradora, ramo e apólice numa linha — some inteira se não houver nada.

    Linha com "(não localizada)" três vezes é pior que linha nenhuma: ocupa
    espaço, não informa, e ensina a pular a seção.
    """
    ficha = conversa.get("ficha_atendimento") or {}
    if not isinstance(ficha, dict):
        return ""
    seguradora = str(ficha.get("seguradora") or ficha.get("insurer") or "").strip()
    ramo = str(ficha.get("ramo") or "").strip()
    apolice = str(ficha.get("apolice") or ficha.get("policy") or "").strip()
    placa = str(ficha.get("placa") or "").strip()

    esquerda = " ".join(p for p in (seguradora.title() if seguradora else "", ramo.title()) if p)
    direita = []
    if apolice:
        direita.append(f"apólice {apolice}")
    if placa:
        direita.append(f"placa {placa.upper()}")
    partes = [p for p in (esquerda, " · ".join(direita)) if p]
    return " · ".join(partes)


def _narrativa(conversa: Dict[str, Any], motivo: str) -> str:
    """O que houve, em português, na voz de quem conta um caso."""
    ficha = conversa.get("ficha_atendimento") or {}
    if isinstance(ficha, dict):
        for campo in ("narrativa", "descricao", "resumo", "relato"):
            valor = str(ficha.get(campo) or "").strip()
            if valor:
                return valor
    return str(motivo or "").strip() or str(conversa.get("last_message_preview") or "").strip()


def _o_que_falta(conversa: Dict[str, Any]) -> list:
    """Só o que BLOQUEIA. Lista de pendência que não bloqueia vira ruído."""
    ficha = conversa.get("ficha_atendimento") or {}
    if not isinstance(ficha, dict):
        return []
    faltando = ficha.get("faltando") or ficha.get("pendencias") or []
    if isinstance(faltando, str):
        faltando = [faltando]
    return [str(f).strip() for f in faltando if str(f).strip()][:4]


def _o_que_fazer(conversa: Dict[str, Any], motivo: str) -> str:
    """A recomendação. É a linha que a atendente lê primeiro, na prática.

    O agente conduziu a conversa inteira e sabe onde parou — entregar isso
    mastigado é a diferença entre ela agir em dez segundos e ela reler tudo.
    """
    # 🔴 SPEC-097.1 R5/R9 — O CASO JÁ ACIONADO TEM OUTRA RECOMENDAÇÃO, E ELA
    #    VEM ANTES DE TUDO.
    #
    # ⛔ Antes o `proximo_passo` da ficha vinha primeiro. Ele é escrito pelo
    # fluxo de ANTES do acionamento ("peça o endereço exato"), e entregá-lo a
    # um caso que já tem protocolo é mandar a atendente refazer trabalho
    # entregue — o mesmo defeito do "conclua o acionamento", com outra roupa.
    #
    # ⛔ E a razão vem da FONTE ÚNICA `SITUACOES_PARA_HUMANO` (R9), a mesma que
    # o prompt e a régua leem. Escrever aqui uma segunda lista de "o que fazer
    # por situação" seria uma segunda verdade sobre R9 — e a que ficasse para
    # trás seria justamente esta, que é a que a atendente lê.
    espera = _a_espera_do_caso(conversa)
    if _e_pos_acionamento(conversa, espera):
        try:
            from app.atendimento.pos_acionamento import (
                SITUACOES_PARA_HUMANO, classificar_turno, texto_da_espera,
            )

            rotulo = classificar_turno(_ultimas_do_cliente(conversa)
                                       + [str(motivo or "")])
            # ⚠️ A espera entra na frase porque *"cobrar"* sem dizer DE QUEM é
            #    instrução que a atendente não consegue executar (R3).
            frase = texto_da_espera(espera)
            quem = (" O caso está %s." % frase) if frase else ""
            razao = SITUACOES_PARA_HUMANO.get(rotulo)
            if razao:
                return ("%s. Responda ao cliente aqui mesmo depois.%s"
                        % (razao.capitalize(), quem))
            return RECOMENDACAO_SEM_SITUACAO + quem
        except Exception as exc:  # noqa: BLE001
            logger.warning("[HumanHandoff] recomendação de caso já acionado "
                           "indisponível (%s)", type(exc).__name__)
            return RECOMENDACAO_SEM_SITUACAO

    ficha = conversa.get("ficha_atendimento") or {}
    if isinstance(ficha, dict):
        sugestao = str(ficha.get("proximo_passo") or ficha.get("sugestao") or "").strip()
        if sugestao:
            return sugestao

    # 🔴 SPEC-121 · conserto único (B1): o pedido com MARCA do motor não recebe a
    #    ordem de "abrir o aviso na seguradora" só porque a prosa diz "sinistro".
    marca = codigo_do_pedido(conversa)
    if marca and _e_carro_reserva(conversa):
        return ("Faça o pedido do carro reserva na seguradora com os dados acima e dê "
                "o retorno ao cliente. O motivo de ter vindo para você está em "
                "*O QUE ACONTECEU*.")
    texto = _texto_do_caso(conversa, motivo)
    if "sinistro" in texto and not _marca_nao_e_sinistro(conversa):
        return ("Sinistro sempre é com pessoa. Confirme os dados com o cliente e "
                "abra o aviso na seguradora.")
    if _o_que_falta(conversa):
        return "Peça ao cliente o que está faltando acima e conclua o acionamento."
    return ("Confira o que o agente coletou e siga com o atendimento. "
            "Se estiver tudo certo, é só concluir.")


def _hora_de_brasilia(bruto: Any) -> str:
    """HH:MM no fuso da corretora. `--:--` quando nao da para saber."""
    from datetime import datetime, timedelta, timezone

    texto = str(bruto or "").strip()
    if not texto:
        return "--:--"
    try:
        limpo = texto.replace("Z", "+00:00")
        quando = datetime.fromisoformat(limpo)
        if quando.tzinfo is None:
            quando = quando.replace(tzinfo=timezone.utc)
        return quando.astimezone(timezone(timedelta(hours=-3))).strftime("%H:%M")
    except Exception:  # noqa: BLE001
        return texto[11:16] if len(texto) >= 16 else "--:--"


def _linha_da_conversa(m: Dict[str, Any], agent_name: str = "") -> str:
    """Uma linha da conversa, com hora e AUTOR DE VERDADE.

    🔴 SPEC-EXTRA-001.2 §10.6 — **O AGENTE ASSINA `🤖 {nome}`; A PESSOA ASSINA
    PELO NOME, SEM EMOJI.** ⛔ Nunca o contrário.

    ⚠️ O dossiê dizia `🤖 IA` e `👤 {nome}`. Os dois emojis juntos apagavam
    exatamente a distinção que o dossiê existe para mostrar: quem lê no grupo
    vê dois ícones e precisa decorar qual é qual. O robô é o que tem ícone; a
    pessoa é a que tem nome.

    🔴 O dossiê antigo chamava todo `role='assistant'` de "*Agente*" — mas a
    rota do dashboard grava a resposta HUMANA com o mesmo `role`, marcada só
    em `payload.origem='dashboard'`. A atendente não tinha como saber o que a
    IA prometeu e o que uma colega prometeu. Numa mesa com duas pessoas
    monitorando, é o dado mais importante do dossiê.
    """
    # 🔴 A hora e de BRASILIA, nao UTC -- 18/08/2026.
    #
    # `created_at` vem em UTC. Fatiar a string em [11:16] entregava a hora
    # crua: um caso das 21h aparecia como 00:00 do dia seguinte (foi o que a
    # foto do grupo mostrou). A atendente compara essa hora com o relogio dela
    # para saber ha quanto tempo o cliente espera -- errar em 3 horas e pior
    # que nao mostrar hora nenhuma.
    hora = _hora_de_brasilia(m.get("created_at"))
    payload = m.get("payload") or {}
    if not isinstance(payload, dict):
        payload = {}
    origem = str(payload.get("origem") or "")

    if str(m.get("role")) == "user":
        autor = "Cliente"
    elif origem == "dashboard":
        autor = str(payload.get("autor") or "atendente")
    elif origem == "espelho":
        autor = "celular da corretora"
    else:
        autor = "🤖 %s" % (str(agent_name or "").strip() or "assistente virtual")

    texto = str(m.get("content") or "").strip().replace("\n", " ")
    return f"{hora} {autor}  {texto[:160]}"


def _nome_do_agente(supabase_client, company_id: str) -> str:
    """O nome que a corretora escolheu para a assistente. `""` no escuro.

    🔴 §7: filtrado por `company_id`. ⚠️ Best-effort — um dossiê que chega sem
    o nome continua melhor que um dossiê que não chega.
    """
    empresa = str(company_id or "").strip()
    if not empresa or supabase_client is None:
        return ""
    try:
        res = (supabase_client.table("agents")
               .select("name, agent_role, is_active")
               .eq("company_id", empresa).eq("is_active", True)
               .limit(10).execute())
        linhas = list(res.data or [])
        for papel in ("attendance", "insured_external"):
            for linha in linhas:
                if str(linha.get("agent_role") or "").lower() == papel:
                    return str(linha.get("name") or "").strip()
        return str((linhas[0] if linhas else {}).get("name") or "").strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[HumanHandoff] nome do agente indisponível (%s)",
                       type(exc).__name__)
        return ""


def _link_da_conversa(conversa: Dict[str, Any]) -> str:
    """O link direto. Sem ele, ela procura na lista — no celular, com o
    cliente esperando."""
    import os as _os

    base = (_os.getenv("FRONTEND_URL") or _os.getenv("APP_BASE_URL") or "").rstrip("/")
    ident = str(conversa.get("id") or "").strip()
    if not base or not ident:
        return ""
    return f"{base}/dashboard/atendimentos/conversas?c={ident}"


#: 🔴 SPEC-120 — OS TRÊS MOMENTOS, nas palavras do Founder (28/09/2026):
#: *"existem 3 momentos: conversa inicial com o segurado, acionamento com a
#: seguradora, pós-acionamento. Precisa explicar para o humano EM QUE MOMENTO
#: isso aconteceu."* O 2º (acionamento) mora no dossiê do corredor
#: (`insurer_dispatch_service.build_handoff_dossier`); estes são os outros dois.
MOMENTO_CONVERSA_INICIAL = "na CONVERSA com o segurado — antes de acionar a seguradora"
MOMENTO_POS_ACIONAMENTO = "DEPOIS do acionamento — o chamado já foi aberto na seguradora"


def _linha_do_momento(momento: str, agora=None) -> str:
    """`🕐 28/09 às 19:05 · <momento>` — o QUANDO e o EM QUE PONTO, numa linha.

    ⚠️ A hora é a do fuso da CORRETORA (`fuso_da_corretora`, o mesmo que o
    resumo das 19h usa) — nunca UTC: *"19:05"* tem de ser a hora que a
    atendente viu no relógio dela. ⛔ Nunca levanta: sem fuso, sai sem hora.
    """
    from datetime import datetime, timezone
    try:
        from app.services.platform_outbound import fuso_da_corretora
        instante = (agora or datetime.now(timezone.utc)).astimezone(fuso_da_corretora())
        return "🕐 %s às %s · %s" % (instante.strftime("%d/%m"),
                                    instante.strftime("%H:%M"), momento)
    except Exception:  # noqa: BLE001
        return "🕐 %s" % momento


def _quem_assumiu(conversa: Dict[str, Any]) -> str:
    """Evita que duas atendentes corram para a mesma conversa."""
    nome = str(conversa.get("claimed_by_name") or "").strip()
    return f"_{nome} já assumiu_" if nome else "_Ninguém assumiu ainda_"


# ===========================================================================
# 🔴 SPEC-121 · CONSERTO ÚNICO (B1 do red team) — O PEDIDO QUE NASCEU ANTES DO
#    ACIONAMENTO TEM MARCA, E A MARCA VENCE A PALAVRA
# ===========================================================================
#
# 📊 O defeito (red team, `rt2_dossie.py`, 29/09/2026): `corridor_playbooks.
# antes_de_acionar` escreve o motivo em prosa ("pedido de carro reserva — falta o
# número do sinistro…"), o agente copia a prosa para `request_human_agent`, e
# `_avisar_suporte` passava a prosa por `claims_shadow.detectar_sinistro`: a
# PALAVRA "sinistro" virava `🚨 *NOVO SINISTRO*` no grupo e `motivo_enum=
# 'sinistro'` na sombra. Yelum sem nº e TODO carro reserva da Zurich (até por
# pane, onde não existe sinistro nenhum) chegavam como sinistro novo — e a
# atendente podia abrir um aviso que não existe.
#
# ⛔ O conserto NÃO depende de tirar a palavra do texto (isso é o cinto; a fatia do
# motor o faz): o pedido carrega a MARCA do motor. Três origens, a primeira que
# existir:
#
#   ① a marca NO `reason` — `[antes_de_acionar:<codigo>] motivo`, que a
#      ferramenta de acionamento manda o agente copiar (contrato do motor:
#      `corridor_playbooks.motivo_com_codigo` / `ler_codigo_antes_de_acionar`)
#   ② o `codigo` declarado — o campo que a ferramenta devolve junto do
#      `pessoa_antes_de_acionar`, repassado pelo agente (campo novo desta tool)
#   ③ o MESMO motor, sobre a ficha que o acionamento acabou de gravar
#      (`nodes._gravar_ficha_do_turno` grava serviço, seguradora e slots ANTES de
#      o agente ler a resposta) — ⚠️ só com a ficha FRESCA: uma ficha de carro
#      reserva de dias atrás não pode rebaixar um sinistro novo de hoje
#
# e a marca fica gravada na ficha (`CHAVE_DO_PEDIDO`), para o aviso tardio do
# vigia (que chega por outro caminho) dizer a mesma coisa.
#
# 🔴 D10 é a LINHA DE CONTROLE: raio/queda que queimou equipamento É sinistro de
#    danos elétricos, e continua `🚨 NOVO SINISTRO`.

#: ⚠️ SÓ O PARAQUEDAS: o dono da tabela código → tipo é o MOTOR
#: (`corridor_playbooks.CODIGOS_ANTES_DE_ACIONAR`, lida por `_codigos_do_motor`).
#: Esta cópia vale apenas enquanto aquela não existir no módulo (a árvore de HEAD
#: `e0fa1b7`), e o guarda (`test_spec121_costura_carro_reserva_grupo.py` ⑤) fica
#: VERMELHO se as duas discordarem sobre o que é sinistro. 🔄 Gatilho de remoção:
#: a tabela do motor publicada.
#: constante_justificada (o único `sinistro`): D10 do Founder (29/09/2026) —
#: *"raio/queda de energia que danificou o motor = SINISTRO de danos elétricos"*.
_CODIGOS_ATE_A_TABELA_DO_MOTOR: Dict[str, str] = {
    "sinistro_danos_eletricos": "sinistro",
    "portao_nao_e_eletricista": "pedido_de_ajuda",
    "falta_de_energia_na_rua": "pedido_de_ajuda",
    "carro_reserva_por_desenho": "pedido_de_ajuda",
    "carro_reserva_motivo": "pedido_de_ajuda",
    "carro_reserva_sem_sinistro": "pedido_de_ajuda",
    "carro_reserva_sem_cartao": "pedido_de_ajuda",
    "carro_reserva_fora_do_horario": "pedido_de_ajuda",
    "carro_reserva_canal_desligado": "pedido_de_ajuda",
}


def _codigos_do_motor() -> Dict[str, str]:
    """código → `sinistro` | `pedido_de_ajuda`, do DONO (o motor)."""
    try:
        from app.services import corridor_playbooks as _cp

        tabela = getattr(_cp, "CODIGOS_ANTES_DE_ACIONAR", None)
        if isinstance(tabela, dict) and tabela:
            return dict(tabela)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[HumanHandoff] tabela de códigos do motor ilegível (%s)",
                       type(exc).__name__)
    return dict(_CODIGOS_ATE_A_TABELA_DO_MOTOR)


def marca_no_motivo(reason: Any) -> tuple:
    """`(codigo | "", motivo sem a marca)` — pela leitura do MOTOR
    (`ler_codigo_antes_de_acionar`). Sem ela no módulo, `("", reason)`."""
    texto = str(reason or "")
    try:
        from app.services import corridor_playbooks as _cp

        ler = getattr(_cp, "ler_codigo_antes_de_acionar", None)
        if callable(ler):
            codigo, resto = ler(texto)
            if codigo:
                return str(codigo).strip().lower(), str(resto)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[HumanHandoff] marca do motivo ilegível (%s)", type(exc).__name__)
    return "", texto


#: Onde a marca mora na ficha (`conversations.ficha_atendimento`).
CHAVE_DO_PEDIDO = "pedido_antes_de_acionar"

#: A ficha tem de ter sido escrita há no máximo isto para o motor valer como
#: marca (②). 📊 O acionamento grava a ficha e o `request_human_agent` vem no
#: MESMO turno, segundos depois; 30 min é folga para provedor lento, e fecha a
#: porta da ficha velha de outro assunto.
_FRESCOR_DA_FICHA_S = 30 * 60


def _instante(bruto: Any):
    from datetime import datetime, timezone

    if hasattr(bruto, "tzinfo"):
        return bruto if bruto.tzinfo else bruto.replace(tzinfo=timezone.utc)
    try:
        quando = datetime.fromisoformat(str(bruto or "").strip().replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return quando if quando.tzinfo else quando.replace(tzinfo=timezone.utc)


def pedido_antes_de_acionar(conversa: Dict[str, Any], codigo_declarado: Any = "",
                            *, agora=None) -> str:
    """O código de `antes_de_acionar` que trouxe ESTE pedido, ou `""`.

    ⛔ Nunca levanta e nunca lê a prosa do motivo: ① o código declarado, se o
    motor o conhece; ② o motor de novo, sobre a ficha fresca. `agora` só existe
    para o teste fixar o relógio do frescor.
    """
    from datetime import datetime, timezone

    declarado = str(codigo_declarado or "").strip().lower()
    if declarado in _codigos_do_motor():
        return declarado
    try:
        ficha = (conversa or {}).get("ficha_atendimento")
        if not isinstance(ficha, dict) or not str(ficha.get("servico") or "").strip():
            return ""
        escrita = _instante(ficha.get("atualizada_em"))
        agora = _instante(agora) if agora is not None else datetime.now(timezone.utc)
        if escrita is None or abs((agora - escrita).total_seconds()) > _FRESCOR_DA_FICHA_S:
            return ""
        from app.services.attendance_ficha import linha_do_corredor, valor_de
        from app.services.corridor_playbooks import antes_de_acionar, resolve_playbook_ref

        ramo = str(ficha.get("ramo") or "").strip().lower()
        ref = resolve_playbook_ref(str(ficha.get("seguradora") or ""),
                                   linha_do_corredor(ramo) or ramo or "auto")
        slots = {k: valor_de(v) for k, v in (ficha.get("confirmados") or {}).items()}
        achado = antes_de_acionar(ref or "", str(ficha.get("servico") or ""), slots)
        return str((achado or {}).get("codigo") or "").strip().lower()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[HumanHandoff] marca do pedido ilegível (%s)", type(exc).__name__)
        return ""


def codigo_do_pedido(conversa: Dict[str, Any]) -> str:
    """A marca já apurada: a pendurada no caso (`_com_o_pedido`) ou a gravada na ficha."""
    caso = conversa or {}
    if CHAVE_DO_PEDIDO in caso:
        return str(caso.get(CHAVE_DO_PEDIDO) or "").strip().lower()
    ficha = caso.get("ficha_atendimento")
    marca = ficha.get(CHAVE_DO_PEDIDO) if isinstance(ficha, dict) else None
    return str((marca or {}).get("codigo") or "").strip().lower() if isinstance(marca, dict) else ""


def _com_o_pedido(conversa: Dict[str, Any], codigo: str) -> Dict[str, Any]:
    """O MESMO caso com a marca pendurada — CÓPIA, como `_com_a_espera`."""
    caso = dict(conversa or {})
    caso[CHAVE_DO_PEDIDO] = str(codigo or "")
    return caso


def tipo_do_pedido(codigo: str, motivo: Any) -> str:
    """`sinistro` ou `pedido_de_ajuda` — **a marca vence a palavra**.

    Com marca: vale a tabela do MOTOR (só D10 é sinistro). Sem marca: o detector de
    sempre (`claims_shadow.detectar_sinistro`) sobre o motivo — o caminho do
    sinistro que o segurado CONTA ao agente, que não passa pelo acionamento.
    """
    from app.services.o_grupo_so_o_que_importa import TIPO_PEDIDO_DE_AJUDA, TIPO_SINISTRO

    marca = str(codigo or "").strip().lower()
    if marca:
        # ⚠️ Código que a tabela não conhece (o motor o criou depois) é pedido de
        #    ajuda: o motor o devolveu, e só D10 é sinistro — o guarda ⑤ cobra a tabela.
        return (TIPO_SINISTRO if _codigos_do_motor().get(marca) == TIPO_SINISTRO
                else TIPO_PEDIDO_DE_AJUDA)
    try:
        from app.services.claims_shadow import detectar_sinistro

        if detectar_sinistro(motivo)[0]:
            return TIPO_SINISTRO
    except Exception as exc:  # noqa: BLE001
        # Não saber classificar não pode calar o pedido de ajuda.
        logger.warning("[HumanHandoff] detector de sinistro mudo (%s)", type(exc).__name__)
    return TIPO_PEDIDO_DE_AJUDA


def _e_carro_reserva(conversa: Dict[str, Any]) -> bool:
    return codigo_do_pedido(conversa).startswith("carro_reserva")


def _marca_nao_e_sinistro(conversa: Dict[str, Any]) -> bool:
    """Há marca do motor e ela NÃO é sinistro — a prosa não decide mais o título."""
    marca = codigo_do_pedido(conversa)
    return bool(marca) and _codigos_do_motor().get(marca) != "sinistro"


#: 🔴 SPEC-121 · conserto único (P3 do red team) — o que o segurado contou para o
#: carro reserva, na ordem em que a atendente pede na seguradora. ⚠️ O agente diz
#: *"já passei para ela com tudo o que você me contou"* (`antes_de_acionar`): sem
#: esta seção a promessa era maior que o dossiê. Os slots são os que
#: `insurer_dispatch` recebe e a ficha guarda (`confirmados`).
_DADOS_DO_CARRO_RESERVA = (
    ("carro_reserva_motivo", "Motivo"),
    ("sinistro_numero", "Nº do sinistro"),
    ("carro_reserva_condutor_nome", "Quem retira"),
    ("carro_reserva_condutor_cpf", "CPF de quem retira"),
    ("carro_reserva_telefone", "Celular de quem retira"),
    ("carro_reserva_cidade", "Cidade da retirada"),
    ("carro_reserva_data_hora", "Data e hora da retirada"),
    ("carro_reserva_cnh_e_cartao", "CNH original e cartão de crédito no nome dele"),
)


def _o_pedido_do_carro_reserva(conversa: Dict[str, Any]) -> list:
    """As linhas do *O PEDIDO* — **PURA**. ⛔ Sem máscara (D-120-I: o grupo é da
    corretora e ela precisa do dado para pedir o carro) e ⛔ nunca em log."""
    from app.services.attendance_ficha import valor_de

    ficha = conversa.get("ficha_atendimento") or {}
    confirmados = (ficha.get("confirmados") or {}) if isinstance(ficha, dict) else {}
    linhas = []
    for slot, rotulo in _DADOS_DO_CARRO_RESERVA:
        valor = " ".join(str(valor_de(confirmados.get(slot)) or "").split())
        if valor:
            linhas.append("%s: %s" % (rotulo, valor[:120]))
    if not linhas:
        return ["⚠️ o agente não chegou a anotar os dados de quem retira — peça ao cliente."]
    diarias = "".join(ch for ch in str(valor_de(confirmados.get("carro_reserva_diarias")) or "")
                      if ch.isdigit())
    try:
        from app.services.corridor_playbooks import CARRO_RESERVA_DIARIAS_PADRAO as _PADRAO
    except Exception:  # noqa: BLE001
        _PADRAO = "15"
    linhas.append("Diárias: %s" % (
        "%s (limite do plano)" % diarias if diarias else
        "o limite do plano — sem ele, %s (a seguradora confirma)" % _PADRAO))
    return linhas


# ===========================================================================
# 🔴 SPEC-123 F7 · D8 — O AGENTE SÓ CHAMA PESSOA QUANDO PRECISA
# ===========================================================================
#
# 📊 30/09/2026 (MCP `execute_sql`, `conversations` desde 01/08): 1112 conversas,
# 502 em `HUMAN_REQUESTED`, `human_handoff_reason` preenchido em **5**; e os 36
# eventos `grupo.%` do mesmo período têm `motivo_classe='desconhecido'` (36 de 36).
# Não há linha de base de POR QUE o agente chama gente — o diário de decisões
# (`diario_de_decisoes`, `origem='atendimento'`) passa a ser ela.
#
# A ordem do Founder (D8): o que o agente resolve sem humano — dúvida simples,
# dado que dá para perguntar ao segurado — não vai a pessoa; sinistro, condomínio,
# empresarial, rota sem corredor e o cliente que pede pessoa continuam indo.
#
# O mecanismo é UMA segunda chance por conversa por dia:
#
#   motivo de REGRA ou caso que é sempre de gente → passa a pessoa como antes
#   qualquer outro motivo, 1ª vez                  → NÃO passa: devolve ao agente a
#                                                    instrução de resolver com o
#                                                    segurado e grava no diário
#   qualquer outro motivo, 2ª vez                  → passa a pessoa como antes
#
# ⛔ SEM LINHA NO DIÁRIO, SEM SEGUNDA CHANCE. A linha é o contador: sem ela a
#    segunda chance viraria um laço (o agente pediria para sempre e nunca
#    passaria). E autonomia que não fica registrada não pode ser avaliada (D7).
#    Diário fora do ar → pessoa, exatamente como antes desta fatia.

#: O estado devolvido ao agente na segunda chance — instrução, não relato.
#: ⚠️ Escrita para modelo inteligente: diz o objetivo e a saída, sem roteiro.
#: 🔴 SEM o carimbo `HANDOFF_OK` (o fiscal `honestidade_do_handoff` ancora nele: sem
#:    ele, "já passei para a equipe" é reescrito) e sem verbo de transferência na
#:    1ª pessoa do passado (o guarda do teste confere com `afirma_transferencia`).
SEGUNDA_CHANCE_DO_HANDOFF = (
    "HANDOFF_NAO_FEITO · SEGUNDA_CHANCE · ninguém da equipe foi chamado. "
    "O objetivo é resolver este caso sem uma pessoa. Se falta um dado que só o "
    "segurado tem, pergunte a ele agora. Se é uma dúvida sobre o seguro, responda "
    "com o que você sabe (apólice, base de conhecimento) e diga ao segurado quando "
    "não tiver certeza. Só chame `request_human_agent` de novo se realmente não "
    "houver saída — e diga no motivo por quê. Não diga ao segurado que alguém da "
    "equipe vai assumir."
)
_MARCA_DA_SEGUNDA_CHANCE = "HANDOFF_NAO_FEITO · SEGUNDA_CHANCE"


def foi_segunda_chance(resultado: Any) -> bool:
    """O retorno da ferramenta foi a segunda chance (nada foi passado a ninguém)?

    ⚠️ Para quem lê o resultado depois (ex.: `nodes._gravar_ficha_do_turno`, que
    hoje marca `fase='com_humano'` a QUALQUER retorno desta ferramenta).
    """
    return _MARCA_DA_SEGUNDA_CHANCE in str(resultado or "")


#: A frase para gente de cada motivo de REGRA (`classificar_o_motivo`).
#: constante_justificada: são as cinco chaves de `_MOTIVOS_DE_REGRA` — o agente PODIA,
#: mas o produto manda passar (D-PILOTO-13); D8 mantém "o cliente pede pessoa".
_FRASE_DA_REGRA = {
    "vitima": "há vítima ou risco à pessoa",
    "cliente_pediu_humano": "o segurado pediu para falar com uma pessoa",
    "valor_acima_do_limite": "envolve valor ou aprovação acima do que o agente decide",
    "fora_do_escopo": "o assunto está fora do que o agente atende",
    "segurado_irritado": "o segurado está irritado ou reclamando",
}

#: Os casos que vão a pessoa NA PRIMEIRA chamada além dos de REGRA, procurados por
#: PALAVRA INTEIRA (sem acento, minúsculo) no motivo e no ramo/serviço da ficha.
#: ⚠️ Errar para o lado de passar é o comportamento de antes desta fatia; errar para o
#:    lado de segurar é chamar o segurado de volta num caso que era de gente.
_SEMPRE_DE_GENTE = (
    # constante_justificada: D8/D10 da SPEC-123 — condomínio fica com a atendente
    ("condominio", ("condominio", "condominial"),
     "é seguro de condomínio, que fica com a equipe"),
    # constante_justificada: D8/D10 — empresarial fica com a atendente ("empresa" e
    # "cnpj" entram: passar a mais é o comportamento de antes)
    ("empresarial", ("empresarial", "empresa", "cnpj"),
     "é seguro empresarial, que fica com a equipe"),
    # constante_justificada: D8 "rota sem corredor" — a ferramenta de acionamento manda
    # o motivo "sem corredor para …"; o portal de vidros é o corredor dessa família e,
    # quando ele não atende, não há outro caminho
    ("sem_corredor", ("corredor", "portal"),
     "não há caminho automático para esta seguradora ou serviço"),
    # constante_justificada: prompt do atendimento, LIMITES — risco grave → pessoa
    ("risco_grave", ("fogo", "fumaca", "incendio", "faisca", "choque", "queimado",
                     "alagamento", "alagado", "emergencia"),
     "há risco à pessoa ou ao imóvel"),
    # constante_justificada: D10 — carro reserva está em espera com o Founder
    ("carro_reserva", ("carro reserva",), "o carro reserva fica com a equipe"),
    # constante_justificada: D10 — conversar com consultora humana da seguradora
    ("consultora", ("consultora", "consultor"),
     "a seguradora pôs uma pessoa dela na conversa"),
)


def por_que_vai_direto_a_pessoa(motivo: Any, *, codigo: Any = "",
                                caso: Optional[Dict[str, Any]] = None,
                                ja_com_a_equipe: bool = False) -> str:
    """`""` = cabe a segunda chance; senão, POR QUE vai direto, em frase de gente.

    **PURA** (o detector de sinistro é o MESMO `claims_shadow.detectar_sinistro` do
    aviso ao grupo). A ordem é a do custo de errar: o que já é da equipe, a marca do
    motor, o pós-acionamento (a R9 decide), a REGRA, o sinistro, a lista D8/D10.
    """
    caso = caso or {}
    if ja_com_a_equipe:
        # constante_justificada: a equipe já tem o caso — segurar aqui não poupa ninguém
        return "o caso já estava com a equipe"
    if str(codigo or "").strip():
        # constante_justificada: `pessoa_antes_de_acionar` — o MOTOR mandou (SPEC-121 B1)
        return "a ferramenta de acionamento mandou passar a uma pessoa antes de acionar"
    if _e_pos_acionamento(caso):
        # constante_justificada: depois do acionamento, quem decide é a R9
        # (`SITUACOES_PARA_HUMANO`), não esta lista — duas verdades sobre o mesmo caso
        return "o caso já foi acionado e o acompanhamento segue a regra do pós-acionamento"
    classe, chave = classificar_o_motivo(motivo)
    if classe == CLASSE_REGRA:
        return _FRASE_DA_REGRA.get(chave, "é um caso que a regra manda para uma pessoa")
    ficha = caso.get("ficha_atendimento") if isinstance(caso.get("ficha_atendimento"), dict) else {}
    # 🔴 SPEC-123 · conserto único (juiz B3 · red team B6) — O QUE O SEGURADO DISSE,
    #    não só o que o modelo escreveu no motivo. As falas são as últimas do
    #    segurado na conversa (`mensagens`, lidas por `_arun` da tabela que o agente
    #    lê) e a prévia. 📊 Antes: "quero falar com um atendente humano agora" com o
    #    motivo "dúvida sobre a franquia" ganhava a segunda chance.
    falas = _falas_do_segurado(caso)
    try:
        from app.atendimento.pos_acionamento import pediu_pessoa
        from app.services.claims_shadow import detectar_sinistro

        if pediu_pessoa([str(motivo or "")] + falas):
            # constante_justificada: D8 — "o cliente que pede pessoa continua indo"
            return _FRASE_DA_REGRA["cliente_pediu_humano"]
        relato = " ".join(p for p in [str(motivo or "")] + falas if p)
        # Juntos (o par "bati" + "carro" pode vir em duas falas) E cada um sozinho (a
        # tranca de venda de uma fala não pode calar o sinistro de outra).
        if any(detectar_sinistro(t, ficha or None)[0]
               for t in [relato, str(motivo or "")] + falas):
            # constante_justificada: D8 — "sinistro continua indo a pessoa"
            return "é sinistro, e sinistro sempre vai para uma pessoa"
    except Exception as exc:  # noqa: BLE001
        # Não saber classificar não pode segurar um sinistro: na dúvida, pessoa.
        logger.warning("[HumanHandoff] detector de sinistro mudo (%s)", type(exc).__name__)
        return "não deu para conferir se é sinistro"
    texto = _sem_acento_minusculo(" ".join((
        _motivo_em_portugues(motivo), str(ficha.get("ramo") or ""),
        str(ficha.get("servico") or ""))))
    #: ⚠️ Nas falas do segurado só o RISCO GRAVE vale: "empresa", "portal",
    #:    "consultor" na boca dele não dizem que o caso é empresarial/sem corredor.
    texto_do_segurado = _sem_acento_minusculo(" ".join(falas))
    for _chave, palavras, frase in _SEMPRE_DE_GENTE:
        alvos = (texto, texto_do_segurado) if _chave == "risco_grave" else (texto,)
        for p in palavras:
            padrao = r"\b%s\b" % re.escape(_sem_acento_minusculo(p))
            if any(re.search(padrao, a) for a in alvos):
                return frase
    return ""


#: Quantas falas do segurado a segunda chance lê — a MESMA janela de
#: `_ultimas_do_cliente` (o rótulo do turno), para as duas leituras verem o mesmo turno.
#: constante_justificada: 📊 no acervo o turno é uma rajada de 1–4 mensagens (R1 da 097.1).
FALAS_DO_SEGURADO_LIDAS = 4


def _falas_do_segurado(caso: Dict[str, Any]) -> list:
    """As últimas falas do segurado (`mensagens`) + a prévia, sem repetir, sem vazias."""
    vistas, falas = set(), []
    for m in list(_ultimas_do_cliente(caso)) + [str(caso.get("last_message_preview") or "")]:
        m = str(m or "").strip()
        if m and m not in vistas:
            vistas.add(m)
            falas.append(m)
    return falas


def _dia_utc() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _chave_da_segunda_chance(conversa_id: str) -> str:
    """UMA por conversa por dia — ⚠️ SEM o motivo de propósito: com ele, o agente que
    trocasse a frase ganharia outra segunda chance, e o contador seria do motivo, não
    da conversa. O dia é o "mesmo episódio": a virada só concede, no máximo, mais uma."""
    return "atendimento:segunda_chance:%s:%s" % (conversa_id, _dia_utc())


def _chave_de_chamou_pessoa(conversa_id: str, motivo: Any) -> str:
    """Conversa + motivo (a CHAVE da classe, nunca a prosa: a prosa traz dado) + dia."""
    _classe, chave = classificar_o_motivo(motivo)
    return "atendimento:chamou_pessoa:%s:%s:%s" % (conversa_id, chave, _dia_utc())


def _sessao_para_mascara(linha: Dict[str, Any]) -> Dict[str, Any]:
    """Os valores da ficha que a máscara do diário troca por marca (nome, CPF, placa…)."""
    ficha = linha.get("ficha_atendimento") if isinstance(linha.get("ficha_atendimento"), dict) else {}
    try:
        from app.services.attendance_ficha import valor_de

        return {k: valor_de(v) for k, v in (ficha.get("confirmados") or {}).items()}
    except Exception:  # noqa: BLE001
        return {}


class HumanHandoffInput(BaseModel):
    """Input schema para a HumanHandoffTool."""

    reason: Optional[str] = Field(
        default=None,
        description="Motivo da transferência. Exemplo: 'sinistro — exige humano', "
        "'risco grave', 'cliente pediu pessoa', 'não há corredor para esta seguradora'.",
    )
    # 🔴 SPEC-121 · conserto único (B1) — a MARCA, não a palavra.
    codigo: Optional[str] = Field(
        default=None,
        description="Só quando a ferramenta de acionamento devolveu "
        "status 'pessoa_antes_de_acionar': copie aqui o `codigo` que ela devolveu. "
        "Nos outros casos, deixe vazio.",
    )


class HumanHandoffTool(BaseTool):
    """
    Ferramenta para solicitar transferência para atendimento humano.

    Use esta ferramenta quando:
    - For SINISTRO (sempre — sinistro não se resolve sozinho)
    - Não existir corredor para acionar aquela seguradora/serviço
    - Houver risco grave à pessoa (fogo, fumaça, choque, água com energia)
    - O usuário pedir explicitamente para falar com uma pessoa
    - Você travar: duas tentativas sem avançar

    A ferramenta avisa o suporte da corretora com um resumo do caso.
    """

    # 🔴 A DECLARAÇÃO QUE FALTAVA — 18/08/2026.
    #
    # `_run` desta tool levanta RuntimeError de propósito, e a docstring dele
    # afirmava "o tool_node já força _arun". Nenhuma linha fazia isso: a lista
    # literal em `nodes.py` não continha `request_human_agent`, então toda
    # chamada caía no caminho síncrono e estourava. 📊 Quatro transferências
    # falsas numa tarde.
    #
    # Agora quem declara é a ferramenta, e o executor obedece. Uma lista no
    # executor já esqueceu uma tool; ia esquecer a próxima.
    exige_async: ClassVar[bool] = True

    name: str = "request_human_agent"
    description: str = """
    Transfere a conversa para um atendente humano da corretora e avisa o suporte
    com um resumo do caso. Use em SINISTRO (sempre), quando não houver corredor
    para acionar a seguradora, em risco grave, em condomínio ou empresarial, quando
    o cliente pedir pessoa, ou quando não houver saída. Dúvida simples e dado que o
    segurado pode informar se resolvem com ele, não com pessoa. Informe o motivo.
    """
    args_schema: Type[BaseModel] = HumanHandoffInput

    supabase_client: object = None

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, supabase_client, **kwargs):
        super().__init__(**kwargs)
        self.supabase_client = supabase_client
        logger.info("[HumanHandoff] Tool inicializada")

    # ------------------------------------------------------------------ #
    # o dossiê
    # ------------------------------------------------------------------ #
    def _montar_dossie(self, conversa: Dict[str, Any], motivo: str) -> str:
        """O que a atendente precisa para agir SEM reler a conversa.

        🔴 REESCRITO EM 14/08/2026 — SPEC-071 Bloco 3.4.

        O dossiê anterior dizia cliente, telefone, motivo e as 12 últimas
        mensagens. Servia para não entrar cego; não servia para **agir**. Os
        defeitos, na ordem em que atrapalham quem está com o celular na mão:

        · **não tinha link** — "Abra em Atendimentos → Conversas" e ela que
          procure na lista, no celular, com o cliente esperando;
        · **não separava a IA de uma colega** — tudo era "*Agente*", inclusive
          o que outra atendente havia escrito pelo dashboard (a rota grava
          `role='assistant'` também). Numa mesa com duas pessoas monitorando,
          *"o que a IA já prometeu?"* é a pergunta mais importante, e não tinha
          resposta;
        · **não dizia o que fazer** — entregava matéria-prima e deixava a
          decisão inteira para quem chegou agora;
        · **não dizia se alguém já assumiu**, então duas atendentes podiam
          correr para a mesma conversa.

        Diretriz do Founder: *"ela olha a mensagem e já sabe o que fazer"* —
        completo, mas fácil de ler; linguagem humana, nunca
        `assistencia.residencial.encanador`; **sem protocolo e sem caso**
        (numeração de um sistema que não existe mais).

        A ordem das seções é a ordem em que a pergunta aparece na cabeça dela:
        o que é → quem é → o que houve → o que falta → **o que fazer** → a
        conversa → o link.
        """
        # 🔴 SPEC-097.1 U2.1 — a espera é LIDA, não deduzida do texto.
        #
        # ⚠️ Achado do gate zero: `_o_que_fazer` e o dossiê só enxergavam a
        # ficha e as mensagens. `dispatch_state` e `work_waits` não chegavam
        # aqui — então "de quem se espera" era impossível de dizer, e o dossiê
        # seguia mentindo em todo caso cujo estado só existe na tabela.
        espera = self._espera_ativa(conversa)
        if _e_pos_acionamento(conversa, espera):
            return self._dossie_de_pos_acionamento(conversa, motivo, espera)

        titulo = _titulo_humano(conversa, motivo)
        linhas = [titulo, _TRACO]

        # QUEM É — três linhas, sem rótulo: rótulo em WhatsApp é ruído.
        quem = str(conversa.get("user_name") or "").strip()
        fone = _fone_bonito(conversa.get("user_phone"))
        # 🔴 `138847853768811 · 138847853768811` -- foi o que saiu no grupo em
        # 18/08/2026. Quando o WhatsApp nao manda `pushName`, o `user_name`
        # nasce igual ao identificador, e o dossie imprimia o MESMO numero duas
        # vezes com um ponto no meio. Nao informa e ainda parece defeito -- que
        # e o que era. So dizemos os dois quando forem coisas diferentes.
        so_digitos = "".join(ch for ch in quem if ch.isdigit())
        if quem and so_digitos == quem:
            quem = ""
        linhas.append(" · ".join([p for p in (quem or "cliente não identificado", fone) if p]))

        apolice = _linha_da_apolice(conversa)
        if apolice:
            linhas.append(apolice)
        linhas.append(_linha_do_momento(MOMENTO_CONVERSA_INICIAL))

        # O QUE ACONTECEU — narrativa, não campos soltos.
        narrativa = _narrativa(conversa, motivo)
        if narrativa:
            linhas += ["", "*O QUE ACONTECEU*", narrativa]

        # 🔴 SPEC-121 · conserto único (P3): o carro reserva leva o que o segurado
        #    CONTOU — é o que a atendente digita no pedido à seguradora.
        if _e_carro_reserva(conversa):
            linhas += ["", "*O PEDIDO*"] + _o_pedido_do_carro_reserva(conversa)

        # O QUE FALTA — some quando não falta nada. Seção vazia é ruído.
        falta = _o_que_falta(conversa)
        if falta:
            linhas += ["", "*O QUE FALTA*"] + [f"⚠️ {f}" for f in falta]

        # O QUE FAZER — a primeira coisa que ela lê de verdade.
        linhas += ["", "*👉 O QUE FAZER*", _o_que_fazer(conversa, motivo)]

        # 🔴 SPEC-EXTRA-001.3 §8.0 — DUAS DECISÕES DA SPEC-071 REVERTIDAS, e é
        # reversão deliberada, não esquecimento.
        #
        # 📊 **As últimas mensagens saem.** No piloto, o dossiê com histórico
        # virou 4 balões e a atendente lia o último — que é o menos importante.
        # O *O QUE ACONTECEU* acima entrega o mesmo em três linhas.
        #
        # 📊 **O link do painel sai, e o WhatsApp do segurado entra.** §1.5
        # causa 3 do diagnóstico: no celular, o número clicável custa UM TOQUE e
        # o painel custa uma página. O piloto provou que a decisão de 14/08
        # estava errada para quem está de pé, com o cliente esperando.
        #
        # ⚠️ O contra-argumento do `telefone_curto` — o dossiê fica no histórico
        # do grupo para sempre — continua válido em OUTRO lugar: por isso
        # NENHUM dos quatro modelos leva o texto das mensagens.
        #
        # 🔴 CPF/CNPJ está no 🆘 **e** no 🚨 — §8.1 e §8.2 da SPEC pedem os dois,
        # porque é o que permite achar a apólice sem sair da mensagem. ⚠️ Uma
        # versão anterior deste comentário dizia *"só o 🆘 leva CPF"* e
        # contradizia `_montar_sinistro`, oito linhas abaixo. Comentário que
        # mente sobre o código encerra a investigação seguinte. A decisão sobre
        # PII no histórico do grupo é do Founder e está escrita na caixa dele.
        #
        # 🔄 Gatilho de retorno: se uma corretora pedir o link de volta, ele
        # volta como PREFERÊNCIA do destino (`human_support_destinations.metadata`),
        # nunca como padrão.
        linhas += [_TRACO]
        from app.services.os_modelos_do_grupo import link_do_whatsapp

        _wa = link_do_whatsapp(conversa.get("user_phone"))
        if _wa:
            linhas.append(f"*WhatsApp do segurado:* {_wa}")
        linhas.append(_quem_assumiu(conversa))
        return "\n".join(linhas)

    # ------------------------------------------------------------------ #
    # 🔴 SPEC-097.1 U2.1 — o dossiê do caso que já foi acionado
    # ------------------------------------------------------------------ #
    def _espera_ativa(self, conversa: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """A linha de `work_waits` ativa desta conversa. `None` sem lastro.

        ⛔ Best-effort: um dossiê sem a espera continua melhor que dossiê
        nenhum — mas ele DIZ que não achou, em vez de inventar de quem se
        espera (R3).
        """
        try:
            achado = (self.supabase_client.table("work_waits")
                      .select("id, company_id, conversation_id, kind, scope, "
                              "status, vence_em, created_at")
                      .eq("company_id", str(conversa.get("company_id") or ""))  # 🔴 §7
                      .eq("conversation_id", str(conversa.get("id") or ""))
                      .eq("status", "ativo")
                      .limit(4).execute())
            linhas = list(achado.data or [])
        except Exception as exc:  # noqa: BLE001
            logger.warning("[HumanHandoff] espera não lida (%s)", type(exc).__name__)
            return None
        if not linhas:
            return None
        # ⚠️ A MESMA regra da projeção (E6/U1.3): entre esperas ativas, a de
        #    menor `vence_em`; empate → `pos_acionamento`. Duas telas com
        #    ordens diferentes contariam duas histórias do mesmo caso.
        linhas.sort(key=lambda w: (str(w.get("vence_em") or "9999"),
                                   0 if str(w.get("scope")) == "pos_acionamento" else 1))
        return linhas[0]

    def _dossie_de_pos_acionamento(self, conversa: Dict[str, Any], motivo: str,
                                   espera: Optional[Dict[str, Any]]) -> str:
        """O formato de §3.3 do relatório, com as quatro perguntas da atendente.

        ⛔ *"conclua o acionamento"* NUNCA aparece aqui: o acionamento já foi
        feito, e mandar concluí-lo é mandar refazer trabalho entregue.
        """
        servico = ""
        texto_do_caso = _texto_do_caso(conversa, motivo)
        for chave, (_emoji, nome) in _TITULOS.items():
            if chave in texto_do_caso and chave not in ("sinistro", "consulta"):
                servico = nome
                break
        titulo = "🔁 *PÓS-ACIONAMENTO%s*" % (" · %s" % servico if servico else "")

        linhas = [titulo, _TRACO]
        quem = str(conversa.get("user_name") or "").strip()
        fone = _fone_bonito(conversa.get("user_phone"))
        so_digitos = "".join(ch for ch in quem if ch.isdigit())
        if quem and so_digitos == quem:
            quem = ""
        linhas.append(" · ".join([p for p in (quem or "cliente não identificado", fone) if p]))
        apolice = _linha_da_apolice(conversa)
        if apolice:
            linhas.append(apolice)
        ficha = conversa.get("ficha_atendimento") or {}
        protocolo = str((ficha or {}).get("protocolo") or "").strip() if isinstance(ficha, dict) else ""
        linhas.append(_linha_do_momento(MOMENTO_POS_ACIONAMENTO))
        # 🔴 SPEC-120 D15 — O NÚMERO DO PROTOCOLO SAI POR EXTENSO. Antes a linha
        #    dizia *"protocolo com o cliente"* — o dossiê SABIA o número e não o
        #    escrevia, e a atendente tinha de perguntar ao segurado o que o
        #    sistema já tinha. Protocolo é o que ela precisa para falar com a
        #    seguradora; não é dado para esconder.
        if protocolo:
            linhas.append(f"Acionamento já entregue · protocolo *{protocolo}*")

        linhas += ["", "*Quem fala*", _quem_fala(conversa)]
        linhas += ["", "*O que ele quer*", _o_que_ele_quer(conversa)]
        linhas += ["", "*Onde parou*", _onde_parou(conversa, espera)]

        falta = _o_que_falta(conversa)
        linhas += ["", "*Falta*"]
        if falta:
            linhas += [f"⚠️ {f}" for f in falta]
        else:
            # ⚠️ A seção NÃO some quando não falta nada: *"nada com o cliente"*
            #    é a informação que impede a atendente de pedir documento a
            #    quem já mandou tudo.
            linhas.append("nada com o cliente. O que falta é a resposta de quem "
                          "está devendo.")

        # 🔴 [J-4]: a recomendação recebe A ESPERA, não só a conversa. Sem ela
        #    `_o_que_fazer` reavaliava o estado do caso sem o lastro que trouxe
        #    o dossiê até aqui e caía no ramo de antes do acionamento — título
        #    certo, ação errada, e a R9 inerte.
        linhas += ["", "*O que fazer*",
                   _o_que_fazer(_com_a_espera(conversa, espera), motivo)]

        # =================================================================
        # 🔴 SPEC-120 — O PÓS-ACIONAMENTO SEGUE A MESMA DECISÃO DO 🆘 (§8.0)
        # =================================================================
        #
        # 📊 Em 16/09/2026 (SPEC-EXTRA-001.3 §8.0) duas decisões da SPEC-071
        # foram revertidas no dossiê principal: *o link do painel sai e o
        # WhatsApp do segurado entra* ("no celular o número clicável custa UM
        # TOQUE e o painel custa uma página") e *as últimas mensagens saem*
        # ("viravam 4 balões e a atendente lia o último"). **Este montador
        # nunca foi atualizado** — continuava mandando o painel e o histórico,
        # e nenhum WhatsApp. O guarda da decisão
        # (`test_os_quatro_modelos_falam_portugues.py`) só olhava o corpo de
        # `_montar_dossie`, então o esquecimento ficou verde.
        #
        # É a confusão que o Founder descreveu em 28/09 — *"não sei se está
        # aparecendo o dossiê errado"*: eram DOIS formatos para a mesma equipe,
        # conforme o caso tivesse passado ou não por um acionamento.
        #
        # E a regra dele, a mesma para os dois: *"eles precisam olhar o
        # dossiê, clicar no número do WhatsApp e já abrir a conversa com o
        # cliente para assumirem. Precisa ser fácil, claro, rápido."*
        linhas += ["", _TRACO]
        from app.services.os_modelos_do_grupo import link_do_whatsapp
        _wa = link_do_whatsapp(conversa.get("user_phone"))
        if _wa:
            linhas.append(f"*WhatsApp do segurado:* {_wa}")
        linhas.append(_quem_assumiu(conversa))
        return "\n".join(linhas)

    def _montar_sinistro(self, conversa: dict, motivo: str) -> str:
        """🚨 NOVO SINISTRO — SPEC-EXTRA-001.3 §8.2.

        ⚠️ Reaproveita as MESMAS peças do dossiê (`_narrativa`, `_o_que_falta`,
        `_linha_da_apolice`): elas já leem a ficha e já falam português. O que
        muda é a FORMA — e a forma é o contrato.

        🔴 *Pontos de atenção* recebe HOJE o que a ficha sabe que FALTA, e diz
        que é isso. ⛔ Não se inventa checklist clínico sem fonte: o conteúdo por
        tipo (colisão, roubo, incêndio, empresarial, condomínio) vem da base de
        produtos, na EXTRA-001.5. O LUGAR já está reservado.
        """
        from app.services.o_fim_do_atendimento import instante_br
        from app.services.os_modelos_do_grupo import modelo_novo_sinistro

        ficha = conversa.get("ficha") if isinstance(conversa.get("ficha"), dict) else {}
        nome = str(conversa.get("user_name") or "").strip()
        if nome and nome.isdigit():
            nome = ""
        return modelo_novo_sinistro(
            tipo=str(ficha.get("tipo_de_sinistro") or ficha.get("servico") or "").strip(),
            segurado=nome or "segurado não identificado",
            documento=str(ficha.get("cpf") or ficha.get("cnpj") or "").strip(),
            apolice=(_linha_da_apolice(conversa) or "").replace("*", "").strip(),
            # ⚠️ `instante_br` é o MESMO formatador que a atendente já lê na
            #    ficha e nas esperas — nada de `created_at[11:16]` em UTC cru,
            #    que foi o `00:00 num caso das 21h` de 18/08.
            quando=instante_br(conversa.get("last_message_at")
                               or conversa.get("created_at")),
            resumo=_narrativa(conversa, motivo),
            pontos_de_atencao=_o_que_falta(conversa),
            telefone=conversa.get("user_phone"))

    async def _avisar_suporte(self, company_id: str, conversa: Dict[str, Any],
                              motivo: str, *, tipo: str = "",
                              dedup: bool = False,
                              prova: str = "",
                              pedido: Optional[str] = None) -> Dict[str, Any]:
        """Envia o dossiê. Devolve o que aconteceu — sem arredondar.

        🔴 SPEC-EXTRA-001.3 — este método PASSOU A SER UM ADAPTADOR.

        A resolução de destino, o `bloco_unico`, o `asyncio.to_thread` e o
        registro em `platform_sends`/`work_events` mudaram-se para
        `o_grupo_so_o_que_importa.enviar_ao_grupo`, que é a porta única por
        onde os 11 pontos de envio ao grupo passam a sair. O que ficou aqui é
        o que só este caminho sabe: **montar o dossiê**.

        ⚠️ `dedup=False` por padrão porque os três chamadores deste método
        (`_arun`, `varrer_handoffs_parados`, `varrer_esperas_vencidas`) já
        reservaram a vez em `reivindicar_o_aviso` — e o marcador é o mesmo.
        Deduplicar duas vezes calaria o segundo tipo de aviso da conversa.

        🔴 SPEC-121 F1 — `prova` é a regra B da porta: COMO se sabe que foi o
        agente quem pediu. Cada chamador declara a sua (`_arun`: o pedido; o
        vigia: o pedido CONFERIDO; a espera: a espera do acionamento). Sem ela, a
        porta cala — e é isso que impede o status `HUMAN_REQUESTED` do espelho
        de virar aviso.

        🔴 SPEC-121 · conserto único (B1) — `pedido` é a MARCA do motor
        (`pedido_antes_de_acionar`); o `_arun` a passa já apurada. Sem ela (o
        vigia), vale a gravada na ficha — e a ficha é LIDA quando a linha do
        chamador não a trouxe, porque o dossiê do carro reserva mora nela.
        """
        from app.services.o_grupo_so_o_que_importa import (
            TIPO_SINISTRO, enviar_ao_grupo,
        )

        if not tipo and "ficha_atendimento" not in (conversa or {}):
            conversa = await asyncio.to_thread(self._com_a_ficha, company_id, conversa)

        # 🔴 SPEC-EXTRA-001.3 BLOCO D.2 — SINISTRO TEM MODELO PRÓPRIO, e passa
        # pela guarda SEMPRE: é notícia de negócio, não lembrete de fila.
        #
        # ⛔ O detector é o MESMO `claims_shadow.detectar_sinistro` que o `_arun`
        # já usa — agora atrás da MARCA (`tipo_do_pedido`, uma função para os
        # dois): dois classificadores para a mesma pergunta são dois
        # classificadores para manter, e o segundo envelhece calado (CLAUDE.md §5).
        codigo_no_texto, motivo = marca_no_motivo(motivo)
        if pedido is None:
            codigo = codigo_do_pedido(conversa) or codigo_no_texto
        else:
            codigo = str(pedido or "")
        conversa = _com_o_pedido(conversa, codigo)
        _tipo = tipo or tipo_do_pedido(codigo, motivo)

        if _tipo == TIPO_SINISTRO:
            texto = await asyncio.to_thread(self._montar_sinistro, conversa, motivo)
        else:
            texto = await asyncio.to_thread(self._montar_dossie, conversa, motivo)
        classe, chave = classificar_o_motivo(motivo)
        saida = await enviar_ao_grupo(
            self.supabase_client, company_id=str(company_id), tipo=_tipo,
            texto=texto, conversation_id=str(conversa.get("id") or ""),
            telefone=str(conversa.get("user_phone") or ""),
            conversa=conversa, dedup=dedup,
            resumo="%s — conversa %s" % (_tipo, str(conversa.get("id") or "")[:8]),
            motivo=chave, motivo_classe=classe, prova_do_agente=prova)
        if saida["enviado"]:
            logger.info("[HumanHandoff] dossiê enviado | empresa=%s | tipo=%s",
                        company_id, _tipo)
        return {"avisado": bool(saida["enviado"]), "motivo": saida["motivo"],
                "calado": bool(saida["calado"])}

    # ------------------------------------------------------------------ #
    # 🔴 SPEC-123 F7 · D8 — a segunda chance e a linha no diário
    # ------------------------------------------------------------------ #
    async def _falas_do_segurado_no_banco(self, linha: Dict[str, Any]) -> list:
        """As últimas falas do SEGURADO desta conversa, em ordem — as mesmas linhas de
        `messages` que o agente leu (`database.get_conversation_history`, que o webhook
        grava ANTES de chamar o agente).

        🔴 §7: `messages` não tem `company_id`; o isolamento é a CONVERSA — `linha` veio
        da leitura `.eq("company_id")` de `_arun`, e só o `id` dela é usado aqui.
        ⚠️ Falhou a leitura → `[]` e a decisão usa a prévia (`last_message_preview`),
        como antes deste conserto. Nunca levanta.
        """
        conversa_id = str((linha or {}).get("id") or "").strip()
        if not conversa_id:
            return []

        def _ler():
            return (self.supabase_client.table("messages")
                    .select("content, created_at")
                    .eq("conversation_id", conversa_id)
                    .eq("role", "user")
                    .order("created_at", desc=True)
                    .limit(FALAS_DO_SEGURADO_LIDAS).execute())

        try:
            achado = await asyncio.to_thread(_ler)
            linhas = list(getattr(achado, "data", None) or [])
            return [str(l.get("content") or "") for l in reversed(linhas)
                    if str(l.get("content") or "").strip()]
        except Exception as exc:  # noqa: BLE001
            logger.warning("[HumanHandoff] falas do segurado ilegíveis (%s) — uso a prévia",
                           type(exc).__name__)
            return []

    async def _ja_teve_segunda_chance(self, company_id: str, conversa_id: str) -> Optional[bool]:
        """`True`/`False` pelo diário; `None` quando não deu para ler (→ pessoa).

        🔴 §7: por `company_id` E pela chave (o índice único da tabela) — a linha de
        outra corretora com a mesma chave não conta.
        """
        chave = _chave_da_segunda_chance(conversa_id)

        def _ler():
            return (self.supabase_client.table("diario_de_decisoes")
                    .select("id")
                    .eq("company_id", str(company_id))
                    .eq("chave_idempotencia", chave)
                    .limit(1).execute())

        try:
            achado = await asyncio.to_thread(_ler)
            return bool(getattr(achado, "data", None))
        except Exception as exc:  # noqa: BLE001
            logger.warning("[HumanHandoff] contador da segunda chance ilegível (%s) — "
                           "passo a pessoa", type(exc).__name__)
            return None

    async def _registrar_no_diario(self, company_id: str, linha: Dict[str, Any], *,
                                   motivo: str, acao: str, classe: str, chave: str,
                                   explicacao: str) -> Optional[str]:
        """UMA linha `origem='atendimento'` no diário. Nunca levanta; `None` = não gravou."""
        try:
            from app.services.diario_de_decisoes import registrar_decisao

            ficha = (linha.get("ficha_atendimento")
                     if isinstance(linha.get("ficha_atendimento"), dict) else {})
            return await registrar_decisao(
                company_id=str(company_id), origem="atendimento", work_run_id=None,
                conversation_id=str(linha.get("id") or "") or None,
                seguradora=str(ficha.get("seguradora") or ""),
                ramo=str(ficha.get("ramo") or ""), rota="",
                servico=str(ficha.get("servico") or ""),
                tela=str(linha.get("last_message_preview") or ""),
                classe=classe, acao=acao, valor=_motivo_em_portugues(motivo),
                nota=None, limiar=None, motivo=_motivo_em_portugues(motivo),
                explicacao_para_gente=explicacao, modelo="", segunda_opiniao=None,
                modo="on", gatilho="request_human_agent", chave_idempotencia=chave,
                sessao=_sessao_para_mascara(linha))
        except Exception as exc:  # noqa: BLE001
            logger.error("[HumanHandoff] diário não registrado (%s)", type(exc).__name__)
            return None

    async def _segunda_chance(self, company_id: str, linha: Dict[str, Any],
                              motivo: str, direto: str) -> bool:
        """`True` = NÃO passar agora (a linha do diário foi gravada). Senão, pessoa."""
        conversa_id = str(linha.get("id") or "").strip()
        if direto or not conversa_id:
            return False
        if await self._ja_teve_segunda_chance(company_id, conversa_id) is not False:
            return False
        dito = _motivo_em_portugues(motivo) or MOTIVO_SEM_DECLARACAO
        # constante_justificada (classe/ação): o que a segunda chance FAZ é devolver a
        # conversa ao segurado — perguntar o dado que falta ou responder a dúvida. A
        # próxima fala do turno é ao segurado; `nao_agiu` é da SOMBRA (nada saiu) e
        # `chamou_pessoa` seria falso.
        diario_id = await self._registrar_no_diario(
            company_id, linha, motivo=motivo, acao="perguntou_segurado",
            classe="perguntar_ao_segurado", chave=_chave_da_segunda_chance(conversa_id),
            explicacao=("O agente ia chamar uma pessoa da corretora (motivo dele: "
                        "\"%s\"). Como não era um caso que precisa de pessoa, ele "
                        "voltou a conversar com o segurado para resolver: perguntar o "
                        "que falta ou responder a dúvida. Se chamar de novo, a pessoa "
                        "é chamada." % dito[:200]))
        return bool(diario_id)

    async def _registrar_chamou_pessoa(self, company_id: str, linha: Dict[str, Any],
                                       motivo: str, direto: str) -> None:
        """A passagem a pessoa vira linha no diário — best-effort, depois da decisão."""
        conversa_id = str(linha.get("id") or "").strip()
        if not conversa_id:
            return
        dito = _motivo_em_portugues(motivo) or MOTIVO_SEM_DECLARACAO
        if direto:
            # constante_justificada: caso que SEMPRE vai a pessoa = a classe do NUNCA
            # sozinho do contrato (o agente não decide isso sem gente).
            classe = "nunca_sozinho"
            explicacao = ("O agente chamou uma pessoa da corretora (motivo dele: \"%s\") "
                          "porque %s." % (dito[:200], direto))
        else:
            # constante_justificada: a 2ª chamada de um caso de "dúvida/dado" — a classe
            # que se tentou (perguntar ao segurado) e não bastou.
            classe = "perguntar_ao_segurado"
            explicacao = ("O agente chamou uma pessoa da corretora (motivo dele: \"%s\"). "
                          "Ele já tinha voltado a falar com o segurado antes e não achou "
                          "saída sem ajuda." % dito[:200])
        await self._registrar_no_diario(
            company_id, linha, motivo=motivo, acao="chamou_pessoa", classe=classe,
            chave=_chave_de_chamou_pessoa(conversa_id, motivo), explicacao=explicacao)

    # ------------------------------------------------------------------ #
    # execução
    # ------------------------------------------------------------------ #
    async def _arun(self, reason: Optional[str] = None, session_id: Optional[str] = None,
                    company_id: Optional[str] = None, codigo: Optional[str] = None,
                    **kwargs) -> str:
        # 🔴 SPEC-121 · conserto único (B1) — a marca `[antes_de_acionar:<codigo>]`
        #    sai do texto ANTES de tudo: a Fila, o grupo e o log leem português.
        codigo_no_texto, reason = marca_no_motivo(reason)
        motivo = str(reason or "").strip()
        # 🔴 FORA DO `try` — o rastro da falha precisa do motivo mesmo quando a
        #    marcação da conversa estoura antes de calculá-lo.
        motivo_humano = _motivo_em_portugues(motivo)
        logger.info("[HumanHandoff] 🔔 pedido | empresa=%s | sessao=%s | motivo=%s",
                    company_id, session_id, motivo)

        if not session_id or not company_id:
            # Antes isto devolvia "Erro interno" e seguia. Agora é explícito:
            # não dá para transferir uma conversa que não sabemos qual é.
            logger.error("[HumanHandoff] faltou %s",
                         "session_id" if not session_id else "company_id")
            return FALHA_DO_HANDOFF.format(motivo="sessao ou empresa ausente na chamada")

        if not self.supabase_client:
            logger.error("[HumanHandoff] supabase_client não configurado")
            return FALHA_DO_HANDOFF.format(motivo="banco indisponivel")

        # 1) marcar a conversa — SEMPRE com company_id (CLAUDE.md §7)
        conversa: Optional[Dict[str, Any]] = None
        # 🔴 O ESTADO DE ANTES, LIDO ANTES — 19/08/2026.
        #
        # O `update` abaixo devolve a linha JÁ ATUALIZADA, então depois dele
        # toda conversa parece ter acabado de virar `HUMAN_REQUESTED`. Sem
        # esta leitura não há como distinguir "primeiro pedido" de "o cliente
        # escreveu de novo numa conversa que já está com a equipe" — e foi
        # essa indistinção que encheu o grupo de alertas repetidos.
        ja_estava_com_a_equipe = False
        # ⚠️ Iniciada FORA do `try`: se a leitura falha, `linha_anterior` não
        #    pode ficar sem nome (o `_e_pos_acionamento` abaixo a usa) — e a
        #    ficha NÃO é reescrita a partir de uma leitura que não houve.
        linha_anterior: Dict[str, Any] = {}
        leu_o_estado = False
        try:
            def _estado_anterior():
                # 🔴 SPEC-097.1 U2.2/U2.3 — a leitura passou a trazer a FICHA e
                # a última mensagem. ⚠️ Não é curiosidade: sem elas não há como
                # saber que o caso já foi acionado, e é isso que decide o
                # `human_handoff_reason` padrão e a marca `agente_concluiu`.
                return (self.supabase_client.table("conversations")
                        .select("id, status, ficha_atendimento, "
                                "last_message_preview, human_handoff_reason")
                        .eq("company_id", company_id)
                        .eq("session_id", session_id)
                        .limit(1).execute())

            antes = await asyncio.to_thread(_estado_anterior)
            linha_anterior = (antes.data or [{}])[0] or {}
            leu_o_estado = bool(antes.data)
            ja_estava_com_a_equipe = bool(
                (antes.data or []) and
                str(linha_anterior.get("status") or "") == "HUMAN_REQUESTED")
        except Exception as exc:  # noqa: BLE001
            # Não sabemos o estado anterior. Trata como PRIMEIRO pedido: o
            # caminho que avisa. Falhar para o lado de avisar demais.
            logger.warning("[HumanHandoff] não li o estado anterior (%s) — "
                           "vou tratar como primeiro pedido", type(exc).__name__)

        # 🔴 SPEC-121 · conserto único (B1) — a MARCA do pedido, apurada UMA vez,
        #    ANTES de marcar a conversa: ela decide o tipo do aviso, o
        #    `motivo_enum` da sombra e fica gravada na ficha para o vigia.
        codigo_do_pedido_atual = pedido_antes_de_acionar(
            linha_anterior, codigo_no_texto or codigo)

        # 🔴 SPEC-123 F7 · D8 — A SEGUNDA CHANCE, ANTES DE MARCAR QUALQUER COISA.
        #    ⛔ Só com o estado LIDO: sem ele não há conversa para contar, e o caminho
        #    é o de antes (pessoa). Na segunda chance NADA é escrito na conversa, nada
        #    vai ao grupo e nenhuma vez é reservada no Redis — só a linha do diário.
        direto = ""
        if leu_o_estado:
            try:
                # 🔴 conserto único (juiz B3 · red team B6): a decisão lê o que o
                #    SEGURADO disse — uma CÓPIA da linha com as falas penduradas.
                caso_com_as_falas = dict(linha_anterior)
                falas = await self._falas_do_segurado_no_banco(linha_anterior)
                if falas:
                    caso_com_as_falas["mensagens"] = falas
                direto = por_que_vai_direto_a_pessoa(
                    motivo, codigo=codigo_do_pedido_atual, caso=caso_com_as_falas,
                    ja_com_a_equipe=ja_estava_com_a_equipe)
                if await self._segunda_chance(company_id, linha_anterior, motivo, direto):
                    logger.info("[HumanHandoff] segunda chance | empresa=%s | conversa=%s",
                                company_id, str(linha_anterior.get("id") or "")[:8])
                    return SEGUNDA_CHANCE_DO_HANDOFF
            except Exception as exc:  # noqa: BLE001
                # ⛔ A segunda chance nunca derruba o pedido: falhou → pessoa, como antes.
                logger.warning("[HumanHandoff] segunda chance indisponível (%s)",
                               type(exc).__name__)

        try:
            dados: Dict[str, Any] = {"status": "HUMAN_REQUESTED"}

            # 🔴 SPEC-097.1 U2.2/E19 — O MOTIVO NUNCA VAI VAZIO NUM CASO
            # ACIONADO.
            #
            # 📊 Medido em 05/09/2026: `human_handoff_reason` é NULL em
            # **725 de 729** conversas. A causa não é falta de escritor — é o
            # `if motivo:` desta linha: o agente chama a tool sem motivo, e o
            # campo nunca é escrito. A atendente abre a Fila e vê "precisa de
            # você" sem uma palavra sobre POR QUÊ.
            #
            # ⚠️ O motivo EXPLÍCITO continua vencendo sempre: o padrão só
            # preenche o silêncio.
            motivo_gravado = motivo_humano
            if not motivo_gravado and _e_pos_acionamento(linha_anterior):
                try:
                    from app.atendimento.pos_acionamento import classificar_turno

                    rotulo = classificar_turno(
                        [str(linha_anterior.get("last_message_preview") or "")])
                except Exception as exc:  # noqa: BLE001
                    logger.warning("[HumanHandoff] rótulo do turno indisponível "
                                   "(%s)", type(exc).__name__)
                    rotulo = "N"
                motivo_gravado = "pos_acionamento:%s" % rotulo

            # 🔴 O TERCEIRO DEGRAU — 09/09/2026, e é ele que fechou o NULL.
            #
            # 📊 As 5 conversas do piloto da AutoFleet eram sinistros NOVOS:
            # `_e_pos_acionamento` devolvia `False`, o modelo chamou a tool sem
            # `reason`, e o `if motivo_gravado:` abaixo não escrevia nada. 4 de 5
            # ficaram com `human_handoff_reason` NULL **depois** do conserto da
            # 097.1, porque aquele conserto só cobria o pós-acionamento.
            #
            # ⚠️ Um "não sei" ESCRITO vale mais que um NULL: a atendente lê que
            # o robô pediu ajuda e não declarou o motivo — que é a verdade — em
            # vez de olhar um campo vazio e não saber se é falta de motivo ou
            # falta de escritor. E é isso que faz o campo virar medida: NULL
            # agora significa "esta linha é anterior a 09/09", nada mais.
            if not motivo_gravado:
                motivo_gravado = MOTIVO_SEM_DECLARACAO
            dados["human_handoff_reason"] = motivo_gravado

            # 🔴 SPEC-097.1 U2.3 — A PARTE DO AGENTE TERMINOU AQUI.
            #
            # 🧑 Decisão do Founder (05/09): *"entregar para o humano é um
            # status em que o agente não tem mais o que fazer"*. O turno conta
            # como resolvido pelo AutoBrokers; o CASO segue aberto na Fila da
            # corretora até alguém encerrar.
            #
            # ⛔ E é por isso que `resolvido_em` NÃO é tocado: aquele campo é o
            # desfecho da CORRETORA. Escrevê-lo aqui faria a Fila esconder um
            # caso que ninguém atendeu ainda.
            if _e_pos_acionamento(linha_anterior):
                from datetime import datetime, timezone

                ficha_atual = linha_anterior.get("ficha_atendimento")
                ficha_nova = dict(ficha_atual) if isinstance(ficha_atual, dict) else {}
                ficha_nova["agente_concluiu"] = {
                    "em": datetime.now(timezone.utc).isoformat(),
                    "motivo": motivo_gravado or "pos_acionamento:N",
                }
                dados["ficha_atendimento"] = ficha_nova

            # 🔴 SPEC-121 · conserto único (B1) — a marca vai para a ficha: é ela
            #    que o aviso TARDIO do vigia lê (ele não passa por aqui). ⚠️ Uma
            #    marca velha é APAGADA quando este pedido não tem marca — senão o
            #    carro reserva de ontem rebaixaria o sinistro de hoje. ⛔ Só com a
            #    ficha LIDA: reescrevê-la de uma leitura que falhou a apagaria.
            _ficha_lida = linha_anterior.get("ficha_atendimento")
            if leu_o_estado and (codigo_do_pedido_atual or (
                    isinstance(_ficha_lida, dict) and CHAVE_DO_PEDIDO in _ficha_lida)):
                from datetime import datetime, timezone

                ficha_nova = dict(dados.get("ficha_atendimento") or (
                    _ficha_lida if isinstance(_ficha_lida, dict) else {}))
                ficha_nova[CHAVE_DO_PEDIDO] = {
                    "codigo": codigo_do_pedido_atual,
                    "em": datetime.now(timezone.utc).isoformat()}
                dados["ficha_atendimento"] = ficha_nova

            # 🔴 EM THREAD — 18/08/2026, junto com o conserto do `exige_async`.
            #
            # Até hoje esta tool NUNCA rodava por `_arun` (o executor a mandava
            # para `_run`, que estourava), então o I/O síncrono aqui dentro
            # nunca chegou a tocar o event loop. Consertar o despacho SEM
            # consertar isto trocaria "handoff não funciona" por "handoff
            # congela o FastAPI inteiro por alguns segundos" — todas as
            # conversas de todas as corretoras paradas junto.
            #
            # O cliente do Supabase é síncrono; `to_thread` é o que existe.
            def _marcar():
                return (self.supabase_client.table("conversations")
                        .update(dados)
                        .eq("company_id", company_id)
                        .eq("session_id", session_id)
                        .execute())

            res = await asyncio.to_thread(_marcar)
            if res.data:
                conversa = res.data[0]
        except Exception as exc:  # noqa: BLE001
            logger.error("[HumanHandoff] falha ao marcar a conversa (%s)", type(exc).__name__)

        if not conversa:
            # A conversa não foi marcada. Antes, esta linha devolvia
            # "Um atendente foi solicitado." — promessa sobre algo que não
            # aconteceu, e ninguém no sistema ficava sabendo.
            logger.error("[HumanHandoff] ❌ conversa não encontrada/atualizada | "
                         "empresa=%s | sessao=%s — NADA foi prometido ao cliente",
                         company_id, session_id)
            # 🔴 Esta falha também deixa linha. Ela é MAIS grave que a de
            #    destino ausente — aqui a conversa nem aparece na Fila.
            await registrar_o_desfecho_do_handoff(
                company_id, EVENTO_HANDOFF_FALHOU,
                "a conversa do pedido não foi encontrada para marcar")
            return FALHA_DO_HANDOFF.format(motivo="conversa nao encontrada para marcar")

        # 2) avisar o humano de verdade — UMA vez por conversa, não por turno
        #
        # A reserva vem antes do envio e é atômica. Três desfechos:
        #
        #   reserva livre                    → avisa (e a reserva fica de pé)
        #   reservada + já era da equipe     → CALA. A equipe já sabe.
        #   reservada + conversa voltou      → avisa. É pedido novo.
        #
        # O terceiro caso é o que impede a trava de virar mordaça: se a equipe
        # resolveu, a conversa saiu de `HUMAN_REQUESTED`, e um pedido novo
        # merece um alerta novo mesmo dentro da janela.
        horas = _env_int("HANDOFF_REALERTA_HORAS", HORAS_ENTRE_AVISOS_PADRAO)
        conversa_id = str(conversa.get("id") or session_id)

        # 🔴 SPEC-123 F7 · D8 — a passagem a pessoa vira UMA linha no diário
        #    (idempotente por conversa + motivo + dia). ⛔ Best-effort: nunca muda o
        #    que é marcado, enviado ou devolvido ao agente.
        if leu_o_estado:
            try:
                await self._registrar_chamou_pessoa(
                    company_id, {**linha_anterior, "id": conversa.get("id") or
                                 linha_anterior.get("id")}, motivo, direto)
            except Exception as exc:  # noqa: BLE001
                logger.warning("[HumanHandoff] diário da passagem não gravado (%s)",
                               type(exc).__name__)

        # 🔴 SPEC-093-B BLOCO B — o robô entregou o atendimento a uma pessoa.
        #
        # ⚠️ Evento OPCIONAL por medição, não por preguiça: 📊 03/09/2026,
        # `tools_config.human_handoff.enabled` está false ou AUSENTE nos 8 agentes
        # — esta tool nunca esteve ligada em lugar nenhum, e os zeros do handoff
        # (§1.3) são "nunca esteve ligada", não "nunca precisou". Quando ela for
        # ligada, o rastro já existe.
        #
        # ⛔ `motivo` é TEXTO LIVRE do modelo e NUNCA entra no payload: o que fica
        # gravado é o enum de duas casas.
        #
        # 🔴 E ELE NÃO É O RASTRO DO HANDOFF — medido em 09/09/2026.
        #
        # 📊 5 pedidos na AutoFleet, **0** linhas `work_events` com `claims.%`.
        # A causa não é este `try`: `registrar_evento` sai por
        # `if not run_id: return False` quando a conversa não tem sombra de
        # sinistro (`work_events.work_run_id` é NOT NULL com FK para
        # `work_runs`), e as 5 conversas não tinham. Nenhuma exceção foi
        # levantada — logo nada foi engolido aqui.
        #
        # ⚠️ Ele CONTINUA, porque quando a sombra existe ele é o único que
        # coloca o handoff na linha do tempo do sinistro. O rastro que vale
        # para TODA corretora é o `registrar_o_desfecho_do_handoff` lá embaixo.
        try:
            # 🔴 O MESMO detector do BLOCO A, e não um regex novo aqui: dois
            # classificadores para a mesma pergunta são dois classificadores para
            # manter, e o segundo envelhece calado (CLAUDE.md §5).
            from app.services.claims_shadow import registrar_gesto
            from app.services.o_grupo_so_o_que_importa import TIPO_SINISTRO

            # 🔴 SPEC-121 · conserto único (B1): a MESMA decisão do aviso
            #    (`tipo_do_pedido`) — a marca vence a palavra aqui também.
            _motivo_enum = ("sinistro" if tipo_do_pedido(codigo_do_pedido_atual, motivo)
                            == TIPO_SINISTRO else "outro")
            await registrar_gesto(
                self.supabase_client, company_id=str(company_id),
                conversation_id=conversa_id,
                event_type="claims.handoff_pedido",
                payload={"motivo_enum": _motivo_enum},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[SOMBRA] handoff não registrado (%s)", type(exc).__name__)
        avisado_ha_pouco = await reivindicar_o_aviso(
            conversa_id, horas, company_id=str(company_id))

        if avisado_ha_pouco and ja_estava_com_a_equipe:
            logger.info("[HumanHandoff] conversa %s JÁ estava com a equipe e já "
                        "foi avisada — não repeti o alerta", conversa_id[:8])
            return JA_ESTAVA_COM_A_EQUIPE

        # 🔴 SPEC-121 F1 — este é o pedido do AGENTE, e ele diz isso à porta.
        from app.services.o_grupo_so_o_que_importa import PROVA_PEDIDO_DO_AGENTE

        aviso = await self._avisar_suporte(company_id, conversa, motivo,
                                           prova=PROVA_PEDIDO_DO_AGENTE,
                                           pedido=codigo_do_pedido_atual)

        if aviso["avisado"]:
            await registrar_o_desfecho_do_handoff(
                company_id, EVENTO_HANDOFF_ENTREGUE, motivo_humano, conversa_id)
            return SUCESSO_DO_HANDOFF

        # Reservou e não avisou: devolve a vez, senão o Vigia fica mudo pelas
        # horas inteiras do marcador justamente no caso em que ninguém soube.
        await devolver_a_vez(conversa_id, company_id=str(company_id))

        # Marcou mas não avisou: a conversa aparece na Fila do painel, então
        # alguém PODE ver — só não foi empurrado. A resposta diz a verdade sem
        # jogar o problema interno no colo do segurado.
        # 🔴 Isto ERA "Registrei seu pedido e ele já está na fila da equipe".
        # Tecnicamente verdadeiro — a conversa entra na Fila do painel. Mas
        # depois de o modelo reescrever no tom da atendente, "já está na fila da
        # equipe" e "já passei para a equipe" viram a mesma frase no ouvido do
        # segurado. Retorno que o modelo consegue confundir com sucesso é o
        # mesmo defeito com outra roupa.
        logger.error("[HumanHandoff] ⚠️ conversa marcada mas SUPORTE NÃO AVISADO | "
                     "empresa=%s | motivo=%s", company_id, aviso["motivo"])
        # 🔴 A LINHA QUE FALTAVA — 09/09/2026.
        #
        # 📊 As 5 falhas do piloto morreram no `logger.error` acima. O log do
        # contêiner some no deploy seguinte, e de fora ninguém tinha como
        # perguntar "quantas vezes o robô pediu ajuda e ninguém recebeu?".
        # Agora a pergunta tem resposta em SQL, e a corretora vê a linha no
        # feed de Atividades no mesmo dia.
        await registrar_o_desfecho_do_handoff(
            company_id, EVENTO_HANDOFF_FALHOU,
            aviso["motivo"] or "motivo desconhecido", conversa_id)
        return FALHA_DO_HANDOFF.format(motivo=aviso["motivo"] or "desconhecido")

    def _run(self, reason: Optional[str] = None, session_id: Optional[str] = None,
             company_id: Optional[str] = None, **kwargs) -> str:
        """Caminho síncrono desativado.

        Avisar o suporte exige I/O assíncrono (resolver destino + enviar). Uma
        versão síncrona que só marcasse a conversa seria exatamente o defeito
        que esta correção desfez: parece que funcionou, e ninguém é avisado.
        """
        # 🔴 A frase "o tool_node já força _arun" ficou aqui por meses SEM
        # SER VERDADE — era um invariante escrito em comentário e nunca
        # implementado. Agora é `exige_async` lá em cima, que o executor lê.
        # O texto do erro mudou junto: se alguém chegar aqui de novo, a
        # mensagem tem de dizer o que fazer, não repetir a promessa quebrada.
        raise RuntimeError(
            "HumanHandoffTool exige execução assíncrona (_arun). Quem chamou "
            "ignorou `exige_async=True` — o executor precisa aguardar `_arun`."
        )

    def _com_a_ficha(self, company_id: str, conversa: Dict[str, Any]) -> Dict[str, Any]:
        """A linha do chamador com a `ficha_atendimento` lida — CÓPIA; a mesma
        linha no escuro. 🔴 §7: por `company_id` e `id`. ⛔ Nunca levanta."""
        caso = dict(conversa or {})
        ident = str(caso.get("id") or "").strip()
        if not ident or not str(company_id or "").strip() or self.supabase_client is None:
            return caso
        try:
            achado = (self.supabase_client.table("conversations")
                      .select("id, ficha_atendimento")
                      .eq("company_id", str(company_id))
                      .eq("id", ident)
                      .limit(1).execute())
            linha = (getattr(achado, "data", None) or [{}])[0] or {}
            if isinstance(linha.get("ficha_atendimento"), dict):
                caso["ficha_atendimento"] = linha["ficha_atendimento"]
        except Exception as exc:  # noqa: BLE001
            logger.warning("[HumanHandoff] ficha não lida para o aviso (%s)",
                           type(exc).__name__)
        return caso
