# -*- coding: utf-8 -*-
"""SPEC-116 U4 — o LEGACY GATE: nenhum modelo fora do catálogo governado.

🔴 CHAMA O MOTOR (CLAUDE.md §9.4). Nada aqui confere "a string está no arquivo":
   · todo papel é resolvido por `model_policy.resolver()` — o mesmo código que a
     fábrica e os call sites chamam — com o BANCO dublado pelo snapshot;
   · a varredura de literais pergunta ao CATÁLOGO (o snapshot gerado da
     migration/banco), não a uma lista escrita neste arquivo.

O que ele garante (G0 · G1 parcial · G2 · G3 da SPEC-116 §9):
  1. todo papel resolve para APPROVED (24/09/2026 — antes: APPROVED | CANDIDATE |
     DEPRECATED com aviso, D-116-11; a Onda A concluiu e produção só roda APPROVED);
  2. nenhuma reserva BLOCKED/HISTORICAL;
  3. todo literal de modelo em backend/app, backend/portal_worker, lib, app,
     components e docling-service/app existe no catálogo e não é
     BLOCKED/HISTORICAL. O que HOJE viola e é de outra fatia está em
     `LITERAIS_PENDENTES_DAS_FATIAS` (arquivo → fatia dona + literais). O teste
     falha com literal NOVO e falha com pendência que já sumiu (a lista só
     encolhe: cada fatia apaga a SUA linha ao consertar);
  4. papel/provedor desconhecido → `ModeloNaoResolvido`;
  5. LINHA DE CONTROLE: rota para `claude-3-5-sonnet-20241022` (BLOCKED) e rota
     `pii` para `mimo-v2.6-pro` (só publico) → VERMELHO obrigatório.
  6. 🔴 LEGACY GATE (Founder 24/09/2026 — conclusão da Onda A): produção só roda
     APPROVED. Rota em DEPRECATED (ex.: claude-sonnet-5) ou Luna abaixo do
     mínimo → VERMELHO; e todo literal DEPRECATED em código de produção tem de
     estar CLASSIFICADO em `DEPRECADOS_NAO_OPERACIONAIS` (HISTÓRICO · COMENTÁRIO
     · BASELINE) — literal DEPRECATED novo num caminho produtivo → VERMELHO.

Rodar (de backend/):  python -m pytest -q tests/test_nenhum_modelo_fora_do_catalogo.py -s
"""
from __future__ import annotations

import copy
import json
import os
import re
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
RAIZ_REPO = BACKEND.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.factories import model_policy as MP  # noqa: E402

SNAP = json.loads(MP.SNAPSHOT_PATH.read_text(encoding="utf-8"))

#: Onde mora código de produto (EVIDENCIAS/01 — o escopo do censo, sem testes).
PASTAS_VARRIDAS = (
    "backend/app", "backend/portal_worker", "lib", "app", "components", "docling-service/app",
)
EXTENSOES = {".py", ".ts", ".tsx", ".js", ".mjs", ".cjs"}
IGNORAR = ("__pycache__", "node_modules", "/tests/", ".test.", ".spec.")

#: Família de IDs de modelo do censo (EVIDENCIAS/01, topo): o literal INTEIRO
#: entre aspas tem de ter a forma de um id (minúsculas, sem espaço).
_LITERAL = re.compile(r"""["'`]([a-z0-9][a-z0-9._:/-]{1,90})["'`]""")
_FAMILIA = re.compile(
    r"^(?:[a-z0-9-]+/)?(?:"
    r"gpt-|chatgpt-|o[134](?:$|-)|claude-|gemini-|grok-|deepseek|mimo-|glm-|mistral|"
    r"(?:meta-)?llama|qwen|kimi-|whisper-|tts-|text-embedding-|embed-|rerank-|nova-|"
    r"eleven_|sonnet-|opus-|haiku-|fable-|mythos-)"
)

#: Palavras de PROVEDOR/família, não ids de modelo: o resolvedor precisa nomear
#: provedores (`PROVEDORES_CONHECIDOS`). Um prefixo terminado em "-" ("gpt-")
#: também não é id — é mapa de família, e esses estão nas pendências da F2.
_NAO_SAO_MODELO = {"deepseek", "mistral", "mistralai", "llama", "meta-llama", "qwen"}

