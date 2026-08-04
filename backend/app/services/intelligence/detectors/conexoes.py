"""Detectores de conexao e custo. SPEC-059 §23.4 e §23.8.

O detector de conexao e o unico do lote que precisa dizer o que PAROU junto.
"A conexão do WhatsApp expirou" nao e util sozinho; o corretor so entende o
tamanho do problema quando sabe que duas Rotinas e um Auxiliar dependem dela
(§23.4). Por isso ele consulta as dependencias antes de escrever o resumo.
"""

from __future__ import annotations

import logging

from ..dedupe_service import chave_de_sinal
from ..schemas import TIER_ANALISE, TIER_DADO_VIVO, SignalDraft, evidencia
from . import ContextoDeDeteccao, plural, registrar

logger = logging.getLogger(__name__)

# `close` e `closed` entram porque é assim que o Evolution reporta canal caído —
# descobrir isso custou um canário: sem eles, o WhatsApp da corretora podia
# estar fora do ar e o detector não veria nada.
#
# O que está aqui é QUEDA MEDIDA: alguém — o provedor, o webhook, a sonda —
# afirmou que o canal não está de pé.
ESTADOS_RUINS = ("expired", "degraded", "error", "disconnected", "revoked",
                 "failed", "close", "closed")

# P-38 — O ESTADO QUE NINGUÉM CONFIRMOU.
#
# O heartbeat da SPEC-063 Bloco V demove para `unknown` o canal que afirmava
# `connected`/`connecting` e que ninguém confirma há mais de 15 minutos. A
# escolha da palavra é deliberada e está certa: **não medimos queda nenhuma**,
# só perdemos o direito de dizer "Conectado" (`channel_state.decidir_heartbeat`,
# regra 3). Afirmar `disconnected` sem ter medido seria o mesmo pecado do outro
# lado — e é por isso que `unknown` NÃO entra em ESTADOS_RUINS.
#
# Só que ficar de fora das duas listas significava SILÊNCIO. 📊 03/08/2026, banco
# de produção: três canais ativos com `last_seen_at` congelado há 4 e 5 dias. O
# heartbeat os demoveria para `unknown` — a tela pararia de mentir — e o
# briefing não diria uma palavra. O canal saía do radar exatamente quando
# passava a merecer atenção: some da tela como "Conectado" e não aparece em
# lugar nenhum como problema.
#
# Então ele ganha classe própria e sinal mais fraco: severidade menor, confiança
# menor, e o texto diz o que é verdade — "não conseguimos confirmar", nunca
# "está indisponível". O tier `TIER_ANALISE` faz a própria SPEC-059 recusar
# severidade `critical` para este caso (`TIERS_QUE_SUSTENTAM_ALERTA_CRITICO`):
# a fraqueza do sinal deixa de depender de alguém lembrar dela.
ESTADOS_SEM_CONFIRMACAO = ("unknown",)

CLASSE_QUEDA = "queda_medida"
CLASSE_SEM_CONFIRMACAO = "sem_confirmacao"

# `connecting` NÃO entra: é estado de transição. Alertar nele produziria um
# aviso a cada reconexão normal.
ESTADOS_TRANSITORIOS = ("connecting", "qr", "pairing", "starting")


# ---------------------------------------------------------------------------
# §23.4 — conexao degradada ou expirada
# ---------------------------------------------------------------------------


def _quem_depende(dependentes: dict) -> str:
    """"um Auxiliar e duas Rotinas" — ou vazio, quando ninguém depende."""
    rotinas = int(dependentes.get("rotinas") or 0)
    auxiliares = int(dependentes.get("auxiliares") or 0)
    pedacos = []
    if auxiliares:
        pedacos.append(plural(auxiliares, "Auxiliar", "Auxiliares"))
    if rotinas:
        pedacos.append(plural(rotinas, "Rotina", "Rotinas"))
    return " e ".join(pedacos)


def descrever_impacto(nome_conexao: str, dependentes: dict) -> str:
    """Frase de §23.4. Sem dependentes, nao inventa consequencia.

    Prometer que "duas rotinas pararam" quando nenhuma parou seria alarme
    falso — e alarme falso e o caminho mais curto para o corretor desligar
    os avisos.
    """
    quem = _quem_depende(dependentes)
    if not quem:
        return f"A conexão {nome_conexao} está indisponível."
    return (f"A conexão {nome_conexao} está indisponível. "
            f"{quem} dependem dela e ficam parados até a reconexão.")


