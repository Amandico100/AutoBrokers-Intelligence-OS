# -*- coding: utf-8 -*-
"""O digest da sombra de sinistros. SPEC-093-B BLOCO C ①–⑥ · referências ② ⑤ ⑥.

O que ele faz, em uma frase
---------------------------
Uma vez por dia, por corretora, lê as sombras dos últimos noventa dias e responde
duas perguntas que ninguém consegue responder olhando conversa por conversa:

    quais CAMINHOS o sinistro percorreu de verdade, e quantas vezes cada um
    quantas sombras carregam cada um dos cinco problemas — sempre com denominador

⛔ E só isso. Ele **não** manda mensagem, **não** decide sinistro, **não** escreve
`knowledge_candidates` (P-093B-CANDIDATO: 📊 o adapter nunca escreveu em produção;
ligar a sombra a um caminho nunca exercido seria dois desconhecidos de uma vez).
A única escrita é `intelligence_signals`, pela porta única do `signal_service` — que
é quem valida taxonomia, redige e deduplica.

🔴 UM MOTOR SÓ DE VARIANTE — o que este módulo NÃO reimplementa
---------------------------------------------------------------
`variantes_de`, `contadores_de` e `assinatura_da_variante` moram em
`claims_shadow.py` (BLOCO A/B) e são **importadas** daqui. Escrever uma segunda
versão delas seria motor paralelo (CLAUDE.md §5) — e pior que duplicado: o guarda
`test_o_sinistro_deixa_rastro.py` importa as DE LÁ, então a segunda cópia seria
justamente a que ninguém mede, e as duas divergiriam em silêncio.

O que é DESTE módulo, porque não existe em lugar nenhum:

    trajetorias_de()      a ponte entre `work_events` (uma linha por evento) e a
                          trajetória que as funções puras esperam — é aqui que a
                          ORDEM nasce, do `created_at` do evento (referência ②)
    esperas_vencidas()    o único caller do motor de prazos (referência ⑥)
    os summaries          o texto do sinal, por TEMPLATE
    digerir()/executar()  a leitura por corretora e a escrita do sinal

🔴 NÚMERO SEM DENOMINADOR NÃO É CITÁVEL (referência ⑤ · Sprout.ai)
-------------------------------------------------------------------
"37 sinistros com documento faltante" não diz nada: pode ser 37 de 40 ou 37 de 4.000.
`contadores_de()` devolve `total` junto, e o resumo escreve `n/total` em toda linha.

⛔ O QUE NUNCA ENTRA NO SINAL
-----------------------------
Texto de conversa, nome, telefone, CPF, apólice, placa. O `summary_redacted` é montado
por TEMPLATE a partir de: contagem, ramo, `seguradora_slug` e a sequência de
`event_type`. Nada mais tem como entrar, porque nada mais é lido.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional

# 🔴 O motor de variante é UM. Ver o cabeçalho.
from .claims_shadow import contadores_de, variantes_de  # noqa: F401
from .prazos_regulatorios import REGIME_NAO_DETERMINADO, espera_vencida

logger = logging.getLogger(__name__)

#: A chave do run que a sombra abre (BLOCO A). ⛔ NÃO é workflow com handler.
WORKFLOW_DA_SOMBRA = "claims.shadow"
#: A chave DESTE trabalho — a que o `tick.py` agenda e o card da Central reivindica.
WORKFLOW_DIGEST = "intelligence.claims_shadow_digest"

#: 💭 limiar inicial (SPEC-093-B BLOCO C ①). Sobe quando o corpus crescer.
LIMIAR_PADRAO = 3
#: Janela de leitura, em dias. Sinistro é lento: 30 dias cortariam o meio do caminho.
JANELA_DIAS = 90
#: Teto de passos escritos no resumo — o resto vira reticências. Sinal é para ler.
MAX_PASSOS_NO_RESUMO = 12

SOURCE_TYPE = "claims_shadow"
SIGNAL_VARIANTE = "process_variant"
SIGNAL_RESUMO = "claims_shadow_resumo"

RAMO_DESCONHECIDO = "desconhecido"
SEGURADORA_DESCONHECIDA = "desconhecida"


def _texto(valor: Any, padrao: str = "") -> str:
    t = str(valor).strip() if valor is not None else ""
    return t or padrao


def _evento_da_sombra(event_type: Any) -> bool:
    """⛔ Só `claims.*`, e só o que o vocabulário declara.

    O filtro é o que impede um evento de OUTRO subsistema (um `work_run.started`,
    por exemplo) de entrar na assinatura e criar uma variante que não descreve
    trabalho de sinistro nenhum.
    """
    nome = _texto(event_type)
    if not nome.startswith("claims."):
        return False
    try:
        from .claims_shadow import vocabulario

        conhecidos = set((vocabulario() or {}).get("eventos") or {})
    except Exception:  # noqa: BLE001
        conhecidos = set()
    return (nome in conhecidos) if conhecidos else True


# ---------------------------------------------------------------------------
# A PONTE: `work_events` → trajetória. É aqui que a ORDEM nasce (referência ②)
# ---------------------------------------------------------------------------
def _ordem(evento: dict, i: int) -> tuple:
    """Chave de ordenação: `created_at` primeiro, posição de entrada como desempate.

    🔴 O desempate importa: dois eventos gravados no mesmo instante existem (o humano
    assume e a espera abre na mesma transação), e sem desempate estável a assinatura
    mudaria entre duas execuções — o que duplicaria o sinal a cada rodada.
    """
    return (_texto(evento.get("created_at") or evento.get("occurred_at")), i)


def trajetorias_de(eventos: Optional[Iterable]) -> list[dict]:
    """Uma trajetória por sombra, com os `event_type` já na ordem do relógio.

    Entrada: as linhas de `work_events` como o PostgREST as devolve —
    ``{work_run_id, event_type, payload_redacted, created_at, company_id}``.

    Saída: a forma que `claims_shadow.variantes_de`/`contadores_de` esperam —
    ``{work_run_id, company_id, ramo, seguradora_slug, eventos: [event_type, …],
    desfechos: [...], esperas: [...]}``.

    ⚠️ `ramo` e `seguradora_slug` vêm do payload do `claims.sombra_aberta` (é o único
    evento do vocabulário que os declara). Sem ele, a trajetória cai em
    `desconhecido/desconhecida` — que é a verdade, e não um chute.
    """
    por_run: dict[str, list[tuple]] = {}
    ficha: dict[str, dict] = {}
    for i, ev in enumerate(eventos or ()):
        if not isinstance(ev, dict):
            continue
        run = _texto(ev.get("work_run_id"))
        if not run:
            continue
        f = ficha.setdefault(run, {"company_id": "", "ramo": "", "seguradora_slug": ""})
        if not f["company_id"]:
            f["company_id"] = _texto(ev.get("company_id"))
        payload = ev.get("payload_redacted") or ev.get("payload") or {}
        if not isinstance(payload, dict):
            payload = {}
        for campo in ("ramo", "seguradora_slug"):
            if not f[campo]:
                f[campo] = _texto(ev.get(campo)) or _texto(payload.get(campo))
        if not _evento_da_sombra(ev.get("event_type")):
            continue
        por_run.setdefault(run, []).append((_ordem(ev, i), ev, payload))

    saida: list[dict] = []
    for run in sorted(por_run):
        linhas = sorted(por_run[run], key=lambda p: p[0])
        f = ficha.get(run) or {}
        tipos = [_texto(ev.get("event_type")) for _o, ev, _p in linhas]
        desfechos = [_texto(p.get("desfecho")) for _o, ev, p in linhas
                     if _texto(ev.get("event_type")) == "claims.encerrado"]
        esperas = [{"work_run_id": run, "kind": _texto(p.get("kind")),
                    "aberta_em": ev.get("created_at"),
                    "satisfeita_em": None, "data_contrato": None}
                   for _o, ev, p in linhas
                   if _texto(ev.get("event_type")) == "claims.espera_aberta"]
        satisfeitos = {_texto(p.get("kind")) for _o, ev, p in linhas
                       if _texto(ev.get("event_type")) == "claims.espera_satisfeita"}
        for e in esperas:
            if e["kind"] in satisfeitos:
                e["satisfeita_em"] = "satisfeita"
        saida.append({
            "work_run_id": run,
            "company_id": f.get("company_id") or "",
            "ramo": f.get("ramo") or RAMO_DESCONHECIDO,
            "seguradora_slug": f.get("seguradora_slug") or SEGURADORA_DESCONHECIDA,
            "eventos": tipos,
            "desfechos": desfechos,
            "esperas": esperas,
        })
    return saida


# ---------------------------------------------------------------------------
# O ÚNICO caller do motor de prazos (referência ⑥ · C⑤)
# ---------------------------------------------------------------------------
def esperas_vencidas(trajetorias: Iterable[dict], *, agora: Any = None) -> dict:
    """Quantas sombras têm espera de SEGURADORA vencida — e quantas não têm regime.

    Devolve ``{"vencidas": n, "regime_nao_determinado": n, "total": n}``: três números,
    porque dois obrigariam a mentir.

    ⚠️ 📊 **Hoje o resultado é `regime_nao_determinado` para toda espera**, e está
    certo assim: a sombra não guarda apólice, então não há `data_contrato`, e a
    CNSP 496/2026 vale por data de formação/renovação do contrato. Contar um "não sei"
    como "passou do prazo" seria inventar o regime pela porta dos fundos. P-093B-PRAZO
    registra o que destravaria o número.

    🔴 Este é o caller que impede `prazos_regulatorios.py` de virar código morto: um
    motor declarado e nunca chamado é uma regra que ninguém aplica (CLAUDE.md §9.4).
    """
    lista = [t for t in (trajetorias or ()) if isinstance(t, dict)]
    vencidas = 0
    indeterminadas = 0
    for t in lista:
        marcada = False
        indefinida = False
        for e in (t.get("esperas") or ()):
            if _texto(e.get("kind")) != "esperando_seguradora" or e.get("satisfeita_em"):
                continue
            r = espera_vencida("esperando_seguradora", e.get("aberta_em"), agora,
                               e.get("data_contrato"))
            if r is True:
                marcada = True
            elif r == REGIME_NAO_DETERMINADO:
                indefinida = True
        vencidas += 1 if marcada else 0
        indeterminadas += 1 if (indefinida and not marcada) else 0
    return {"vencidas": vencidas, "regime_nao_determinado": indeterminadas,
            "total": len(lista)}


# ---------------------------------------------------------------------------
# Os textos — por TEMPLATE, e só de contagem, enum e event_type
# ---------------------------------------------------------------------------
_ROTULO_DO_CONTADOR = {
    "sem_documento": "sem documento recebido",
    "espera_de_seguradora_sem_retorno": "com espera de seguradora sem retorno",
    "com_nota_da_atendente": "com nota da atendente",
    "com_retomada_do_humano": "com retomada do humano",
    "encerrados_sem_desfecho": "encerrados sem desfecho conhecido",
}


def _passo_legivel(event_type: Any) -> str:
    return _texto(event_type).replace("claims.", "").replace("_", " ")


def summary_de_variante(variante: dict) -> str:
    """O texto do sinal, por TEMPLATE. ⛔ Só contagem, ramo, slug e event_types."""
    passos = list(variante.get("eventos") or ())
    mostrados = [_passo_legivel(p) for p in passos[:MAX_PASSOS_NO_RESUMO]]
    if len(passos) > MAX_PASSOS_NO_RESUMO:
        mostrados.append("…")
    return "%d sinistro(s) %s × %s seguiram %d passo(s): %s" % (
        int(variante.get("n") or 0),
        _texto(variante.get("ramo"), RAMO_DESCONHECIDO),
        _texto(variante.get("seguradora_slug"), SEGURADORA_DESCONHECIDA),
        len(passos), " → ".join(mostrados))


def summary_de_contadores(contadores: dict, *, janela_dias: int = JANELA_DIAS,
                          prazos: Optional[dict] = None) -> str:
    """Cada número com o seu denominador, sem exceção (referência ⑤).

    ⚠️ Percorre as chaves na ordem em que `contadores_de` as devolveu: o rótulo é
    cosmético, o dono do contrato é quem conta.
    """
    total = int(contadores.get("total") or 0)
    partes = []
    for chave, valor in contadores.items():
        if chave == "total" or not isinstance(valor, int):
            continue
        rotulo = _ROTULO_DO_CONTADOR.get(chave, chave.replace("_", " "))
        partes.append("%d/%d %s" % (valor, total, rotulo))
    texto = "%d sombra(s) de sinistro em %d dia(s): %s" % (
        total, int(janela_dias), " · ".join(partes))
    if prazos:
        texto += (" · prazo regulatório: %d/%d vencida(s), %d/%d sem regime "
                  "determinado" % (int(prazos.get("vencidas") or 0), total,
                                   int(prazos.get("regime_nao_determinado") or 0), total))
    return texto


# ---------------------------------------------------------------------------
# A leitura por corretora e a escrita do sinal
# ---------------------------------------------------------------------------
def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _confianca_por_n(n: int, total: int) -> float:
    """Proporcional a `n`, com teto. Frequência não vira certeza.

    Uma variante vista 3 vezes descreve o processo com menos autoridade do que uma
    vista 300 — mas nem a de 300 vira fato: o `trust_tier` continua de ANÁLISE.
    """
    if total <= 0:
        return 0.5
    fracao = max(0.0, min(1.0, float(n) / float(total)))
    return round(0.5 + 0.4 * fracao, 3)


def _ler_sombras(cliente: Any, company_id: str, desde: str) -> tuple[list[dict], bool]:
    """As sombras da corretora na janela. Devolve `(linhas, truncou)`.

    🔴 Era `.limit(2000)`, e 2.000 NUNCA chegariam: o PostgREST devolve no máximo
    1.000 linhas por resposta e ignora o pedido maior — sem erro, sem log, sem
    sintoma (`app/leitura_completa.py`). O digest é uma CONTAGEM com denominador:
    receber 1.000 de N faria `contadores_de` responder outra pergunta, com cara de
    resposta certa. É o defeito de 06/08/2026 (P-122) reencenado.

    ⚠️ A ordenação por `created_at desc` também saiu, e não por descuido: paginar
    por uma coluna que EMPATA perde e repete linhas (📊 `curadoria_cartas.py`: 12
    perdidas e 12 repetidas em 11.640). `ler_paginado` ordena por `id`, que nunca
    empata — e a ordem das sombras não importa aqui, porque quem ordena a trajetória
    é `_ordem()`, pelo relógio do evento.
    """
    from app.leitura_completa import ler_paginado

    linhas, truncou = ler_paginado(
        lambda: (cliente.table("work_runs")
                 .select("id, company_id, conversation_id, created_at, status")
                 .eq("company_id", company_id)
                 .eq("workflow_key", WORKFLOW_DA_SOMBRA)
                 .gte("created_at", desde)),
        chave_unica="id", rotulo="claims.shadow/work_runs")
    return [x for x in (linhas or []) if x.get("id")], bool(truncou)


def _ler_eventos(cliente: Any, company_id: str,
                 run_ids: list[str]) -> tuple[list[dict], bool]:
    """Os eventos das sombras da corretora. ⛔ Filtro de `company_id` SEMPRE.

    🔴 Filtrar só por `work_run_id` "funcionaria" — os ids vieram da corretora certa.
    Mas o backend usa service role: a segunda barreira é o filtro do código, e uma
    consulta sem ele passa a depender de o passo anterior nunca ter errado
    (CLAUDE.md §7).

    🔴 O `.limit(20000)` que estava aqui era o mesmo engano em escala pior: um lote
    de 100 sombras conversadas passa de mil eventos com facilidade, e o que chegava
    era o primeiro milheiro — a assinatura da variante saía TRUNCADA, ou seja, uma
    variante que ninguém percorreu. Devolve `(linhas, truncou)`; `truncou` também é
    `True` quando uma página falhou, porque meia leitura não é leitura.

    ⚠️ `id` entrou no `select` de propósito: é por ele que a paginação ordena, e é
    ele (bigint sequencial) que dá o desempate ESTÁVEL de `_ordem()` quando dois
    eventos têm o mesmo `created_at`. Antes o desempate era a ordem de chegada de uma
    consulta ordenada por uma coluna que empata — instável entre duas execuções, que
    é exatamente o que duplicaria o sinal a cada rodada.
    """
    from app.leitura_completa import ler_paginado

    saida: list[dict] = []
    truncou = False
    for i in range(0, len(run_ids), 100):
        lote = run_ids[i:i + 100]
        linhas, cortou = ler_paginado(
            lambda alvo=lote: (
                cliente.table("work_events")
                .select("id, work_run_id, event_type, payload_redacted, "
                        "created_at, company_id")
                .eq("company_id", company_id)
                .in_("work_run_id", alvo)),
            chave_unica="id", rotulo="claims.shadow/work_events")
        saida.extend(linhas or [])
        truncou = truncou or bool(cortou)
    return saida, truncou


def _evidencia_de(ref: str, resumo: str, valores: dict) -> dict:
    from .intelligence.schemas import TIER_ANALISE, evidencia

    return evidencia(tipo="analysis", sistema="claims_shadow", ref=ref,
                     resumo=resumo, tier=TIER_ANALISE, valores=valores)


def _escrever_sinais(db: Any, company_id: str, variantes: list[dict],
                     contadores: dict, prazos: dict, janela: tuple[str, str]) -> int:
    """Grava pela porta única do `signal_service`. Devolve quantos sinais entraram.

    🔴 `subject_id=None`, `work_run_id=None`, `conversation_id=None`: o sinal é
    AGREGADO. Prendê-lo a uma conversa transformaria uma estatística de processo em
    um apontamento sobre um segurado — e é justamente o que a minimização proíbe
    (referência ⑦).
    """
    from .intelligence.schemas import TIER_ANALISE, SignalDraft
    from .intelligence.signal_service import SignalService

    servico = SignalService(db)
    total = int(contadores.get("total") or 0)
    gravados = 0

    for v in variantes:
        resumo = summary_de_variante(v)
        rascunho = SignalDraft(
            company_id=company_id, signal_type=SIGNAL_VARIANTE,
            subject_type="claims_shadow", subject_id=None,
            summary_redacted=resumo, dedupe_key=v["dedupe_key"],
            source_type=SOURCE_TYPE, source_ref=WORKFLOW_DIGEST,
            rule_key="claims_shadow.variante", rule_version="1",
            trust_tier=TIER_ANALISE, severity="info",
            confidence=_confianca_por_n(int(v.get("n") or 0), total),
            window_start=janela[0], window_end=janela[1],
            evidencias=[_evidencia_de(
                "work_runs:%s" % WORKFLOW_DA_SOMBRA, resumo,
                {"n": v.get("n"), "passos": len(v.get("eventos") or ()),
                 "ramo": v.get("ramo"), "seguradora_slug": v.get("seguradora_slug"),
                 "assinatura": list(v.get("eventos") or ())})],
            metadata={"assinatura": list(v.get("eventos") or ()), "n": v.get("n"),
                      "ramo": v.get("ramo"),
                      "seguradora_slug": v.get("seguradora_slug"),
                      "denominador": total})
        if servico.registrar(rascunho):
            gravados += 1

    if total > 0:
        resumo = summary_de_contadores(contadores, prazos=prazos)
        rascunho = SignalDraft(
            company_id=company_id, signal_type=SIGNAL_RESUMO,
            subject_type="claims_shadow", subject_id=None,
            summary_redacted=resumo,
            dedupe_key="claims_shadow_resumo:%s:%s" % (company_id, janela[1][:10]),
            source_type=SOURCE_TYPE, source_ref=WORKFLOW_DIGEST,
            rule_key="claims_shadow.resumo", rule_version="1",
            trust_tier=TIER_ANALISE, severity="info", confidence=0.6,
            window_start=janela[0], window_end=janela[1],
            evidencias=[_evidencia_de("work_events:claims.*", resumo,
                                      {**contadores, "prazo_regulatorio": prazos})],
            metadata={"contadores": dict(contadores), "prazo_regulatorio": dict(prazos),
                      "denominador": total, "janela_dias": JANELA_DIAS})
        if servico.registrar(rascunho):
            gravados += 1
    return gravados


def digerir(db: Any, company_id: str, *, agora: Optional[datetime] = None,
            limiar: int = LIMIAR_PADRAO) -> dict:
    """Uma corretora, uma janela. Síncrono e sem `ctx` — para dar para chamar à mão.

    ⛔ Nunca agrega entre corretoras: `company_id` é argumento, não filtro opcional.
    """
    cliente = getattr(db, "client", db)
    fim = agora or _agora()
    inicio = fim - timedelta(days=JANELA_DIAS)
    janela = (inicio.isoformat(), fim.isoformat())

    # 🔴 `truncado` é a metade que faltava do conserto da paginação: um teto que corta
    # em silêncio produz o mesmo número menor-que-a-verdade que o `.limit()` produzia.
    # Quem lê o resultado precisa poder dizer "este número está incompleto" —
    # é a mesma regra do `nao_instrumentado` da Central (SPEC-088 §4).
    truncado: list[str] = []
    sombras, cortou = _ler_sombras(cliente, company_id, inicio.isoformat())
    if cortou:
        truncado.append("sombras")
    if not sombras:
        return {"sombras": 0, "variantes": 0, "sinais": 0,
                "contadores": {"total": 0}, "prazos": {"vencidas": 0,
                                                       "regime_nao_determinado": 0,
                                                       "total": 0},
                "truncado": truncado}

    eventos, cortou = _ler_eventos(cliente, company_id, [str(s["id"]) for s in sombras])
    if cortou:
        truncado.append("eventos")
    for ev in eventos:
        ev.setdefault("company_id", company_id)

    trajs = trajetorias_de(eventos)
    # 🔴 Uma sombra que abriu e nada mais aconteceu É o caso que mais interessa. Sem
    # esta linha ela sumiria do denominador — e o contador "sem documento" ficaria
    # bonito exatamente onde a operação está pior.
    vistas = {t["work_run_id"] for t in trajs}
    for s in sombras:
        if str(s["id"]) not in vistas:
            trajs.append({"work_run_id": str(s["id"]), "company_id": company_id,
                          "ramo": RAMO_DESCONHECIDO,
                          "seguradora_slug": SEGURADORA_DESCONHECIDA,
                          "eventos": [], "desfechos": [], "esperas": []})

    variantes = variantes_de(trajs, limiar=limiar)
    contadores = contadores_de(trajs)
    prazos = esperas_vencidas(trajs, agora=fim)
    sinais = _escrever_sinais(db, company_id, variantes, contadores, prazos, janela)
    return {"sombras": len(sombras), "variantes": len(variantes), "sinais": sinais,
            "contadores": contadores, "prazos": prazos, "truncado": truncado}


async def executar(ctx: dict) -> str:
    """O corpo do workflow `intelligence.claims_shadow_digest` (Work OS, SPEC-055).

    Fica aqui, e não em `intelligence/workflows.py`, porque o `@registrar_workflow`
    de lá é só a tomada: o trabalho mora junto das funções que ele usa.
    """
    from .work.workflows import executar_passo

    company_id, db = ctx["company_id"], ctx["db"]
    limiar = int((ctx.get("payload") or {}).get("limiar") or LIMIAR_PADRAO)

    async def _digerir() -> Any:
        return digerir(db, company_id, limiar=limiar)

    r = await executar_passo(ctx, step_key="digerir_sombras", ordinal=1,
                             nome="Agrupar as sombras de sinistro em variantes",
                             step_type="analysis", fn=_digerir) or {}
    if not r.get("sombras"):
        return "Nenhuma sombra de sinistro na janela de %d dias." % JANELA_DIAS
    return ("%d sombra(s) lidas, %d variante(s) com N>=%d, %d sinal(is). %s"
            % (r.get("sombras", 0), r.get("variantes", 0), limiar, r.get("sinais", 0),
               summary_de_contadores(r.get("contadores") or {"total": 0},
                                     prazos=r.get("prazos"))))
