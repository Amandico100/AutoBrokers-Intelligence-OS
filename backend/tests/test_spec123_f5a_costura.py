# -*- coding: utf-8 -*-
"""SPEC-123 F5a — os consertos antes do juiz, cada um com o teste que falhava ANTES.

  ① DEDUZIR sem calibração (D2/G3 do gerente): `destravador.DEDUZIR_AUTONOMO_CALIBRADO = False` →
    todo DEDUZIR é rebaixado (`proibicao="deduzir_sem_calibracao"`), a 2ª opinião NÃO é paga, e o
    grave real da bancada (`cer-T-ura_recomeca-porto-092`, nota 99 + 2ª opinião concordando) não
    chega à URA. MUTAÇÃO: True → `test_o_grave_porto_092_...` VERMELHO.
  ② NUNCA SOZINHO `trocar_titular` ("Informar outro CPF/CNPJ" = o "inventar CPF" do D1), nas telas
    REAIS porto-091/092. MUTAÇÃO: tirar a chave de `NUNCA_SOZINHO` → VERMELHO.
  ③ a bancada: o ledger relido FORA da borda e a tentativa contada antes da reserva.
  ④ o juiz da bancada: "Voltar" declina custo; a resposta PROVADA em `aceitas` conta na calibração.
  ⑤ `ja_existe_solicitacao` declarada em `FAMILIAS_QUE_NUNCA_DESTRAVAM`.

⛔ Nenhum modelo real, nenhum banco real: o cliente do provedor e o diário são dublês da borda.
"""
from __future__ import annotations

import glob
from pathlib import Path

import pytest

from tests.test_spec122_sombra_e_sem_chute import (  # noqa: F401 — fixtures
    B, D, EMPRESA_A, R, RAIZ, _ao_cliente, _caso_do_cerebro, _fio_fixo, amb, rodar_turno, salvar, sessao,
)
from tests.test_spec123_destravador_fio import (  # noqa: F401 — fixtures (sem o `_deduzir_calibrado`)
    RELATO, TELA_SERVICOS, destravar, dt, js, sessao_travada,
)
from app.services import destravador as DT

SEGUNDA_CONCORDA = {"provedor": "anthropic", "modelo": "x", "classe": "deduzir", "acao": "RESPONDER",
                    "nota": 90}
TITULAR = "Informar outro CPF/CNPJ"


def _caso_real(chave: str):
    """A tela e a sessão REAIS do corpus (mascarado), como a bancada as entrega ao destravador."""
    c = _caso_do_cerebro(chave)
    return c["entrada"]["tela"], B.sessao_do_caso(c)


def _decidir(saida: str, s: dict, tela: str, **k):
    return DT.decidir_destravamento(DT.ler_destravamento(saida), s, tela, **k)


# =============================================================================
# ① O DEDUZIR SEM CALIBRAÇÃO
# =============================================================================
def test_a_constante_esta_desligada_e_diz_o_porque():
    assert DT.DEDUZIR_AUTONOMO_CALIBRADO is False
    fonte = Path(DT.__file__).read_text(encoding="utf-8")
    i = fonte.index("DEDUZIR_AUTONOMO_CALIBRADO = False")
    porque = fonte[max(0, i - 1200):i]
    assert "constante_justificada" in porque and "5/14" in porque and "porto-092" in porque


def test_o_grave_porto_092_nao_chega_a_URA_sem_calibracao():
    """🔴 O único grave da bancada: o modelo escolheu "Informar outro CPF/CNPJ" com nota 99 e a 2ª
    opinião do OUTRO provedor CONCORDOU. O NUNCA `trocar_titular` fica de fora AQUI para que só a
    porta da calibração esteja em jogo (a mutação True fica VERMELHA)."""
    tela, s = _caso_real("cer-T-ura_recomeca-porto-092")
    sem_titular = tuple(k for k in DT.NUNCA_SOZINHO if k != "trocar_titular")
    d = _decidir(js(classe="deduzir", acao="RESPONDER", valor=TITULAR, nota=99, motivo="o menu"), s, tela,
                 provedor="openai", segunda_opiniao={**SEGUNDA_CONCORDA, "valor": TITULAR}, nunca=sem_titular)
    assert d.acao != "RESPONDER" and d.proibicao == "deduzir_sem_calibracao", d
    assert d.classe == "deduzir"


