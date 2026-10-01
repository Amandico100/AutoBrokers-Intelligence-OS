# -*- coding: utf-8 -*-
"""SPEC-123 F1a — A POLÍTICA do destravador, em código (D1–D3 do Founder, 30/09/2026).

Uma tela REAL do acervo por caso (o texto vem do acervo, não da imaginação — CLAUDE.md §9.4) e
a política do PRODUTO (`destravador.decidir_destravamento`), que usa os parsers e as regex do
PRODUTO (`rotulo_de`, `rotulo_e_de_navegacao`, `_RX_DINHEIRO_NA_TELA`, `guard_human_phase_reply`).
A saída do modelo entra pelo parser REAL (`ler_destravamento`). Os casos que precisam do fio
inteiro (2ª opinião, reserva, sombra, conversa do segurado) passam por `destravar` com o
cliente do provedor dublado (`test_spec123_destravador_fio.dt`).

MUTAÇÕES (uma vez, restaurando por cópia — resultado no relatório da F1a):
  M1 tirar "aceite_de_custo" de `NUNCA_SOZINHO`      → os testes do custo ficam VERMELHOS
  M2 tirar a exigência da 2ª opinião do DEDUZIR      → discordou / mesmo provedor ficam VERMELHOS
  M3 baixar `LIMIAR_MINIMO` para 60                  → a nota 69 fica VERMELHA
"""
from __future__ import annotations

import asyncio
import inspect
import json
import types

import pytest

from tests.test_spec122_sombra_e_sem_chute import (  # noqa: F401 — fixtures
    AC, CLIENTE, D, EMPRESA_A, EMPRESA_B, R, _fio_fixo, amb, sessao, tela_real,
)
from tests.test_spec123_destravador_fio import (  # noqa: F401 — fixtures
    REF_YELUM_RES, RELATO, TELA_SERVICOS, destravar, dt, js, sessao_travada,
)
from app.services import destravador as DT


@pytest.fixture(autouse=True)
def _deduzir_calibrado(monkeypatch):
    """F5a (§9.3 — a lição MIGRA): este arquivo prova a MECÂNICA do DEDUZIR calibrado (limiar, 2ª
    opinião de outro provedor, discordância). Em produção ela está atrás de
    `destravador.DEDUZIR_AUTONOMO_CALIBRADO = False` (G3 sem calibração); o comportamento de HOJE —
    todo DEDUZIR rebaixado — é guardado em `test_spec123_f5a_costura.py`."""
    from app.services import destravador as _DT

    monkeypatch.setattr(_DT, "DEDUZIR_AUTONOMO_CALIBRADO", True)


def decidir(saida: str, s: dict, tela: str, **k):
    """A saída do modelo pelo parser REAL → a política REAL."""
    return DT.decidir_destravamento(DT.ler_destravamento(saida), s, tela, **k)


# ----------------------------------------------------------------------------- as telas REAIS
TELA_CONTINUAR = tela_real("allianz-residencial", r"dever[áa] ser agendado")
TELA_PLACA = tela_real("hdi-auto", r"qual a placa do ve")
TELA_RISCO_HDI = tela_real("hdi-auto", r"situa[çc][õo]es de risco")
TELA_OFICINA_YELUM = tela_real("yelum-auto", r"oficinas referenciadas como sugest")
TELA_OFICINA_ALLIANZ = tela_real("allianz-auto", r"oficina referenciada Allianz")
TELA_SINISTRO = tela_real("mapfre-auto", r"Abrir sinistro\nAcompanhar")
TELA_ATENDIMENTO_AZUL = tela_real("azul-auto", r"Cancelar servi[çc]o agendado")
TELA_NOVO_ALLIANZ = tela_real("allianz-auto", r"Abrir novo atendimento")
TELA_RAMO_ALLIANZ = tela_real("allianz-residencial", r"Qual seguro deseja utilizar")

REF_HDI = "hdi-auto-whatsapp@v1"
REF_YELUM_AUTO = "yelum-auto-whatsapp@v3"
REF_ALLIANZ_AUTO = "allianz-auto-whatsapp@v1"
REF_ALLIANZ_RES = "allianz-residencial-whatsapp@v1"
REF_MAPFRE = "mapfre-auto-whatsapp@v1"
REF_AZUL = "azul-auto-whatsapp@v1"
PLACA = "ABC1D23"          # 💭 sintética — nunca de um segurado


def deduz(valor, nota=90, classe="deduzir"):
    return js(classe=classe, acao="RESPONDER", valor=valor, nota=nota, motivo="o caso indica")


SEGUNDA_OK = {"provedor": "anthropic", "modelo": "x", "classe": "deduzir", "acao": "RESPONDER",
              "valor": "Encanador", "nota": 90}


