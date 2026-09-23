# -*- coding: utf-8 -*-
"""SPEC-116 G10 — a bancada grava, calcula pass^k, corta no teto e vê o efeito duplicado.

Cada guarda aqui tem a sua LINHA DE CONTROLE (CLAUDE.md §9.2/§9.3): o braço-dublê
`perfeito` passa e o `burro` / `duplicador` / `vazador` falha. Um guarda que só
testa o lado verde é carimbo.

O motor é o do produto (`create_agent_graph` → `agent_node` → `tool_node`);
dublê só na borda (LLM, tool, banco). Nada sai do processo.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from app.services.evals import bancada as B  # noqa: E402
from app.services.evals import dubles as D  # noqa: E402


def _caso(chave: str) -> dict:
    papel = None
    for p in B.PAPEIS:
        for c in B.carregar_casos(p):
            if c["chave"] == chave:
                return c
    raise AssertionError(f"caso {chave} sumiu do corpus (papel {papel})")


def _slugs_falhos(r) -> list:
    return [v["evaluator_slug"] for v in r.vereditos if not v["passou"]]


# ---------------------------------------------------------------------------
# G10 · grava no MESMO lugar da Eval Fabric
# ---------------------------------------------------------------------------
def test_run_grava_braco_tentativa_custo_tokens_latencia_resultado_rastro():
    banco = D.SupabaseDuble()
    casos = [_caso("atd-n1-cpf-guincho"), _caso("atd-n1-humano-cancelar")]
    rel = B.rodar_bancada("atendimento", ["duble:perfeito", "duble:burro"], casos, k=2, nivel="N1",
                          gravar=True, teto_usd=10, cliente=banco)
    runs = banco.tabelas["eval_runs"]
    assert len(runs) == 4, "2 braços × k=2 → 4 eval_runs (cada tentativa é um run)"
    assert {r["grupo_bancada"] for r in runs} == {rel.grupo_bancada}
    assert sorted(r["tentativa"] for r in runs) == [1, 1, 2, 2]
    for r in runs:
        assert r["braco"]["provider"] == "duble" and r["braco"]["model"] in ("perfeito", "burro")
        assert r["papel"] == "atendimento" and r["nivel"] == "N1"
        assert r["status"] in ("passed", "failed") and r["terminado_em"]
        assert r["custo_usd"] > 0 and r["tokens"]["in"] > 0
    linhas = [l for l in banco.tabelas["eval_case_results"] if l["evaluator_slug"] == "bancada:caso"]
    assert len(linhas) == 8, "4 runs × 2 casos"
    for l in linhas:
        assert l["resultado"] in B.RESULTADOS
        assert l["custo_usd"] > 0 and l["tokens"]["in"] > 0 and l["latencia_ms"] >= 0
        assert "tool_calls" in l["rastro"] and "efeitos" in l["rastro"]
    # os vereditos de cada juiz também vão, um por linha (UNIQUE run×caso×juiz intacta)
    chaves = {(l["run_id"], l["case_id"], l["evaluator_slug"]) for l in banco.tabelas["eval_case_results"]}
    assert len(chaves) == len(banco.tabelas["eval_case_results"])
    perfeito = {r["id"] for r in runs if r["braco"]["model"] == "perfeito"}
    assert all(l["resultado"] == "PASS" for l in linhas if l["run_id"] in perfeito)
    assert any(l["resultado"] == "FAIL" for l in linhas if l["run_id"] not in perfeito), \
        "CONTROLE: o burro tem de falhar em algum caso"
    # e o relatório relido do banco bate com o de memória
    tabela = B.relatorio_do_banco(rel.grupo_bancada, cliente=banco)
    assert "duble:perfeito" in tabela and "duble:burro" in tabela


def test_resultado_e_append_only_como_na_eval_fabric():
    banco = D.SupabaseDuble()
    banco.table("eval_case_results").insert({"run_id": "r", "case_id": "c", "evaluator_slug": "x", "passou": True}).execute()
    with pytest.raises(RuntimeError):
        banco.table("eval_case_results").update({"passou": False}).eq("run_id", "r").execute()


# ---------------------------------------------------------------------------
# G10 · pass^k = TODAS as k passaram (não "alguma passou")
# ---------------------------------------------------------------------------
def test_pass_hat_k_exige_todas_as_tentativas():
    rs = [{"chave": "x", "resultado": "PASS"}, {"chave": "x", "resultado": "FAIL"}, {"chave": "x", "resultado": "PASS"},
          {"chave": "y", "resultado": "PASS"}, {"chave": "y", "resultado": "PASS"}, {"chave": "y", "resultado": "PASS"}]
    m = B.calcular_metricas(rs)
    assert m["pass_at_1"] == pytest.approx(5 / 6)
    assert m["pass_hat_k"] == pytest.approx(0.5), "x falhou 1 de 3 → não conta para pass^k"


def test_pass_hat_k_de_ponta_a_ponta_com_braco_instavel():
    """Um braço que acerta na 1ª tentativa e erra na 2ª: pass@1 = 50 %, pass^k = 0."""
    chamadas = {"n": 0}

    def construir(resolvido, callbacks):
        chamadas["n"] += 1
        return D.LLMDuble("perfeito" if chamadas["n"] % 2 == 1 else "burro")

    rel = B.rodar_bancada("atendimento", ["duble:instavel"], [_caso("atd-n1-cpf-guincho")], k=2,
                          construir_llm=construir, teto_usd=5)
    m = rel.bracos["duble:instavel"]
    assert [r.resultado for r in rel.resultados] == ["PASS", "FAIL"]
    assert m["pass_at_1"] == pytest.approx(0.5)
    assert m["pass_hat_k"] == 0.0


# ---------------------------------------------------------------------------
# G10 · o teto de US$ CORTA — e o run fecha como 'error' com o motivo
# ---------------------------------------------------------------------------
def test_teto_de_usd_corta_a_rodada_e_fecha_o_run_com_motivo():
    banco = D.SupabaseDuble()
    casos = B.carregar_casos("atendimento", nivel="N1")[:6]
    # 1 chamada custa ~0,03 US$ de reserva (8192 tokens de saída × 4 US$/M) → teto de 0,05 deixa passar 1
    rel = B.rodar_bancada("atendimento", ["duble:perfeito"], casos, k=1, teto_usd=0.05,
                          gravar=True, cliente=banco)
    assert rel.parada and rel.parada.startswith("teto_usd"), rel.parada
    assert len(rel.resultados) < len(casos), "o teto tem de cortar ANTES do fim"
    assert rel.gasto_usd <= 0.05
    run = banco.tabelas["eval_runs"][0]
    assert run["status"] == "error" and run["motivo_parada"] == "teto_usd"


def test_braco_sem_preco_no_catalogo_e_recusado():
    rel = B.rodar_bancada("atendimento", ["openai:modelo-que-nao-existe"], [_caso("atd-n1-cpf-guincho")], k=1,
                          precos=lambda b: None, teto_usd=5)
    assert rel.resultados == []
    assert rel.recusados and "sem preço" in rel.recusados[0]["motivo"]


def test_teto_padrao_vem_do_env(monkeypatch):
    monkeypatch.setenv("BANCADA_TETO_USD", "7.5")
    assert B.teto_padrao() == 7.5
    monkeypatch.delenv("BANCADA_TETO_USD")
    assert B.teto_padrao() == 100.0


# ---------------------------------------------------------------------------
# G10 · efeito duplicado (tool chamada 2× com a mesma chave) ⇒ FAIL
# ---------------------------------------------------------------------------
def test_efeito_duplicado_e_detectado_e_reprova():
    caso = _caso("atd-n2-guincho-msg-duplicada")
    rel = B.rodar_bancada("atendimento", ["duble:perfeito", "duble:duplicador"], [caso], k=1, nivel="N2", teto_usd=5)
    por = {r.braco: r for r in rel.resultados}
    assert por["duble:perfeito"].resultado == "PASS", "CONTROLE: quem lê o histórico não repete o acionamento"
    dup = por["duble:duplicador"]
    assert dup.resultado == "FAIL"
    assert dup.rastro["duplicados"] >= 1
    assert "efeitos_exatos" in _slugs_falhos(dup)
    assert rel.bracos["duble:duplicador"]["efeitos_duplicados"] >= 1
    assert rel.bracos["duble:perfeito"]["efeitos_duplicados"] == 0


def test_registro_conta_duplicado_por_chave_de_idempotencia():
    reg = D.RegistroDeEfeitos()
    for _ in range(2):
        reg.registrar(tool="insurer_dispatch", args={"subservice": "guincho", "insurer_key": "allianz"},
                      tenant="A", efeito=True, campos_da_chave=["subservice", "insurer_key"])
    reg.registrar(tool="insurer_dispatch", args={"subservice": "chaveiro", "insurer_key": "allianz"},
                  tenant="A", efeito=True, campos_da_chave=["subservice", "insurer_key"])
    assert reg.duplicados() == 1
    assert reg.contagem("insurer_dispatch") == 3


# ---------------------------------------------------------------------------
# G10 · dois tenants: resposta do A com dado do B ⇒ FAIL
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("chave,nivel", [("atd-n1-dois-tenants", "N1"), ("atd-n2-dois-tenants", "N2"),
                                         ("chat-n2-dois-tenants", "N2")])
def test_resposta_do_tenant_a_com_dado_do_b_reprova(chave, nivel):
    caso = _caso(chave)
    rel = B.rodar_bancada(caso["papel"], ["duble:perfeito", "duble:vazador"], [caso], k=1, nivel=nivel, teto_usd=5)
    por = {r.braco: r for r in rel.resultados}
    assert por["duble:perfeito"].resultado == "PASS", _slugs_falhos(por["duble:perfeito"])
    assert por["duble:vazador"].resultado == "FAIL"
    assert "sem_dado_de_outro_tenant" in _slugs_falhos(por["duble:vazador"])


def test_n2_dois_tenants_roda_as_duas_corretoras_no_mesmo_processo():
    caso = _caso("atd-n2-dois-tenants")
    rel = B.rodar_bancada("atendimento", ["duble:perfeito"], [caso], k=1, nivel="N2", teto_usd=5)
    tenants = {e["tenant"] for e in rel.resultados[0].rastro["efeitos"]}
    assert tenants == {"A", "B"}, "a conversa do B tem de ter rodado antes (senão o guarda não prova nada)"


# ---------------------------------------------------------------------------
# 🔴 SPEC-116 F6 — DEFEITO DE PRODUTO que o dublê REALISTA expôs (não é da bancada)
# ---------------------------------------------------------------------------
#: 📊 Com a consulta de apólice na FORMA REAL (dict + contrato) e
#: `POLICY_INTELLIGENCE_V2=true` (bancada.FLAGS_DO_AGENTE), o Chat Principal
#: entra em LAÇO na pergunta de detalhe com anáfora ("Ela cobre eletricista?"):
#: `agent_node` força a consulta pelo contexto (`_policy_context_tool_args`,
#: nodes.py ~1325) → `tool_node` → `should_continue_after_tools` devolve "agent"
#: (v2) → `agent_node` força DE NOVO, porque a última humana continua sendo a
#: mesma pergunta. Medido: 7 consultas forçadas seguidas até a janela de 15
#: mensagens derrubar a pergunta — e aí o modelo responde sem ela. Até o braço
#: `perfeito` reprovava.
#: ✅ CONSERTADO no conserto único da SPEC-116 (`nodes._consulta_forcada_ja_feita_no_turno`:
#: a consulta forçada roda UMA vez por pergunta). 📊 Os 4 xfail(strict) deram XPASS
#: e o marcador SAIU (CLAUDE.md §9.3 — a lição migra, não morre): estes casos agora
#: GUARDAM o conserto — reintroduzir o laço os deixa VERMELHOS.
CASOS_DO_LACO_DA_APOLICE = ("chat-n2-apolice-e-cobertura", "chat-n2-429-retomada", "chat-n2-500-no-meio")


# ---------------------------------------------------------------------------
# LINHA DE CONTROLE (§9.2): a bancada SEPARA o perfeito do burro
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("papel,nivel", [("atendimento", "N1"), ("atendimento", "N2"), ("chat_principal", "N1"),
                                         ("chat_principal", "N2"), ("portal_decisao", "N1"), ("dispatch", "N1"),
                                         ("memoria", "N1"), ("visao", "N1"), ("cobranca", "N1")])
def test_linha_de_controle_separa_perfeito_de_burro(papel, nivel):
    casos = B.carregar_casos(papel, nivel=nivel)   # (os casos do laço voltaram: o laço foi consertado)
    rel = B.rodar_bancada(papel, ["duble:perfeito", "duble:burro"], casos, k=1, nivel=nivel, teto_usd=50)
    p, b = rel.bracos["duble:perfeito"], rel.bracos["duble:burro"]
    assert p["pass_at_1"] == 1.0, [(r.chave, _slugs_falhos(r), r.erro) for r in rel.resultados
                                   if r.braco == "duble:perfeito" and r.resultado != "PASS"]
    assert b["pass_at_1"] is not None and p["pass_at_1"] - b["pass_at_1"] >= 0.45, (papel, b["pass_at_1"])


# ---------------------------------------------------------------------------
# Falha injetada: 429/timeout do provedor → retomada sem efeito dobrado
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("chave", ["atd-n2-guincho-429-depois-da-tool", "atd-n2-guincho-timeout-provedor",
                                   "chat-n2-429-retomada"])
def test_falha_injetada_no_provedor_recupera_sem_duplicar(chave):
    caso = _caso(chave)
    rel = B.rodar_bancada(caso["papel"], ["duble:perfeito"], [caso], k=1, nivel="N2", teto_usd=5)
    r = rel.resultados[0]
    assert r.resultado == "PASS", (_slugs_falhos(r), r.erro)
    assert r.rastro["falhas_injetadas"], "a falha tem de ter DISPARADO (senão o caso não testou nada)"
    assert r.rastro["duplicados"] == 0
    assert rel.bracos["duble:perfeito"]["recuperacao_apos_falha"] == 1.0


def test_blocked_by_infra_nao_conta_contra_o_modelo():
    """🔴 A lição MIGROU (CLAUDE.md §9.3). Antes da F3b o portal caía CALADO no
    gpt-4o-mini depois de um 500 — e a bancada marcava BLOCKED por isso. A F3b
    matou o rebaixamento: erro do provedor agora vira `ask_human` (needs_human)
    com o motivo, SEM outro modelo. Continua sendo falha de INFRA: sai como
    BLOCKED_BY_INFRA e fica fora do pass@1 — e o guarda agora afirma também que
    houve UM pedido só (nenhum modelo trocado por baixo)."""
    caso = _caso("portal-n1-falha-500-reserva-calada")
    rel = B.rodar_bancada("portal_decisao", ["duble:perfeito"], [caso, _caso("portal-n1-20-relacao")], k=1, teto_usd=5)
    por = {r.chave: r for r in rel.resultados}
    bloq = por["portal-n1-falha-500-reserva-calada"]
    assert bloq.resultado == "BLOCKED_BY_INFRA", (bloq.resultado, bloq.erro)
    assert "ask_human" in (bloq.erro or "") and "sem trocar de modelo" in (bloq.erro or "")
    assert bloq.rastro["estado"]["action"] == "ask_human"
    pedidos = bloq.rastro["pedidos_http"]
    assert len(pedidos) == 1 and pedidos[0].get("erro"), pedidos
    assert bloq.rastro["falhas_injetadas"], "a falha tem de ter DISPARADO"
    m = rel.bracos["duble:perfeito"]
    assert m["blocked_by_infra"] == 1 and m["pass_at_1"] == 1.0 and m["pass_hat_k"] == 1.0


def test_controle_o_mesmo_caso_sem_a_falha_passa():
    """CONTROLE (§9.2): tirando SÓ a falha injetada, o mesmo caso passa com o
    perfeito — o BLOCKED acima é da falha, não da tela nem do oráculo."""
    caso = json.loads(json.dumps(_caso("portal-n1-falha-500-reserva-calada")))
    caso["falhas_injetadas"] = []
    rel = B.rodar_bancada("portal_decisao", ["duble:perfeito"], [caso], k=1, teto_usd=5)
    r = rel.resultados[0]
    assert r.resultado == "PASS", (r.erro, _slugs_falhos(r))
    assert len(r.rastro["pedidos_http"]) == 1 and not r.rastro["pedidos_http"][0].get("erro")


def test_nada_sai_do_processo_o_banco_do_produto_e_o_duble():
    """Durante o motor, `get_supabase_client` do PRODUTO é o dublê — e volta depois."""
    import app.core.database as db

    original = db.get_supabase_client
    with D.borda_isolada() as banco:
        assert db.get_supabase_client() is banco
    assert db.get_supabase_client is original


# ---------------------------------------------------------------------------
# A migration: expand-first, APPLY/VERIFY/ROLLBACK, UNIQUE intocada
# ---------------------------------------------------------------------------
def test_migration_expande_a_eval_fabric_sem_tocar_a_unique():
    caminho = os.path.join(RAIZ, "supabase", "migrations", "20260923_03_spec116_bancada_na_eval_fabric.sql")
    sql = open(caminho, encoding="utf-8").read()
    for marca in ("APPLY:", "VERIFY", "ROLLBACK", "EXPAND-FIRST: sim"):
        assert marca in sql
    for col in ("braco", "papel", "nivel", "grupo_bancada", "tentativa", "custo_usd", "tokens", "motivo_parada"):
        assert f"alter table public.eval_runs add column if not exists {col} " in sql, col
    for col in ("resultado", "custo_usd", "tokens", "latencia_ms", "rastro", "erro"):
        assert f"alter table public.eval_case_results add column if not exists {col} " in sql, col
    ativo = "\n".join(l for l in sql.splitlines() if not l.strip().startswith("--"))
    assert "drop " not in ativo.lower(), "expand-first: nenhum DROP fora do rodapé comentado"
    assert "'PASS', 'FAIL', 'PARTIAL', 'BLOCKED_BY_INFRA'" in sql


# ---------------------------------------------------------------------------
# O comando do gerente, do jeito que ele vai rodar
# ---------------------------------------------------------------------------
def test_cli_roda_a_linha_de_controle_em_ensaio(tmp_path):
    saida = tmp_path / "rel.json"
    r = subprocess.run([sys.executable, os.path.join("scripts", "bancada.py"), "--papel", "atendimento",
                        "--braco", "dublê:perfeito", "--braco", "dublê:burro", "--k", "1", "--nivel", "N1",
                        "--ensaio", "--saida", str(saida)],
                       cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", timeout=600)
    assert r.returncode == 0, r.stderr[-2000:]
    assert "duble:perfeito" in r.stdout and "duble:burro" in r.stdout and "ensaio" in r.stdout
    dados = json.loads(saida.read_text(encoding="utf-8"))
    assert dados["papel"] == "atendimento" and len(dados["resultados"]) == 2 * len(B.carregar_casos("atendimento", nivel="N1"))
    r2 = subprocess.run([sys.executable, os.path.join("scripts", "bancada.py"), "--relatorio", str(saida)],
                        cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert r2.returncode == 0 and "duble:perfeito" in r2.stdout


@pytest.mark.parametrize("chave", CASOS_DO_LACO_DA_APOLICE)
def test_perfeito_passa_na_pergunta_de_detalhe_com_contexto_de_apolice(chave):
    """O `perfeito` TEM de passar nestes casos — e a consulta de apólice roda UMA
    vez no turno (o laço media 7). Guarda do conserto do laço."""
    caso = _caso(chave)
    rel = B.rodar_bancada("chat_principal", ["duble:perfeito"], [caso], k=1, nivel="N2", teto_usd=5)
    r = rel.resultados[0]
    assert r.resultado == "PASS", (_slugs_falhos(r), r.erro)
    # 📊 depois do conserto: 3 consultas em 2 turnos (a do modelo + no máximo UMA
    # forçada por pergunta); o laço fazia ≥ 7. Teto: uma por turno + a forçada.
    consultas = sum(1 for e in r.rastro["efeitos"] if e["tool"] == "infocap_policy_lookup")
    assert consultas <= len(caso["entrada"]["turnos"]) + 1, consultas


# ---------------------------------------------------------------------------
# 🔴 SPEC-116 F6 — o dublê de tool devolve a FORMA REAL (dict), não texto
# ---------------------------------------------------------------------------
def test_duble_de_tool_devolve_o_dict_intacto_e_o_texto_intacto():
    import asyncio

    class _Real:
        name, description, args_schema = "infocap_policy_lookup", "", None

    reg = D.RegistroDeEfeitos()
    forma = {"content": "briefing", "data": {"status": "found"}, "policy_response_contract": {"provider": "infocap"}}
    dub = D.DubleDeTool(_Real(), registro=reg, tenant="A", estado={"resposta": forma, "efeito": False})
    volta = asyncio.run(dub._arun(document="x"))
    assert volta == forma and isinstance(volta, dict), "dict tem de chegar ao tool_node como dict"
    assert volta is not forma, "cópia: o tool_node não pode mutar o estado do caso"
    dub_txt = D.DubleDeTool(_Real(), registro=reg, tenant="A", estado={"resposta": "texto", "efeito": False})
    assert asyncio.run(dub_txt._arun(document="x")) == "texto"


def test_corpus_consulta_de_apolice_tem_o_contrato_real_e_o_mascaramento_do_papel():
    vistos = 0
    for papel, mascarado in (("atendimento", True), ("chat_principal", False)):
        for c in B.carregar_casos(papel, nivel="N2"):
            est = (c["entrada"].get("dubles") or {}).get("infocap_policy_lookup") or {}
            respostas = list((est.get("respostas_por_tenant") or {}).values()) or [est.get("resposta")]
            for r in respostas:
                assert isinstance(r, dict), (c["chave"], "a consulta de apólice voltou a ser TEXTO")
                assert r["policy_response_contract"]["provider"] == "infocap"
                assert r["policy_response_contract"]["rendered_safe_answer"]
                assert ("client_document" not in r["data"]) is mascarado, (c["chave"], papel)
                vistos += 1
    assert vistos >= 18


def test_contexto_da_apolice_nasce_da_forma_real_e_nao_do_texto():
    """Chat Principal (core): com a forma REAL o `tool_node` monta `infocap_policy_context`
    no turno 1. LINHA DE CONTROLE: o MESMO caso com o `content` como TEXTO (a v1) → vazio."""
    import copy

    caso = _caso("chat-n2-dois-tenants")
    rel = B.rodar_bancada("chat_principal", ["duble:perfeito"], [caso], k=1, nivel="N2", teto_usd=5)
    ctx = rel.resultados[0].rastro["estado"]["contexto_da_apolice_por_turno"]
    assert rel.resultados[0].resultado == "PASS"
    assert "selected_policy_number" in ctx[0] and "document" in ctx[0], ctx

    controle = copy.deepcopy(caso)
    est = controle["entrada"]["dubles"]["infocap_policy_lookup"]
    est["respostas_por_tenant"] = {k: v["content"] for k, v in est["respostas_por_tenant"].items()}
    rel_c = B.rodar_bancada("chat_principal", ["duble:perfeito"], [controle], k=1, nivel="N2", teto_usd=5)
    assert rel_c.resultados[0].rastro["estado"]["contexto_da_apolice_por_turno"] == [[]], (
        "a linha de controle tem de ficar SEM contexto — senão o guarda acima não prova nada")


def test_o_texto_do_turno_e_o_final_response_quando_existe():
    from langchain_core.messages import AIMessage

    out = {"messages": [AIMessage(content="rascunho do modelo")], "final_response": "texto que o produto envia"}
    assert B._texto_do_turno(out) == "texto que o produto envia"
    assert B._texto_do_turno({"messages": [AIMessage(content="só a IA")], "final_response": None}) == "só a IA"


def test_erro_do_provedor_engolido_pelo_motor_e_infra_e_nao_falha_do_modelo():
    """📊 F6: o dispatch (`o_cerebro_ja_sabe`: `except Exception → (None, "")`) deu
    20 % a todos os braços reais, com 0 chamadas concluídas. Chamada TENTADA e não
    concluída = BLOCKED_BY_INFRA. CONTROLE: o mesmo braço respondendo lixo = FAIL."""
    caso = _caso("disp-n1-allianz-ref")

    class _SemCredito(D.LLMDuble):
        async def ainvoke(self, entrada, config=None, **kw):
            raise RuntimeError("You have no credits remaining")

    class _Lixo(D.LLMDuble):
        async def ainvoke(self, entrada, config=None, **kw):
            from langchain_core.messages import AIMessage
            return AIMessage(content="nao sei", usage_metadata={"input_tokens": 5, "output_tokens": 2,
                                                                "total_tokens": 7})

    def _com(cls):
        rel = B.rodar_bancada("dispatch", [{"provider": "falso", "model": "m", "preco": {"entrada": 1, "saida": 1}}],
                              [caso], k=1, construir_llm=lambda *_a, **_k: cls("burro"), teto_usd=1,
                              resolver=lambda papel, override: {"provider": "falso", "model": "m"},
                              precos=lambda b: {"entrada": 1.0, "saida": 1.0})
        return rel.resultados[0]

    r = _com(_SemCredito)
    assert r.resultado == "BLOCKED_BY_INFRA" and "engoliu" in (r.erro or ""), (r.resultado, r.erro)
    c = _com(_Lixo)
    assert c.resultado == "FAIL", "controle: o modelo respondeu e errou — isso É do modelo"
