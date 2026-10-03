# -*- coding: utf-8 -*-
"""SPEC-127 P2 (+ a contenção do P6, D-127-B) — o DOM para de errar calado.

Cada guarda roda o MOTOR (`plano_de_contencao`, `run_adaptive`,
`vidros_lanternas.abrir_atendimento`, `perception.validar_acao`) sobre as
ÁRVORES derivadas do HTML REAL do intake (`fixtures/vidros/telas_dom.py`), e
cada um tem a sua linha de CONTROLE — a prova de que ele consegue ficar
vermelho (CLAUDE.md §9.3/§9.4/§9.5).
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from portal_worker import adaptive as AD  # noqa: E402
from portal_worker import perception as P  # noqa: E402
from portal_worker.guardrails import PortalActionGuard  # noqa: E402
from portal_worker.journeys import vidros_lanternas as VL  # noqa: E402
from tests._pagina_falsa_do_dom import PaginaFalsa, RuntimeFalso, tela  # noqa: E402

DESCRICAO = "BATI O CARRO E O PARA-BRISA TRINCOU INTEIRO NA ESTRADA"
CASO = {
    "cpf_cnpj": "12345678909", "placa": "QAB1A91", "data_dano": "14/08/2026",
    "segurado": {"nome": "SEGURADO DE TESTE", "apolice": "9999999", "chassi": "9BWZZZ377VT004251",
                 "cep": "88130000", "endereco": "RUA DE TESTE 1", "telefone": "47911112222",
                 "email": "segurado@example.invalid"},
    "solicitante": {"relacao": "Corretor", "nome": "CORRETORA DE TESTE",
                    "email": "corretora@example.invalid", "telefone": "4733334444",
                    "cpf_cnpj": "00000000000191"},
    "dano": {"peca": "para-brisa", "como": "COLISÃO ACIDENTAL", "onde": "urbano",
             "descricao": DESCRICAO},
    "local": {"estado": "SC", "cidade": "Palhoca", "cep": "88130000",
              "cidade_servico": {"uf": "SC", "cidade": "Joinville"}},
    "especificos": {},
}


def _caso(**mudar):
    c = json.loads(json.dumps(CASO))
    for k, v in mudar.items():
        c[k] = v
    return c


def _sem_respostas(apelido):
    t = tela(apelido)
    for q in t["questoes"]:
        q["respondida"], q["escolhida"] = False, ""
    return t


# =====================================================================
# G3 — NUNCA sozinho: reparo × troca, ofertas, custo, cancelar, novo, "Não sabe"
# =====================================================================
def test_reparo_sem_a_resposta_do_segurado_PARA_com_os_dois_botoes_reais():
    plano = AD.plano_de_contencao(tela("yelum_parabrisa_reparo"), _caso())
    p = plano["parada"]
    assert p and p["stage"] == "decidir_reparo" and p["acao_esperada"] == "responder:aceita_reparo"
    assert p["nunca"] == "aceite_de_custo"
    assert p["opcoes"] == ["Sim, quero tentar o reparo", "Não, prefiro seguir com a troca"]
    assert plano["acoes"] == []


@pytest.mark.parametrize("dito,botao", [("sim", "Sim, quero tentar o reparo"),
                                        ("nao", "Não, prefiro seguir com a troca")])
def test_CONTROLE_reparo_com_a_resposta_DELE_o_codigo_aperta_o_botao_dele(dito, botao):
    plano = AD.plano_de_contencao(tela("yelum_parabrisa_reparo"), _caso(especificos={"aceita_reparo": dito}))
    assert plano["parada"] is None
    assert plano["acoes"] == [{"action": "click", "target": botao, "slot": "aceita_reparo"}]


def test_no_laco_o_reparo_para_e_NINGUEM_aperta(monkeypatch):
    pagina = PaginaFalsa("yelum_parabrisa_reparo")
    chamado = []

    async def _cerebro(*a, **k):
        chamado.append(1)
        return {"action": "click", "target": "Sim, quero tentar o reparo", "value": "", "reason": "t"}

    monkeypatch.setattr(AD, "decide_next_action", _cerebro)
    r = asyncio.run(AD.run_adaptive(pagina, "abrir vidros", _caso(), {}, confirm=True, conter=True))
    assert r.status == "needs_human" and (r.captured or {}).get("stage") == "decidir_reparo"
    assert pagina.cliques == [] and chamado == [], (pagina.cliques, chamado)


@pytest.mark.parametrize("botao,familia", [
    ("Sim, quero tentar o reparo", "aceite_de_custo"),
    ("Não, prefiro seguir com a troca", "aceite_de_custo"),
    ("Quero o polimento de farol", "aceite_de_custo"),
    ("Incluir calibração ADAS", "aceite_de_custo"),
    ("Aceito a cola rápida", "aceite_de_custo"),
    ("Cancelar atendimento", "cancelar"),
    ("Desistir do atendimento", "cancelar"),
    ("Novo atendimento", "novo_atendimento"),
    ("Solicitar novo atendimento", "novo_atendimento"),
])
def test_o_validador_recusa_o_modelo_apertar_botao_NUNCA(botao, familia):
    t = tela("yelum_final")
    t["buttons"].append({"text": botao, "disabled": False})
    g = PortalActionGuard(material_liberado=True, acao_material_esperada="avancar|confirmar")
    v = P.validar_acao({"action": "click", "target": botao}, t, guard=g, conter=True)
    assert not v.ok and familia in v.motivo, v.motivo
    assert P.familia_nunca_sozinho(botao) == familia


def test_CONTROLE_navegar_continua_livre_e_sem_conter_nada_muda():
    t = tela("yelum_parabrisa_50_peca_causa")
    g = PortalActionGuard(material_liberado=True, acao_material_esperada="avancar|confirmar")
    assert P.validar_acao({"action": "click", "target": "Avançar"}, t, guard=g, conter=True).ok
    assert P.validar_acao({"action": "click", "target": "Voltar"}, t, guard=g, conter=True).ok
    # sem `conter` (Allianz, cobrança): o botão de reparo não é material e passa — os dois DIFEREM
    t5 = tela("yelum_parabrisa_reparo")
    assert P.validar_acao({"action": "click", "target": "Sim, quero tentar o reparo"}, t5, guard=g).ok
    assert not P.validar_acao({"action": "click", "target": "Sim, quero tentar o reparo"}, t5,
                              guard=g, conter=True).ok


def test_nao_sabe_nunca_e_do_modelo():
    t = _sem_respostas("yelum_lateral_80")
    v = P.validar_acao({"action": "check", "target": "Qual o lado do item danificado?", "value": "Não sabe"},
                       t, conter=True)
    assert not v.ok and "Nao sabe" in v.motivo


# =====================================================================
# P6 (contenção) — peça, causa, perímetro, lado, trinca, descrição
# =====================================================================
def test_o_que_e_FATO_o_codigo_escreve_com_a_opcao_REAL():
    plano = AD.plano_de_contencao(tela("yelum_parabrisa_50_peca_causa"), _caso())
    assert plano["parada"] is None
    feitas = {a["slot"]: a["value"] for a in plano["acoes"]}
    assert feitas == {"como": "COLISÃO ACIDENTAL", "onde": "Urbano (Cidade)", "descricao": DESCRICAO}, feitas


def test_causa_que_nao_e_IGUAL_PARA_com_as_11_opcoes_reais():
    plano = AD.plano_de_contencao(tela("yelum_parabrisa_50_peca_causa"),
                                  _caso(dano={**CASO["dano"], "como": "uma pedra bateu"}))
    p = plano["parada"]
    assert p["stage"] == "motivo_ambiguo" and p["acao_esperada"] == "responder:como"
    assert len(p["opcoes"]) == 11 and "COLISÃO ACIDENTAL" in p["opcoes"], p["opcoes"]


def test_perimetro_desconhecido_PARA_e_nunca_vira_Nao_Sabe():
    plano = AD.plano_de_contencao(tela("yelum_parabrisa_50_peca_causa"),
                                  _caso(dano={**CASO["dano"], "onde": ""}))
    p = plano["parada"]
    assert p["stage"] == "perimetro_desconhecido" and p["opcoes"] == ["Urbano (Cidade)", "Rodoviário", "Não Sabe"]
    assert not any(a.get("value") == "Não Sabe" for a in plano["acoes"])


def test_descricao_curta_PARA():
    plano = AD.plano_de_contencao(tela("yelum_parabrisa_50_peca_causa"),
                                  _caso(dano={**CASO["dano"], "descricao": "quebrou"}))
    assert plano["parada"]["stage"] == "descricao_curta"


def test_peca_vazia_sem_fato_PARA_com_as_30_pecas_reais():
    t = tela("yelum_parabrisa_50_peca_causa")
    t["mdselects"][0]["value"], t["mdselects"][0]["vazio"] = "", True
    plano = AD.plano_de_contencao(t, _caso(dano={**CASO["dano"], "peca": "o vidro do carro"}))
    p = plano["parada"]
    assert p["stage"] == "peca_ambigua" and len(p["opcoes"]) == 30, p
    # CONTROLE: a peça que o segurado disse casa → o código escreve a opção REAL
    plano2 = AD.plano_de_contencao(t, _caso())
    assert {"slot": "peca", "value": "VIDRO PARABRISA"}.items() <= plano2["acoes"][0].items(), plano2


def test_lataria_com_mais_de_uma_peca_PARA():
    t = tela("yelum_lataria_pecas")
    t["mdselects"][0]["value"], t["mdselects"][0]["vazio"] = "", True
    plano = AD.plano_de_contencao(t, _caso(dano={**CASO["dano"], "pecas_lataria": ["capô", "teto"]}))
    assert plano["parada"]["stage"] == "peca_de_lataria_ambigua"


def test_o_80_responde_com_o_que_o_SEGURADO_disse_e_para_no_que_ele_nao_disse():
    t = _sem_respostas("yelum_lateral_80")
    sem = AD.plano_de_contencao(t, _caso())
    assert sem["parada"]["stage"] == "questionario_incompleto"
    assert sem["parada"]["opcoes"] == ["DIANTEIRA", "TRASEIRA", "Não sabe"]
    com = AD.plano_de_contencao(t, _caso(especificos={"porta_dianteira_ou_traseira": "traseira",
                                                       "lado_motorista_ou_carona": "motorista"}))
    assert com["acoes"] == [{"action": "check", "target": "1) O vidro danificado é da porta dianteira ou traseira?",
                             "value": "TRASEIRA", "slot": "pergunta"}], com


def test_o_laco_responde_o_80_e_so_entao_o_modelo_navega(monkeypatch):
    pagina = PaginaFalsa("yelum_lateral_80", telas={"yelum_lateral_80": _sem_respostas("yelum_lateral_80")},
                         fluxo={("yelum_lateral_80", "Avançar"): "protocolo"})
    vistos = []

    async def _cerebro(state, goal, collected, history, force=False, **_k):
        vistos.append([q.get("respondida") for q in state.get("questoes") or []])
        return {"action": "click", "target": "Avançar", "value": "", "reason": "t"}

    monkeypatch.setattr(AD, "decide_next_action", _cerebro)
    caso = _caso(especificos={"porta_dianteira_ou_traseira": "traseira", "lado_motorista_ou_carona": "motorista"})
    r = asyncio.run(AD.run_adaptive(pagina, "abrir vidros", caso, {}, confirm=True, conter=True))
    assert [x for x in pagina.log if x[0] == "check"] == [
        ("check", "1) O vidro danificado é da porta dianteira ou traseira?", "TRASEIRA"),
        ("check", "2) Qual o lado do item danificado?", "Lado do motorista")]
    assert vistos and vistos[0] == [True, True], vistos   # o modelo só viu a tela já respondida
    assert r.status == "done"


def test_o_validador_recusa_o_modelo_escolher_a_PECA():
    t = tela("yelum_parabrisa_50_peca_causa")
    for acao in ({"action": "select", "target": "Qual foi a peça danificada?", "value": "VIDRO PARABRISA"},
                 {"action": "select", "target": "Como ocorreu o dano ao veículo?", "value": "CHOQUE TERMICO"},
                 {"action": "select", "target": "Onde ocorreu o dano ao veículo?", "value": "Rodoviário"},
                 {"action": "fill", "target": "descricaoDoDano", "value": DESCRICAO}):
        v = P.validar_acao(acao, t, collected=CASO, conter=True)
        assert not v.ok and "campo critico" in v.motivo, (acao, v.motivo)
        # CONTROLE: sem `conter`, a mesma ação passa — a recusa vem da contenção
        assert P.validar_acao(acao, t, collected=CASO).ok, acao


def test_cidade_e_cobertura_tambem_nao_sao_do_modelo():
    t = tela("yelum_lataria_50_cidade_cep")
    v = P.validar_acao({"action": "fill", "target": "Escolha a cidade disponível para atendimento.",
                        "value": "Palhoca"}, t, collected=CASO, conter=True)
    assert not v.ok and "cidade_servico" in v.motivo
    tp = tela("porto_passo1_cobertura")
    v2 = P.validar_acao({"action": "check", "target": "tipoAtendimento", "value": "Roda, pneu"}, tp, conter=True)
    assert not v2.ok


# =====================================================================
# Rádio "Selecione a cobertura" da Porto — pelo CÓDIGO, pela peça
# =====================================================================
@pytest.mark.parametrize("peca,valor", [("para-brisa", "1"), ("lanterna traseira", "1"),
                                        ("roda liga leve", "2"), ("pneu", "2")])
def test_a_cobertura_da_porto_e_marcada_pela_peca(peca, valor):
    cob = VL.cobertura_do_passo1(tela("porto_passo1_cobertura"), "Porto Seguro", peca)
    assert cob == {"acao": "marcar", "valor": valor}


def test_cobertura_sem_peca_ou_em_outra_seguradora():
    assert VL.cobertura_do_passo1(tela("porto_passo1_cobertura"), "Porto Seguro", "")["acao"] == "parar"
    assert VL.cobertura_do_passo1(tela("porto_passo1_cobertura"), "Yelum", "pneu")["acao"] == "parar"
    assert VL.cobertura_do_passo1(tela("yelum_passo1"), "Yelum", "pneu") == {"acao": "nada"}


# =====================================================================
# Fronteira A no DOM — "Iniciar atendimento" + "Confirmar" dentro do guard
# =====================================================================
def _passo1(p, texto):
    if texto == "Iniciar atendimento" and p.atual in ("yelum_passo1", "porto_passo1_cobertura"):
        p.tela["buttons"].append({"text": "Confirmar", "disabled": False})


def _abrir(monkeypatch, *, confirm, inicio="yelum_passo1", insurer="Yelum", peca="para-brisa"):
    pagina = PaginaFalsa(inicio, {(inicio, "Confirmar"): "protocolo"}, ao_clicar=_passo1)
    rt = RuntimeFalso(pagina, liberado=confirm)
    params = {**_caso(dano={**CASO["dano"], "peca": peca}), "insurer_name": insurer, "confirm": confirm,
              "_runtime": rt}

    async def _navegou(page, ins):
        return True

    async def _cerebro(*a, **k):
        return {"action": "done", "target": "", "value": "", "reason": "t"}

    monkeypatch.setattr(VL, "_select_insurer_start", _navegou)
    monkeypatch.setattr(AD, "decide_next_action", _cerebro)
    ev: dict = {}
    r = asyncio.run(VL.abrir_atendimento(pagina, params, ev))
    return r, pagina, rt, ev


def test_sem_confirm_os_cliques_da_fronteira_A_NAO_saem(monkeypatch):
    r, pagina, rt, _ev = _abrir(monkeypatch, confirm=False)
    # §9.3 — a lição MIGRA (conserto da 127, juiz B3): o stage era `pronto_para_abrir`, cujo texto diz "a sua
    # apolice cobre" — falso aqui, onde o GET /apolices (o "Iniciar atendimento") NÃO saiu. Stage próprio.
    assert r.status == "needs_human" and (r.captured or {}).get("stage") == "pronto_para_iniciar"
    assert "Iniciar atendimento" not in pagina.cliques and "Confirmar" not in pagina.cliques, pagina.cliques
    assert rt.gravacoes == []


def test_CONTROLE_com_confirm_o_efeito_e_ARMADO_antes_do_clique(monkeypatch):
    r, pagina, rt, ev = _abrir(monkeypatch, confirm=True)
    rel = pagina.relogio
    assert "clique:Iniciar atendimento" in rel and "clique:Confirmar" in rel, rel
    assert rel.index("efeito:armed") < rel.index("clique:Iniciar atendimento"), rel
    assert rel.index("clique:Confirmar") < rel.index("efeito:submitted"), rel
    assert r.status == "done" and ev.get("protocolo") == "40000001"


def test_a_porto_marca_a_cobertura_antes_do_guard_e_do_clique(monkeypatch):
    r, pagina, rt, ev = _abrir(monkeypatch, confirm=True, inicio="porto_passo1_cobertura",
                               insurer="Porto Seguro", peca="roda liga leve")
    assert ("cobertura", "2") in pagina.log and ev.get("cobertura_do_passo1") == "2"
    assert pagina.log.index(("cobertura", "2")) < pagina.log.index(("click", "Iniciar atendimento"))


# =====================================================================
# PII ao modelo — só o que a TELA pede
# =====================================================================
_PII = ("12345678909", "SEGURADO DE TESTE", "9999999", "9BWZZZ377VT004251", "88130000",
        "RUA DE TESTE", "47911112222", "segurado@example.invalid", "Palhoca", "Joinville",
        "abcdefghijklmnopqrstuvwxyz0123")


def test_o_modelo_recebe_so_o_que_a_tela_pede(monkeypatch):
    pagina = PaginaFalsa("yelum_contato_20", {("yelum_contato_20", "Avançar"): "protocolo"})
    # Dois campos de telefone: AMBÍGUO, o código não escreve (regra do fato) — a tela pede ao modelo.
    pagina.tela["inputs"].append({**[c for c in pagina.tela["inputs"] if c["id"] == "telefone-input"][0],
                                  "id": "telefone-input-2"})
    for c in pagina.tela["inputs"]:
        c["empty_required"] = False
    enviados = []

    async def _cerebro(state, goal, collected, history, force=False, **_k):
        enviados.append(json.dumps({"tela": state, "dados": collected}, ensure_ascii=False))
        return {"action": "click", "target": "Avançar", "value": "", "reason": "t"}

    monkeypatch.setattr(AD, "decide_next_action", _cerebro)
    asyncio.run(AD.run_adaptive(pagina, "abrir vidros", _caso(), {}, confirm=True, conter=True))
    assert enviados
    for bruto in enviados:
        for pii in _PII:
            assert pii not in bruto, f"{pii!r} foi ao provedor"
    # o que a tela pedia e o código não preencheu foi junto (e só isso)
    assert "4733334444" in enviados[0]


def test_CONTROLE_sem_conter_o_modelo_ainda_recebe_tudo(monkeypatch):
    """Allianz/cobrança: `run_adaptive` sem `conter` não muda. E prova que a
    asserção acima CONSEGUE ficar vermelha."""
    pagina = PaginaFalsa("yelum_contato_20", {("yelum_contato_20", "Avançar"): "protocolo"})
    enviados = []

    async def _cerebro(state, goal, collected, history, force=False, **_k):
        enviados.append(json.dumps({"tela": state, "dados": collected}, ensure_ascii=False))
        return {"action": "done", "target": "", "value": "", "reason": "t"}

    monkeypatch.setattr(AD, "decide_next_action", _cerebro)
    asyncio.run(AD.run_adaptive(pagina, "abrir vidros", _caso(), {}, confirm=True))
    assert "12345678909" in enviados[0] and "abcdefghijklmnopqrstuvwxyz0123" in enviados[0]


def test_dados_para_o_modelo_puro():
    d = AD.dados_para_o_modelo(CASO, tela("yelum_parabrisa_50_peca_causa"))
    assert d == {"dano": {"peca": "para-brisa"}}, d
    d20 = AD.dados_para_o_modelo(CASO, tela("yelum_contato_20"))
    assert set(d20["solicitante"]) == {"nome", "email", "telefone", "cpf_cnpj"}, d20
    assert "segurado" not in d20 and "cpf_cnpj" not in d20 and "local" not in d20
    assert AD._url_sem_token("https://p/#/x/passo2/abcdefghijklmnopqrstuvwxyz0123") == "https://p/#/x/passo2/<token>"


# =====================================================================
# A fixture é derivada, mascarada — e é a árvore do HTML real
# =====================================================================
_FIXTURE = Path(RAIZ) / "tests" / "fixtures" / "vidros" / "telas_dom.py"
_RX_PII = (
    re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),            # CPF
    re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"),     # CNPJ
    re.compile(r"\b\d{5}-?\d{3}\b"),                             # CEP
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),                     # e-mail
    re.compile(r"\(?\b\d{2}\)?\s?9?\d{4}-?\d{4}\b"),             # telefone
    re.compile(r"\b[A-Z]{3}-?\d[A-Z0-9]\d{2}\b"),                # placa
    re.compile(r"eyJ[A-Za-z0-9_-]{8,}"),                         # JWT
    re.compile(r"passo\d/[A-Za-z0-9_-]{12,}"),                   # token da SPA na URL
)


def test_a_fixture_nao_carrega_PII_nem_token():
    texto = _FIXTURE.read_text(encoding="utf-8")
    for rx in _RX_PII:
        assert not rx.search(texto), f"{rx.pattern} casou: {rx.search(texto).group(0)!r}"
    assert "'[preenchido]'" not in texto or "value" in texto


def test_CONTROLE_o_grep_de_PII_pega_PII():
    for amostra in ("123.456.789-09", "00.000.000/0001-91", "88130-000", "a@b.com", "(47) 99999-1111",
                    "QAB1A91", "eyJhbGciOiJIUzI1NiJ9", "passo2/abcdefghijklmn"):
        assert any(rx.search(amostra) for rx in _RX_PII), amostra


def test_a_fixture_e_a_arvore_do_html_real():
    pytest.importorskip("lxml")
    from tests import _arvore_do_html as A
    from tests.fixtures.vidros.telas_dom import TELAS

    base = A.pasta_do_intake()
    if not base.exists():
        pytest.skip(f"intake local ausente ({base}); defina AUTOBROKERS_INTAKE_VIDROS")
    for apelido, rel in A.TELAS:
        assert A.arvore_do_html(base / rel) == TELAS[apelido], apelido
