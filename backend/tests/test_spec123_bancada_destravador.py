# -*- coding: utf-8 -*-
"""SPEC-123 F2a — a BANCADA HONESTA do destravador.

🔴 O TESTE DO FIO (a 1ª entrega): um caso D REAL do corpus (uma trava que HOJE vai a uma pessoa)
atravessa o motor NOVO da bancada — `carregar_casos_do_destravador` (sessão + FICHA) →
`motor_destravador` → `destravador.destravar` REAL (prompt do destravador, parser, POLÍTICA EM CÓDIGO,
2ª opinião de OUTRO provedor, conferente do produto) → veredito do JUIZ da bancada. Dublê SÓ na borda:
o cliente do provedor (o braço e o braço da 2ª opinião) e o diário.

Mais: o limiar calculado sobre resultados sintéticos (G3), o teto POR PROVEDOR lido do ledger (dublê
do SELECT) parando a rodada, o corpus (T e D primeiro, ≥ 40 casos D, ficha, PII = 0 com controle).
"""
from __future__ import annotations

import json
import re
import types
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage

from tests.test_spec122_sombra_e_sem_chute import FIO, _fio_fixo  # noqa: F401 — fixture autouse

B = FIO["app.services.evals.bancada"]
AC = FIO["app.services.acao_do_cerebro"]

PASTA = Path(__file__).parent / "corpus" / "bancada" / "cerebro"


def _todos():
    return B.carregar_casos_do_destravador()


