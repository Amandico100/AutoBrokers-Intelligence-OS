# -*- coding: utf-8 -*-
"""SPEC-125 S0 — a bancada da CONVERSA (segurado simulado ⇄ agente de atendimento REAL). Sem LLM: os três
"modelos" (agente, segurado, juiz) são dublês de teste; o MOTOR é o do produto.

O FIO que o primeiro teste atravessa (CLAUDE.md §9.4 — o motor, nunca uma cópia):
    cenário → segurado (falas fixas + o braço do segurado) → `texto_combinado_dos_itens` + `webhook._midia_do_turno`
    → `graph.invoke_agent` (`_build_initial_state` REAL + grafo REAL + `tool_node` sobre dublês) → resposta
    → `checagens_da_conversa` + juiz LLM → `julgar_caso`/`classificar` → o relatório da bancada.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from app.services.evals import bancada as B  # noqa: E402
from app.services.evals import dubles as D  # noqa: E402

PROTO_RX = re.compile(r"Protocolo (\d{6,})")


# ---------------------------------------------------------------------------
# Os "modelos" de teste — só a borda (o modelo) é falsa
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _classificador_da_confirmacao_na_borda():
    """🔴 SPEC-126 U2 parte B (§9.3 — a lição MIGRA): o portão do acionamento passou a ser regex E
    classificador (`insurer_dispatch_tool.portao_da_confirmacao`). Aqui o classificador é um MODELO-DUBLÊ na
    BORDA (`llm_factory.invocar_com_reserva`, papel `confirmacao`) que diz OK para TUDO — então quem decide
    todo "não acionou" deste arquivo continua sendo a regex; e nenhum teste chama modelo pago."""
    from app.services.evals import bancada_confirmacao as _BC

    with _BC.classificador_duble_na_borda() as chamadas:
        yield chamadas


class _Modelo:
    """Duck-typed como chat model. `papel`: agente_bom · agente_ruim · segurado_e_juiz."""

    def __init__(self, papel: str, vistos: dict):
        self.papel, self.vistos = papel, vistos
        self.model_name = f"fake:{papel}"
        self.callbacks = []

    def bind_tools(self, tools, **_k):
        self.vistos.setdefault("tools", sorted(getattr(t, "name", str(t)) for t in tools or []))
        return self

    async def ainvoke(self, msgs, config=None, **_k):
        from langchain_core.messages import AIMessage

        msgs = msgs if isinstance(msgs, list) else [msgs]
        texto, calls = (self._agente(msgs) if self.papel.startswith("agente") else self._segurado_ou_juiz(msgs))
        return AIMessage(content=texto, tool_calls=calls,
                         usage_metadata={"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
                         response_metadata={"model_name": self.model_name})

    def invoke(self, msgs, config=None, **_k):
        import asyncio

        return asyncio.get_event_loop().run_until_complete(self.ainvoke(msgs, config))

    @staticmethod
    def _call(nome, args):
        return [{"name": nome, "args": args, "id": f"call_{nome}_{len(str(args))}", "type": "tool_call"}]

    def _agente(self, msgs):
        sistema = next((D._texto_de(m.content) for m in msgs if D._tipo(m) == "system"), "")
        self.vistos.setdefault("sistemas", []).append(sistema)
        humanas = [D._texto_de(m.content) for m in msgs if D._tipo(m) == "human"]
        self.vistos.setdefault("humanas", []).append(humanas[-1] if humanas else "")
        ultima = msgs[-1]
        h = (humanas[-1] if humanas else "").lower()
        if D._tipo(ultima) == "tool":
            m = PROTO_RX.search(D._texto_de(ultima.content))
            if m:
                return f"Feito! Protocolo {m.group(1)}. O prestador já foi designado.", []
            return "Achei sua apólice ✅ Onde o carro está agora?", []
        if "chaveiro" in h:
            return "", self._call("infocap_policy_lookup", {"document": self.vistos["cpf"]})
        if "acácias" in h or "acacias" in h:
            if self.papel == "agente_ruim":
                return "Certo. E qual é a cidade?", []
            return "Confirma o chaveiro na Rua das Acácias 120, Centro, Campinas - SP?", []
        if "sim pode" in h:
            return "", self._call("insurer_dispatch", {"subservice": "chaveiro", "insurer_key": "allianz",
                                                       "line_kind": "auto", "dados_confirmados": True})
        return "Por nada! Qualquer coisa estou aqui.", []

    def _segurado_ou_juiz(self, msgs):
        sistema = D._texto_de(msgs[0].content)
        if sistema.startswith("Você avalia"):
            self.vistos["juiz_chamado"] = True
            return json.dumps({"criterios": [{"id": "c1", "veredito": "certo", "trecho": "Confirma"}],
                               "tom_humano": 4, "entendeu_o_obvio": 5, "comentario": "ok"}), []
        self.vistos["segurado_chamadas"] = self.vistos.get("segurado_chamadas", 0) + 1
        if self.vistos["segurado_chamadas"] == 1:
            return json.dumps({"mensagens": ["sim pode"], "encerrar": False}), []
        return json.dumps({"mensagens": ["valeu"], "encerrar": True}), []


CENARIO = {
    "chave": "conv-teste-fio", "id": "T1", "critico": True, "tenant": "A", "origem": "teste SPEC-125 S0",
    "persona": "teste", "objetivo": "chaveiro", "telefone": "{{FONE:T1}}",
    "fatos": {"cpf": {"valor": "{{CPF:T1}}", "fonte": "segurado", "perguntas": [r"\bcpf\b"]},
              "placa": {"valor": "{{PLACA:A1}}", "fonte": "apolice", "perguntas": [r"\bplaca\b"]},
              "endereco": {"valor": "Rua das Acácias 120, Centro, Campinas - SP", "fonte": "segurado",
                           "perguntas": [r"endereco|onde (voce|vc|o carro) (esta|ta)"]},
              "cidade": {"valor": "Campinas - SP", "fonte": "segurado", "perguntas": [r"\bcidade\b"],
                         "conhecido_com": ["endereco"]}},
    "roteiro": {"falas_fixas": [[{"imagem": "Foto da chave do carro caída no banco do motorista, porta travada."},
                                 "oi preciso de chaveiro, a chave ficou trancada. cpf {{CPF:T1}}"],
                                ["Rua das Acácias 120, Centro, Campinas - SP"]], "max_turnos": 5},
    "dubles_de": "atd-n2-guincho-feliz",
    "dubles": {"insurer_dispatch": {"resposta": {"status": "dispatched",
                                                 "content": "ACIONAMENTO REGISTRADO. Protocolo {{APOLICE:PT1}}."},
                                    "chave": ["subservice", "insurer_key"]}},
    "gabarito": {"pessoa": "proibida", "efeitos_exatos": {"insurer_dispatch": 1}, "protocolo_exato": "{{APOLICE:PT1}}",
                 "criterios_llm": ["confirmou numa linha"]},
}


def _caso_do_teste():
    import copy

    linha = copy.deepcopy(CENARIO)
    gab = linha["gabarito"]
    return {"chave": linha["chave"], "id": "T1", "papel": "conversa", "nivel": "N3", "critico": True, "tenant": "A",
            "entrada": {**{k: linha.get(k) for k in ("persona", "objetivo", "fatos", "roteiro", "telefone")},
                        "dubles": B._resolver_dubles(linha)},
            "oraculo": {"efeitos_exatos": gab["efeitos_exatos"], "conversa": gab}, "origem": linha["origem"],
            "falhas_injetadas": [], "efeitos_proibidos": []}


def _rodar(papel_do_agente: str, *, orcamentos=None, teto=50.0):
    vistos = {"cpf": D.materializar("{{CPF:T1}}")}

    def construir(resolvido, _cb):
        return _Modelo(B._campo(resolvido, "model"), vistos)

    def resolver(papel, *, override, **_k):
        return {"papel": papel, "provider": override["provider"], "model": override["model"],
                "effort": None, "api_surface": "teste", "capacidades": {"tools": True, "max_output": 512}}

    rel = B.rodar_bancada("conversa", [f"fake:{papel_do_agente}"], casos=[_caso_do_teste()], k=1, nivel="N3",
                          construir_llm=construir, resolver=resolver,
                          precos=lambda b: {"entrada": 1.0, "saida": 4.0}, teto_usd=teto,
                          segunda="fake:segurado_e_juiz", orcamentos=orcamentos)
    return rel, vistos


# ---------------------------------------------------------------------------
# 1 · O FIO — cenário → agente REAL → juiz
# ---------------------------------------------------------------------------
def test_o_fio_cenario_segurado_agente_real_juiz():
    rel, vistos = _rodar("agente_bom")
    assert not rel.parada, rel.parada
    r = rel.resultados[0]
    assert r.erro is None, r.erro
    est = r.rastro["estado"]
    trans = est["transcricao"]
    # o segurado: 2 falas fixas + 2 do braço do segurado (a última encerra) → 4 turnos
    assert [t["origem"] for t in trans] == ["fixa", "fixa", "modelo", "modelo"], trans
    # a rajada (foto + texto) entrou como UMA mensagem, montada pelo WEBHOOK (marca do buffer + visão do turno)
    entrada1 = trans[0]["entrada_do_agente"]
    assert "🖼️ [Imagem enviada]" in entrada1 and "[CONTEXTO VISUAL — imagem enviada pelo cliente]" in entrada1
    assert "chave do carro caída" in entrada1 and trans[0]["itens"] == 2
    # o prompt é o de PRODUÇÃO (`_build_initial_state`), não o de `_estado_base`
    sistema = vistos["sistemas"][0]
    for bloco in ("SÓ RELATE O QUE VOCÊ REALMENTE FEZ",            # base do papel (prompts.py)
                  "atendente de assistencia e sinistro",            # o molde do agente (agent_system_prompt)
                  "COMO CONDUZIR UM ACIONAMENTO",                   # bloco gerado dos corredores (graph.py)
                  "COMO FALAR DE NÚMERO E DE DADO"):                # graph.py
        assert bloco in sistema, bloco
    assert D.materializar("{{CORRETORA:A}}") in sistema               # a corretora FICTÍCIA do tenant
    # as ferramentas REAIS do papel (schema real) chegaram ao modelo, e a execução foi nos dublês
    assert {"infocap_policy_lookup", "insurer_dispatch", "request_human_agent"} <= set(vistos["tools"])
    assert [t["tools"] for t in trans][0] == ["infocap_policy_lookup"]
    assert "insurer_dispatch" in trans[2]["tools"]
    assert vistos.get("juiz_chamado") and est["juiz_llm"]["nota"] is not None
    # o protocolo que a ferramenta devolveu chegou ao segurado; nenhuma checagem falhou
    falhos = [v["evaluator_slug"] for v in r.vereditos if not v["passou"]]
    assert r.resultado == "PASS", (falhos, [t["agente"] for t in trans])
    slugs = {v["evaluator_slug"] for v in r.vereditos}
    assert {"perguntou_o_que_ja_sabia", "repetiu_pergunta", "pessoa_na_regra", "protocolo_exato",
            "sem_protocolo_inventado", "baloes_por_turno", "efeitos_exatos", "juiz_llm"} <= slugs
    # o custo do segurado/juiz é separado do agente
    assert r.rastro["segunda"]["chamadas"] == 3


def test_o_fio_fica_vermelho_com_o_agente_que_repergunta():
    """LINHA DE CONTROLE (§9.2): o MESMO cenário, o agente que pergunta a cidade depois do endereço completo."""
    rel, _ = _rodar("agente_ruim")
    r = rel.resultados[0]
    falhos = {v["evaluator_slug"]: v["motivo"] for v in r.vereditos if not v["passou"]}
    assert r.resultado == "FAIL" and "perguntou_o_que_ja_sabia" in falhos, falhos
    assert "cidade" in falhos["perguntou_o_que_ja_sabia"]


# ---------------------------------------------------------------------------
# 2 · "perguntou o que já sabia" consegue ficar vermelha (e não fica com a confirmação)
# ---------------------------------------------------------------------------
def _checa(falas_agente, fatos, segurado=None):
    caso = {"entrada": {"fatos": fatos, "dubles": {}}, "oraculo": {"conversa": {}}}
    trans = [{"turno": i + 1, "segurado": [(segurado or {}).get(i + 1, "...")], "entrada_do_agente": "",
              "agente": a, "tools": [], "tool_args": [], "baloes": 1, "itens": 1} for i, a in enumerate(falas_agente)]
    return B.checagens_da_conversa(caso, {"texto": "\n".join(falas_agente), "estado": {"transcricao": trans}})


CPF = D.materializar("{{CPF:X9}}")
FATOS = D.materializar({"cpf": {"valor": CPF, "fonte": "segurado", "perguntas": [r"\bcpf\b"]},
                        "placa": {"valor": "{{PLACA:A1}}", "fonte": "apolice", "perguntas": [r"\bplaca\b"]}})


def test_perguntou_o_que_ja_sabia_fica_vermelha_e_a_confirmacao_nao():
    # controle: pedir o CPF ANTES de ele ser dito é legítimo
    ok = _checa(["Me passa seu CPF?", "Obrigada!"], FATOS, {2: f"é {CPF}"})
    assert ok["perguntou_o_que_ja_sabia"]["passou"], ok
    # mutação: pedir de novo DEPOIS de ele ter dito
    ruim = _checa(["Me passa seu CPF?", "Pode me passar o CPF do titular?"], FATOS, {2: f"meu cpf {CPF}"})
    assert not ruim["perguntou_o_que_ja_sabia"]["passou"], ruim
    # confirmar TRAZENDO o valor (T8) não é repergunta
    conf = _checa(["Me passa seu CPF?", f"Confirma o CPF {CPF[:3]}.***.***-{CPF[-2:]} e o {CPF[4:7]}{CPF[8:11]}?"],
                  FATOS, {2: f"{CPF}"})
    assert conf["perguntou_o_que_ja_sabia"]["passou"], conf
    # dado da apólice pedido ao segurado
    ap = _checa(["Qual a placa do carro?"], FATOS)
    assert not ap["pediu_dado_da_apolice"]["passou"] and not ap["perguntou_o_que_ja_sabia"]["passou"]


def test_repeticao_protocolo_inventado_e_pessoa_sem_regra():
    rep = _checa(["Qual o modelo do seu carro?", "Certo. Qual o modelo do seu carro?"], {})
    assert not rep["repetiu_pergunta"]["passou"]
    inv = _checa(["Pronto, seu protocolo é 4455667788."], {})
    assert not inv["sem_protocolo_inventado"]["passou"]
    caso = {"entrada": {"fatos": {}, "dubles": {}}, "oraculo": {"conversa": {"pessoa": "proibida"}}}
    s = {"texto": "x", "efeitos": {"request_human_agent": 1},
         "estado": {"transcricao": [{"turno": 1, "segurado": ["oi"], "agente": "x", "tools": ["request_human_agent"],
                                     "tool_args": [{}], "baloes": 1, "itens": 1}]}}
    assert not B.checagens_da_conversa(caso, s)["pessoa_na_regra"]["passou"]


def test_nota_do_juiz():
    j = B.nota_do_juiz({"criterios": [{"id": "c1", "veredito": "certo"}, {"id": "c2", "veredito": "errado"}],
                        "tom_humano": 5, "entendeu_o_obvio": 5})
    assert not j["passou"] and j["errados"] == ["c2"] and 0 < j["nota"] < 1
    assert B.nota_do_juiz({"criterios": [{"id": "c1", "veredito": "certo"}], "tom_humano": 4,
                           "entendeu_o_obvio": 4})["passou"]


# ---------------------------------------------------------------------------
# 3 · O TETO DO LEDGER — lido FORA da borda, só details.papel='conversa', e a rodada PARA
# ---------------------------------------------------------------------------
def _ledger(gasto_conversa: float):
    return D.SupabaseDuble({
        "llm_pricing": [{"model_name": "gpt-6-luna", "provider": "openai"}],
        "token_usage_logs": [
            {"service_type": "bancada", "model_name": "gpt-6-luna", "details->>papel": "conversa",
             "total_cost_usd": gasto_conversa},
            {"service_type": "bancada", "model_name": "gpt-6-luna", "details->>papel": "visao", "total_cost_usd": 9.0}]})


def test_o_ledger_e_lido_fora_da_borda_e_so_da_conversa(monkeypatch):
    import app.core.database as db

    cliente = _ledger(0.03)
    # o caminho do CLI: sem `cliente=`, o cliente do produto é capturado na CONSTRUÇÃO (fora da borda)
    monkeypatch.setattr(db, "get_supabase_client", lambda *a, **k: cliente)
    orc = B.orcamentos_da_conversa(["openai", "duble"], 0.05, "2026-10-01T00:00:00+00:00")
    assert list(orc) == ["openai"]
    o = orc["openai"]
    assert abs(o.inicial - 0.03) < 1e-9 and abs(o.teto_usd - 0.02) < 1e-9   # a linha de 'visao' não conta
    # DENTRO da borda (o banco do produto é um dublê VAZIO): a releitura continua no cliente capturado
    with D.borda_isolada(D.SupabaseDuble()):
        cliente.tabelas["token_usage_logs"][0]["total_cost_usd"] = 0.045
        for _ in range(o.a_cada - 1):
            o.reservar(0.0)
        with pytest.raises(B.TetoDeGastoAtingido):
            o.reservar(0.01)            # 10ª reserva relê: 0.045 + 0.01 > 0.05


def test_o_teto_para_a_conversa():
    o = B.orcamentos_da_conversa(["fake"], 0.0005, "2026-10-01T00:00:00+00:00", ler=lambda p, d: 0.0)
    rel, _ = _rodar("agente_bom", orcamentos=o)
    assert rel.parada and rel.parada.startswith("teto_usd"), rel.parada


# ---------------------------------------------------------------------------
# 4 · O CORPUS e o MOLDE
# ---------------------------------------------------------------------------
def test_o_corpus_tem_os_16_cenarios_do_laudo_e_as_2_rajadas():
    cs = B.carregar_cenarios_da_conversa()
    ids = [c["id"] for c in cs]
    assert ids == [f"C{i}" for i in range(1, 17)] + ["R1", "R2"], ids
    assert {c["id"] for c in cs if c["critico"]} == {"C6", "C7", "C10", "C13", "C15", "C16"}
    assert len({c["chave"] for c in cs}) == len(cs)
    for c in cs:
        m = D.materializar(c)
        assert "{{" not in json.dumps(m, ensure_ascii=False), c["chave"]
        for f in m["entrada"]["fatos"].values():
            for rx in f.get("perguntas") or []:
                re.compile(rx)
        assert m["entrada"]["dubles"].get("infocap_policy_lookup"), c["chave"]
    r1 = next(c for c in cs if c["id"] == "R1")["entrada"]["roteiro"]["falas_fixas"][0]
    r2 = next(c for c in cs if c["id"] == "R2")["entrada"]["roteiro"]["falas_fixas"][0]
    assert len(r1) == 5 and sum(1 for x in r2 if isinstance(x, dict) and "imagem" in x) == 8 and len(r2) == 9
    assert [c["id"] for c in B.carregar_cenarios_da_conversa("C1,R2")] == ["C1", "R2"]


def test_o_molde_e_o_do_produto():
    ts = Path(RAIZ).parent / "lib" / "admin" / "agent-blueprints-canonical.ts"
    if not ts.exists():
        pytest.skip("lib/ fora desta árvore (contêiner do backend)")
    texto = ts.read_text(encoding="utf-8")
    bloco = texto[texto.index("EVEN_ATTENDANCE_BLUEPRINT"):]
    arr = bloco[bloco.index("system_prompt_template: [") + len("system_prompt_template: ["):bloco.index("].join(' ')")]
    tpl = " ".join(p.replace("\\'", "'") for p in re.findall(r"'((?:[^'\\]|\\.)*)'", arr))
    m = json.loads((B.CORPUS_DIR / "conversa" / "agente_molde.json").read_text(encoding="utf-8"))
    assert m["template"] == tpl, "o molde do produto mudou: regenere conversa/agente_molde.json"
    a = B.agente_molde("B")
    assert "{{attendant_name}}" not in a["agent_system_prompt"] and "{{CORRETORA:B}}" in a["agent_system_prompt"]
    assert a["is_active"] is False and a["agent_role"] == "attendance"