# =============================================================================
# O PARSER — estrito: qualquer desvio → PESSOA
# =============================================================================
@pytest.mark.parametrize("saida, erro", [
    ("Encanador", "nao_e_json"),
    ('{"acao": "RESPONDER", "valor": "1", "motivo": "V2 da 122"}', "chaves_invalidas"),
    (js(classe="deduzir", acao="RESPONDER", valor="1", nota=101), "nota_fora_de_0_100"),
    (js(classe="deduzir", acao="RESPONDER", valor="1", nota="90"), "nota_invalida"),
    (js(classe="deduzir", acao="RESPONDER", valor="1", nota=True), "nota_invalida"),
    (js(classe="deduzir", acao="PESSOA", valor="", nota=50), "classe_e_acao_incoerentes"),
    (js(classe="chutar", acao="RESPONDER", valor="1", nota=90), "classe_desconhecida"),
    (js(classe="deduzir", acao="RESPONDER", valor="", nota=90), "valor_vazio"),
    (js(classe="deduzir", acao="RESPONDER", valor="1", nota=90, extra=1), "chaves_invalidas"),
    ("[1, 2]", "nao_e_objeto"),
])
def test_saida_invalida_vira_pessoa(saida, erro):
    p = DT.ler_destravamento(saida)
    assert (p.formato_ok, p.erro, p.acao) == (False, erro, "PESSOA")
    s = sessao_travada()
    d = DT.decidir_destravamento(p, s, TELA_SERVICOS)
    assert d.acao == "PESSOA" and d.proibicao == f"saida_invalida:{erro}"


def test_CONTROLE_o_parser_aceita_a_forma_certa_e_uma_cerca():
    p = DT.ler_destravamento("```json\n" + deduz("Encanador", 88) + "\n```")
    assert (p.formato_ok, p.classe, p.acao, p.valor, p.nota) == (True, "deduzir", "RESPONDER", "Encanador", 88)


# =============================================================================
# AS CINCO CLASSES
# =============================================================================
def test_conduzir_opcao_de_navegacao_e_livre_sem_segunda_opiniao():
    s = sessao(REF_ALLIANZ_RES, "maquina_de_lavar")
    d = decidir(deduz("1", 95, classe="conduzir"), s, TELA_CONTINUAR)
    assert (d.acao, d.valor, d.classe, d.proibicao) == ("RESPONDER", "1", "conduzir", ""), d


def test_conduzir_que_escolhe_conteudo_vira_deduzir_e_pede_segunda_opiniao():
    s = sessao_travada()
    d = decidir(deduz("Encanador", 95, classe="conduzir"), s, TELA_SERVICOS, pedir_segunda=True)
    assert (d.classe, d.proibicao) == ("deduzir", "precisa_segunda_opiniao"), d


def test_responder_com_dado_do_caso_e_livre():
    s = sessao(REF_HDI, "guincho", slots={"veiculo_placa": PLACA})
    d = decidir(js(classe="responder_com_dado", acao="RESPONDER", valor=PLACA, nota=97), s, TELA_PLACA)
    assert (d.acao, d.valor, d.classe) == ("RESPONDER", PLACA, "responder_com_dado"), d


def test_deduzir_com_nota_e_segunda_opiniao_de_outro_provedor_age():
    s = sessao_travada()
    d = decidir(deduz("Encanador", 80), s, TELA_SERVICOS, provedor="openai", segunda_opiniao=dict(SEGUNDA_OK))
    assert (d.acao, d.valor, d.classe) == ("RESPONDER", "Encanador", "deduzir"), d
    assert d.segunda_opiniao["concordou"] is True


def test_perguntar_ao_segurado_leva_a_pergunta_e_as_opcoes_de_conteudo():
    s = sessao(REF_HDI, "guincho")
    d = decidir(js(classe="perguntar_ao_segurado", acao="PERGUNTAR_AO_SEGURADO",
                   valor="Você está num lugar com pouca luz ou pouco movimento?", nota=60), s, TELA_RISCO_HDI)
    assert d.acao == "PERGUNTAR_AO_SEGURADO" and d.valor.startswith("Você")
    rotulos = [o[1] for o in d.opcoes]
    assert "Rodovia" in rotulos and "Nenhuma das anteriores" in rotulos
    assert not [r for r in rotulos if r.lower().startswith("volta")], rotulos