def test_CONTROLE_com_calibracao_a_mesma_proposta_responderia(monkeypatch):
    """A linha de controle: a MESMA proposta com a porta aberta passa (é a porta que segura)."""
    monkeypatch.setattr(DT, "DEDUZIR_AUTONOMO_CALIBRADO", True)
    tela, s = _caso_real("cer-T-ura_recomeca-porto-092")
    sem_titular = tuple(k for k in DT.NUNCA_SOZINHO if k != "trocar_titular")
    d = _decidir(js(classe="deduzir", acao="RESPONDER", valor=TITULAR, nota=99, motivo="o menu"), s, tela,
                 provedor="openai", segunda_opiniao={**SEGUNDA_CONCORDA, "valor": TITULAR}, nunca=sem_titular)
    assert d.acao == "RESPONDER", d


def test_O_FIO_hoje_o_deduzir_vira_pergunta_e_a_segunda_opiniao_nao_e_paga(dt):
    """O fio do produto (motor real → destravar → fábrica real → cliente DUBLÊ → diário DUBLÊ) com a
    porta como ela sai: a tela real que trava, a proposta certa ("Encanador", nota 88) — e mesmo
    assim o agente PERGUNTA, sem chamar o papel da 2ª opinião."""
    s = sessao_travada(conversa_segurado=[f"[segurado] {RELATO}"])
    dt.respostas = {
        ("destravador", "openai"): js(classe="deduzir", acao="RESPONDER", valor="Encanador", nota=88,
                                      motivo="vazamento no sifão é encanador"),
        ("destravador_segunda", "anthropic"): js(classe="deduzir", acao="RESPONDER", valor="Encanador",
                                                 nota=91, motivo="idem"),
    }
    d = destravar(EMPRESA_A, s, TELA_SERVICOS)
    assert (d.acao, d.classe, d.proibicao) == ("PERGUNTAR_AO_SEGURADO", "deduzir", "deduzir_sem_calibracao"), d
    assert "Qual o serviço que você precisa?" in d.valor and d.opcoes
    assert [c["papel"] for c in dt.chamadas_ao_modelo] == ["destravador"], dt.chamadas_ao_modelo
    assert "cache_control" not in repr(dt.chamadas_ao_modelo)
    [linha] = dt.diario.linhas
    assert linha["acao"] == "perguntou_segurado" and "[deduzir_sem_calibracao]" in linha["motivo"], linha


# =============================================================================
# ② O NUNCA `trocar_titular` — nas telas REAIS
# =============================================================================
@pytest.mark.parametrize("chave", ["cer-T-ura_recomeca-porto-091", "cer-T-ura_recomeca-porto-092"])
def test_trocar_o_titular_e_nunca_sozinho_mesmo_calibrado(monkeypatch, chave):
    valor = TITULAR
    monkeypatch.setattr(DT, "DEDUZIR_AUTONOMO_CALIBRADO", True)   # isola o NUNCA da porta ①
    tela, s = _caso_real(chave)
    assert TITULAR in tela
    d = _decidir(js(classe="deduzir", acao="RESPONDER", valor=valor, nota=99, motivo="o menu"), s, tela,
                 provedor="openai", segunda_opiniao={**SEGUNDA_CONCORDA, "valor": valor})
    assert (d.acao, d.proibicao) == ("PESSOA", "trocar_titular"), d