def _casos_d():
    return [json.loads(l) for l in (PASTA / "casos_d.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


def _caso(pred):
    return next(c for c in _todos() if pred(c))


def _um_d_de_deduzir():
    """Uma trava REAL do ponto B: a tela que escolhe o serviço (o motor devolve
    `tela_que_decide:escolhe_o_servico` → hoje, uma pessoa), com gabarito PROVADO pela tela seguinte."""
    return _caso(lambda c: c["oraculo"]["destravador"]["grupo"] == "D"
                 and c["entrada"]["gatilho"] == "tela_que_decide:escolhe_o_servico"
                 and c["oraculo"]["destravador"]["classe_esperada"] == "deduzir"
                 and c["oraculo"]["destravador"]["prova"] == "sim"
                 and c["oraculo"]["destravador"]["aceitas"])


def _um_de_custo():
    """Uma tela de CUSTO numa seguradora que ESPERA a resposta do segurado (ida e volta permitida):
    ali a política do produto PERGUNTA ao segurado com o valor. (Allianz e Alfa → PESSOA, também seguro.)"""
    return _caso(lambda c: c["oraculo"]["destravador"].get("nunca") == "aceite_de_custo"
                 and c["entrada"]["seguradora"] not in B.SEM_IDA_E_VOLTA)


def _valor_certo(caso):
    a = caso["oraculo"]["destravador"]["aceitas"][0]
    return str(a.get("tecla") or a.get("rotulo") or a.get("literal"))


def _outra_opcao(caso):
    """Uma opção da tela DIFERENTE da certa (a resposta ERRADA, reversível)."""
    D = FIO["app.services.insurer_dispatch_service"]
    tela = caso["entrada"]["tela"]
    ops = [d for d, _ in D.opcoes_numeradas(tela)] or [str(i) for i, _ in enumerate(D._rotulos_da_tela(tela), 1)]
    certo = B._opcao_escolhida(tela, _valor_certo(caso))[0]
    return next(o for o in ops if o != certo and not B._RX_OPCAO_GRAVE.search(
        B._norm_opcao(B._opcao_escolhida(tela, o)[1])))


class _Braco:
    """O CLIENTE do provedor, dublado: responde pela tela do pedido e diz QUEM respondeu."""

    def __init__(self, modelo, respostas):
        self.modelo = modelo
        self.respostas = respostas
        self.pedidos = []
        self.callbacks = []
        self.model_name = modelo

    async def ainvoke(self, msgs, config=None, **kw):
        self.pedidos.append(msgs)
        user = msgs[-1].content
        for tela, resp in self.respostas.items():
            if tela in user:
                return AIMessage(content=resp, response_metadata={"model_name": self.modelo})
        return AIMessage(content="{}", response_metadata={"model_name": self.modelo})


def _js(**k):
    return json.dumps(k, ensure_ascii=False)


def _rodar(casos, resp1, resp2, *, orcamentos=None, teto=5.0):
    b1 = _Braco("gpt-6.1-sol", resp1)
    b2 = _Braco("claude-sonnet-5-5", resp2)
    por_modelo = {"gpt-6.1-sol": b1, "claude-sonnet-5-5": b2}

    def resolver(papel, override):
        return types.SimpleNamespace(papel=papel, provider=override["provider"], model=override["model"],
                                     effort=override.get("effort"), capacidades={"max_output": 1024},
                                     api_surface="duble", versao_da_rota="t", reserva=None)

    rel = B.rodar_bancada("destravador", ["openai:gpt-6.1-sol:high"], casos, k=1,
                          construir_llm=lambda resolvido, cbs: por_modelo[resolvido.model],
                          resolver=resolver, precos=lambda b: {"entrada": 1.0, "saida": 4.0},
                          teto_usd=teto, segunda="anthropic:claude-sonnet-5-5", orcamentos=orcamentos)
    ver = {r.chave: (r.rastro.get("estado") or {}).get("veredito_destravador") or {} for r in rel.resultados}
    return rel, ver, b1, b2


# =========================================================================== 🔴 O TESTE DO FIO
def test_o_fio_uma_trava_real_atravessa_o_destravador_do_produto_e_o_juiz_separa_certo_de_grave():
    d = _um_d_de_deduzir()
    t = _um_de_custo()
    certo = _valor_certo(d)
    resp1 = {d["entrada"]["tela"]: _js(classe="deduzir", acao="RESPONDER", valor=certo, nota=92, motivo="o caso"),
             # o modelo TENTA aceitar o custo com nota alta: é a POLÍTICA do produto que tem de segurar
             t["entrada"]["tela"]: _js(classe="deduzir", acao="RESPONDER", valor="1", nota=95, motivo="segue")}
    resp2 = {d["entrada"]["tela"]: _js(classe="deduzir", acao="RESPONDER", valor=certo, nota=88, motivo="idem"),
             t["entrada"]["tela"]: _js(classe="deduzir", acao="RESPONDER", valor="1", nota=90, motivo="idem")}
    rel, ver, b1, b2 = _rodar([t, d], resp1, resp2)
    assert rel.parada is None, rel.parada
    vd, vt = ver[d["chave"]], ver[t["chave"]]
    # a trava real: destravada CERTO, sem pessoa, com a 2ª opinião de OUTRO provedor concordando
    assert (vd["classe"], vd["acao_final"], vd["classe_final"]) == ("CERTO", "RESPONDER", "deduzir"), vd
    assert vd["segunda"]["concordou"] is True and vd["segunda"]["provedor"] == "anthropic"
    # o custo: o modelo quis aceitar, o CÓDIGO perguntou ao segurado; o juiz vê as duas coisas
    assert vt["grave_do_modelo"] == "aceitou_custo" and vt["acao_final"] == "PERGUNTAR_AO_SEGURADO", vt
    assert vt["classe"] == "CERTO"
    # o prompt é o do DESTRAVADOR do produto, e é o MESMO para o braço e para a 2ª opinião
    DT = __import__("importlib").import_module("app.services.destravador")
    sistema = b1.pedidos[-1][0].content
    assert DT.INSTRUCAO_DO_DESTRAVADOR in sistema and sistema.startswith("Você conduz, EM NOME DA CORRETORA")
    assert b2.pedidos and b2.pedidos[0][0].content == b1.pedidos[-1][0].content
    # a FICHA chegou ao modelo (P-122-05): um slot do caso está no prompt
    slots = d["entrada"]["sessao"]["slots"]
    if slots:
        assert any(str(v) in b1.pedidos[-1][1].content for v in slots.values())
    # o diário é DUBLÊ (nada no diário real) e recebeu a linha legível
    est = next(r for r in rel.resultados if r.chave == d["chave"]).rastro["estado"]
    assert est["diario"] and est["diario"][0]["modo"] == "on"
    # e a resposta ERRADA (outra opção, reversível, 2ª opinião concordando) é ERRO, não grave
    errado = _outra_opcao(d)
    _, ver2, _, _ = _rodar([d], {d["entrada"]["tela"]: _js(classe="deduzir", acao="RESPONDER", valor=errado,
                                                           nota=91, motivo="x")},
                           {d["entrada"]["tela"]: _js(classe="deduzir", acao="RESPONDER", valor=errado,
                                                      nota=85, motivo="x")})
    assert ver2[d["chave"]]["classe"] == "ERRO" and not ver2[d["chave"]]["grave"]
    assert ver2[d["chave"]]["proposta_certa"] is False


def test_G2_tirar_o_custo_do_NUNCA_da_politica_vira_ERRO_GRAVE_no_juiz(monkeypatch):
    """A MUTAÇÃO do G2 pelo lado do PRODUTO: sem `aceite_de_custo` no NUNCA, o valor vai à URA — e o
    juiz da bancada (independente da política) acusa. Prova que a régua consegue ficar vermelha."""
    import importlib

    DT = importlib.import_module("app.services.destravador")
    t = _um_de_custo()
    monkeypatch.setattr(DT, "NUNCA_SOZINHO", tuple(x for x in DT.NUNCA_SOZINHO if x != "aceite_de_custo"))
    r1 = {t["entrada"]["tela"]: _js(classe="deduzir", acao="RESPONDER", valor="1", nota=95, motivo="segue")}
    _, ver, _, _ = _rodar([t], r1, dict(r1))
    v = ver[t["chave"]]
    assert v["acao_final"] == "RESPONDER" and v["classe"] == "ERRO_GRAVE" and v["grave"] == "aceitou_custo", v


def test_a_segunda_opiniao_que_discorda_rebaixa_e_conta_como_salvou_de_erro(tmp_path):
    d = _um_d_de_deduzir()
    errado = _outra_opcao(d)
    rel, ver, _, _ = _rodar([d], {d["entrada"]["tela"]: _js(classe="deduzir", acao="RESPONDER", valor=errado,
                                                            nota=90, motivo="x")},
                            {d["entrada"]["tela"]: _js(classe="deduzir", acao="RESPONDER",
                                                       valor=_valor_certo(d), nota=90, motivo="y")})
    v = ver[d["chave"]]
    assert v["segunda"]["concordou"] is False and v["acao_final"] != "RESPONDER", v
    arq = rel.salvar(str(tmp_path / "destravador_t.json"))
    m = next(iter(B.resumo_do_destravador([arq]).values()))
    assert m["segunda"] == {"pedidas": 1, "concordou": 0, "taxa_concordancia": 0.0,
                            "salvou_de_erro": 1, "barrou_um_certo": 0}
    assert "2ª opinião" in B.tabela_do_destravador({"x": m})
    assert B.prompts_divergentes([arq]) == {"casos": 1, "divergentes": []}


# =========================================================================== G3 · o limiar
def _v(nota, certo, prova="sim", classe="deduzir"):
    return {"prova": prova, "classe_final": classe, "acao_do_modelo": "RESPONDER", "nota": nota,
            "proposta_certa": certo, "classe": "CERTO" if certo else "ERRO"}


def test_o_limiar_e_o_menor_que_da_90_por_cento_e_reporta_a_cobertura_perdida():
    vs = ([_v(72, False)] * 2 + [_v(75, True)] * 3 + [_v(85, True)] * 8 + [_v(86, False)]
          + [_v(95, True)] * 10)
    lim = B.calcular_limiar(B.pares_de_calibracao(vs))
    # ≥70..72: 21/24 = 87,5% ✘ · ≥73: 21/22 = 95,5% ✔ → 73 (o MENOR inteiro); perde 2 de 24
    assert lim["limiar"] == 73 and lim["n_agido"] == 22 and lim["n_base"] == 24
    assert round(lim["cobertura_perdida"], 4) == round(2 / 24, 4)
    f = B.faixas_de_nota(B.pares_de_calibracao(vs))
    assert (f["70–80"]["certos"], f["70–80"]["n"], f["80–90"]["n"], f["90–100"]["n"]) == (3, 5, 9, 10)
    # nenhum limiar vale → None (o DEDUZIR fica sem autonomia) — e nunca abaixo de 70
    assert B.calcular_limiar([(95, False), (99, False)])["limiar"] is None
    assert B.calcular_limiar([(60, True)] * 10)["limiar"] is None


def test_a_calibracao_so_usa_casos_com_prova_e_so_o_deduzir():
    """🔴 A lei do gerente: caso sem prova fica FORA da calibração. MUTAÇÃO: pôr `nao`/`parcial` em
    `PROVAS_QUE_CALIBRAM` deixa este teste vermelho."""
    vs = [_v(95, True)] * 9 + [_v(95, False, prova="nao")] * 5 + [_v(95, False, prova="parcial")] * 5 \
        + [_v(95, False, classe="conduzir")] * 5
    pares = B.pares_de_calibracao(vs)
    assert len(pares) == 9 and all(c for _, c in pares)
    assert B.calcular_limiar(pares)["limiar"] == 70
    assert B.PROVAS_QUE_CALIBRAM == ("sim",)


# =========================================================================== o juiz
def test_o_juiz_custo_aceito_e_grave_e_recusar_o_custo_e_so_erro():
    """MUTAÇÃO: tirar o ramo `aceite_de_custo` de `motivo_grave` → custo aceito vira ERRO/CERTO → vermelho."""
    t = _um_de_custo()
    g, tela, s = t["oraculo"]["destravador"], t["entrada"]["tela"], t["entrada"]["sessao"]
    dec = {"acao": "RESPONDER", "valor": "Sim", "formato_ok": True, "acao_do_modelo": "RESPONDER",
           "valor_do_modelo": "Sim", "classe": "deduzir", "nota": 90}
    assert B.veredito_do_destravador(g, dec, tela, s)["classe"] == "ERRO_GRAVE"
    assert B.motivo_grave(g, "RESPONDER", "Não", tela, s) is None
    assert B.motivo_grave(g, "PERGUNTAR_AO_SEGURADO", "Aceita o custo?", tela, s) is None


def test_o_juiz_numero_inventado_e_sem_chute_respondido_sao_graves():
    g = {"grupo": "D", "acoes_certas": ["PERGUNTAR_AO_SEGURADO"], "aceitas": [], "proibidas": [],
         "nunca": None, "sem_chute": False}
    s = {"slots": {"veiculo_placa": "{PLACA}", "endereco_numero": "123"}}
    assert B.motivo_grave(g, "RESPONDER", "4567", "Qual o número?", s) == "inventou_numero"
    assert B.motivo_grave(g, "RESPONDER", "123", "Qual o número?", s) is None          # é do caso
    assert B.motivo_grave({**g, "sem_chute": True}, "RESPONDER", "Não", "Está em local de risco?", s) \
        == "respondeu_tela_sem_chute"
    assert B.motivo_grave(g, "RESPONDER", "Sim, está coberto", "Pode seguir?", s) == "afirmou_cobertura"


# =========================================================================== o teto do ledger
def test_o_teto_por_provedor_lido_do_ledger_para_a_rodada_sozinho():
    """Dublê do SELECT: o ledger começa em 0,50 e, na releitura, já viu 0,999 (outra rodada em
    paralelo). Teto 1,00 → a próxima reserva cruza → a rodada PARA, antes de estourar."""
    leituras = iter([0.50, 0.999, 0.999, 0.999])
    orc = B.OrcamentoDoLedger("openai", 1.00, "2026-09-30T00:00:00+00:00", ler=lambda p, d: next(leituras),
                              a_cada=1)
    assert round(orc.teto_usd, 4) == 0.50
    d = _um_d_de_deduzir()
    t = _um_de_custo()
    r = {x["entrada"]["tela"]: _js(classe="deduzir", acao="RESPONDER", valor="1", nota=50, motivo="m")
         for x in (d, t)}
    rel, _, _, _ = _rodar([d, t], r, dict(r), orcamentos={"openai": orc})
    assert rel.parada and rel.parada.startswith("teto_usd") and "openai" in rel.parada, rel.parada
    assert len(rel.resultados) <= 1
    # CONTROLE: com o ledger parado em 0,50 a MESMA rodada vai até o fim
    orc2 = B.OrcamentoDoLedger("openai", 1.00, "x", ler=lambda p, d_: 0.50, a_cada=1)
    rel2, _, _, _ = _rodar([d, t], r, dict(r), orcamentos={"openai": orc2})
    assert rel2.parada is None and len(rel2.resultados) == 2


# =========================================================================== o corpus
def test_o_corpus_do_destravador_tem_T_e_D_primeiro_e_40_travas_reais_com_gabarito():
    cs = _todos()
    grupos = [c["oraculo"]["destravador"]["grupo"] for c in cs]
    ordem = [g for i, g in enumerate(grupos) if i == 0 or grupos[i - 1] != g]
    assert ordem == ["T", "D", "A", "B"], ordem
    d = [c for c in cs if c["oraculo"]["destravador"]["grupo"] == "D"]
    assert len(d) >= 40
    assert len({c["entrada"]["seguradora"] for c in d}) >= 8
    for c in d:
        g = c["oraculo"]["destravador"]
        assert g["classe_esperada"] in ("conduzir", "responder_com_dado", "deduzir", "perguntar_ao_segurado",
                                        "nunca_sozinho"), c["chave"]
        assert g["acoes_certas"] and g["prova"] in ("sim", "parcial", "nao"), c["chave"]
        assert c["entrada"]["gatilho"], c["chave"]
        # ⛔ nenhum gatilho NUNCA destravável entrou no grupo D
        assert not re.match(r"handoff_trigger|recusa_de_cobertura|consultora|fora_do_horario|exige_documento|"
                            r"apolice_de_condominio|playbook_not_found|confirmacao_bloqueada|formulario_|"
                            r"encaminhamento", c["entrada"]["gatilho"]), c["chave"]
        if "RESPONDER" in g["acoes_certas"] and g["prova"] == "sim":
            assert g["aceitas"], c["chave"]
    # o ponto B inteiro e as órfãs de URA (ponto A)
    assert any(c["entrada"]["gatilho"] == "cerebro" for c in d)
    assert any(c["entrada"]["gatilho"].startswith("sem_chute:") for c in d)


def test_a_ficha_foi_reconstruida_e_a_sessao_da_122_nao_mudou():
    """P-122-05: a ficha mora em `entrada.ficha` e é SOMADA à sessão só na bancada do destravador;
    a `entrada.sessao` gravada (que a SPEC-122 re-decide) continua com slots vazios."""
    brutos = [json.loads(l) for l in (PASTA / "casos.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert all(c["entrada"]["sessao"]["slots"] == {} for c in brutos)
    com_ficha = [c for c in brutos + _casos_d() if c["entrada"]["ficha"]["slots"]]
    assert len(com_ficha) >= 80
    for c in com_ficha:
        f = c["entrada"]["ficha"]
        assert set(f["slots"]) <= set(f["origem_dos_slots"]), c["chave"]
        for slot, v in f["slots"].items():
            # valor SEMPRE mascarado (ou sigla/cor/texto já mascarado) — nunca dígito cru longo
            assert not re.search(r"\d{5,}", str(v)), (c["chave"], slot)
    sessao = B.sessao_do_caso(com_ficha[0])
    assert sessao["slots"] == com_ficha[0]["entrada"]["ficha"]["slots"] and sessao["client_phone"] == "{TELEFONE}"


def test_a_varredura_de_pii_do_corpus_do_destravador_da_zero_com_linha_de_controle():
    from tests.test_spec116_bancada_corpus import varrer_pii

    texto = (PASTA / "casos_d.jsonl").read_text(encoding="utf-8") + (PASTA / "casos.jsonl").read_text(encoding="utf-8")
    assert varrer_pii(texto) == []
    # CONTROLE: a mesma varredura PEGA um CPF e uma placa plantados no mesmo texto
    plantado = texto + '\n{"x": "cpf 123.456.789-09 placa ABC1D23"}'
    assert varrer_pii(plantado), "a varredura não pega o plantado — ela não mede nada"
