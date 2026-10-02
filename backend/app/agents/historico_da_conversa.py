# -*- coding: utf-8 -*-
"""A conversa INTEIRA do atendimento em aberto — de UMA fonte só. SPEC-125 · S2 · D1.

> Ordem do Founder (01/10/2026): *"lembrar de 3 ou 5 trocas é um absurdo"* — se o
> atendimento tem 100 mensagens, as 100 ficam disponíveis, também para o destravador.

📊 **O que havia antes** (BLOCO 0 da SPEC-125, §3):

```
agent_node          as últimas 15 mensagens do CHECKPOINTER — e o SystemMessage de cada
                    turno (o prompt inteiro, ~26 mil tokens) ocupava uma das 15 vagas
langchain_service   lia 60 mensagens de `messages` e NINGUÉM as usava (código morto)
destravador         15 mensagens × 300 chars, de uma conversa escolhida SEM ordem
a equipe            o que a atendente disse ao segurado NUNCA chegava ao agente
```

🔴 **A fonte agora é `messages`** — a mesma tabela que o painel mostra, onde estão o
segurado, o agente e a EQUIPE (`payload.origem` em `ORIGENS_HUMANAS`). O recorte é o
do ASSUNTO, e o motor que diz onde ele começa é o que o produto JÁ usa
(`o_fim_do_atendimento`: a regra dos N dias de silêncio e o `resolvido_em`) — nenhuma
régua nova (CLAUDE.md §5).

📊 **O teto, medido** (SELECT de 01/10/2026, `messages` × `conversations` canal
whatsapp, assunto = corte por silêncio > 7 dias, tokens 💭 = chars/4):
1.432 assuntos em 1.081 conversas · p50 **174** · p90 **986** · p99 **4.846** ·
máx **15.924** tokens · **0** acima de 40 mil · **1** acima de 12 mil.

⛔ **Nunca levanta e nunca corta calado.** Acima do teto, o começo vira um RESUMO no
topo, que diz quantas mensagens resume e de quando a quando. Falhou a leitura, o
chamador fica com o que tinha (o checkpointer) — perder a memória por um soluço do
banco seria pior que o defeito que esta peça conserta.

🔴 **Multi-tenant (CLAUDE.md §7):** `messages` NÃO tem `company_id` — a cerca é o
`conversation_id`, e ele só é aceito se a conversa foi achada COM a corretora no
filtro E conferida no código. 📊 72 telefones existem em duas corretoras.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OS TETOS — todos por TOKENS, nenhum por contagem de mensagens
# ---------------------------------------------------------------------------

#: constante_justificada — o teto da conversa que o AGENTE DE ATENDIMENTO recebe.
#: 📊 p99 4.846 · máx 15.924 tokens por assunto (SELECT de 01/10/2026, acima): 40 mil
#: cobre 100 % dos assuntos medidos com folga de 2,5× sobre o maior. 💭 É ~1/3 de
#: uma janela de 128 mil — o prompt (~10 mil) e o RAG (≤ 15 mil) cabem ao lado.
TETO_DO_ATENDIMENTO_TOKENS = 40_000

#: constante_justificada — o teto do DESTRAVADOR (a 2ª opinião sobre a tela da URA
#: precisa do caso, não do papo inteiro, e roda com teto de relógio).
#: 📊 só 1 de 1.432 assuntos passa de 12 mil tokens; p99 4.846.
TETO_DO_DESTRAVADOR_TOKENS = 12_000

#: constante_justificada — o teto dos RESULTADOS DE FERRAMENTA que atravessam turnos
#: (apólice, acionamento, handoff). 💭 Um resultado de apólice do InfoCap tem
#: poucos milhares de chars; 12 mil tokens guardam vários deles. Acima, os MAIS
#: ANTIGOS ficam com o par (a chamada existiu) e o conteúdo vira uma linha que diz
#: que foi omitido — nunca somem calados.
TETO_DOS_RESULTADOS_TOKENS = 12_000

#: O teto da rede de segurança do `agent_node` (a conversa + os resultados que
#: atravessam turnos). Uma conta, não um número novo.
TETO_DA_CONVERSA_NO_MODELO_TOKENS = TETO_DO_ATENDIMENTO_TOKENS + TETO_DOS_RESULTADOS_TOKENS

#: Quanto do teto o RESUMO do começo pode ocupar quando a conversa não cabe.
FRACAO_DO_RESUMO = 0.15

#: Quantas páginas de `messages` se leem, no máximo, atrás do começo do assunto.
#: 📊 o maior assunto medido tem 1.648 mensagens; a página é a do PostgREST (1.000).
PAGINAS_MAXIMAS = 5

#: O nome que as falas da EQUIPE levam no histórico do modelo (campo `name` da
#: mensagem — a OpenAI o aceita no papel do assistente; os outros o ignoram e a
#: marca no texto basta).
NOME_DA_EQUIPE = "equipe_da_corretora"
MARCA_DA_EQUIPE = "[Fala de uma PESSOA da equipe da corretora — não foi você quem escreveu]"

#: A ferramenta cujo resultado ANTIGO é comprimido (SPEC-125 T2): o RAG se busca de
#: novo e já está refletido na resposta. Apólice, acionamento e handoff são FATOS
#: DO CASO — ficam inteiros enquanto o assunto durar.
FERRAMENTAS_COMPRIMIDAS = ("knowledge_base_search",)
CONTEUDO_COMPRIMIDO = ("[🔍 RAG: Conteúdo bruto removido para otimização. As informações "
                       "relevantes já constam na resposta anterior da Assistente.]")


def tokens(texto: Any) -> int:
    """≈ 4 caracteres por token — a MESMA régua de `evals.dubles.estimar_tokens` e
    do BLOCO 0. É estimativa: só decide teto; custo vem do `usage_metadata`."""
    return len(str(texto or "")) // 4


# ---------------------------------------------------------------------------
# O RESULTADO
# ---------------------------------------------------------------------------
@dataclass
class Fala:
    quem: str            # "segurado" · "agente" · "equipe"
    texto: str
    quando: Optional[datetime] = None


@dataclass
class Historico:
    falas: List[Fala] = field(default_factory=list)
    resumo: str = ""                       # o começo que não coube — nunca vazio quando algo ficou fora
    inicio: Optional[datetime] = None      # quando o assunto em aberto começou
    conversation_id: str = ""
    lida: bool = False                     # a conversa foi achada E lida (só então substitui o checkpointer)
    erro: str = ""

    @property
    def turnos_do_segurado(self) -> int:
        return sum(1 for f in self.falas if f.quem == "segurado")


# ---------------------------------------------------------------------------
# PURO — onde o assunto em aberto começa
# ---------------------------------------------------------------------------
def _ordenadas(linhas) -> List[Tuple[datetime, dict]]:
    from app.services.o_fim_do_atendimento import _quando

    pares = []
    for m in linhas or ():
        if isinstance(m, dict):
            q = _quando(m.get("created_at"))
            if q is not None:
                pares.append((q, m))
    pares.sort(key=lambda p: p[0])      # ⚠️ em Python: dublê e PostgREST nem sempre ordenam
    return pares


def inicio_do_assunto(pares: List[Tuple[datetime, dict]], *, n_dias: Optional[int] = None,
                      resolvido_em: Any = None) -> int:
    """O índice (em `pares`, já ordenados) da primeira linha do assunto em aberto. **PURA.**

    É a régua de `o_fim_do_atendimento.contexto_do_reencontro` e de
    `mensagens_vencidas`, aplicada a cada fala do segurado em vez de só à de agora:

    ```
    fala do segurado com a fala ANTERIOR (qualquer uma) há mais de N dias  → ASSUNTO NOVO
    fala do segurado com a última fala DA CORRETORA há mais de N dias     → ASSUNTO NOVO
                     (e as falas do segurado no meio do silêncio ficam fora: são as VENCIDAS)
    `resolvido_em` preenchido                                            → o que veio antes dele é
                                                                            o atendimento anterior
    ```
    ⚠️ N = 0 desliga a regra dos dias (a mesma convenção de `janela_de_silencio_dias`).
    ⛔ Só uma fala do SEGURADO abre assunto — é na fala dele que o produto decide.
    """
    from app.services.o_fim_do_atendimento import _e_da_corretora, _quando, janela_de_silencio_dias

    dias = janela_de_silencio_dias() if n_dias is None else int(n_dias)
    limite = dias * 86400
    inicio = 0
    anterior = None
    nossa = None
    for i, (q, m) in enumerate(pares):
        papel = str(m.get("role") or "").strip().lower()
        if papel == "user" and dias > 0:
            if (anterior is not None and (q - anterior).total_seconds() > limite) or \
               (nossa is not None and (q - nossa).total_seconds() > limite):
                inicio = i
                nossa = None             # o silêncio foi consumido: o assunto é outro
        if _e_da_corretora(m):
            nossa = q
        anterior = q
    fim = _quando(resolvido_em)
    if fim is not None:
        depois = next((i for i, (q, _m) in enumerate(pares) if q > fim), len(pares))
        inicio = max(inicio, depois)
    return inicio


def _quem(m: dict) -> str:
    from app.services.o_fim_do_atendimento import e_origem_humana

    papel = str(m.get("role") or "").strip().lower()
    if papel == "user":
        return "segurado"
    if papel == "assistant":
        return "equipe" if e_origem_humana(m) else "agente"
    return ""


def falas_do_assunto(linhas, *, texto_do_turno: str = "", turno_corrente: bool = True,
                     agora: Optional[datetime] = None, n_dias: Optional[int] = None,
                     resolvido_em: Any = None) -> Tuple[List[Fala], Optional[datetime]]:
    """As falas do assunto em aberto, a mais antiga primeiro, SEM a do turno de agora. **PURA.**

    ⛔ **A linha do turno de agora sai** (`turno_corrente=True`): o webhook a grava em
    `messages` ANTES de chamar o agente (passo 5 → passo 7), e ela já chega ao modelo
    como a HumanMessage do turno — duas vezes seria a rajada repetida. Sai só UMA linha,
    a última, e só se for do segurado: a de texto igual (ou que é o começo do texto do
    turno, quando a visão acrescenta a descrição), ou — se o texto foi mascarado pelo
    guardrail — a que nasceu dentro da folga do turno (`_TURNO_SEGUNDOS`, a do produto).
    ⛔ `#nota` interna não entra: o segurado nunca a leu, e o agente não pode repeti-la.
    """
    from app.services.o_fim_do_atendimento import _TURNO_SEGUNDOS, e_anotacao

    agora = agora or datetime.now(timezone.utc)
    pares = [(q, m) for q, m in _ordenadas(linhas) if not e_anotacao(m)]
    i0 = inicio_do_assunto(pares, n_dias=n_dias, resolvido_em=resolvido_em)
    do_assunto = pares[i0:]
    inicio = do_assunto[0][0] if do_assunto else None
    if turno_corrente and do_assunto:
        q, m = do_assunto[-1]
        if str(m.get("role") or "").strip().lower() == "user":
            linha = " ".join(str(m.get("content") or "").split())
            turno = " ".join(str(texto_do_turno or "").split())
            if (linha and turno and (linha == turno or turno.startswith(linha))) or \
               (agora - q).total_seconds() < _TURNO_SEGUNDOS:
                do_assunto = do_assunto[:-1]
    falas = []
    for q, m in do_assunto:
        quem = _quem(m)
        texto = str(m.get("content") or "").strip()
        if quem and texto:
            falas.append(Fala(quem=quem, texto=texto, quando=q))
    return falas, inicio


def _quando_curto(q: Optional[datetime]) -> str:
    return q.strftime("%d/%m %H:%M") if q else "?"


def caber_no_teto(falas: List[Fala], teto: int) -> Tuple[List[Fala], str]:
    """`(as que cabem inteiras, o resumo do começo)` — **PURA**. Nunca corta calado.

    Cabe tudo → `(falas, "")`. Não cabe → as MAIS NOVAS ficam inteiras e o começo
    vira um resumo EXTRATIVO (as próprias falas, aparadas, em ordem) que diz quantas
    mensagens resume e de quando a quando. 💭 Extrativo de propósito: sem modelo no
    caminho do turno (custo e relógio), e sem risco de o resumo inventar um dado.
    📊 Hoje NENHUM assunto medido passa de 40 mil tokens — este ramo é a rede.
    """
    teto = max(1, int(teto))
    total = sum(tokens(f.texto) for f in falas)
    if total <= teto:
        return list(falas), ""
    verba_resumo = int(teto * FRACAO_DO_RESUMO)
    verba = teto - verba_resumo
    mantidas: List[Fala] = []
    usado = 0
    for f in reversed(falas):
        t = tokens(f.texto)
        if usado + t > verba and mantidas:
            break
        mantidas.append(f)
        usado += t
    mantidas.reverse()
    fora = falas[:len(falas) - len(mantidas)]
    cab = (f"[RESUMO DO COMEÇO DESTE ATENDIMENTO — escrito pelo sistema, não é fala de ninguém] "
           f"{len(fora)} mensagens, de {_quando_curto(fora[0].quando)} a {_quando_curto(fora[-1].quando)}, "
           f"não cabem aqui inteiras. Em ordem, o começo de cada uma:")
    linhas = [cab]
    gasto = tokens(cab)
    listadas = 0
    for f in fora:
        rotulo = {"segurado": "segurado", "agente": "você", "equipe": "equipe"}.get(f.quem, f.quem)
        item = f"- [{rotulo}] {' '.join(f.texto.split())[:160]}"
        if gasto + tokens(item) > verba_resumo:
            break
        linhas.append(item)
        gasto += tokens(item)
        listadas += 1
    if listadas < len(fora):
        linhas.append(f"- … e mais {len(fora) - listadas} mensagens antigas não listadas.")
    return mantidas, "\n".join(linhas)


# ---------------------------------------------------------------------------
# A LEITURA — a conversa, achada COM a corretora
# ---------------------------------------------------------------------------
async def _achar_a_conversa(db, empresa: str, *, session_id: str = "", telefone: str = "") -> Optional[dict]:
    from app.services.o_fim_do_atendimento import _cliente, _executar, _quando

    consulta = (_cliente(db).table("conversations")
                .select("id, company_id, resolvido_em, updated_at, last_message_at")
                .eq("company_id", empresa))                      # 🔴 CLAUDE.md §7
    if session_id:
        consulta = consulta.eq("session_id", session_id)
    else:
        # 🔴 As 4 grafias (com e sem o 55, com e sem o 9) e o número cru — a régua ÚNICA
        #    de `quem_e_o_segurado.formas_do_telefone`. 📊 905 de 1.081 conversas guardam
        #    o número COM o 55, e `_variantes_do_telefone` sozinha o tira: o destravador
        #    não achava a conversa em ~84 % dos casos.
        from app.agents.quem_e_o_segurado import formas_do_telefone

        formas = formas_do_telefone(telefone)
        if not formas:
            return None
        consulta = consulta.eq("channel", "whatsapp").in_("user_phone", formas)
    achado = await _executar(consulta.order("updated_at", desc=True).limit(5))
    linhas = [x for x in (getattr(achado, "data", None) or [])
              if isinstance(x, dict) and str(x.get("company_id") or "") == empresa]   # cinto
    if not linhas:
        return None

    # 🔴 A MAIS RECENTE, decidida em Python: o `.order` vai ao banco, mas um dublê
    #    (ou um PostgREST mal configurado) pode ignorá-lo — e `linhas[0]` de uma lista
    #    sem ordem era exatamente o defeito do destravador (BLOCO 0 §3.5).
    def _recencia(c):
        return max([q for q in (_quando(c.get("last_message_at")), _quando(c.get("updated_at")))
                    if q is not None] or [datetime.min.replace(tzinfo=timezone.utc)])

    return max(linhas, key=_recencia)


async def _ler_mensagens(db, conversa: str) -> Tuple[List[dict], str]:
    """As linhas da conversa, em páginas, da mais nova para trás. `(linhas, erro)`."""
    from app.services.o_fim_do_atendimento import _LEITURA_LARGA_DA_JANELA, _cliente, _executar

    pagina = int(_LEITURA_LARGA_DA_JANELA)
    todas: List[dict] = []
    vistas = set()
    antes_de = None
    for _ in range(PAGINAS_MAXIMAS):
        q = (_cliente(db).table("messages")
             .select("id, conversation_id, role, content, created_at, payload")
             .eq("conversation_id", conversa))
        if antes_de:
            q = q.lt("created_at", antes_de)
        achado = await _executar(q.order("created_at", desc=True).limit(pagina))
        # 🔴 cinto (§7): a linha só entra se for DESTA conversa — que foi achada COM a corretora.
        lote = [m for m in (getattr(achado, "data", None) or []) if isinstance(m, dict)
                and str(m.get("conversation_id") or "") == conversa]
        novas = [m for m in lote if (m.get("id") or id(m)) not in vistas]
        for m in novas:
            vistas.add(m.get("id") or id(m))
        todas.extend(novas)
        # ⛔ página incompleta = acabou; página sem nada novo = o banco ignorou o cursor.
        if len(lote) < pagina or not novas:
            break
        datas = sorted(str(m.get("created_at") or "") for m in novas if m.get("created_at"))
        if not datas:
            break
        antes_de = datas[0]
    return todas, ""


async def historico_do_atendimento(db, *, company_id: str, session_id: str = "", telefone: str = "",
                                   texto_do_turno: str = "", turno_corrente: bool = True,
                                   teto_tokens: int = TETO_DO_ATENDIMENTO_TOKENS,
                                   agora: Optional[datetime] = None) -> Historico:
    """O helper ÚNICO: a conversa do assunto em aberto, por tokens. **Nunca levanta.**

    Acha a conversa por (`company_id`, `session_id`) — a mesma chave da ficha e do
    reencontro — ou por (`company_id`, telefone) — a do destravador, que só tem o
    telefone. `Historico.lida` diz se a conversa foi achada e lida: só então o
    chamador troca a sua fonte por esta.
    """
    empresa = str(company_id or "").strip()
    if db is None or not empresa or not (str(session_id or "").strip() or str(telefone or "").strip()):
        return Historico(erro="sem_chave")
    try:
        conversa = await _achar_a_conversa(db, empresa, session_id=str(session_id or "").strip(),
                                           telefone=str(telefone or ""))
        if not conversa:
            return Historico(erro="sem_conversa")
        cid = str(conversa.get("id") or "")
        linhas, erro = await _ler_mensagens(db, cid)
        if erro:
            return Historico(conversation_id=cid, erro=erro)
        falas, inicio = falas_do_assunto(linhas, texto_do_turno=texto_do_turno,
                                         turno_corrente=turno_corrente, agora=agora,
                                         resolvido_em=conversa.get("resolvido_em"))
        mantidas, resumo = caber_no_teto(falas, teto_tokens)
        if resumo:
            logger.info("[HISTORICO] %d falas do assunto, %d resumidas (teto %d tokens)",
                        len(falas), len(falas) - len(mantidas), teto_tokens)
        return Historico(falas=mantidas, resumo=resumo, inicio=inicio, conversation_id=cid, lida=True)
    except Exception as erro:  # noqa: BLE001
        # ⛔ Nunca o conteúdo nem o id — só a classe do erro.
        logger.warning("[HISTORICO] conversa não lida (%s)", type(erro).__name__)
        return Historico(erro=type(erro).__name__)


# ---------------------------------------------------------------------------
# AS DUAS FORMAS DE ENTREGAR — ao modelo do atendimento e ao destravador
# ---------------------------------------------------------------------------
def como_mensagens_do_modelo(hist: Historico) -> list:
    """O histórico como mensagens do LangChain, a mais antiga primeiro.

    segurado → HumanMessage · agente → AIMessage · EQUIPE → AIMessage marcada (texto +
    `name`): é o lado da corretora falando com o segurado, mas não foi o modelo — e ele
    precisa saber disso para não negar o que a atendente prometeu nem repetir o que
    ela já perguntou (laudo T3/M2).
    """
    from langchain_core.messages import AIMessage, HumanMessage

    out = []
    if hist.resumo:
        out.append(HumanMessage(content=hist.resumo))
    for f in hist.falas:
        if f.quem == "segurado":
            out.append(HumanMessage(content=f.texto))
        elif f.quem == "equipe":
            out.append(AIMessage(content=f"{MARCA_DA_EQUIPE}: {f.texto}", name=NOME_DA_EQUIPE))
        else:
            out.append(AIMessage(content=f.texto))
    return out


def linhas_para_o_destravador(hist: Historico) -> List[str]:
    """`[segurado] …` · `[corretora] …` (o agente) · `[equipe da corretora] …`, a mais antiga primeiro."""
    out = [hist.resumo] if hist.resumo else []
    rotulo = {"segurado": "segurado", "agente": "corretora", "equipe": "equipe da corretora"}
    for f in hist.falas:
        out.append(f"[{rotulo.get(f.quem, f.quem)}] {' '.join(f.texto.split())}")
    return out


# ---------------------------------------------------------------------------
# OS RESULTADOS DE FERRAMENTA QUE ATRAVESSAM TURNOS
# ---------------------------------------------------------------------------
def _tipo(m) -> str:
    return str(getattr(m, "type", "") or "")


def _ids_das_chamadas(m) -> List[str]:
    ids = []
    for tc in getattr(m, "tool_calls", None) or []:
        i = tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", None)
        if i:
            ids.append(str(i))
    return ids


def resultados_que_continuam(anteriores: Optional[list], *, checkpoint_em: Any = None,
                             hist: Optional[Historico] = None,
                             teto_tokens: int = TETO_DOS_RESULTADOS_TOKENS) -> list:
    """Os pares (chamada → resultado) de ferramenta dos turnos ANTERIORES do MESMO assunto. **PURA.**

    🔴 A REGRA (SPEC-125 S2, T2): o checkpointer passa a guardar só o turno corrente,
    mas o que uma ferramenta APUROU continua sendo fato do caso enquanto o assunto
    durar — a apólice que o InfoCap trouxe, o protocolo do acionamento, o `HANDOFF_OK`.
    📊 O fiscal da honestidade (S1) lê o carimbo de acionamento de um turno ANTERIOR
    (`honestidade_do_handoff._houve_acionamento_confirmado`) — sem isto, "acionei o
    guincho" voltaria a ser reescrito no turno seguinte ao acionamento.
    Por isso eles atravessam; o texto da conversa NÃO (vem de `messages`).

    ```
    o assunto começou no turno de agora (nenhuma fala anterior)  → nada atravessa
    o checkpoint é de ANTES do começo do assunto                  → nada atravessa
    checkpoint do regime antigo (tem SystemMessage)               → só os K últimos turnos,
                                                                    K = falas do segurado no assunto
    knowledge_base_search                                         → o par fica, o conteúdo é comprimido
    acima do teto                                                 → os mais ANTIGOS ficam com o par e
                                                                    uma linha "omitido por tamanho"
    ```
    """
    from langchain_core.messages import AIMessage, ToolMessage

    from app.services.o_fim_do_atendimento import _quando

    msgs = list(anteriores or [])
    if not msgs or hist is None or hist.turnos_do_segurado <= 0:
        return []
    quando = _quando(checkpoint_em)
    if quando is not None and hist.inicio is not None and quando < hist.inicio:
        return []
    if any(_tipo(m) == "system" for m in msgs):
        humanas = [i for i, m in enumerate(msgs) if _tipo(m) == "human"]
        k = hist.turnos_do_segurado
        msgs = msgs[humanas[-k]:] if len(humanas) >= k else msgs

    respostas: Dict[str, Any] = {}
    for m in msgs:
        if _tipo(m) == "tool" and getattr(m, "tool_call_id", None):
            respostas[str(m.tool_call_id)] = m
    grupos = []
    for m in msgs:
        if _tipo(m) != "ai":
            continue
        ids = _ids_das_chamadas(m)
        if not ids or not all(i in respostas for i in ids):
            continue                      # par incompleto: o provedor recusaria
        chamada = AIMessage(content="", tool_calls=list(m.tool_calls))
        resultados = []
        for i in ids:
            r = respostas[i]
            nome = str(getattr(r, "name", "") or "")
            conteudo = CONTEUDO_COMPRIMIDO if nome in FERRAMENTAS_COMPRIMIDAS else str(r.content or "")
            resultados.append(ToolMessage(content=conteudo, tool_call_id=i, name=nome))
        grupos.append([chamada, resultados])

    usado = 0
    for grupo in reversed(grupos):         # os mais NOVOS ficam inteiros
        custo = sum(tokens(r.content) + tokens(json.dumps(grupo[0].tool_calls, default=str))
                    for r in grupo[1])
        if usado + custo > teto_tokens:
            grupo[1] = [ToolMessage(content=(f"[resultado antigo de {r.name} omitido por tamanho — "
                                             f"o que ele trouxe já está nas respostas acima]"),
                                    tool_call_id=r.tool_call_id, name=r.name) for r in grupo[1]]
        else:
            usado += custo
    out = []
    for chamada, resultados in grupos:
        out.append(chamada)
        out.extend(resultados)
    return out


# ---------------------------------------------------------------------------
# A MONTAGEM DO TURNO — o que entra no estado do grafo
# ---------------------------------------------------------------------------
async def mensagens_do_turno(db, *, company_id: str, session_id: str, texto_do_turno: str,
                             anteriores: Optional[list] = None, checkpoint_em: Any = None) -> Tuple[list, Historico]:
    """`(mensagens para o estado inicial, histórico)` do agente de ATENDIMENTO. **Nunca levanta.**

    Conversa lida → `[REMOVE_ALL, *conversa do assunto, *resultados que continuam, Human(turno)]`:
    o reducer `add_messages` APAGA o checkpoint anterior e o turno começa da fonte única.
    Não lida (sem conversa, banco fora) → `[Human(turno)]`, o comportamento de antes:
    o checkpointer segue sendo a memória, e o `agent_node` o apara por tokens.
    ⛔ O SystemMessage não entra em nenhum dos dois: ele vive em `state["system_prompt"]`
    e o `agent_node` o monta a cada chamada (📊 era ele que fazia o checkpoint de uma
    thread chegar a 2,1 MB).
    """
    from langchain_core.messages import HumanMessage, RemoveMessage
    from langgraph.graph.message import REMOVE_ALL_MESSAGES

    turno = HumanMessage(content=texto_do_turno)
    hist = await historico_do_atendimento(db, company_id=company_id, session_id=session_id,
                                          texto_do_turno=texto_do_turno)
    if not hist.lida:
        return [turno], hist
    carregados = resultados_que_continuam(anteriores, checkpoint_em=checkpoint_em, hist=hist)
    return [RemoveMessage(id=REMOVE_ALL_MESSAGES), *como_mensagens_do_modelo(hist), *carregados, turno], hist


# ---------------------------------------------------------------------------
# A REDE DE SEGURANÇA DO `agent_node` — por tokens, nunca por contagem
# ---------------------------------------------------------------------------
def _tokens_da_mensagem(m) -> int:
    from app.agents.utils import extract_text_from_content

    t = tokens(extract_text_from_content(getattr(m, "content", "") or ""))
    if getattr(m, "tool_calls", None):
        t += tokens(json.dumps(m.tool_calls, default=str))
    return t


def aparar_ao_teto(mensagens: list, teto: int = TETO_DA_CONVERSA_NO_MODELO_TOKENS) -> list:
    """O que o `agent_node` manda ao modelo: sem SystemMessage, o turno corrente inteiro,
    e o que veio antes dele até o teto. **PURA.** Nunca corta calado.

    No atendimento o histórico já chega aparado (`historico_do_atendimento`) e isto não
    corta nada. É a rede para o caminho que ainda vive do checkpointer (o copiloto da
    corretora, o canal web, e o atendimento quando a leitura de `messages` falhou).
    ⛔ O turno corrente — da última HumanMessage em diante, com as ferramentas dele —
    nunca é aparado.
    """
    from langchain_core.messages import HumanMessage

    msgs = [m for m in (mensagens or []) if _tipo(m) != "system"]
    humanas = [i for i, m in enumerate(msgs) if _tipo(m) == "human"]
    corte = humanas[-1] if humanas else 0
    antes, turno = msgs[:corte], msgs[corte:]
    if sum(_tokens_da_mensagem(m) for m in antes) <= teto:
        return antes + turno
    mantidas = []
    usado = 0
    for m in reversed(antes):
        t = _tokens_da_mensagem(m)
        if usado + t > teto:
            break
        mantidas.append(m)
        usado += t
    mantidas.reverse()
    fora = len(antes) - len(mantidas)
    logger.info("[HISTORICO] %d mensagens antigas fora do contexto (teto %d tokens)", fora, teto)
    nota = HumanMessage(content=(f"[Nota do sistema: {fora} mensagens mais antigas desta conversa "
                                 f"ficaram fora do contexto por tamanho.]"))
    return [nota] + mantidas + turno