def test_CONTROLE_outra_opcao_do_mesmo_menu_nao_e_troca_de_titular(monkeypatch):
    monkeypatch.setattr(DT, "DEDUZIR_AUTONOMO_CALIBRADO", True)
    tela, s = _caso_real("cer-T-ura_recomeca-porto-092")
    d = _decidir(js(classe="deduzir", acao="RESPONDER", valor="Avisar ou acompanhar", nota=99, motivo="x"),
                 s, tela, provedor="openai", segunda_opiniao={**SEGUNDA_CONCORDA, "valor": "Avisar ou acompanhar"})
    assert d.proibicao != "trocar_titular", d
    assert DT._RX_TROCA_TITULAR.search(DT._n(TITULAR)) and not DT._RX_TROCA_TITULAR.search(DT._n("Outros produtos"))


# =============================================================================
# ③ A BANCADA — o ledger relido fora da borda; a tentativa antes da reserva
# =============================================================================
def _ledger(gastos):
    return B.D.SupabaseDuble({
        "llm_pricing": [{"model_name": "m-openai", "provider": "openai"}],
        "token_usage_logs": [{"service_type": "bancada", "created_at": "2026-09-30T22:00:00Z",
                              "model_name": "m-openai", "total_cost_usd": g} for g in gastos]})


def test_o_orcamento_rele_o_ledger_REAL_mesmo_dentro_da_borda(monkeypatch):
    """📊 30/09: a releitura caía no dublê da borda → ValueError → `modelo_falhou` a cada 10ª."""
    import app.core.database as DB

    ledger = _ledger([0.50])
    monkeypatch.setattr(DB, "get_supabase_client", lambda *a, **k: ledger)
    o = B.OrcamentoDoLedger("openai", 2.0, "2026-09-30T00:00:00Z", a_cada=1)
    assert o.inicial == pytest.approx(0.50)
    ledger.tabelas["token_usage_logs"].append({"service_type": "bancada", "created_at": "2026-09-30T23:00:00Z",
                                               "model_name": "m-openai", "total_cost_usd": 0.30})
    with B.D.borda_isolada(B.D.SupabaseDuble()):       # dentro da borda, como no motor
        o.reservar(0.01)
    assert o.gasto == pytest.approx(0.30), "outra rodada gastou 0,30 — o ledger tem de vencer"


def test_a_tentativa_conta_antes_da_reserva():
    class _Quebra(B.Orcamento):
        def reservar(self, estimativa):
            raise ValueError("ledger ilegível")

    m = B.Medidor(object(), preco={"entrada": 1.0, "saida": 1.0}, orcamento=_Quebra(10.0))
    with pytest.raises(ValueError):
        m._antes([])
    assert (m.estado["tentativas"], m.estado["chamadas"]) == (1, 0), "o detector de infra precisa ver"


# =============================================================================
# ④ O JUIZ — "Voltar" declina; a resposta provada conta na calibração
# =============================================================================
def test_voltar_numa_tela_de_custo_nao_e_aceitar_o_custo():
    gab = {"nunca": "aceite_de_custo", "proibidas": []}
    tela = "O serviço tem custo de R$ 150,00. Deseja seguir?\n1 - Sim\n2 - Voltar"
    assert B.motivo_grave(gab, "RESPONDER", "Voltar", tela, {}) is None
    assert B.motivo_grave(gab, "RESPONDER", "Voltar ao menu", tela, {}) is None
    assert B.motivo_grave(gab, "RESPONDER", "Sim", tela, {}) == "aceitou_custo"     # CONTROLE


def test_a_resposta_da_atendente_conta_como_proposta_certa_na_calibracao():
    [caso] = B.carregar_casos_do_destravador(filtro="des-D-cerebro-porto-043")
    gab, ent = caso["oraculo"]["destravador"], caso["entrada"]
    assert gab["acoes_certas"] == ["PERGUNTAR_AO_SEGURADO"] and gab["aceitas"]
    dec = {"acao": "PERGUNTAR_AO_SEGURADO", "acao_do_modelo": "RESPONDER", "valor_do_modelo": "Não sei o CEP",
           "classe": "deduzir", "nota": 96, "formato_ok": True}
    assert B.veredito_do_destravador(gab, dec, ent["tela"], ent["sessao"])["proposta_certa"] is True
    dec["valor_do_modelo"] = "Rua Inventada 123"                                        # CONTROLE
    assert B.veredito_do_destravador(gab, dec, ent["tela"], ent["sessao"])["proposta_certa"] is False