#: Exceções PERMANENTES — arquivo → {literal: motivo}. Só o que NÃO escolhe modelo.
ALLOWLIST: dict = {
    "backend/app/models/conversation_log.py": {
        "gpt-5.1": "exemplo de documentação da API (json_schema_extra), não escolhe modelo",
    },
    # SPEC-116 F3b: benchmark COMPARATIVO de RAG do admin — modelos fixos por
    # desenho (rodadas só são comparáveis com o mesmo gerador/juiz). Não pede papel.
    # Hoje os quatro estão no catálogo (3 DEPRECATED, 1 APPROVED) e não violam; a
    # entrada existe para que, quando virarem BLOCKED, a decisão seja revista AQUI
    # (trocar o literal) e não descoberta no CI de outra SPEC.
    "backend/app/services/benchmark_service.py": {
        "gpt-4o": "benchmark comparativo de RAG: gerador de perguntas fixo por desenho",
        "gpt-4o-mini": "benchmark comparativo de RAG: HyDE fixo por desenho",
        "claude-sonnet-4-6": "benchmark comparativo de RAG: juiz de chunks fixo por desenho",
        "text-embedding-3-small": "benchmark comparativo de RAG: o embedding do índice",
    },
}

#: 🔴 O QUE HOJE VIOLA E É DE OUTRA FATIA. arquivo → (fatia dona, {literais}).
#: Cada fatia APAGA a sua linha (ou o literal) ao consertar; o teste falha se a
#: pendência sumir do código e continuar aqui, e falha com literal NOVO.
#: 📊 medido 23/09/2026 com `python tests/test_nenhum_modelo_fora_do_catalogo.py`.
LITERAIS_PENDENTES_DAS_FATIAS: dict = {
    # 📊 23/09/2026 — ZERADA. A F3a tirou os literais de langchain_service.py,
    # vision_service.py e subagent_tool.py; a F3b, o de atlas_parser.py ("gpt-5.1",
    # a tabela de preços própria do Atlas). Daqui em diante, literal fora do
    # catálogo é literal NOVO e o teste fica vermelho.
}


#: 🔴 (conserto único, red team P1): o gate só acusava literal FORA do catálogo
#: ou BLOCKED/HISTORICAL — 📊 a mutação `return ChatOpenAIGovernado(model=
#: "gpt-4o-mini")` na fábrica passava com 13 verdes, porque gpt-4o-mini é
#: DEPRECATED (usável). Agora TODO literal de modelo em código de produção é
#: INVENTARIADO: o que existia em 23/09 (📊 `varrer()` rodado, 26 literais em 19
#: arquivos — rótulos de log, docstrings, preço de fallback, dicionários de
#: tradução de modelo, embeddings = rota `embedding`) está aqui; literal NOVO,
#: mesmo de modelo APROVADO, fica VERMELHO — peça o PAPEL ao resolvedor ou
#: registre aqui com o motivo. A lista só ENCOLHE: literal que sumiu do código
#: tem de sair daqui (o teste acusa o vencido).
LITERAIS_CONHECIDOS: dict = {
    "backend/app/api/webhook.py": {"gpt-4o"},
    "backend/app/core/callbacks/cost_callback.py": {"gpt-4o-mini", "gpt-4o-mini-2024-07-18"},
    "backend/app/factories/llm_factory.py": {"claude-opus-5", "claude-sonnet-5", "gpt-4o"},
    "backend/app/services/agent_council.py": {"gpt-4o-mini"},
    "backend/app/services/attendance_distiller.py": {"claude-opus-5", "text-embedding-3-small"},
    "backend/app/services/audio_service.py": {"gpt-transcribe"},
    "backend/app/services/global_knowledge_seed.py": {"text-embedding-3-small"},
    "backend/app/services/ingestion_service.py": {"gpt-4o-mini"},
    "backend/app/services/knowledge/insurance_corpus.py": {"text-embedding-3-small"},
    "backend/app/services/langchain_service.py": {"claude-sonnet-5"},
    "backend/app/services/llama_guard_service.py": {"meta-llama/llama-prompt-guard-2-86m"},
    "backend/app/services/memory_service.py": {"gpt-4o-mini"},
    "backend/app/services/proactive_suggestions.py": {"claude-opus-5", "gpt-4o"},
    "backend/app/services/prompt_optimizer.py": {"claude-opus-5"},
    "backend/app/services/search_service.py": {"gpt-4o-mini"},
    "backend/app/services/vision_service.py": {"gpt-4o-mini"},
    "backend/portal_worker/adaptive.py": {"gpt-4o-mini"},
    "backend/portal_worker/modelo_do_portal.py": {"gpt-4o", "gpt-4o-mini"},
    # serviço SEM banco: o default acompanha à mão a rota `visao_documento` (24/09/2026)
    "docling-service/app/config.py": {"gpt-6-sol"},
}

