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
_CHAVE_DO_MARCADOR = "handoff_realerta:{}"
HORAS_ENTRE_AVISOS_PADRAO = 6


def _env_int(nome: str, padrao: int, minimo: int = 1) -> int:
    try:
        return max(minimo, int(os.getenv(nome, str(padrao))))
    except (TypeError, ValueError):
        return padrao


async def reivindicar_o_aviso(conversa_id: str, horas: int) -> bool:
    """Alguém já avisou o grupo sobre esta conversa nas últimas `horas`?

    `True` = já avisaram, **fique quieto**. `False` = a vez é sua, e este
    retorno JÁ RESERVOU o direito — é teste-e-marca atômico (`nx=True`), para
    que dois workers na mesma passada não avisem em dobro.

    🔴 Redis fora do ar devolve `False`: **avisar demais é melhor que calar.**
    O defeito grave é o silêncio; a repetição é só incômodo.
    """
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        gravou = await r.set(_CHAVE_DO_MARCADOR.format(conversa_id), "1",
                             ex=max(1, int(horas)) * 3600, nx=True)
        return not gravou
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Handoff] marcador indisponível (%s) — vai avisar",
                       type(exc).__name__)
        return False


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


async def devolver_a_vez(conversa_id: str) -> None:
    """Libera o marcador. Chamado quando o aviso RESERVADO não saiu.

    🔴 Sem isto, uma falha de envio silenciaria o grupo pelas horas inteiras
    do marcador: quem reservou não avisou, e ninguém mais pode. Reserva que
    não virou aviso tem de ser devolvida — é o mesmo princípio de "flag que
    mente é pior que flag ausente", aplicado a uma reserva.
    """
    try:
        from app.core.redis import get_async_redis_client

        r = await get_async_redis_client()
        await r.delete(_CHAVE_DO_MARCADOR.format(conversa_id))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Handoff] não consegui devolver o marcador (%s)",
                       type(exc).__name__)

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
    texto = _texto_do_caso(conversa, motivo)
    for chave, (emoji, nome) in _TITULOS.items():
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

    texto = _texto_do_caso(conversa, motivo)
    if "sinistro" in texto:
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


