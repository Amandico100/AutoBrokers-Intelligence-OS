# -*- coding: utf-8 -*-
"""SPEC-116 U4 — o LEGACY GATE: nenhum modelo fora do catálogo governado.

🔴 CHAMA O MOTOR (CLAUDE.md §9.4). Nada aqui confere "a string está no arquivo":
   · todo papel é resolvido por `model_policy.resolver()` — o mesmo código que a
     fábrica e os call sites chamam — com o BANCO dublado pelo snapshot;
   · a varredura de literais pergunta ao CATÁLOGO (o snapshot gerado da
     migration/banco), não a uma lista escrita neste arquivo.

O que ele garante (G0 · G1 parcial · G2 · G3 da SPEC-116 §9):
  1. todo papel resolve para APPROVED | CANDIDATE | DEPRECATED; os DEPRECATED
     saem numa LISTA impressa — aviso, não falha (D-116-11: legado vira
     DEPRECATED já e BLOCKED só depois que a bancada provar o substituto);
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
}

#: 🔴 O QUE HOJE VIOLA E É DE OUTRA FATIA. arquivo → (fatia dona, {literais}).
#: Cada fatia APAGA a sua linha (ou o literal) ao consertar; o teste falha se a
#: pendência sumir do código e continuar aqui, e falha com literal NOVO.
#: 📊 medido 23/09/2026 com `python tests/test_nenhum_modelo_fora_do_catalogo.py`.
LITERAIS_PENDENTES_DAS_FATIAS: dict = {
    # F2 — fábrica, mapas de família, histórico
    "backend/app/factories/llm_factory.py": ("F2", {
        "claude-fable", "claude-haiku-5", "claude-mythos", "gpt-5",
        "meta-llama/llama-3.1-405b", "o1", "o3"}),
    "backend/app/core/utils.py": ("F2", {"meta-llama/llama-3.1-405b", "o1", "o3"}),
    "backend/app/core/callbacks/cost_callback.py": ("F2", {"o1", "o3"}),
    "backend/app/services/langchain_service.py": ("F2", {
        "claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022", "claude-3-opus-20240229",
        "claude-opus-4-20250514", "claude-sonnet-4-20250514", "gemini-1.5-flash",
        "gemini-1.5-pro", "gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite",
        "gemini-2.5-pro", "gemini-3-pro-preview", "gemini-3-pro-preview-11-2025", "gpt-5.1",
        "gpt-5.2", "gpt-5.2-chat-latest", "gpt-5.2-pro", "o1", "o1-mini", "o3-mini"}),
    "backend/app/agents/nodes.py": ("F2", {"gpt-4-turbo"}),
    # F3 — call sites por fora da fábrica
    "backend/app/services/vision_service.py": ("F3", {"claude-3-5-sonnet-20241022"}),
    "backend/app/services/atlas/atlas_parser.py": ("F3", {"gpt-5.1"}),
    "backend/app/agents/tools/subagent_tool.py": ("F3", {"gpt-4-turbo"}),
    # F4 — nascimento e UI
    "components/admin/AgentConfigModal.tsx": ("F4", {
        "claude-3-5-sonnet-20240620", "claude-3-7-sonnet-20250219", "claude-opus-4-1-20250805",
        "claude-opus-4-20250514", "claude-sonnet-4-20250514", "deepseek-chat", "gemini-2.5-flash",
        "gemini-2.5-flash-lite", "gemini-2.5-pro", "gemini-3-deep-think", "gemini-3.1-pro-preview",
        "gpt-4.1", "gpt-5", "gpt-5.1", "gpt-5.2", "gpt-5.2-chat-latest", "grok-4",
        "meta-llama/llama-3.1-405b-instruct", "mistral-large-latest", "o1", "o1-mini", "o3",
        "o3-mini", "o3-pro"}),
    "lib/admin/agent-health.ts": ("F4", {"gpt-3.5-turbo", "gpt-4.1-mini"}),
    # SEM DONO na SPEC-116 §7 — whitelist do sync de preço do OpenRouter (reportado ao gerente)
    "backend/app/api/pricing.py": ("SEM_DONO", {
        "deepseek/deepseek-chat-v3-0324", "deepseek/deepseek-r1", "deepseek/deepseek-r1-0528",
        "deepseek/deepseek-v3.2", "meta-llama/llama-3.1-405b-instruct",
        "meta-llama/llama-3.1-70b-instruct", "meta-llama/llama-3.3-70b-instruct",
        "meta-llama/llama-4-maverick", "meta-llama/llama-4-scout", "mistralai/codestral-2501",
        "mistralai/devstral-medium", "mistralai/devstral-small", "mistralai/mistral-large-2411",
        "mistralai/mistral-small-3.2-24b-instruct", "moonshotai/kimi-k2-0711",
        "moonshotai/kimi-k2-0905", "moonshotai/kimi-k2.5", "qwen/qwen-2.5-72b-instruct",
        "qwen/qwen-2.5-coder-32b-instruct", "qwen/qwen3-235b-a22b",
        "qwen/qwen3-coder-480b-a35b-instruct", "qwen/qwen3.5-plus", "x-ai/grok-3",
        "x-ai/grok-3-mini", "x-ai/grok-4", "x-ai/grok-4.1-fast", "x-ai/grok-code-fast-1",
        "z-ai/glm-4.5-air", "z-ai/glm-4.7", "z-ai/glm-5"}),
}


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
def test_todo_papel_resolve_para_um_lifecycle_usavel(banco):
    papeis = MP.papeis_conhecidos()
    assert len(papeis) >= 20, papeis
    deprecados = []
    for papel in papeis:
        r = MP.resolver(papel)
        assert r.origem == "rota", (papel, r.origem)
        assert r.lifecycle in MP.LIFECYCLES_USAVEIS, (papel, r.model, r.lifecycle)
        assert r.classe_de_dado in (MP.catalogo()[r.model]["classes_de_dado"]), (papel, r.model)
        if r.lifecycle == "DEPRECATED":
            deprecados.append(f"{papel} → {r.provider}/{r.model}")
    print("\n⚠️ PAPÉIS EM MODELO DEPRECATED (aviso, não falha — D-116-11):")
    for linha in deprecados:
        print("   ·", linha)


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
    pap["atendimento"].update(provider="xiaomi", modelo_primario="mimo-v2.6-pro")
    MP.limpar_cache()
    with pytest.raises(MP.ModeloNaoResolvido, match="pii"):
        MP.resolver("atendimento")
    # e a bancada não fura a regra: override também respeita a classe da rota
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