def descrever_sem_confirmacao(nome_conexao: str, dependentes: dict) -> str:
    """P-38 — a frase do canal que ninguém conseguiu medir.

    A diferença com `descrever_impacto` não é de tom, é de **verdade**: ali o
    canal está comprovadamente fora; aqui só sabemos que não conseguimos
    confirmá-lo. Escrever "está indisponível" nos dois casos treinaria o
    corretor a desconfiar dos dois — e o dia em que a queda for real ele já
    terá aprendido a não olhar.
    """
    quem = _quem_depende(dependentes)
    base = (f"Não conseguimos confirmar a conexão {nome_conexao} — ela pode estar "
            f"fora do ar sem ter avisado.")
    if not quem:
        return base
    return f"{base} {quem} dependem dela."


def canais_com_problema(integracoes: list[dict]) -> list[dict]:
    """Puro: quais canais estão realmente com problema.

    A regra que este código existe para NÃO violar, descoberta no canário
    com dado de produção: **canal desligado não é canal quebrado**.

    A Resulta tem duas integrações antigas com `is_active=false` e estado
    `close`/`retired` — canais que alguém aposentou de propósito. Tratar
    `is_active=false` como indisponibilidade faria o primeiro briefing dela
    abrir com dois alertas sobre coisas que ela desligou por decisão própria.
    Alarme falso no dia um é o jeito mais rápido de o corretor aprender a
    ignorar a tela inteira.

    O que importa é a combinação: canal LIGADO em estado ruim.

    P-38 — devolve DUAS classes, e quem chama precisa saber a diferença:
    `queda_medida` (alguém afirmou que caiu) e `sem_confirmacao` (o heartbeat
    demoveu para `unknown` porque ninguém confirmou nada). Misturar as duas
    faria o briefing anunciar como queda algo que não foi medido.
    """
    saida = []
    for i in integracoes or []:
        if not bool(i.get("is_active")):
            continue  # desligada de propósito: decisão, não defeito
        estado = str(i.get("channel_status") or "").lower()
        if estado in ESTADOS_TRANSITORIOS:
            continue
        if estado in ESTADOS_RUINS:
            classe = CLASSE_QUEDA
        elif estado in ESTADOS_SEM_CONFIRMACAO:
            classe = CLASSE_SEM_CONFIRMACAO
        else:
            continue
        saida.append({
            "id": str(i["id"]),
            "nome": f"{i.get('provider') or 'canal'} ({i.get('purpose') or 'geral'})",
            "estado": estado, "origem": "integrations", "classe": classe})
    return saida