def test_perguntar_onde_a_seguradora_nao_espera_vai_a_pessoa(monkeypatch):
    # F1c: QUAL seguradora espera é fato que muda (a D6 abre a Allianz); a lição fica — a recusa é
    # testada desligando a ida e volta DE PROPÓSITO (CLAUDE.md §9.3), não por um nome de seguradora.
    monkeypatch.setattr(D, "ida_e_volta_permitida", lambda playbook: False)
    s = sessao(REF_ALLIANZ_RES, "maquina_de_lavar")
    d = decidir(js(classe="perguntar_ao_segurado", acao="PERGUNTAR_AO_SEGURADO", valor="Você quer?",
                   nota=60), s, TELA_CONTINUAR)
    assert (d.acao, d.proibicao) == ("PESSOA", "ida_e_volta_proibida")


def test_sem_chute_o_modelo_nunca_responde_pergunta_ao_segurado():
    s = sessao(REF_HDI, "guincho")
    d = decidir(deduz("Nenhuma das anteriores", 99), s, TELA_RISCO_HDI, gatilho="sem_chute:situacao_risco_opcao",
                provedor="openai", segunda_opiniao={**SEGUNDA_OK, "valor": "Nenhuma das anteriores"})
    assert (d.acao, d.proibicao) == ("PERGUNTAR_AO_SEGURADO", "passo_sem_chute"), d
    assert "situações" in d.valor


# =============================================================================
# O NUNCA SOZINHO — um teste por item
# =============================================================================
def test_NUNCA_custo_pergunta_ao_segurado_mostrando_o_custo_da_tela():
    s = sessao(REF_YELUM_AUTO, "guincho")
    d = decidir(deduz("Sim", 95), s, TELA_OFICINA_YELUM, provedor="openai",
                segunda_opiniao={**SEGUNDA_OK, "valor": "Sim"})
    assert (d.acao, d.proibicao) == ("PERGUNTAR_AO_SEGURADO", "custo_e_do_segurado"), d
    assert "custo ou pagamento" in d.valor and "“" in d.valor, "a pergunta tem de MOSTRAR o trecho da tela"


def test_NUNCA_custo_onde_a_seguradora_nao_espera_vai_a_pessoa(monkeypatch):
    monkeypatch.setattr(D, "ida_e_volta_permitida", lambda playbook: False)   # (ver o teste acima)
    s = sessao(REF_ALLIANZ_AUTO, "guincho")
    d = decidir(deduz("1", 95), s, TELA_OFICINA_ALLIANZ, provedor="openai",
                segunda_opiniao={**SEGUNDA_OK, "valor": "1"})
    assert (d.acao, d.proibicao) == ("PESSOA", "custo_e_do_segurado"), d


def test_NUNCA_o_valor_que_aceita_custo_numa_tela_sem_dinheiro():
    s = sessao(REF_ALLIANZ_RES, "maquina_de_lavar")
    d = decidir(deduz("Sim, aceito o custo de R$ 200", 95, classe="conduzir"), s, TELA_CONTINUAR)
    assert d.acao != "RESPONDER" and d.proibicao == "custo_e_do_segurado", d


def test_NUNCA_abrir_sinistro():
    s = sessao(REF_MAPFRE, "guincho")
    d = decidir(deduz("Abrir sinistro", 99), s, TELA_SINISTRO, provedor="openai",
                segunda_opiniao={**SEGUNDA_OK, "valor": "Abrir sinistro"})
    assert (d.acao, d.proibicao) == ("PESSOA", "abrir_sinistro"), d


def test_NUNCA_cancelar_pedido():
    s = sessao(REF_AZUL, "guincho")
    d = decidir(deduz("3", 99), s, TELA_ATENDIMENTO_AZUL, provedor="openai",
                segunda_opiniao={**SEGUNDA_OK, "valor": "3"})
    assert (d.acao, d.proibicao) == ("PESSOA", "cancelar_pedido"), d


@pytest.mark.parametrize("tela_ref, valor", [("azul", "1"), ("allianz", "2")])
def test_NUNCA_novo_atendimento_quando_ja_ha_um(tela_ref, valor):
    tela, ref = ((TELA_ATENDIMENTO_AZUL, REF_AZUL) if tela_ref == "azul" else (TELA_NOVO_ALLIANZ, REF_ALLIANZ_AUTO))
    s = sessao(ref, "guincho")
    d = decidir(deduz(valor, 99), s, tela, provedor="openai", segunda_opiniao={**SEGUNDA_OK, "valor": valor})
    assert (d.acao, d.proibicao) == ("PESSOA", "novo_atendimento"), d


def test_NUNCA_numero_inventado():
    s = sessao(REF_HDI, "guincho", slots={"veiculo_placa": PLACA})
    d = decidir(js(classe="responder_com_dado", acao="RESPONDER", valor="12345678900", nota=99), s, TELA_PLACA)
    assert (d.acao, d.proibicao) == ("PESSOA", "inventar_dado"), d