#: 🔴 LEGACY GATE (24/09/2026). Todo literal de modelo DEPRECATED que AINDA mora
#: em código de produção, com a classificação que prova que ele NÃO escolhe o
#: modelo de nada que roda. 📊 medido 24/09/2026 com `varrer()` contra o catálogo
#: pós-20260924_01. Um DEPRECATED fora desta lista (ou um literal novo num
#: arquivo daqui) fica VERMELHO; a lista só encolhe.
DEPRECADOS_NAO_OPERACIONAIS: dict = {
    "backend/app/api/webhook.py": {"gpt-4o": "COMENTÁRIO: o `or gpt-4o` que morreu"},
    "backend/app/core/callbacks/cost_callback.py": {
        "gpt-4o-mini": "COMENTÁRIO: exemplo do mapeamento snapshot → id do catálogo",
        "gpt-4o-mini-2024-07-18": "COMENTÁRIO: idem"},
    "backend/app/factories/llm_factory.py": {
        "claude-opus-5": "COMENTÁRIO/HISTÓRICO: o despacho rodava opus 5 (EVIDENCIAS/02)",
        "claude-sonnet-5": "COMENTÁRIO/HISTÓRICO: idem",
        "gpt-4o": "COMENTÁRIO: o `or gpt-4o` que morreu"},
    "backend/app/services/agent_council.py": {"gpt-4o-mini": "COMENTÁRIO: o fallback que morreu"},
    "backend/app/services/attendance_distiller.py": {
        "claude-opus-5": "HISTÓRICO: as 18 sínteses gravadas pelo opus 5 (📊)"},
    "backend/app/services/benchmark_service.py": {
        "gpt-4o": "BASELINE: benchmark comparativo de RAG, fixo por desenho (ALLOWLIST)",
        "gpt-4o-mini": "BASELINE: idem",
        "claude-sonnet-4-6": "BASELINE: idem"},
    "backend/app/services/ingestion_service.py": {"gpt-4o-mini": "COMENTÁRIO: o literal que morreu"},
    "backend/app/services/langchain_service.py": {"claude-sonnet-5": "COMENTÁRIO/HISTÓRICO: a UI que o recusava"},
    "backend/app/services/llama_guard_service.py": {
        "meta-llama/llama-prompt-guard-2-86m":
            "⚠️ OPERACIONAL — DECISÃO PENDENTE: guarda de prompt (Groq), DEPRECATED desde antes "
            "da 116; sem substituto APPROVED no catálogo (trocar = escolher modelo = Founder)"},
    "backend/app/services/memory_service.py": {"gpt-4o-mini": "HISTÓRICO: o DEFAULT da coluna legada (📊)"},
    "backend/app/services/proactive_suggestions.py": {
        "claude-opus-5": "COMENTÁRIO/HISTÓRICO: custo medido com opus 5",
        "gpt-4o": "COMENTÁRIO: o default que morreu"},
    "backend/app/services/prompt_optimizer.py": {"claude-opus-5": "COMENTÁRIO/HISTÓRICO"},
    "backend/app/services/search_service.py": {"gpt-4o-mini": "COMENTÁRIO: o literal que morreu"},
    "backend/app/services/vision_service.py": {"gpt-4o-mini": "COMENTÁRIO: o literal que morreu"},
    "backend/portal_worker/adaptive.py": {"gpt-4o-mini": "COMENTÁRIO: a reserva calada que morreu"},
    "backend/portal_worker/modelo_do_portal.py": {
        "gpt-4o": "COMENTÁRIO: o fixo que morreu", "gpt-4o-mini": "COMENTÁRIO: a reserva que morreu"},
}


def deprecados_nao_classificados(achados: dict, catalogo: dict, classificados: dict) -> dict:
    """arquivo → {literais DEPRECATED sem classificação não-operacional}."""
    out: dict = {}
    for arq, lits in achados.items():
        ruins = {l for l in lits if (catalogo.get(l) or {}).get("lifecycle") == "DEPRECATED"}
        ruins -= set(classificados.get(arq, {}))
        if ruins:
            out[arq] = ruins
    return out