@registrar("conexoes.conexao_degradada")
def conexao_degradada(ctx: ContextoDeDeteccao) -> list[SignalDraft]:
    problemas: list[dict] = []

    try:
        conns = (ctx.db.table("tenant_connections")
                 .select("id, name, status, health_status, last_checked_at")
                 .eq("company_id", ctx.company_id).limit(100).execute()).data or []
        for c in conns:
            estado = str(c.get("health_status") or c.get("status") or "").lower()
            if estado in ESTADOS_RUINS:
                problemas.append({"id": str(c["id"]),
                                  "nome": c.get("name") or "conexão",
                                  "estado": estado, "origem": "tenant_connections",
                                  "classe": CLASSE_QUEDA})
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Detector] tenant_connections: %s", type(exc).__name__)

    # O canal WhatsApp e a conexao que mais dói quando cai: sem ele o
    # atendimento inteiro para. Ele vive em `integrations`, nao em
    # `tenant_connections`, e por isso e consultado separadamente.
    try:
        integ = (ctx.db.table("integrations")
                 .select("id, provider, is_active, channel_status, last_seen_at, purpose")
                 .eq("company_id", ctx.company_id).limit(50).execute()).data or []
        problemas.extend(canais_com_problema(integ))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Detector] integrations: %s", type(exc).__name__)

    if not problemas:
        return []

    dependentes = _contar_dependentes(ctx)
    tem_dependente = bool(dependentes.get("rotinas") or dependentes.get("auxiliares"))
    saida: list[SignalDraft] = []
    for p in problemas:
        # P-38 — o sinal do canal NÃO CONFIRMADO é o mesmo tipo, com a mesma
        # chave de deduplicação e força menor. Tipo novo o esconderia de quem já
        # olha `connection_health`; mesma força faria a suspeita competir de
        # igual para igual com a queda medida na fila do briefing.
        sem_confirmacao = p.get("classe") == CLASSE_SEM_CONFIRMACAO
        saida.append(SignalDraft(
            company_id=ctx.company_id,
            signal_type="connection_health",
            subject_type="connection", subject_id=p["id"],
            summary_redacted=(descrever_sem_confirmacao(p["nome"], dependentes)
                              if sem_confirmacao
                              else descrever_impacto(p["nome"], dependentes)),
            dedupe_key=chave_de_sinal(
                company_id=ctx.company_id, signal_type="connection_health",
                subject_type="connection", subject_id=p["id"],
                rule_key=ctx.rule_key, rule_version=ctx.rule_version,
                parametros={"estado": p["estado"]}),
            # `TIER_ANALISE` não é decoração: `TIERS_QUE_SUSTENTAM_ALERTA_CRITICO`
            # o exclui, então a SPEC-059 RECUSA um `critical` vindo daqui. A
            # fraqueza do sinal deixa de depender de alguém lembrar dela.
            trust_tier=TIER_ANALISE if sem_confirmacao else TIER_DADO_VIVO,
            rule_key=ctx.rule_key, rule_version=ctx.rule_version,
            severity=("medium" if tem_dependente else "low") if sem_confirmacao
                     else ("critical" if tem_dependente else "high"),
            # Confiança < 1 porque é isto que sabemos: que NÃO sabemos.
            confidence=0.6 if sem_confirmacao else 1.0,
            impact_score=min(100.0, (30.0 if sem_confirmacao else 60.0)
                             + 10.0 * (dependentes.get("rotinas", 0)
                                       + dependentes.get("auxiliares", 0))),
            urgency_score=40.0 if sem_confirmacao else 85.0,
            actionability_score=60.0 if sem_confirmacao else 90.0,
            freshness_score=100.0,
            metadata={"conexao": p["nome"], "estado": p["estado"],
                      "origem": p["origem"], "dependentes": dependentes,
                      "classe": p.get("classe", CLASSE_QUEDA),
                      "confirmado": not sem_confirmacao},
            evidencias=[evidencia(
                tipo="ausencia_de_confirmacao" if sem_confirmacao else "estado",
                sistema=p["origem"], ref=f"{p['origem']}:{p['id']}",
                resumo=(f"o heartbeat demoveu {p['nome']} para '{p['estado']}': "
                        f"ninguém confirmou o canal dentro da janela"
                        if sem_confirmacao
                        else f"estado='{p['estado']}' na conexão {p['nome']}"),
                tier=TIER_ANALISE if sem_confirmacao else TIER_DADO_VIVO,
                valores={"estado": p["estado"], **dependentes})],
        ))
    return saida


def _contar_dependentes(ctx: ContextoDeDeteccao) -> dict:
    """Quantas Rotinas e Auxiliares ativos existem hoje na corretora.

    Aproximacao honesta: hoje nao ha um grafo formal de dependencia entre
    conexao e Rotina. Contar os ATIVOS e o limite superior real, e o resumo
    usa a palavra "dependem" apenas quando ha algo ativo — nunca inventa um
    numero especifico de dependencia que o banco nao sustenta.
    """
    dep = {"rotinas": 0, "auxiliares": 0}
    try:
        r = (ctx.db.table("routines").select("id", count="exact")
             .eq("company_id", ctx.company_id).eq("is_active", True).execute())
        dep["rotinas"] = int(getattr(r, "count", None) or len(r.data or []))
    except Exception:  # noqa: BLE001
        pass
    try:
        a = (ctx.db.table("tenant_auxiliaries").select("id", count="exact")
             .eq("company_id", ctx.company_id).eq("status", "active").execute())
        dep["auxiliares"] = int(getattr(a, "count", None) or len(a.data or []))
    except Exception:  # noqa: BLE001
        pass
    return dep


# ---------------------------------------------------------------------------
# §23.8 — orcamento proximo do limite
# ---------------------------------------------------------------------------