def test_NUNCA_dado_inventado_mesmo_com_as_duas_opinioes_concordando():
    s = sessao(REF_HDI, "guincho", slots={"veiculo_placa": PLACA})
    d = decidir(js(classe="responder_com_dado", acao="RESPONDER", valor="XYZ9Z99", nota=99), s, TELA_PLACA,
                provedor="openai", segunda_opiniao={**SEGUNDA_OK, "valor": "XYZ9Z99"})
    assert (d.acao, d.proibicao) == ("PESSOA", "inventar_dado"), d


def test_NUNCA_afirmar_cobertura():
    s = sessao(REF_ALLIANZ_RES, "maquina_de_lavar")
    d = decidir(js(classe="perguntar_ao_segurado", acao="PERGUNTAR_AO_SEGURADO",
                   valor="Seu seguro cobre o conserto, pode seguir?", nota=80), s, TELA_CONTINUAR)
    assert (d.acao, d.proibicao) == ("PESSOA", "afirma_cobertura")


def test_NUNCA_condominio_ou_empresarial():
    s = sessao(REF_ALLIANZ_RES, "encanador")
    d = decidir(deduz("2", 99), s, TELA_RAMO_ALLIANZ, provedor="openai", segunda_opiniao={**SEGUNDA_OK, "valor": "2"})
    assert (d.acao, d.proibicao) == ("PESSOA", "condominio_ou_empresarial"), d


def test_CONTROLE_a_mesma_tela_de_servico_escolher_o_servico_NAO_e_proibido():
    """A lista da 122 proibia escolher o serviço; aqui é DEDUZIR — e age com nota + 2ª opinião."""
    assert "escolhe_o_servico" in AC.PROIBICOES, "a V2 da 122 (bancada) não mudou"
    s = sessao_travada()
    d = decidir(deduz("Encanador", 90), s, TELA_SERVICOS, provedor="openai", segunda_opiniao=dict(SEGUNDA_OK))
    assert d.acao == "RESPONDER" and not d.proibicao


def test_o_gatilho_nunca_destravavel_nem_chama_o_modelo(dt):
    s = sessao_travada()
    d = destravar(EMPRESA_A, s, TELA_SERVICOS, gatilho="handoff_trigger:sinistro")
    assert (d.acao, d.proibicao) == ("PESSOA", "gatilho_nao_destravavel")
    assert dt.chamadas_ao_modelo == [] and dt.diario.linhas == []


# =============================================================================
# O LIMIAR (D2) e a 2ª OPINIÃO (D3)
# =============================================================================
def test_nota_69_nao_age_nem_com_limiar_pedido_abaixo():
    s = sessao_travada()
    for pedido in (70, 50, 0, None):
        d = decidir(deduz("Encanador", 69), s, TELA_SERVICOS, limiar=pedido, provedor="openai",
                    segunda_opiniao=dict(SEGUNDA_OK))
        assert d.acao != "RESPONDER" and d.proibicao == "nota_abaixo_do_limiar", (pedido, d)
        assert d.limiar == 70
    # CONTROLE: 70 age
    d = decidir(deduz("Encanador", 70), s, TELA_SERVICOS, provedor="openai", segunda_opiniao=dict(SEGUNDA_OK))
    assert d.acao == "RESPONDER"


def test_o_limiar_calibrado_para_cima_vale():
    s = sessao_travada()
    d = decidir(deduz("Encanador", 80), s, TELA_SERVICOS, limiar=85, provedor="openai",
                segunda_opiniao=dict(SEGUNDA_OK))
    assert d.proibicao == "nota_abaixo_do_limiar" and d.limiar == 85


def test_validar_limiar():
    assert DT.validar_limiar(70) == 70 and DT.validar_limiar(100) == 100
    for ruim in (69, 101, "x", None, True, 70.5):
        with pytest.raises(DT.LimiarRecusado):
            DT.validar_limiar(ruim)


def test_segunda_opiniao_do_mesmo_provedor_e_recusada():
    s = sessao_travada()
    d = decidir(deduz("Encanador", 95), s, TELA_SERVICOS, provedor="anthropic", segunda_opiniao=dict(SEGUNDA_OK))
    assert d.acao != "RESPONDER" and d.proibicao == "segunda_opiniao_do_mesmo_provedor", d


def test_segunda_opiniao_discordando_nao_age():
    s = sessao_travada()
    d = decidir(deduz("Encanador", 95), s, TELA_SERVICOS, provedor="openai",
                segunda_opiniao={**SEGUNDA_OK, "valor": "Desentupimento"})
    assert d.acao != "RESPONDER" and d.proibicao == "segunda_opiniao_discordou", d