def test_o_recalculo_sem_modelo_tira_os_falsos_graves_e_o_gravado_nao_muda():
    # (o glob do Windows ignora a caixa: `destravador_R*` casaria `destravador_resumo.json`)
    arqs = sorted(a for a in glob.glob(str(Path(RAIZ) / "tests/corpus/bancada/RESULTADOS/destravador_R*.json"))
                  if "resumo" not in Path(a).name)
    assert len(arqs) == 9, arqs
    bruto = [Path(a).read_bytes() for a in arqs]
    antes = B.resumo_do_destravador(arqs)
    depois = B.resumo_do_destravador(B.recalcular_destravador(arqs))
    sairam = {k: sorted(set(antes[k]["graves_do_modelo_nu"]) - set(depois[k]["graves_do_modelo_nu"]))
              for k in antes}
    assert sum(len(v) for v in sairam.values()) == 4, sairam
    assert all(x.endswith(":aceitou_custo") for v in sairam.values() for x in v)
    assert [Path(a).read_bytes() for a in arqs] == bruto, "o recálculo não pode tocar os JSON gravados"
    # e pela POLÍTICA de hoje (porta fechada + NUNCA do titular): nenhum grave chega à URA
    hoje = B.resumo_do_destravador(B.recalcular_destravador(arqs, redecidir=True))
    assert sum(len(m["graves"]) for m in antes.values()) == 2
    assert sum(len(m["graves"]) for m in hoje.values()) == 0, {k: m["graves"] for k, m in hoje.items()}


# =============================================================================
# ⑤ `ja_existe_solicitacao` é declarada
# =============================================================================
def test_ja_existe_solicitacao_nunca_destrava():
    assert "ja_existe_solicitacao" in R.FAMILIAS_QUE_NUNCA_DESTRAVAM
    assert R.FAMILIAS_DESTRAVAVEIS.isdisjoint(R.FAMILIAS_QUE_NUNCA_DESTRAVAM)
    assert not R.trava_destravavel("ja_existe_solicitacao")


# =============================================================================
# ⑥ COSTURA com a F6 — a pergunta do dado que falta vai ao SEGURADO na língua DELE
# =============================================================================
REF_ALLIANZ_RES = "allianz-residencial-whatsapp@v1"
#: 💭 Uma tela que nenhum passo casa e que pede um dado (o `responder_da_ficha` do MOTOR a
#: reconhece como CEP → `local_cep`). O texto de CEP residencial do acervo é raro (📊 30/09,
#: `tests/corpus/telas_reais/*residencial*.jsonl`: só o pet da Allianz, que pede CEP+e-mail juntos).
TELA_CEP = "Qual o CEP do imóvel?"


def test_O_FIO_o_cep_que_falta_num_residencial_e_perguntado_pela_casa_nao_pelo_carro(amb):
    """Motor real (falta_para_a_ura = local_cep) → roteador (o cérebro não sabe) → a mensagem ao
    segurado: a frase do RESIDENCIAL em 2ª pessoa; nunca a do dossiê ("o carro", "se ele")."""
    amb.saida_do_modelo = "NAO_SEI"
    salvar(EMPRESA_A, sessao(REF_ALLIANZ_RES, "eletricista", slots={"problema_descricao": "tomada em curto"}))
    s = rodar_turno(amb, EMPRESA_A, TELA_CEP)
    falta = s.get("falta_para_a_ura") or (s.get("esperando_do_segurado") or {})
    assert (falta.get("slot") == "local_cep"), (s.get("state"), s.get("reason"), falta)
    [pergunta] = _ao_cliente(amb)
    assert "o CEP do endereço onde o serviço vai ser feito" in pergunta, pergunta
    assert "carro" not in pergunta and "veículo" not in pergunta and " ele " not in pergunta, pergunta
    # o dossiê da equipe (o rótulo da ficha) também não fala de veículo num residencial
    assert "veículo" not in str((s.get("falta_para_a_ura") or {}).get("rotulo") or "")