def _linha_da_conversa(m: Dict[str, Any]) -> str:
    """Uma linha da conversa, com hora e AUTOR DE VERDADE.

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
        autor = f"👤 {str(payload.get('autor') or 'atendente')}"
    elif origem == "espelho":
        autor = "👤 celular"
    else:
        autor = "🤖 IA"

    texto = str(m.get("content") or "").strip().replace("\n", " ")
    return f"{hora} {autor}  {texto[:160]}"


def _link_da_conversa(conversa: Dict[str, Any]) -> str:
    """O link direto. Sem ele, ela procura na lista — no celular, com o
    cliente esperando."""
    import os as _os

    base = (_os.getenv("FRONTEND_URL") or _os.getenv("APP_BASE_URL") or "").rstrip("/")
    ident = str(conversa.get("id") or "").strip()
    if not base or not ident:
        return ""
    return f"{base}/dashboard/atendimentos/conversas?c={ident}"


def _quem_assumiu(conversa: Dict[str, Any]) -> str:
    """Evita que duas atendentes corram para a mesma conversa."""
    nome = str(conversa.get("claimed_by_name") or "").strip()
    return f"_{nome} já assumiu_" if nome else "_Ninguém assumiu ainda_"


class HumanHandoffInput(BaseModel):
    """Input schema para a HumanHandoffTool."""

    reason: Optional[str] = Field(
        default=None,
        description="Motivo da transferência. Exemplo: 'sinistro — exige humano', "
        "'risco grave', 'cliente pediu pessoa', 'não há corredor para esta seguradora'.",
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
    para acionar a seguradora, em risco grave, quando o cliente pedir pessoa, ou
    quando você travar. Informe o motivo.
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

        # O QUE ACONTECEU — narrativa, não campos soltos.
        narrativa = _narrativa(conversa, motivo)
        if narrativa:
            linhas += ["", "*O QUE ACONTECEU*", narrativa]

        # O QUE FALTA — some quando não falta nada. Seção vazia é ruído.
        falta = _o_que_falta(conversa)
        if falta:
            linhas += ["", "*O QUE FALTA*"] + [f"⚠️ {f}" for f in falta]

        # O QUE FAZER — a primeira coisa que ela lê de verdade.
        linhas += ["", "*👉 O QUE FAZER*", _o_que_fazer(conversa, motivo)]

        # A CONVERSA — com autor de verdade.
        linhas += ["", _TRACO]
        try:
            msgs = (self.supabase_client.table("messages")
                    .select("role, content, created_at, payload")
                    .eq("conversation_id", conversa["id"])
                    .order("created_at", desc=True)
                    .limit(_MSGS_NO_DOSSIE).execute().data or [])
            if msgs:
                linhas.append(f"*CONVERSA* _(últimas {len(msgs)})_")
                for m in reversed(msgs):
                    linhas.append(_linha_da_conversa(m))
        except Exception as exc:  # noqa: BLE001
            # Dossiê sem histórico continua melhor que silêncio — mas quem lê
            # precisa saber que está entrando às cegas.
            logger.warning("[HumanHandoff] histórico indisponível (%s)", type(exc).__name__)
            linhas.append("_(não consegui carregar o histórico — você entra sem ele)_")

        # O LINK e o estado. `claimed_by_name` existe justamente para evitar
        # que duas atendentes corram para a mesma conversa.
        linhas += [_TRACO]
        link = _link_da_conversa(conversa)
        if link:
            linhas.append(f"▶ {link}")
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
        if protocolo:
            linhas.append("Acionamento já entregue · protocolo com o cliente")

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

        linhas += ["", _TRACO]
        try:
            # 🔴 §7 (red team 097.1 [7]): `messages` não tem `company_id` — a corretora
            #    é conferida na CONVERSA (lida com `.eq("company_id")` em `_arun`) antes
            #    desta leitura; conversa sem corretora não tem transcrição no dossiê.
            if not str(conversa.get("company_id") or "").strip():
                raise PermissionError("conversa sem corretora: a transcrição não entra")
            msgs = (self.supabase_client.table("messages")
                    .select("role, content, created_at, payload")
                    .eq("conversation_id", conversa["id"])
                    .order("created_at", desc=True)
                    .limit(_MSGS_NO_DOSSIE).execute().data or [])
            if msgs:
                linhas.append(f"*CONVERSA* _(últimas {len(msgs)})_")
                for m in reversed(msgs):
                    linhas.append(_linha_da_conversa(m))
        except Exception as exc:  # noqa: BLE001
            logger.warning("[HumanHandoff] histórico indisponível (%s)", type(exc).__name__)
            linhas.append("_(não consegui carregar o histórico — você entra sem ele)_")

        linhas += [_TRACO]
        link = _link_da_conversa(conversa)
        if link:
            linhas.append(f"▶ {link}")
        linhas.append(_quem_assumiu(conversa))
        return "\n".join(linhas)

    async def _avisar_suporte(self, company_id: str, conversa: Dict[str, Any],
                              motivo: str) -> Dict[str, Any]:
        """Envia o dossiê. Devolve o que aconteceu — sem arredondar."""
        from app.services.dispatch_router import resolver_destino_de_suporte

        alvo = await resolver_destino_de_suporte(company_id)
        if alvo.get("recusa"):
            return {"avisado": False, "motivo": alvo["recusa"]}
        destino = alvo.get("destino") or ""
        if not destino:
            return {"avisado": False,
                    "motivo": "a corretora não tem destino de suporte humano configurado"}

        try:
            from app.services.integration_service import get_integration_service
            from app.services.whatsapp_service import get_whatsapp_service

            integ = await asyncio.to_thread(
                get_integration_service(self.supabase_client).get_whatsapp_integration,
                company_id)
            if not integ:
                return {"avisado": False,
                        "motivo": "a corretora não tem canal de WhatsApp conectado para avisar"}

            # 🔴 `bloco_unico=True` -- o dossie e DOCUMENTO, nao conversa.
            # Sem isto ele passava pela humanizacao da atendente e chegava
            # picotado em cinco baloes (grupo TESTE SUPORTE HUMANO, 18/08).
            #
            # 🔴 E em THREAD: `_montar_dossie` lê `messages` do Supabase e
            # `send_message` faz HTTP, os dois síncronos. Direto no event loop
            # isso trava o FastAPI por alguns segundos a cada transferência.
            def _montar_e_enviar():
                get_whatsapp_service().send_message(
                    destino, self._montar_dossie(conversa, motivo), integ,
                    bloco_unico=True)

            await asyncio.to_thread(_montar_e_enviar)
            logger.info("[HumanHandoff] dossiê enviado | empresa=%s | fonte=%s",
                        company_id, alvo.get("fonte"))
            return {"avisado": True, "motivo": ""}
        except Exception as exc:  # noqa: BLE001
            logger.error("[HumanHandoff] falha ao avisar o suporte (%s)", type(exc).__name__)
            return {"avisado": False, "motivo": f"falha no envio ({type(exc).__name__})"}

    # ------------------------------------------------------------------ #
    # execução
    # ------------------------------------------------------------------ #
    async def _arun(self, reason: Optional[str] = None, session_id: Optional[str] = None,
                    company_id: Optional[str] = None, **kwargs) -> str:
        motivo = str(reason or "").strip()
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
            ja_estava_com_a_equipe = bool(
                (antes.data or []) and
                str(linha_anterior.get("status") or "") == "HUMAN_REQUESTED")
        except Exception as exc:  # noqa: BLE001
            # Não sabemos o estado anterior. Trata como PRIMEIRO pedido: o
            # caminho que avisa. Falhar para o lado de avisar demais.
            logger.warning("[HumanHandoff] não li o estado anterior (%s) — "
                           "vou tratar como primeiro pedido", type(exc).__name__)

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
            motivo_gravado = motivo
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
            if motivo_gravado:
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
        try:
            # 🔴 O MESMO detector do BLOCO A, e não um regex novo aqui: dois
            # classificadores para a mesma pergunta são dois classificadores para
            # manter, e o segundo envelhece calado (CLAUDE.md §5).
            from app.services.claims_shadow import detectar_sinistro, registrar_gesto

            _motivo_enum = "sinistro" if detectar_sinistro(motivo)[0] else "outro"
            await registrar_gesto(
                self.supabase_client, company_id=str(company_id),
                conversation_id=conversa_id,
                event_type="claims.handoff_pedido",
                payload={"motivo_enum": _motivo_enum},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[SOMBRA] handoff não registrado (%s)", type(exc).__name__)
        avisado_ha_pouco = await reivindicar_o_aviso(conversa_id, horas)

        if avisado_ha_pouco and ja_estava_com_a_equipe:
            logger.info("[HumanHandoff] conversa %s JÁ estava com a equipe e já "
                        "foi avisada — não repeti o alerta", conversa_id[:8])
            return JA_ESTAVA_COM_A_EQUIPE

        aviso = await self._avisar_suporte(company_id, conversa, motivo)

        if aviso["avisado"]:
            return SUCESSO_DO_HANDOFF

        # Reservou e não avisou: devolve a vez, senão o Vigia fica mudo pelas
        # horas inteiras do marcador justamente no caso em que ninguém soube.
        await devolver_a_vez(conversa_id)

        # Marcou mas não avisou: a conversa aparece na Fila do painel, então
        # alguém PODE ver — só não foi empurrado. A resposta diz a verdade sem
        # jogar o problema interno no colo do segurado.
        # 🔴 Isto ERA "Registrei seu pedido e ele já está na fila da equipe".
        # Tecnicamente verdadeiro — a conversa entra na Fila do painel. Mas
        # depois de o modelo reescrever no tom da Saionara, "já está na fila da
        # equipe" e "já passei para a equipe" viram a mesma frase no ouvido do
        # segurado. Retorno que o modelo consegue confundir com sucesso é o
        # mesmo defeito com outra roupa.
        logger.error("[HumanHandoff] ⚠️ conversa marcada mas SUPORTE NÃO AVISADO | "
                     "empresa=%s | motivo=%s", company_id, aviso["motivo"])
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