def test_sem_segunda_opiniao_nao_age():
    s = sessao_travada()
    d = decidir(deduz("Encanador", 99), s, TELA_SERVICOS, provedor="openai")
    assert d.acao != "RESPONDER" and d.proibicao == "sem_segunda_opiniao", d


def test_a_reserva_decidiu_a_segunda_opiniao_troca_de_lado(dt):
    """🔴 O primário (openai) caiu, a RESERVA (anthropic) decidiu → a 2ª opinião vem da OPENAI."""
    s = sessao_travada()
    dt.respostas = {
        ("destravador", "openai"): ConnectionError("provedor caiu"),
        ("destravador", "anthropic"): deduz("Encanador", 90),
        ("destravador_segunda", "openai"): deduz("Encanador", 88),
        ("destravador_segunda", "anthropic"): deduz("Encanador", 99),
    }
    d = destravar(EMPRESA_A, s, TELA_SERVICOS)
    quem = [(c["papel"], c["provedor"]) for c in dt.chamadas_ao_modelo]
    assert quem == [("destravador", "openai"), ("destravador", "anthropic"),
                    ("destravador_segunda", "openai")], quem
    assert (d.acao, d.provedor, d.segunda_opiniao["provedor"]) == ("RESPONDER", "anthropic", "openai"), d


def test_a_segunda_opiniao_que_diz_ser_do_mesmo_provedor_e_recusada(dt):
    s = sessao_travada()
    dt.respostas = {
        ("destravador", "openai"): deduz("Encanador", 90),
        ("destravador_segunda", "anthropic"): deduz("Encanador", 90),
        # a borda diz que quem respondeu a "segunda" foi a openai (o provedor REAL da resposta vence)
        ("meta", "destravador_segunda", "anthropic"): {"model_provider": "openai", "model_name": "x"},
    }
    d = destravar(EMPRESA_A, s, TELA_SERVICOS)
    assert d.acao != "RESPONDER" and d.proibicao == "segunda_opiniao_do_mesmo_provedor", d


def test_provedor_de_quem_decidiu_desconhecido_nao_deduz(dt):
    s = sessao_travada()
    dt.respostas = {
        ("destravador", "openai"): deduz("Encanador", 95),
        ("meta", "destravador", "openai"): {"model_name": "modelo-sem-nome"},
        ("destravador_segunda", "anthropic"): deduz("Encanador", 95),
    }
    d = destravar(EMPRESA_A, s, TELA_SERVICOS)
    assert d.acao != "RESPONDER" and d.proibicao == "sem_segunda_opiniao", d
    assert [c["papel"] for c in dt.chamadas_ao_modelo] == ["destravador"]


def test_o_modelo_caiu_de_vez_pessoa_e_nada_no_diario(dt):
    s = sessao_travada()
    dt.respostas = {"destravador": ConnectionError("tudo caiu")}
    d = destravar(EMPRESA_A, s, TELA_SERVICOS)
    assert (d.acao, d.proibicao, d.modelo_chamado) == ("PESSOA", "modelo_falhou", False)
    assert dt.diario.linhas == []


# =============================================================================
# O MODO (cerebro_modos) — duas corretoras, o cinto do código, o limiar da linha
# =============================================================================
def _ligar(amb_, company, seguradora="yelum", ramo="todos", modo="on", limiar=None):
    linha = {"company_id": company, "insurer_key": seguradora, "ramo": ramo, "modo": modo}
    if limiar is not None:
        linha["limiar"] = limiar
    amb_.chaves.append(linha)


def test_duas_corretoras_nao_leem_o_modo_uma_da_outra(amb):
    _ligar(amb, EMPRESA_A, limiar=85)
    assert asyncio.run(DT.modo_do_destravador(EMPRESA_A, "yelum", "residencial")) == ("on", 85)
    assert asyncio.run(DT.modo_do_destravador(EMPRESA_B, "yelum", "residencial")) == ("off", 70)
    # o banco que VAZA a linha de A quando B pergunta: o cinto do código recusa
    AC._CACHE_DA_CHAVE.clear()
    amb.banco_vaza = True
    assert asyncio.run(DT.modo_do_destravador(EMPRESA_B, "yelum", "residencial")) == ("off", 70)
    AC._CACHE_DA_CHAVE.clear()
    assert asyncio.run(DT.modo_do_destravador(EMPRESA_A, "yelum", "residencial")) == ("on", 85)  # CONTROLE


def test_linha_com_limiar_abaixo_de_70_vale_off(amb):
    _ligar(amb, EMPRESA_A, limiar=69)
    assert asyncio.run(DT.modo_do_destravador(EMPRESA_A, "yelum", "auto")) == ("off", 70)