def literais_fora_do_inventario(achados: dict, conhecidos: dict):
    """(novos, vencidos) contra o inventário — a allowlist permanente não conta."""
    novos, vencidos = {}, {}
    for arq, lits in achados.items():
        n = set(lits) - set(ALLOWLIST.get(arq, {})) - set(conhecidos.get(arq, set()))
        if n:
            novos[arq] = n
    for arq, lits in conhecidos.items():
        v = set(lits) - set(achados.get(arq, set()))
        if v:
            vencidos[arq] = v
    return novos, vencidos


def _eh_id_de_modelo(s: str) -> bool:
    if s in _NAO_SAO_MODELO or s.endswith("-"):
        return False
    return bool(_FAMILIA.match(s))


def literais_do_texto(texto: str) -> set:
    return {m for m in _LITERAL.findall(texto) if _eh_id_de_modelo(m)}


def varrer(raiz: Path = RAIZ_REPO) -> dict:
    """arquivo (relativo, com /) → {literais de modelo}."""
    achados: dict = {}
    for pasta in PASTAS_VARRIDAS:
        base = raiz / pasta
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file() or p.suffix not in EXTENSOES:
                continue
            rel = p.relative_to(raiz).as_posix()
            if any(x in "/" + rel for x in IGNORAR):
                continue
            try:
                texto = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            lits = literais_do_texto(texto)
            if lits:
                achados[rel] = lits
    return achados


def violacoes(achados: dict, catalogo: dict) -> dict:
    """arquivo → {literais fora do catálogo ou BLOCKED/HISTORICAL}, menos a allowlist."""
    out: dict = {}
    for arq, lits in achados.items():
        ruins = set()
        for lit in lits:
            linha = catalogo.get(lit)
            if linha is None or linha.get("lifecycle") in MP.LIFECYCLES_PROIBIDOS:
                ruins.add(lit)
        ruins -= set(ALLOWLIST.get(arq, {}))
        if ruins:
            out[arq] = ruins
    return out


def comparar_com_pendentes(viol: dict, pendentes: dict):
    """(novos, vencidos): literal que viola sem estar pendente · pendência que já não viola."""
    novos = {a: v - set(pendentes.get(a, ("", set()))[1]) for a, v in viol.items()}
    novos = {a: v for a, v in novos.items() if v}
    vencidos = {a: set(p[1]) - viol.get(a, set()) for a, p in pendentes.items()}
    vencidos = {a: v for a, v in vencidos.items() if v}
    return novos, vencidos


# ---------------------------------------------------------------------------
# O dublê do BANCO (a única borda): o snapshot, copiado por teste
# ---------------------------------------------------------------------------
@pytest.fixture
def banco():
    cat = copy.deepcopy(SNAP["catalogo"])
    pap = copy.deepcopy(SNAP["papeis"])
    original = MP.leitor_do_banco
    MP.leitor_do_banco = lambda: (cat, pap)
    MP.limpar_cache()
    yield cat, pap
    MP.leitor_do_banco = original
    MP.limpar_cache()


# ---------------------------------------------------------------------------
# 1–2. todo papel resolve; reservas limpas
# ---------------------------------------------------------------------------
def test_todo_papel_resolve_para_um_modelo_de_producao(banco):
    """🔴 (24/09/2026) a verdade antiga era "DEPRECATED é aviso" (D-116-11); a Onda
    A concluiu e o Founder decidiu: produção só roda APPROVED. A lição migra: o
    esperado de cada papel vem da ROTA (snapshot), e o resolvedor confere."""
    cat, pap = banco
    papeis = MP.papeis_conhecidos()
    assert len(papeis) >= 20, papeis
    for papel in papeis:
        r = MP.resolver(papel)
        assert r.origem == "rota", (papel, r.origem)
        assert (r.provider, r.model, r.effort) == (
            pap[papel]["provider"], pap[papel]["modelo_primario"], pap[papel]["esforco"]), papel
        assert r.lifecycle in MP.LIFECYCLES_DE_PRODUCAO, (papel, r.model, r.lifecycle)
        assert r.classe_de_dado in (MP.catalogo()[r.model]["classes_de_dado"]), (papel, r.model)


def test_nenhuma_reserva_bloqueada_ou_historica(banco):
    cat, pap = banco
    for papel, rota in pap.items():
        if rota.get("modelo_reserva"):
            ciclo = cat[rota["modelo_reserva"]]["lifecycle"]
            assert ciclo not in MP.LIFECYCLES_PROIBIDOS, (papel, rota["modelo_reserva"], ciclo)
            assert MP.resolver(papel).reserva is not None