def projetar_consumo(gasto_ate_agora: float, dias_decorridos: float,
                     dias_no_mes: int = 30) -> float:
    """Projecao linear simples. Transparente de proposito — §23.8.

    Modelo mais sofisticado daria um numero mais bonito e menos explicavel.
    Aqui o corretor precisa poder conferir de cabeca: "gastei X em 10 dias,
    no ritmo atual fecho o mês em 3X".
    """
    if dias_decorridos <= 0:
        return 0.0
    return round(float(gasto_ate_agora) / float(dias_decorridos) * float(dias_no_mes), 2)


@registrar("conexoes.orcamento_no_limite")
def orcamento_no_limite(ctx: ContextoDeDeteccao) -> list[SignalDraft]:
    """Custo tecnico acumulado no mes, com projecao.

    IMPORTANTE: isto NAO e cobranca. A SPEC-062 e a unica autoridade de preço
    ao cliente (CLAUDE.md §13.6). O que aparece aqui e o **custo técnico do
    provedor**, exatamente como `usage_events` o registra — em dólar, porque e
    assim que o provedor cobra. Converter para real aqui exigiria uma taxa de
    câmbio que ninguém declarou, e número inventado que se apresenta como
    medido é pior do que número ausente (D16).
    """
    limite = float(ctx.cfg("limite_usd", 0) or 0)
    if limite <= 0:
        return []  # sem limite declarado nao ha "proximo do limite"

    percentual_alerta = float(ctx.cfg("percentual_alerta", 80))
    inicio_mes = ctx.agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    try:
        r = (ctx.db.table("usage_events")
             .select("provider_cost_usd")
             .eq("company_id", ctx.company_id)
             .gte("occurred_at", inicio_mes.isoformat()).limit(5000).execute())
        gasto = sum(float(x.get("provider_cost_usd") or 0) for x in (r.data or []))
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Detector] usage_events: %s", type(exc).__name__)
        return []

    if gasto <= 0:
        return []
    dias = max(1.0, (ctx.agora - inicio_mes).total_seconds() / 86400.0)
    projecao = projetar_consumo(gasto, dias)
    percentual = round(100.0 * gasto / limite, 1)
    if percentual < percentual_alerta and projecao < limite:
        return []

    return [SignalDraft(
        company_id=ctx.company_id, signal_type="budget_risk",
        subject_type="budget", subject_id=ctx.agora.strftime("%Y-%m"),
        summary_redacted=(
            f"O custo técnico do mês está em US$ {gasto:.2f} ({percentual:.0f}% do "
            f"limite de US$ {limite:.2f}); no ritmo atual fecha em US$ {projecao:.2f}."),
        dedupe_key=chave_de_sinal(
            company_id=ctx.company_id, signal_type="budget_risk",
            subject_type="budget", subject_id=ctx.agora.strftime("%Y-%m"),
            rule_key=ctx.rule_key, rule_version=ctx.rule_version,
            parametros={"faixa": "acima" if percentual >= 100 else "alerta"}),
        trust_tier=TIER_ANALISE,  # projecao e analise derivada, nao dado vivo
        rule_key=ctx.rule_key, rule_version=ctx.rule_version,
        severity="high" if percentual >= 100 else "medium",
        confidence=0.9, impact_score=60.0, urgency_score=50.0,
        actionability_score=55.0, freshness_score=100.0,
        metadata={"gasto_usd": round(gasto, 2), "limite_usd": limite,
                  "projecao_usd": projecao, "percentual": percentual,
                  "metodo": "projeção linear sobre os dias decorridos do mês"},
        evidencias=[
            evidencia(tipo="soma", sistema="usage_events",
                      ref=f"company:{ctx.company_id}:{ctx.agora.strftime('%Y-%m')}",
                      resumo=f"custo técnico acumulado de US$ {gasto:.2f} em {dias:.0f} dias",
                      tier=TIER_DADO_VIVO,
                      valores={"gasto_usd": round(gasto, 2), "dias": round(dias, 1)}),
            evidencia(tipo="projecao", sistema="intelligence",
                      ref="projecao_linear",
                      resumo=f"projeção linear para o mês: US$ {projecao:.2f}",
                      tier=TIER_ANALISE,
                      valores={"projecao_usd": projecao, "limite_usd": limite}),
        ],
    )]