def test_sem_limiar_na_linha_vale_70_e_sem_banco_vale_off(amb, monkeypatch):
    _ligar(amb, EMPRESA_A, modo="sombra")
    assert asyncio.run(DT.modo_do_destravador(EMPRESA_A, "yelum", "auto")) == ("sombra", 70)

    async def _sem_banco():
        raise ConnectionError("fora")
    AC._CACHE_DA_CHAVE.clear()
    monkeypatch.setattr(R, "_db", _sem_banco)
    assert asyncio.run(DT.modo_do_destravador(EMPRESA_A, "yelum", "auto")) == ("off", 70)


# =============================================================================
# A SOMBRA (ponto B) e a CONVERSA DO SEGURADO (P-122-07)
# =============================================================================
def test_agendar_em_sombra_decide_grava_nao_agiu_e_nao_envia(dt):
    _ligar(dt, EMPRESA_A, modo="sombra")
    s = sessao_travada()
    dt.respostas = {("destravador", "openai"): deduz("Encanador", 90),
                    ("destravador_segunda", "anthropic"): deduz("Encanador", 90)}

    async def _rodar():
        t = DT.agendar_em_sombra(EMPRESA_A, dict(s), TELA_SERVICOS, gatilho=s["reason"])
        assert t is not None
        return await t
    p = asyncio.run(_rodar())
    assert dt.enviadas == [] and dt.wa == [] and dt.grupo == []
    [linha] = dt.diario.linhas
    assert (linha["modo"], linha["acao"], linha["classe"]) == ("sombra", "nao_agiu", "deduzir")
    assert "nada foi enviado" in linha["explicacao_para_gente"]
    assert p["gatilho"] == "tela_que_decide:escolhe_o_servico" and p["diario_id"] == "diario-1"
    assert p["destravador"]["acao_final"] == "RESPONDER" and p["sistema"]["acao"] == "PESSOA"
    # a sombra NÃO usa o relógio do disjuntor de produção
    assert not any(c["relogio"] for c in dt.chamadas_ao_modelo)
    # CONTROLE: a chave `on` (não `sombra`) → a sombra não roda (quem decide é o roteador)
    dt.chaves.clear()
    _ligar(dt, EMPRESA_A, modo="on")
    AC._CACHE_DA_CHAVE.clear()
    dt.redis.d.clear()
    antes = len(dt.chamadas_ao_modelo)

    async def _de_novo():
        tt = DT.agendar_em_sombra(EMPRESA_A, dict(s), TELA_SERVICOS, gatilho=s["reason"])
        return await tt if tt is not None else None
    assert asyncio.run(_de_novo()) is None and len(dt.chamadas_ao_modelo) == antes


class _BancoDaConversa:
    """A borda do banco da conversa do SEGURADO: conversas de DUAS corretoras com o mesmo telefone."""

    def __init__(self, conversas, mensagens):
        self.client, self.conversas, self.mensagens, self.filtros_vistos = self, conversas, mensagens, []

    def table(self, nome):
        banco = self

        class _Q:
            def __init__(self):
                self.f = {}

            def select(self, *a, **k):
                return self

            def eq(self, c, v):
                self.f[c] = v
                return self

            def in_(self, c, v):
                self.f[c] = list(v)
                return self

            def order(self, *a, **k):
                return self

            def limit(self, *a, **k):
                return self

            async def execute(self):
                banco.filtros_vistos.append((nome, dict(self.f)))
                if nome == "conversations":
                    rows = [c for c in banco.conversas if c["company_id"] == self.f.get("company_id")
                            and c["user_phone"] in self.f.get("user_phone", [])]
                    return types.SimpleNamespace(data=rows)
                if nome == "messages":
                    rows = [m for m in banco.mensagens if m["conversation_id"] == self.f.get("conversation_id")]
                    return types.SimpleNamespace(data=list(reversed(rows)))
                return types.SimpleNamespace(data=[])
        return _Q()