# ---------------------------------------------------------------------------
# 3. a varredura de literais (G0 / G3)
# ---------------------------------------------------------------------------
def test_nenhum_literal_novo_fora_do_catalogo():
    viol = violacoes(varrer(), SNAP["catalogo"])
    novos, vencidos = comparar_com_pendentes(viol, LITERAIS_PENDENTES_DAS_FATIAS)
    pend = sum(len(p[1]) for p in LITERAIS_PENDENTES_DAS_FATIAS.values())
    print(f"\npendências declaradas: {pend} literais em {len(LITERAIS_PENDENTES_DAS_FATIAS)} arquivos")
    assert not novos, (
        "literal de modelo FORA do catálogo (ou BLOCKED/HISTORICAL) que não é pendência de "
        f"fatia nenhuma — cadastre no catálogo ou peça o PAPEL ao resolvedor: {novos}")
    assert not vencidos, (
        "pendência que já sumiu do código — apague-a de LITERAIS_PENDENTES_DAS_FATIAS "
        f"(a lista só encolhe): {vencidos}")


def test_controle_um_literal_novo_num_call_site_fica_vermelho():
    """G0 · LINHA DE CONTROLE: o mesmo checador, com UM call site inventado."""
    achados = varrer()
    achados["backend/app/services/call_site_inventado.py"] = literais_do_texto(
        'llm = ChatOpenAI(model="gpt-4.5-preview")  # e um velho: "claude-3-5-haiku-20241022"')
    viol = violacoes(achados, SNAP["catalogo"])
    novos, _ = comparar_com_pendentes(viol, LITERAIS_PENDENTES_DAS_FATIAS)
    assert novos.get("backend/app/services/call_site_inventado.py") == {
        "gpt-4.5-preview", "claude-3-5-haiku-20241022"}, novos
    # e um literal APROVADO no mesmo lugar NÃO acusa (o checador sabe diferenciar)
    assert literais_do_texto('model="claude-sonnet-5"') == {"claude-sonnet-5"}
    assert not violacoes({"x.py": {"claude-sonnet-5"}}, SNAP["catalogo"])


def test_nenhum_literal_de_modelo_novo_em_codigo_de_producao():
    """🔴 (conserto único) TODO literal de modelo — até de modelo usável — é
    inventariado. Os DEPRECATED saem numa lista de AVISO."""
    achados = varrer()
    cat = SNAP["catalogo"]
    avisos = sorted(f"{a}: {l}" for a, ls in achados.items() for l in ls
                    if (cat.get(l) or {}).get("lifecycle") == "DEPRECATED")
    print(f"\n⚠️ LITERAIS DE MODELO DEPRECATED EM CÓDIGO DE PRODUÇÃO ({len(avisos)}, aviso):")
    for linha in avisos:
        print("   ·", linha)
    novos, vencidos = literais_fora_do_inventario(achados, LITERAIS_CONHECIDOS)
    assert not novos, (
        "literal de modelo NOVO em código de produção — peça o PAPEL ao resolvedor "
        f"(model_policy) ou registre em LITERAIS_CONHECIDOS com o motivo: {novos}")
    assert not vencidos, (
        f"literal que já sumiu do código — apague-o de LITERAIS_CONHECIDOS: {vencidos}")


def test_controle_literal_usavel_novo_na_fabrica_fica_vermelho():
    """LINHA DE CONTROLE (a mutação do red team): `gpt-4o-mini` (DEPRECATED,
    USÁVEL — o checador do catálogo não o acusa) reintroduzido na fábrica."""
    achados = {a: set(l) for a, l in varrer().items()}
    arq = "backend/app/factories/llm_factory.py"
    achados.setdefault(arq, set()).update(literais_do_texto(
        'return ChatOpenAIGovernado(model="gpt-4o-mini", api_key=api_key)'))
    assert not violacoes({arq: {"gpt-4o-mini"}}, SNAP["catalogo"]), \
        "pré-condição: o checador do CATÁLOGO não vê este literal (é usável)"
    novos, _ = literais_fora_do_inventario(achados, LITERAIS_CONHECIDOS)
    assert novos == {arq: {"gpt-4o-mini"}}, novos
    # e um arquivo NOVO com modelo APROVADO também acusa
    novos, _ = literais_fora_do_inventario(
        {"backend/app/services/novo.py": {"claude-sonnet-5"}}, LITERAIS_CONHECIDOS)
    assert novos == {"backend/app/services/novo.py": {"claude-sonnet-5"}}


