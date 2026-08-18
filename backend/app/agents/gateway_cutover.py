"""Cutover do grafo para o Tool Gateway. SPEC-057 §Bloco I.

O problema
----------
Desde a SPEC-056 existe um Tool Gateway que responde, de forma composta e
auditável, *"este agente pode usar esta ferramenta?"*. Mas o grafo continuava
anexando ferramentas pelo caminho antigo — `tools_config`, capability solta,
router de HTTP entrando por conta própria. O registro estava pronto e ninguém
o consultava.

Trocar isso de uma vez seria mudar a autoridade do cérebro de um sistema em
produção sem rede. A SPEC-054 §9.4 exige o contrário: comparar antes e depois
das ferramentas carregadas, provar equivalência, e só então virar a chave.

Três modos
----------
    off      nada acontece. Comportamento idêntico ao de antes.
    shadow   o Gateway decide em paralelo, o diff é gravado, e o que vale
             continua sendo a lista antiga. Custo: uma consulta por conversa.
    on       o Gateway decide de verdade.

A regra que torna o modo `on` seguro
------------------------------------
O Gateway só pode **tirar** ferramenta, nunca acrescentar. Ele responde por
autoridade; quem constrói o objeto da ferramenta é o grafo. Se o Gateway
liberasse algo que o grafo não montou, não haveria o que anexar — e, mais
importante, um cutover que só reduz privilégio não consegue abrir brecha
nenhuma, por pior que seja o bug.

Falha aqui nunca derruba a conversa. Se o Gateway quebrar, o corretor continua
sendo atendido pelo caminho antigo e o erro vira registro. Autoridade que
derruba atendimento quando falha é pior do que autoridade nenhuma.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

MODO_OFF = "off"
MODO_SHADOW = "shadow"
MODO_ON = "on"

# Ferramentas que o Gateway não governa porque não são poder concedido: são
# o mínimo para o agente conversar. Tirar a busca no conhecimento da própria
# corretora não é restringir privilégio, é quebrar o produto.
SEMPRE_PERMITIDAS = frozenset({
    "knowledge_base_search",
    "buscar_conhecimento",
    "human_handoff",
    "transferir_para_humano",
})


def modo_atual() -> str:
    v = str(os.getenv("TOOL_GATEWAY_MODE", MODO_OFF)).strip().lower()
    return v if v in (MODO_OFF, MODO_SHADOW, MODO_ON) else MODO_OFF


@dataclass
class ResultadoCutover:
    modo: str
    aplicar: bool = False
    permitidas: set[str] = field(default_factory=set)
    skill_key: Optional[str] = None
    diff_identico: bool = True
    so_no_legado: list[str] = field(default_factory=list)
    so_no_gateway: list[str] = field(default_factory=list)
    erro: Optional[str] = None


def _chave_da_tool(t: Any) -> str:
    return str(getattr(t, "name", "") or getattr(t, "tool_key", "") or type(t).__name__)


# O nome que a ferramenta tem no LangChain nem sempre é a chave dela no
# Registry. Este mapa é a ponte — e é explícito de propósito: adivinhar por
# heurística faria o cutover negar ferramenta certa por diferença de nome.
NOME_PARA_CHAVE = {
    "knowledge_base_search": "knowledge.search",
    "buscar_conhecimento": "knowledge.search",
    "web_search": "research.web_search",
    "web_scrape": "research.web_scrape",
    "web_search_deep": "research.web_search_deep",
    "document_read": "research.document_read",
    "csv_analytics": "analytics.csv",
    "analisar_csv": "analytics.csv",
    # 🔴 O nome REAL da tool no runtime e `request_human_agent` (human_handoff.py).
    # Sem esta linha, `tool_invocations` ficava CEGA justamente para a
    # ferramenta que mais precisava ser auditada: em 17/08 a consulta "zero
    # entradas de handoff" nao provava nada, porque a tabela nunca conseguiria
    # ter uma. Instrumento cego transforma medicao em palpite.
    "request_human_agent": "support.human_handoff",
    "human_handoff": "support.human_handoff",
    "transferir_para_humano": "support.human_handoff",
    "control_plane_read": "operations.control_plane_read",
    "infocap_policy_lookup": "insurance.policy_lookup",
    "consultar_apolice": "insurance.policy_lookup",
    "vehicle_lookup": "insurance.policy_evidence",
    "insurer_dispatch": "insurance.insurer_dispatch",
    "portal_action": "portal.execute",
    "subagent": "delegation.subagent",
    "gerar_relatorio": "artifacts.generate_report",
    "avaliar_automacao": "factory.evaluate_request",
    # SPEC-060. Sem estas linhas, o cutover leria `pesquisar_na_web` como uma
    # chave que o Registry não conhece e a marcaria como "só no legado" — o
    # diff acusaria divergência onde não há, e a métrica que decide virar a
    # chave do Gateway ficaria errada para baixo.
    "pesquisar_na_web": "research.search_web",
    "monitorar_fonte": "research.create_monitor",
    "analisar_site": "research.site_audit",
    # SPEC-059.
    "briefing_da_corretora": "intelligence.briefing",
    "prioridades_da_corretora": "intelligence.findings",
    "responder_recomendacao": "intelligence.respond",
    "preferencias_de_briefing": "intelligence.preferences",
}


def chave_de_registro(t: Any) -> str:
    nome = _chave_da_tool(t)
    return NOME_PARA_CHAVE.get(nome, nome)


def avaliar(
    *,
    tools_legado: list[Any],
    supabase_client: Any,
    company_id: Optional[str],
    agent_role: str,
    texto_usuario: str = "",
    active_capabilities: Optional[dict] = None,
) -> ResultadoCutover:
    """Decide o que o Gateway diria, grava o diff e devolve o veredito.

    Chamada uma vez por montagem de grafo. Em `off` devolve imediatamente sem
    tocar no banco.
    """
    modo = modo_atual()
    if modo == MODO_OFF or not company_id or not supabase_client:
        return ResultadoCutover(modo=MODO_OFF)

    inicio = time.monotonic()
    legado = {chave_de_registro(t) for t in tools_legado}
    resultado = ResultadoCutover(modo=modo)

    try:
        from ..services.skills.gateway import ToolGateway
        from ..services.skills.registry import SkillRegistry

        # Sonda o Registry ANTES de resolver. Sem isto, banco fora do ar seria
        # indistinguível de "conversa sem procedimento": o `SkillRegistry`
        # engole a própria exceção e devolve lista vazia, o resolver devolve
        # None, e o diff sairia registrado como IDÊNTICO.
        #
        # O efeito seria o pior possível num cutover: a métrica diria "98% de
        # concordância, pode virar a chave" medindo um Gateway que nunca foi
        # consultado. Falha tem de aparecer como falha.
        cliente = getattr(supabase_client, "client", supabase_client)
        cliente.table("skill_bindings").select("id").limit(1).execute()

        registry = SkillRegistry(supabase_client)
        skill = registry.resolver(agent_role=agent_role, texto=texto_usuario,
                                  company_id=company_id)

        if skill is None:
            # Sem Skill resolvida não há procedimento a governar: a conversa é
            # conversa. Nesse caso o Gateway não tem opinião, e forçar uma
            # seria justamente o erro que o `resolver` devolvendo None evita.
            resultado.permitidas = legado
            resultado.diff_identico = True
            _gravar(supabase_client, company_id, agent_role, None, None,
                    legado, legado, [], [], [], True, modo,
                    int((time.monotonic() - inicio) * 1000), None)
            return resultado

        decisao = ToolGateway(supabase_client).selecionar(
            company_id=company_id, agent_role=agent_role, skill=skill,
            active_capabilities=active_capabilities or {})

        concedidas = set(decisao.keys())
        resultado.skill_key = skill.skill_key
        resultado.permitidas = concedidas

        so_legado = sorted(legado - concedidas - SEMPRE_PERMITIDAS)
        so_gateway = sorted(concedidas - legado)
        resultado.so_no_legado = so_legado
        resultado.so_no_gateway = so_gateway
        resultado.diff_identico = not so_legado and not so_gateway
        resultado.aplicar = modo == MODO_ON

        _gravar(supabase_client, company_id, agent_role, skill.skill_key,
                None, sorted(legado), sorted(concedidas), so_legado, so_gateway,
                decisao.denied, resultado.diff_identico, modo,
                int((time.monotonic() - inicio) * 1000), None)

        if not resultado.diff_identico:
            logger.info(
                "[Cutover] %s · skill=%s · a menos=%s · a mais=%s",
                modo, skill.skill_key, so_legado or "-", so_gateway or "-")

    except Exception as exc:  # noqa: BLE001
        # Fail-open DE PROPÓSITO, e só aqui. O caminho antigo continua sendo a
        # autoridade enquanto o novo não provar que funciona; derrubar o
        # atendimento do corretor porque o Gateway teve um erro seria trocar um
        # risco de privilégio por um risco de indisponibilidade — pior troca.
        logger.warning("[Cutover] falhou (%s) — seguindo pelo caminho antigo",
                       type(exc).__name__)
        resultado.erro = type(exc).__name__
        resultado.aplicar = False
        resultado.permitidas = legado
        _gravar(supabase_client, company_id, agent_role, None, None,
                sorted(legado), [], [], [], [], False, modo,
                int((time.monotonic() - inicio) * 1000), type(exc).__name__)

    return resultado


def aplicar(tools_legado: list[Any], r: ResultadoCutover) -> list[Any]:
    """Filtra a lista pelo veredito. Só subtrai — nunca acrescenta."""
    if not r.aplicar or not r.permitidas:
        return tools_legado

    mantidas, removidas = [], []
    for t in tools_legado:
        nome = _chave_da_tool(t)
        if nome in SEMPRE_PERMITIDAS or chave_de_registro(t) in r.permitidas:
            mantidas.append(t)
        else:
            removidas.append(nome)

    if removidas:
        logger.info("[Cutover] ON · skill=%s · removidas: %s",
                    r.skill_key, ", ".join(removidas))
    # Lista vazia nunca: um agente sem ferramenta nenhuma responde pior do que
    # um agente com o conjunto antigo, e o cutover não pode piorar o produto.
    return mantidas or tools_legado


def _gravar(db: Any, company_id: str, agent_role: str, skill_key: Optional[str],
            confianca: Optional[float], legado: list[str], gateway: list[str],
            so_legado: list[str], so_gateway: list[str], negadas: list,
            identico: bool, modo: str, ms: int, erro: Optional[str]) -> None:
    """Grava o diff. Nunca guarda o texto do usuário — só chaves de ferramenta."""
    try:
        cliente = getattr(db, "client", db)
        cliente.table("tool_gateway_shadow_diffs").insert({
            "company_id": company_id,
            "agent_role": agent_role,
            "skill_key": skill_key,
            "skill_confianca": confianca,
            "legado": legado,
            "gateway": gateway,
            "so_no_legado": so_legado,
            "so_no_gateway": so_gateway,
            "negadas": [{"tool": d.get("tool_key"), "motivo": d.get("motivo")}
                        for d in (negadas or [])][:20],
            "identico": identico,
            "modo": modo,
            "duracao_ms": ms,
            "erro": erro,
        }).execute()
    except Exception as exc:  # noqa: BLE001
        logger.debug("[Cutover] diff nao gravado: %s", type(exc).__name__)


def progresso(db: Any, dias: int = 7) -> dict:
    """Resumo do cutover — o que responde 'já pode virar a chave?'."""
    try:
        cliente = getattr(db, "client", db)
        r = (cliente.table("tool_gateway_shadow_diffs")
             .select("identico, modo, erro, so_no_legado, so_no_gateway")
             .order("created_at", desc=True).limit(2000).execute()).data or []
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "erro": type(exc).__name__}

    total = len(r)
    if not total:
        return {"ok": True, "decisoes": 0, "pronto_para_virar": False,
                "motivo": "nenhuma decisão registrada ainda"}

    identicas = sum(1 for x in r if x.get("identico"))
    erros = sum(1 for x in r if x.get("erro"))
    a_menos = sum(1 for x in r if x.get("so_no_legado"))
    a_mais = sum(1 for x in r if x.get("so_no_gateway"))
    pct = round(100.0 * identicas / total, 1)

    # 300 decisões e 98% não são números mágicos: é o mínimo para uma amostra
    # cobrir os papéis e os caminhos de conversa que existem hoje. Abaixo disso
    # "bateu sempre" significa "quase não rodou".
    pronto = total >= 300 and pct >= 98.0 and erros == 0
    return {
        "ok": True, "decisoes": total, "identicas": identicas,
        "pct_identicas": pct, "com_erro": erros,
        "tool_a_menos": a_menos, "tool_a_mais": a_mais,
        "pronto_para_virar": pronto,
        "motivo": ("critérios atendidos" if pronto else
                   f"faltam {max(0, 300 - total)} decisões · {pct}% idênticas · {erros} erro(s)"),
    }