def test_a_conversa_do_segurado_vem_do_banco_so_da_corretora_dona(dt, monkeypatch):
    import app.core.database as core_db

    fone = CLIENTE[2:]
    banco = _BancoDaConversa(
        [{"id": "conv-A", "company_id": EMPRESA_A, "user_phone": fone},
         {"id": "conv-B", "company_id": EMPRESA_B, "user_phone": fone}],
        [{"conversation_id": "conv-A", "role": "user", "content": "a pia da cozinha está vazando"},
         {"conversation_id": "conv-A", "role": "assistant", "content": "Vou acionar a assistência."},
         {"conversation_id": "conv-B", "role": "user", "content": "SEGREDO DA OUTRA CORRETORA"}])
    monkeypatch.setattr(core_db, "get_supabase_client", lambda: banco)
    s = sessao_travada(slots={})
    msgs = asyncio.run(DT.mensagens_do_destravador(EMPRESA_A, s, TELA_SERVICOS, gatilho=s["reason"]))
    assert "[segurado] a pia da cozinha está vazando" in msgs["user"]
    assert "[corretora] Vou acionar a assistência." in msgs["user"]
    assert "SEGREDO DA OUTRA CORRETORA" not in msgs["user"]
    assert banco.filtros_vistos[0][0] == "conversations"
    assert banco.filtros_vistos[0][1]["company_id"] == EMPRESA_A, "o filtro da corretora não foi ao banco"
    # CONTROLE: a corretora B lê a DELA
    msgs_b = asyncio.run(DT.mensagens_do_destravador(EMPRESA_B, s, TELA_SERVICOS, gatilho=s["reason"]))
    assert "SEGREDO DA OUTRA CORRETORA" in msgs_b["user"] and "pia da cozinha" not in msgs_b["user"]


# =============================================================================
# ESTRUTURA — o destravador não tem como enviar; a constante que decide diz por quê
# =============================================================================
def test_o_destravador_nao_tem_como_enviar():
    fonte = inspect.getsource(DT)
    proibidos = ("send_message", "reply_human_phase", "_emit(", "send_to_insurer", "send_to_client",
                 "save_active_dispatch", "enviar_ao_grupo")
    assert [p for p in proibidos if p in fonte] == []
    # F1c: `llm`/`llm_segunda` (a injeção da bancada) — nenhum deles é um canal de envio
    assert list(inspect.signature(DT.destravar).parameters) == ["company_id", "sessao", "tela", "gatilho",
                                                               "modo", "limiar", "llm", "llm_segunda"]


def test_toda_regex_que_decide_tem_o_porque_ao_lado():
    """CLAUDE.md §9.5: constante que escolhe entre alternativas diz POR QUÊ, escrito ao lado."""
    linhas = inspect.getsource(DT).splitlines()
    sem = []
    for i, l in enumerate(linhas):
        if l.startswith("_RX_") or l.startswith("GATILHOS_NUNCA") or l.startswith("LIMIAR_MINIMO"):
            acima = "\n".join(linhas[max(0, i - 6):i])
            if "constante_justificada" not in acima:
                sem.append(l.split("=")[0].strip())
    assert sem == [], sem


def test_nenhum_modelo_por_nome_no_destravador():
    fonte = inspect.getsource(DT)
    assert not [m for m in ("gpt-", "claude-", "sonnet", "opus") if m in fonte.lower()]


# =============================================================================
# F1c — os ajustes antes da bancada real (cada um reproduzido VERMELHO antes do conserto)
# =============================================================================
TELA_DIGITAR_ENDERECO = tela_real("hdi-auto", r"informar o endere[çc]o onde o ve[íi]culo est[áa] agora")
TELA_TIPO_DE_SERVICO = tela_real("allianz-residencial", r"Informe o tipo de servi[çc]o:\s*\n\s*\n\*1 -\* Servi[çc]os Emerg")
TELA_PEDE_OUTRO_HDI = tela_real("hdi-auto", r"Gostaria de solicitar algum outro servi[çc]o\?")
TELA_ALGO_MAIS = tela_real("porto-auto", r"Posso te ajudar com algo mais\?[\s\S]*Novo atendimento")
TELA_CHAVEIRO_ALLIANZ = tela_real("allianz-residencial", r"\*1 -\* Abrir a porta")
TELA_JA_HA_UM_ALLIANZ = tela_real("allianz-residencial", r"Identifiquei que temos uma solicita[çc][ãa]o")
SEGUNDA = lambda v: {**SEGUNDA_OK, "valor": v}   # noqa: E731


@pytest.mark.parametrize("slots, valor, e_dado", [
    # 📊 os achados: um RÓTULO passava por dado do caso porque casava por substring
    ({"endereco_origem": "{ENDERECO}"}, "Digitar endereço", False),
    ({"endereco_origem": "{ENDERECO}"}, "endereço", False),
    ({"bairro": "Centro"}, "Centro de serviços", False),
    ({"local": "casa"}, "Casa de praia", False),
    # CONTROLE: o dado de verdade continua sendo dado
    ({"endereco_origem": "{ENDERECO}"}, "{ENDERECO}", True),
    ({"bairro": "Centro"}, "Centro", True),
    ({"veiculo_placa": PLACA}, PLACA.lower(), True),
    ({"endereco_origem": "Rua das Flores 123 fundos"}, "Rua das Flores 123", True),
    ({"endereco_origem": "Rua das Flores 123"}, "Rua das Flores, 123 - fundos", True),
])
def test_e_dado_do_caso_nao_aceita_rotulo_nem_pedaco_curto(slots, valor, e_dado):
    s = sessao(REF_HDI, "guincho", slots=slots)
    assert DT._e_dado_do_caso(valor, s) is e_dado, (slots, valor)