def test_legacy_gate_nenhum_deprecated_operacional_novo():
    """🔴 LEGACY GATE: DEPRECATED em código de produção só com classificação."""
    achados = varrer()
    cat = SNAP["catalogo"]
    ruins = deprecados_nao_classificados(achados, cat, DEPRECADOS_NAO_OPERACIONAIS)
    assert not ruins, (
        "literal de modelo DEPRECATED em código de produção sem classificação — produção "
        "só roda APPROVED: peça o PAPEL ao resolvedor ou classifique em "
        f"DEPRECADOS_NAO_OPERACIONAIS: {ruins}")
    vencidos = {a: set(c) - achados.get(a, set()) for a, c in DEPRECADOS_NAO_OPERACIONAIS.items()}
    vencidos = {a: v for a, v in vencidos.items() if v}
    assert not vencidos, f"classificação de literal que já sumiu — apague-a (a lista só encolhe): {vencidos}"


def test_controle_legacy_gate_fica_vermelho_com_deprecated_novo():
    """LINHA DE CONTROLE: `gpt-4o-mini` num call site NOVO e `claude-sonnet-5` num
    arquivo já classificado (literal não) → os dois acusados."""
    cat = SNAP["catalogo"]
    assert cat["gpt-4o-mini"]["lifecycle"] == "DEPRECATED"
    assert cat["claude-sonnet-5"]["lifecycle"] == "DEPRECATED"
    achados = {a: set(l) for a, l in varrer().items()}
    achados["backend/app/services/call_site_novo.py"] = literais_do_texto('ChatOpenAI(model="gpt-4o-mini")')
    achados["backend/app/services/prompt_optimizer.py"] = set(achados.get(
        "backend/app/services/prompt_optimizer.py", set())) | {"claude-sonnet-5"}
    ruins = deprecados_nao_classificados(achados, cat, DEPRECADOS_NAO_OPERACIONAIS)
    assert ruins == {"backend/app/services/call_site_novo.py": {"gpt-4o-mini"},
                     "backend/app/services/prompt_optimizer.py": {"claude-sonnet-5"}}, ruins
    # controle do controle: um APPROVED novo NÃO é acusado por ESTE checador
    assert not deprecados_nao_classificados({"x.py": {"gpt-6-sol"}}, cat, {})


def test_controle_rota_de_producao_em_deprecated_e_recusada(banco):
    """A rota em claude-sonnet-5 (DEPRECATED) é recusada; a BANCADA ainda o mede."""
    cat, pap = banco
    assert cat["claude-sonnet-5"]["lifecycle"] == "DEPRECATED"
    pap["chat_principal"].update(provider="anthropic", modelo_primario="claude-sonnet-5", esforco=None)
    MP.limpar_cache()
    with pytest.raises(MP.ModeloNaoResolvido, match="APPROVED"):
        MP.resolver("chat_principal")
    r = MP.resolver("juiz_eval", override={"provider": "anthropic", "model": "claude-sonnet-5"})
    assert (r.model, r.origem, r.lifecycle) == ("claude-sonnet-5", "bancada", "DEPRECATED")


def test_controle_luna_abaixo_do_minimo_e_recusada_em_producao(banco):
    cat, pap = banco
    assert cat["gpt-6-luna"]["capacidades"].get("esforco_minimo_producao") == "medium"
    for esforco in ("low", "none", None):
        pap["memoria"].update(provider="openai", modelo_primario="gpt-6-luna", esforco=esforco)
        MP.limpar_cache()
        with pytest.raises(MP.ModeloNaoResolvido, match="exige esforço"):
            MP.resolver("memoria")
    # CONTROLE: medium e high passam; a bancada mede a Luna em low
    for esforco in ("medium", "high"):
        pap["memoria"]["esforco"] = esforco
        MP.limpar_cache()
        assert MP.resolver("memoria").effort == esforco
    r = MP.resolver("memoria", override={"provider": "openai", "model": "gpt-6-luna", "effort": "low"})
    assert (r.effort, r.origem) == ("low", "bancada")


def test_controle_candidate_nao_roda_em_producao(banco):
    cat, pap = banco
    assert cat["gpt-6-astra"]["lifecycle"] == "CANDIDATE"
    pap["atendimento"].update(provider="openai", modelo_primario="gpt-6-astra", esforco="medium")
    MP.limpar_cache()
    with pytest.raises(MP.ModeloNaoResolvido, match="APPROVED"):
        MP.resolver("atendimento")
    # e o modelo DO AGENTE (papel sem rota) também é produção
    with pytest.raises(MP.ModeloNaoResolvido, match="APPROVED"):
        MP.resolver("papel_sem_rota", agente={"llm_provider": "openai", "llm_model": "gpt-4o-mini"})
    r = MP.resolver("papel_sem_rota", agente={"llm_provider": "openai", "llm_model": "gpt-6-sol"})
    assert (r.model, r.origem) == ("gpt-6-sol", "agente")


def test_pendencias_tem_dono_e_fatia_valida():
    for arq, (fatia, lits) in LITERAIS_PENDENTES_DAS_FATIAS.items():
        assert fatia in ("F2", "F3", "F4", "F5a", "F6", "SEM_DONO"), (arq, fatia)
        assert lits, arq


# ---------------------------------------------------------------------------
# 4. desconhecido é ERRO
# ---------------------------------------------------------------------------
def test_papel_inexistente_e_erro(banco):
    with pytest.raises(MP.ModeloNaoResolvido):
        MP.resolver("papel_inexistente")


def test_provedor_desconhecido_e_erro(banco):
    cat, pap = banco
    with pytest.raises(MP.ModeloNaoResolvido):
        MP.resolver("atendimento", override={"provider": "moonshot", "model": "claude-sonnet-5"})
    pap["hyde"]["provider"] = "moonshot"
    MP.limpar_cache()
    with pytest.raises(MP.ModeloNaoResolvido):
        MP.resolver("hyde")


def test_modelo_fora_do_catalogo_e_erro(banco):
    with pytest.raises(MP.ModeloNaoResolvido):
        MP.resolver("atendimento", override={"provider": "openai", "model": "gpt-4.5-preview"})
    with pytest.raises(MP.ModeloNaoResolvido):
        MP.resolver("papel_novo", agente={"llm_provider": "openai", "llm_model": "gpt-4.5-preview"})


# ---------------------------------------------------------------------------
# 5. LINHA DE CONTROLE — defeitos históricos reintroduzidos ficam VERMELHOS
# ---------------------------------------------------------------------------
def test_controle_rota_para_modelo_retirado_e_recusada(banco):
    """G3: claude-3-5-sonnet-20241022 foi RETIRADO em 28/10/2025 (BLOCKED)."""
    cat, pap = banco
    assert cat["claude-3-5-sonnet-20241022"]["lifecycle"] == "BLOCKED"
    pap["visao"].update(provider="anthropic", modelo_primario="claude-3-5-sonnet-20241022")
    MP.limpar_cache()
    with pytest.raises(MP.ModeloNaoResolvido, match="lifecycle"):
        MP.resolver("visao")


def test_controle_rota_pii_para_modelo_sem_pii_e_recusada(banco):
    """G2: MiMo só pode ver dado público (D-116-06/10)."""
    cat, pap = banco
    assert "pii" not in cat["mimo-v2.6-pro"]["classes_de_dado"]
    assert pap["atendimento"]["classe_de_dado"] == "pii"
    # (24/09/2026) em produção um CANDIDATE já cai pelo lifecycle; para a regra de
    # CLASSE ser a que dispara, o dublê o promove — a lição LGPD continua provada.
    cat["mimo-v2.6-pro"]["lifecycle"] = "APPROVED"
    pap["atendimento"].update(provider="xiaomi", modelo_primario="mimo-v2.6-pro", esforco=None)
    MP.limpar_cache()
    with pytest.raises(MP.ModeloNaoResolvido, match="pii"):
        MP.resolver("atendimento")
    # e a bancada não fura a regra: override também respeita a classe da rota
    cat["mimo-v2.6-pro"]["lifecycle"] = "CANDIDATE"  # de volta ao valor real
    MP.limpar_cache()
    pap["atendimento"].update(provider="anthropic", modelo_primario="claude-sonnet-5")
    with pytest.raises(MP.ModeloNaoResolvido, match="pii"):
        MP.resolver("atendimento", override={"provider": "xiaomi", "model": "mimo-v2.6-pro"})
    # linha de controle do controle: rota PÚBLICA aceita o MiMo como CANDIDATE
    r = MP.resolver("extrator_planos", override={"provider": "xiaomi", "model": "mimo-v2.6-pro"})
    assert (r.model, r.origem, r.lifecycle) == ("mimo-v2.6-pro", "bancada", "CANDIDATE")