def test_a_opcao_da_tela_nao_passa_por_dado_do_caso_e_vai_a_regua_do_deduzir():
    """📊 F1c achado 1, pela POLÍTICA: "Digitar endereço" com o endereço do caso mascarado era
    RESPONDER livre (responder_com_dado); é uma ESCOLHA da tela — a régua do DEDUZIR vale."""
    s = sessao(REF_HDI, "guincho", slots={"endereco_origem": "{ENDERECO}"})
    d = decidir(js(classe="responder_com_dado", acao="RESPONDER", valor="Digitar endereço", nota=95), s,
                TELA_DIGITAR_ENDERECO, pedir_segunda=True)
    assert (d.classe, d.proibicao) == ("deduzir", "precisa_segunda_opiniao"), d
    # CONTROLE: o dado do caso, na tela de placa, continua livre
    s2 = sessao(REF_HDI, "guincho", slots={"veiculo_placa": PLACA})
    d2 = decidir(js(classe="responder_com_dado", acao="RESPONDER", valor=PLACA, nota=95), s2, TELA_PLACA)
    assert (d2.acao, d2.classe, d2.proibicao) == ("RESPONDER", "responder_com_dado", ""), d2


@pytest.mark.parametrize("valor", ["3", "Outros serviços"])
def test_a_categoria_outros_servicos_do_primeiro_menu_e_deduzir_nao_novo_atendimento(valor):
    """📊 F1c achado 2 — `des-D-escolhe_servico-allianz-025`: nota 92 + 2ª opinião concordando deram
    PESSOA (`novo_atendimento`), porque o NUNCA usava a régua da NAVEGAÇÃO (`_RX_COMECA_TRABALHO_NOVO`,
    que casa "outros serviços"). No 1º menu, "Outros serviços" é CATEGORIA: não há atendimento ainda."""
    s = sessao(REF_ALLIANZ_RES, "")
    d = decidir(deduz(valor, 92), s, TELA_TIPO_DE_SERVICO, provedor="openai", segunda_opiniao=SEGUNDA(valor))
    assert (d.acao, d.classe, d.proibicao) == ("RESPONDER", "deduzir", ""), d


@pytest.mark.parametrize("tela, ref, valor", [
    (TELA_JA_HA_UM_ALLIANZ, REF_ALLIANZ_RES, "2"),          # "Abrir novo atendimento"
    (TELA_ALGO_MAIS, "porto-auto-whatsapp@v1", "Novo atendimento"),   # "Posso te ajudar com algo mais?"
    (TELA_PEDE_OUTRO_HDI, REF_HDI, "Sim"),                   # o "Sim" que abriria outro serviço
])
def test_NUNCA_novo_atendimento_continua_onde_ja_ha_um(tela, ref, valor):
    s = sessao(ref, "guincho")
    d = decidir(deduz(valor, 99), s, tela, provedor="openai", segunda_opiniao=SEGUNDA(valor))
    assert (d.acao, d.proibicao) == ("PESSOA", "novo_atendimento"), d


def test_CONTROLE_abrir_a_porta_e_o_servico_de_chaveiro_nao_um_novo_atendimento():
    s = sessao(REF_ALLIANZ_RES, "chaveiro")
    d = decidir(deduz("1", 90), s, TELA_CHAVEIRO_ALLIANZ, provedor="openai", segunda_opiniao=SEGUNDA("1"))
    assert d.proibicao != "novo_atendimento", d


@pytest.mark.parametrize("rotulo, tela, abre", [
    # 📊 os rótulos do acervo (git 20fb1c4): "Pedir outro serviço" (hdi, depois da solicitação concluída)
    ("Pedir outro serviço", "", True),
    ("Não, abrir novo serviço", "", True),
    ("Abrir um novo atendimento", "", True),
    # o PLURAL é categoria — só abre trabalho novo quando a tela mostra que já há um
    ("Outros serviços", "Vamos lá! Informe o tipo de serviço:", False),
    ("Outros serviços", "Identifiquei que temos uma solicitação de serviço feita. O que deseja?", True),
    # CONTROLE: o serviço de chaveiro não é atendimento novo
    ("Abrir a porta", "O que você precisa?", False),
])
def test_abre_novo_atendimento_pelo_rotulo(rotulo, tela, abre):
    assert DT._abre_novo_atendimento(DT._n(rotulo), D._norm_text(tela), False, False, {}) is abre