def test_controle_reserva_retirada_e_recusada(banco):
    cat, pap = banco
    pap["portal_decisao"].update(provider_reserva="anthropic", modelo_reserva="claude-3-5-haiku-20241022")
    MP.limpar_cache()
    with pytest.raises(MP.ModeloNaoResolvido):
        MP.resolver("portal_decisao")


# ---------------------------------------------------------------------------
# 6. o snapshot é o catálogo (uma fonte) · o preço vem dele (G8 parcial)
# ---------------------------------------------------------------------------
def _gerador():
    import importlib.util
    caminho = BACKEND / "scripts" / "gerar_snapshot_de_modelos.py"
    spec = importlib.util.spec_from_file_location("gerar_snapshot_de_modelos", caminho)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_snapshot_e_gerado_da_fonte_unica():
    if SNAP.get("origem") != "migration":
        pytest.skip(f"snapshot gerado do {SNAP.get('origem')!r}: o banco é a fonte agora")
    cat, pap = _gerador().ler_da_migration()
    assert SNAP["catalogo"] == cat, "snapshot divergiu da migration — rode scripts/gerar_snapshot_de_modelos.py"
    assert SNAP["papeis"] == pap
    assert all(r["lifecycle"] for r in cat.values()), "linha sem lifecycle"


class _BancoGravador:
    """Dublê do banco do LEDGER: llm_pricing indisponível (cai no snapshot) e
    token_usage_logs guarda o que seria inserido."""

    def __init__(self):
        self.inseridos = []
        self.client = self

    def table(self, nome):
        banco = self

        class _Q:
            def select(self, *a, **k):
                raise ConnectionError("banco de preço fora")

            def insert(self, linha):
                banco.inseridos.append((nome, linha))
                return self

            def execute(self):
                return type("R", (), {"data": [{"ok": 1}]})()

        return _Q()


@pytest.fixture
def uso():
    import app.core.database as _db
    import app.services.usage_service as U

    gravador = _BancoGravador()
    orig_db, orig_u = _db.get_supabase_client, U.get_supabase_client
    _db.get_supabase_client = U.get_supabase_client = lambda: gravador
    U._pricing_cache = {}
    U._cache_loaded_at = 0
    try:
        yield U.UsageService(), gravador
    finally:
        _db.get_supabase_client, U.get_supabase_client = orig_db, orig_u
        U._pricing_cache = {}
        U._cache_loaded_at = 0


def test_preco_vem_do_catalogo_com_cache_por_modelo(uso):
    svc, _ = uso
    assert svc.calculate_cost("claude-sonnet-5", 1_000_000, 1_000_000) == pytest.approx(12.0)
    # cache read do Opus 5.5 é 0,20/4 = 0,05× (não o 0,10 igual para todos de antes)
    assert svc.calculate_cost("claude-opus-5-5", 1_000_000, 0, cache_read_tokens=1_000_000)         == pytest.approx(0.20)
    # id datado que o provedor devolve casa com a linha sem data
    assert svc.calculate_cost("gpt-4o-2024-08-06", 1_000_000, 0) == pytest.approx(2.50)
    # contexto longo do GPT-6 Sol (> 272K): a chamada inteira no preço longo 4/15
    assert svc.calculate_cost("gpt-6-sol", 300_000, 1_000_000) == pytest.approx(0.3 * 4 + 15)


def test_preco_desconhecido_nao_e_o_do_mini(uso):
    svc, gravador = uso
    assert svc.get_pricing("modelo-que-nao-existe") is None
    assert svc.calculate_cost("modelo-que-nao-existe", 1_000_000, 1_000_000) == 0.0
    assert svc.track_cost_sync("chat", "modelo-que-nao-existe", 1000, 1000)
    _, linha = gravador.inseridos[-1]
    assert linha["total_cost_usd"] == 0.0
    assert linha["details"].get("preco_desconhecido") is True
    # linha de controle: modelo com preço grava custo e NÃO leva a flag
    assert svc.track_cost_sync("chat", "claude-sonnet-5", 1_000_000, 0)
    _, linha = gravador.inseridos[-1]
    assert linha["total_cost_usd"] == pytest.approx(2.0)
    assert "preco_desconhecido" not in linha["details"]
    # rerank 0/0 no catálogo = desconhecido, não "de graça"
    assert svc.get_pricing("rerank-multilingual-v3.0") is None


if __name__ == "__main__":  # medição: imprime as violações de hoje, por arquivo
    for arq, v in sorted(violacoes(varrer(), SNAP["catalogo"]).items()):
        print(f"{arq}: {sorted(v)}")
