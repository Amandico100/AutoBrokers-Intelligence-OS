# -*- coding: utf-8 -*-
"""SPEC-131-A · F2 — o pedido e a consulta certos.

O que este arquivo prova, sempre com o MOTOR real (`pedido.de_apolice`, `presets`, `config.mesclar`) e nenhuma rede:
  · RAMO: sigla desconhecida → `RamoIndisponivel(motivo="ramo_desconhecido")`, NUNCA AUTO (mutação 3 da SPEC);
    ramo conhecido fora do Agger → `ramo_nao_cotado`.
  · AS OPÇÕES DA RENOVAÇÃO: `anterior` (igual ou maior que a ficha), `franquia_reduzida` (cede se repetida),
    `completa_mais`; ⛔ `economica`/`minima` nunca (mutação 7 da SPEC).
  · CONFIG: antecedência 10, janela, opções, teto por corretora; o que não valida volta ao padrão.
  · CPF/CNPJ: a régua pura do dígito verificador (P-1310-02).
  · LENTE: o `anterior` de 3 fichas sintéticas reconferido campo a campo por um caminho INDEPENDENTE (abaixo).

⛔ Tudo sintético: nenhum CPF, placa, nome ou endereço real; nenhuma corretora pelo nome.
"""
from __future__ import annotations

import copy
import random
import sys
from dataclasses import fields
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.providers.policy_data_provider import (  # noqa: E402
    Apolice, ApoliceDocumental, CampoComOrigem, Cobertura, ItemDeRisco, LinhaDeCoberturaDoDocumento,
    RamoCanonico, SeguradoraCanonica, Vigencia, indisponivel_por, normalizar_rotulo, reconciliar,
)
from app.services.multicalculo import config as CFG  # noqa: E402
from app.services.multicalculo import pedido as PED  # noqa: E402
from app.utils import documento_br as DOC  # noqa: E402
from portal_worker.multicalculo import presets as P  # noqa: E402

CPF = "529.982.247-25"          # sintético (o mesmo da 129-B)
CNPJ = "11.222.333/0001-81"     # sintético (o exemplo clássico)
PORTO = "05886"
FIM = date(2026, 11, 1)
CONFIG = CFG.mesclar(None, "renovacao")


# ---------------------------------------------------------------------------------------------------------------------
# as peças sintéticas
# ---------------------------------------------------------------------------------------------------------------------
def _d(v) -> Decimal:
    return Decimal(str(v)).quantize(Decimal("0.01"))


def _apolice(ramo: str, coberturas=(), *, placa=None) -> Apolice:
    item = ItemDeRisco(item=1, placa=CampoComOrigem(valor=placa, origem="sistema_de_gestao")) if placa else None
    return Apolice(apolice_ref="sintetica:1", numero_humano="0000000001",
                   seguradora=SeguradoraCanonica(chave="PORT", coenti=PORTO), ramo=RamoCanonico(abreviatura=ramo),
                   vigencia=Vigencia(inicio=date(2025, 11, 1), fim=FIM, situacao="VIGENTE"),
                   coberturas=tuple(coberturas), item_de_risco=item)


def _ficha(linhas=(), *, objeto=None) -> ApoliceDocumental:
    """linhas = (rótulo, limite, franquia_texto)."""
    nomes = {f.name for f in fields(ApoliceDocumental)}
    extra = {"tipo_documento": "apolice", "objeto_do_risco": objeto, "leitura": {"estado": "fechou"}}
    return ApoliceDocumental(
        linhas=tuple(LinhaDeCoberturaDoDocumento(rotulo=r, limite=_d(l) if l is not None else indisponivel_por().valor,
                                                 premio=_d(10), franquia_texto=f, pagina=1)
                     for (r, l, f) in linhas),
        **{k: v for k, v in extra.items() if k in nomes})


def _perfil_auto():
    return {"segurado": {"cpf_cnpj": CPF, "nome": "Pessoa Sintetica", "nascimento": "1980-02-01", "sexo": "F",
                         "estado_civil": 1, "cep": "88000-000"},
            "veiculo": {"fipe": "009999-1", "ano_fabricacao": 2019, "ano_modelo": 2020, "combustivel": "flex"},
            "renovacao": {"bonus_anterior": 4}, "condutor": {"tempo_habilitacao": 15}}


def _perfil_cond():
    return {"segurado": {"cpf_cnpj": CNPJ, "nome": "Condominio Sintetico"},
            "risco": {"logradouro": "Rua Sintetica", "bairro": "Centro", "cidade": "Cidade Sintetica", "uf": "SC",
                      "tipo_imovel": "residencial", "estrutura": "vertical", "ano_fundacao": "2005", "blocos": "1",
                      "pavimentos": "5", "elevadores": 0, "cep": "88000000"},
            "renovacao": {"bonus_anterior": 5, "sinistros_anterior": 0}}


def _perfil_resi():
    return {"segurado": {"cpf_cnpj": CPF, "nome": "Pessoa Sintetica", "nascimento": "1980-02-01"},
            "risco": {"logradouro": "Rua Sintetica", "bairro": "Centro", "cidade": "Cidade Sintetica", "uf": "SC",
                      "tipo_imovel": "casa", "construcao": "superior", "uso": "habitual", "objeto": "predio + conteudo",
                      "cep": "88000000"},
            "renovacao": {"bonus_anterior": 0, "sinistros_anterior": 0}}


def _auto(linhas):
    ficha = _ficha(linhas, objeto={"chassi": "9BWZZZ377VT000001"})
    return PED.de_apolice(reconciliar(_apolice("AUTO", placa="AAA1A11"), ficha), _perfil_auto(), ficha=ficha,
                          config=CONFIG)


# =====================================================================================================================
# 1. O RAMO — nunca AUTO por omissão
# =====================================================================================================================
DEZ_DESCONHECIDAS = ("NAUT", "RCPR", "GOC", "CAPI", "MOBI", "FROT", "PQRE", "CTVE", "TRAN", "RISC")


@pytest.mark.parametrize("sigla,ramo", [("AUTO", 31), ("RESI", 2), ("COND", 16), ("EMPR", 18)])
def test_o_ramo_cotado_vai_ao_codigo_do_agger(sigla, ramo):
    assert PED._ramo_do_agger(_apolice(sigla)) == ramo


@pytest.mark.parametrize("sigla", ["VIND", "VGRP", "VIAG", "VIDA"])
def test_ramo_conhecido_fora_do_agger_e_ramo_nao_cotado(sigla):
    with pytest.raises(PED.RamoIndisponivel) as erro:
        PED._ramo_do_agger(_apolice(sigla))
    assert erro.value.motivo == "ramo_nao_cotado"


@pytest.mark.parametrize("sigla", DEZ_DESCONHECIDAS)
def test_as_dez_siglas_desconhecidas_nunca_viram_carro(sigla):
    """🔴 Mutação 3 da SPEC (`familia None → RAMO_AUTO`) deixa este guarda VERMELHO: 📊 13 renovações de 99 na maior
    carteira (CAPI, RCPR, GOC, NAUT) viravam pedido de carro e o motivo mostrado seria "falta a placa"."""
    with pytest.raises(PED.RamoIndisponivel) as erro:
        PED._ramo_do_agger(_apolice(sigla))
    assert erro.value.motivo == "ramo_desconhecido"
    with pytest.raises(PED.RamoIndisponivel) as pelo_motor:
        PED.de_apolice(_apolice(sigla), _perfil_auto(), config=CONFIG)      # o caminho de produção, inteiro
    assert pelo_motor.value.motivo == "ramo_desconhecido"


def test_ramo_indisponivel_continua_compativel_com_quem_ja_a_usa():
    e = PED.RamoIndisponivel("ramo 91 não implementado")
    assert isinstance(e, ValueError) and e.motivo in PED.MOTIVOS_DE_RAMO_INDISPONIVEL and "91" in str(e)
    with pytest.raises(PED.RamoIndisponivel) as erro:
        PED.catalogo_do_ramo(91)
    assert erro.value.motivo == "ramo_nao_cotado"
    with pytest.raises(ValueError):
        PED.RamoIndisponivel("x", motivo="qualquer_coisa")                   # o motivo é de uma lista fechada


# =====================================================================================================================
# 2. A CONFIG da renovação
# =====================================================================================================================
def test_o_padrao_da_renovacao_e_o_do_contrato():
    ren = CONFIG["servicos"]["renovacao"]
    assert ren["antecedencia_dias"] == 10 == CONFIG["renovacao"]["antecedencia_dias"]       # D-131-01
    assert ren["janela"] == {"preparar": "00:30", "calcular": "02:00", "conferir": "05:30", "desvio": "06:15",
                             "avisar": "06:45", "prosseguir_de": "01:00", "prosseguir_ate": "06:30",
                             "retentativa_min": 60}
    assert ren["opcoes"] == ["anterior", "franquia_reduzida", "completa_mais"]
    assert ren["teto_sessoes_corretora"] == 1
    assert CFG.antecedencia_dias(CONFIG) == 10 and CFG.opcoes_da_renovacao(CONFIG) == tuple(ren["opcoes"])
    assert CFG.janela_da_renovacao(CONFIG) == ren["janela"] and CFG.teto_sessoes_corretora(CONFIG) == 1
    assert CFG.comissao_a_mais_pp(CONFIG) == 1.0
    # a base (sem serviço) também leva o bloco, com os mesmos números
    base = CFG.mesclar(None)
    assert base["servicos"]["renovacao"]["antecedencia_dias"] == 10 == base["renovacao"]["antecedencia_dias"]


@pytest.mark.parametrize("bloco,chave,esperado", [
    ({"opcoes": ["anterior", "economica"]}, "opcoes", ["anterior", "franquia_reduzida", "completa_mais"]),
    ({"opcoes": ["minima"]}, "opcoes", ["anterior", "franquia_reduzida", "completa_mais"]),
    ({"opcoes": []}, "opcoes", ["anterior", "franquia_reduzida", "completa_mais"]),
    ({"opcoes": ["anterior", "anterior"]}, "opcoes", ["anterior", "franquia_reduzida", "completa_mais"]),
    ({"opcoes": ["anterior", "franquia_reduzida", "completa_mais", "padrao"]}, "opcoes",
     ["anterior", "franquia_reduzida", "completa_mais"]),
    ({"opcoes": ["anterior"]}, "opcoes", ["anterior"]),
    ({"opcoes": ["completa_mais", "anterior"]}, "opcoes", ["completa_mais", "anterior"]),
    ({"antecedencia_dias": 0}, "antecedencia_dias", 10),
    ({"antecedencia_dias": 61}, "antecedencia_dias", 10),
    ({"antecedencia_dias": 7.5}, "antecedencia_dias", 10),
    ({"antecedencia_dias": True}, "antecedencia_dias", 10),
    ({"antecedencia_dias": 7}, "antecedencia_dias", 7),
    ({"teto_sessoes_corretora": 0}, "teto_sessoes_corretora", 1),
    ({"teto_sessoes_corretora": 2}, "teto_sessoes_corretora", 2),
])
def test_a_config_da_renovacao_valida_e_o_que_nao_valida_volta_ao_padrao(bloco, chave, esperado):
    cfg = CFG.mesclar({"servicos": {"renovacao": bloco}}, "renovacao")
    assert cfg["servicos"]["renovacao"][chave] == esperado
    if chave == "antecedencia_dias":
        assert cfg["renovacao"]["antecedencia_dias"] == esperado            # um número só, nos dois caminhos


@pytest.mark.parametrize("janela,errada", [({"calcular": "25:00"}, "calcular"), ({"avisar": "6:45"}, "avisar"),
                                            ({"conferir": 530}, "conferir"), ({"retentativa_min": 0},
                                                                              "retentativa_min")])
def test_a_janela_so_aceita_HH_MM_e_o_resto_fica(janela, errada):
    cfg = CFG.mesclar({"servicos": {"renovacao": {"janela": {**janela, "preparar": "00:45"}}}}, "renovacao")
    jan = cfg["servicos"]["renovacao"]["janela"]
    assert jan[errada] == CFG.PADRAO_DO_PRODUTO["servicos"]["renovacao"]["janela"][errada]
    assert jan["preparar"] == "00:45"                                       # o que estava certo fica


def test_a_antecedencia_salva_pela_tela_antes_continua_valendo():
    """A tela "Serviços" (131-0) grava em `servicos.renovacao.renovacao.antecedencia_dias`: o madrugada lê o MESMO
    número em `servicos.renovacao.antecedencia_dias` (um número só, nunca dois)."""
    linha = {"servicos": {"renovacao": {"renovacao": {"antecedencia_dias": 20}}}}
    cfg = CFG.mesclar(linha, "renovacao")
    assert cfg["renovacao"]["antecedencia_dias"] == 20 == cfg["servicos"]["renovacao"]["antecedencia_dias"]
    assert CFG.erros_da_edicao(servicos=linha["servicos"]) == []
    assert CFG.erros_da_edicao(servicos={"renovacao": {"renovacao": {"antecedencia_dias": 61}}}) != []
    # a cotação não herda nada da renovação
    assert "antecedencia_dias" not in CFG.mesclar(linha, "cotacao")["servicos"]["cotacao"]


# =====================================================================================================================
# 3. AS OPÇÕES DA RENOVAÇÃO — AUTO
# =====================================================================================================================
# 3 fichas sintéticas (rótulo, limite, texto da franquia)
FICHA_A = (("Casco", 80000, "Franquia normal"), ("RCF-V Danos Materiais", 100000, None),
           ("RCF-V Danos Corporais", 100000, None), ("RCF-V Danos Morais", 10000, None),
           ("APP Morte por passageiro", 5000, None), ("Vidros básico", None, None),
           ("Carro reserva 7 dias", None, None), ("Assistência 24h Básica", None, None))
FICHA_B = (("Casco", 120000, "Reduzida"), ("Danos Materiais", 300000, None), ("Danos Corporais", 300000, None),
           ("Vidros completo", None, None), ("Carro reserva 15 dias", None, None))
FICHA_C = (("Casco", 60000, None), ("Danos Materiais", 150500, None), ("Veículo reserva 30 dias", None, None))

# 🔬 O CAMINHO INDEPENDENTE da lente: o que cada ficha DIZ, escrito à mão (não lido pelo código do produto), e a
# ESCADA de cada código escrita aqui de novo a partir do topo de presets.py (franquia 2 normal < 1 reduzida ·
# vidros 1 básico < 2 completo · reserva 0 < 1 (7 d) < 2 (15 d) · assistência 4 básica < 1 completa).
DIZ = {
    "A": {"tipoFranquia": 2, "isDanosMateriais": 100000, "isDanosCorporais": 100000, "isDanosMorais": 10000,
          "isAppMorte": 5000, "vidros": 1, "carroReserva": 1, "assist24hs": 4},
    "B": {"tipoFranquia": 1, "isDanosMateriais": 300000, "isDanosCorporais": 300000, "vidros": 2, "carroReserva": 2},
    "C": {"isDanosMateriais": 150500, "carroReserva": 3},          # 30 dias: acima do maior código medido
}
_ESCADA = {"tipoFranquia": [2, 1], "vidros": [1, 2], "carroReserva": [0, 1, 2, 3], "assist24hs": [4, 1]}


def _nivel(chave, v):
    return _ESCADA[chave].index(v) if chave in _ESCADA else float(v)


@pytest.mark.parametrize("nome,linhas", [("A", FICHA_A), ("B", FICHA_B), ("C", FICHA_C)])
def test_lente_o_anterior_e_igual_ou_maior_que_a_ficha_campo_a_campo(nome, linhas):
    pedido = _auto(linhas)
    anterior = pedido.coberturas_por_opcao["anterior"]
    assert set(anterior) == set(P.CHAVES_DE_COBERTURA)                      # o corpo inteiro, explícito
    for chave, disse in DIZ[nome].items():
        tem = anterior[chave]
        if chave == "carroReserva" and disse == 3:                         # 30 dias não cabe em 15: marca, nunca cala
            assert tem == 2 and "anterior.carroReserva" in pedido.nao_conferidos
            continue
        assert _nivel(chave, tem) >= _nivel(chave, disse), (nome, chave, tem, disse)
        assert f"anterior.{chave}" not in pedido.nao_conferidos
    for chave in set(P.CHAVES_DE_COBERTURA) - set(DIZ[nome]):
        assert anterior[chave] == P.PRESETS[P.PADRAO][chave]               # o que a ficha não traz: o preset completo
        assert f"anterior.{chave}" in pedido.nao_conferidos                # e a marca "não conferido"
    assert anterior["isDanosMateriais"] % 1000 == 0                         # sempre para cima, nunca para baixo


def test_a_franquia_reduzida_so_existe_quando_muda_algo():
    a = _auto(FICHA_A)
    assert a.opcoes == ("anterior", "franquia_reduzida", "completa_mais")
    red = a.coberturas_por_opcao["franquia_reduzida"]
    assert red["tipoFranquia"] == 1 and {k: v for k, v in red.items() if k != "tipoFranquia"} == \
        {k: v for k, v in a.coberturas_por_opcao["anterior"].items() if k != "tipoFranquia"}
    b = _auto(FICHA_B)                                                       # já era reduzida: cede o lugar
    assert b.opcoes == ("anterior", "completa_mais") and "franquia_reduzida" not in b.coberturas_por_opcao


def test_a_completa_mais_e_pequenos_reparos_sobre_o_anterior_nunca_abaixo():
    for linhas in (FICHA_A, FICHA_B, FICHA_C):
        p = _auto(linhas)
        mais, ant = p.coberturas_por_opcao["completa_mais"], p.coberturas_por_opcao["anterior"]
        assert mais["reparoRapido"] is True
        for k in ("tipoFranquia", "vidros", "carroReserva", "assist24hs", "isDanosMateriais", "isDanosCorporais"):
            assert _nivel(k, mais[k]) >= _nivel(k, ant[k]) and _nivel(k, mais[k]) >= _nivel(k, P.PRESETS["padrao"][k])


def test_uma_opcao_so_e_as_opcoes_nao_vao_ao_robo():
    um = PED.de_apolice(_apolice("AUTO", placa="AAA1A11"), _perfil_auto(),
                        config=CFG.mesclar({"servicos": {"renovacao": {"opcoes": ["anterior"]}}}, "renovacao"))
    assert um.opcoes == ("anterior",) and set(um.coberturas_por_opcao) == {"anterior"}
    d = um.para_dict()
    assert "opcoes" not in d and d["coberturas"] == {} and "nao_conferidos" not in d
    assert CPF not in repr(um) and "Sintetica" not in repr(um)


@pytest.mark.parametrize("proibida", ["economica", "minima"])
def test_economica_e_minima_nunca_numa_renovacao(proibida):
    """🔴 Mutação 7 da SPEC: a guarda recusa mesmo quando a config vem crua (sem passar pela validação)."""
    crua = copy.deepcopy(CONFIG)
    crua["servicos"]["renovacao"]["opcoes"] = ["anterior", proibida]
    with pytest.raises(P.OpcaoProibidaNaRenovacao):
        PED.de_apolice(_apolice("AUTO", placa="AAA1A11"), _perfil_auto(), config=crua)
    with pytest.raises(P.OpcaoProibidaNaRenovacao):
        P.coberturas_da_renovacao_auto({}, [proibida])
    with pytest.raises(P.OpcaoProibidaNaRenovacao):
        P.coberturas_da_renovacao_re(2, 100000.0, {}, [proibida])
    assert proibida not in P.OPCOES_DA_RENOVACAO
    assert set(P.PROIBIDAS_NA_RENOVACAO) == {"economica", "minima"}


def test_os_nomes_fixos_e_os_presets_de_antes_nao_mudam():
    assert P.OPCOES_DA_RENOVACAO == ("anterior", "franquia_reduzida", "completa_mais")
    assert (P.ANTERIOR, P.FRANQUIA_REDUZIDA) == ("anterior", "franquia_reduzida")
    assert P.ORDEM == ("padrao", "economica", "completa_mais", "minima")    # o QCM e a cotação não mudam
    # 🔴 o `anterior` não tem preset FIXO: sem as coberturas da ficha, a porta recusa (nunca a padrão disfarçada)
    assert "anterior" not in P.PRESETS and "franquia_reduzida" not in P.PRESETS


# =====================================================================================================================
# 4. AS OPÇÕES DA RENOVAÇÃO — RE
# =====================================================================================================================
_COND = (("Incêndio / raio / explosão / fumaça / aeronave", 17600000, None),
         ("Incêndio de bens de condôminos", 2000000, None), ("RC Síndico", 700000, None),
         ("Vendaval, Ciclone, Tornado, Granizo", 90000, None))


def test_re_anterior_leva_as_coberturas_da_ficha_e_a_basica_reajustada():
    ficha = _ficha(_COND, objeto={"cep": "88000000"})
    pedido = PED.de_apolice(reconciliar(_apolice("COND"), ficha), _perfil_cond(), ficha=ficha, config=CONFIG)
    basica = CFG.basica_renovada(CONFIG, 16, 17600000)                       # P-129C-03: o reajuste é o da config
    ant = pedido.coberturas_por_opcao["anterior"]
    assert ant[P.CHAVE_DA_BASICA] == pytest.approx(basica)
    assert ant["isValorSindico"] == 700000 and ant["isDanosIncendioRaioExplosaoCond"] == 2000000
    assert ant["isDanosVendaval"] == 90000
    tipica = P.coberturas_re(16, "padrao", basica)
    assert pedido.coberturas_por_opcao["franquia_reduzida"] == tipica       # RE: a típica do ramo
    # o condomínio típico JÁ tem assistência completa (📊 8/15) e o anterior cobre ≥ a típica: a completa+ seria o MESMO
    # cálculo — cede o lugar (nunca um calcularV2 pago duas vezes)
    assert pedido.opcoes == ("anterior", "franquia_reduzida") and ant["assist24hs"] == P.ASSISTENCIA_RE["completa"]


def test_re_sem_cobertura_lida_o_anterior_e_a_tipica_e_nao_se_repete():
    ficha = _ficha((("Incêndio, Raio e Explosão", 100000, None),), objeto={"cep": "88000000"})
    pedido = PED.de_apolice(reconciliar(_apolice("RESI"), ficha), _perfil_resi(), ficha=ficha, config=CONFIG)
    assert pedido.opcoes == ("anterior", "completa_mais")                   # a "típica" cedeu: era igual
    assert len({tuple(sorted(v.items())) for v in pedido.coberturas_por_opcao.values()}) == len(pedido.opcoes)
    mais, ant = pedido.coberturas_por_opcao["completa_mais"], pedido.coberturas_por_opcao["anterior"]
    assert mais["assist24hs"] == P.ASSISTENCIA_RE["completa"] != ant["assist24hs"]
    assert all(mais[k] >= ant[k] for k in P.CHAVES_DE_COBERTURA_RE[2] if k != "assist24hs")   # nunca abaixo


# =====================================================================================================================
# 5. CPF/CNPJ — a régua pura (P-1310-02)
# =====================================================================================================================
@pytest.mark.parametrize("doc,ok", [
    (CPF, True), ("52998224725", True), (CNPJ, True), ("11222333000181", True),
    ("00000000000", False), ("000.000.000-00", False), ("11111111111", False), ("99999999999999", False),
    ("52998224724", False), ("11222333000182", False), ("5299822472", False), ("", False), (None, False),
    ("abc", False), ("529982247250", False),
])
def test_documento_valido(doc, ok):
    assert DOC.documento_valido(doc) is ok
    if ok:
        assert DOC.exigir_documento_valido(doc).isdigit()
    else:
        with pytest.raises(DOC.DocumentoInvalido) as erro:
            DOC.exigir_documento_valido(doc)
        assert erro.value.motivo == "documento_invalido" and (not doc or str(doc) not in str(erro.value))


def test_a_regua_e_uma_so_e_o_agente_continua_com_os_nomes_de_sempre():
    """A régua mudou de casa: o agente REEXPORTA (nunca uma segunda conta, CLAUDE.md §5)."""
    from app.agents.tools import insurer_dispatch_tool as T
    from app.agents.tools.insurer_dispatch_tool import documento_br_valido

    assert T.documento_br_valido is DOC.documento_valido
    assert T.cpf_valido is DOC.cpf_valido and T.cnpj_valido is DOC.cnpj_valido

    rnd = random.Random(1311)
    amostra = ["00000000000", "11111111111", CPF, CNPJ, "52998224724"]
    amostra += ["".join(rnd.choice("0123456789") for _ in range(n)) for n in (11, 14) for _ in range(400)]
    validos = [d for d in amostra if documento_br_valido(d)]
    assert validos, "a amostra precisa ter documento válido (o guarda conseguiria ver a diferença?)"
    assert [DOC.documento_valido(d) for d in amostra] == [documento_br_valido(d) for d in amostra]


# =====================================================================================================================
# 6. A CONSULTA À INFOCAP — o documento inválido nunca sai (P-1310-02), em TODA chamada a /cliente_cpf
# =====================================================================================================================
INVALIDOS = ("00000000000", "529.982.247-24", "111.111.111-11", "11222333000182")


class _RedeProibida:
    """Dublê do httpx.AsyncClient: qualquer abertura de conexão é registrada (e falha o teste depois)."""
    abertas = 0

    def __init__(self, *a, **k):
        type(self).abertas += 1
        raise AssertionError("a InfoCap foi chamada com um documento inválido")


@pytest.fixture
def conector(monkeypatch):
    from app.api import infocap_connector as IC

    _RedeProibida.abertas = 0
    monkeypatch.setenv("BACKEND_INTERNAL_API_KEY", "chave-sintetica")
    monkeypatch.setattr(IC.httpx, "AsyncClient", _RedeProibida)
    chamadas = []

    async def _conexao(db, **k):                  # o controle: o documento VÁLIDO passa da barreira e chega aqui
        chamadas.append(k.get("company_id"))
        return {"selected_connection": None}

    monkeypatch.setattr(IC, "_resolve_infocap_connection", _conexao)
    monkeypatch.setattr(IC, "_connection_block_response", lambda decisao, source: {"ok": False, "status": "sem_conexao"})
    return IC, chamadas


@pytest.mark.parametrize("doc", INVALIDOS)
def test_a_consulta_do_produto_recusa_o_documento_invalido_antes_da_rede(conector, doc):
    import asyncio

    IC, chamadas = conector
    cid = "00000000-0000-4000-8000-000000000001"
    r1 = asyncio.run(IC.infocap_lookup(IC.InfocapLookupPayload(company_id=cid, document=doc),
                                       x_autobrokers_internal_key="chave-sintetica", db=None))
    r2 = asyncio.run(IC.infocap_vehicle_item(IC.InfocapVehiclePayload(company_id=cid, document=doc),
                                             x_autobrokers_internal_key="chave-sintetica", db=None))
    assert r1["status"] == r2["status"] == "documento_invalido"
    assert _RedeProibida.abertas == 0 and chamadas == []                # nem a conexão foi resolvida
    assert doc not in str(r1) and doc not in str(r2)                    # a resposta nunca ecoa o documento


@pytest.mark.parametrize("doc", [CPF, CNPJ])
def test_controle_o_documento_valido_passa_da_barreira(conector, doc):
    import asyncio

    IC, chamadas = conector
    cid = "00000000-0000-4000-8000-000000000001"
    r = asyncio.run(IC.infocap_lookup(IC.InfocapLookupPayload(company_id=cid, document=doc),
                                      x_autobrokers_internal_key="chave-sintetica", db=None))
    assert r["status"] == "sem_conexao" and chamadas == [cid]          # a barreira CONSEGUE deixar passar


def test_toda_chamada_a_cliente_cpf_passa_pelo_helper():
    """Guarda de FORMA (CLAUDE.md §9.4, exceção): nenhuma consulta por CPF monta o parâmetro com os dígitos crus."""
    import re as _re

    fonte = (Path(__file__).resolve().parents[1] / "app" / "api" / "infocap_connector.py").read_text(encoding="utf-8")
    assert not _re.search(r'"cpf_cnpj":\s*digits\b', fonte)
    assert not _re.search(r'cpf_search_param"\)\s*or\s*"cpf_cnpj"\):\s*doc_digits', fonte)
    assert fonte.count("_cpf_cnpj_ou_recusa(") >= 6 and fonte.count("_recusa_documento_invalido(") >= 4
    from app.api import infocap_connector as IC
    for doc in INVALIDOS:
        with pytest.raises(DOC.DocumentoInvalido):
            IC._cpf_cnpj_ou_recusa(doc)


# =====================================================================================================================
# 7. A COMISSÃO da renovação (D-131-16 · BLOCO 0 A5)
# =====================================================================================================================
def test_a_comissao_e_a_do_ano_anterior_mais_o_ponto_da_config():
    ap = _apolice("AUTO", placa="AAA1A11")
    p = PED.de_apolice(ap, _perfil_auto(), config=CONFIG, comissao_anterior_pct=20)
    assert p.valor("comissao_desconto", "comissao_percentual") == 20 + CFG.comissao_a_mais_pp(CONFIG) == 21.0
    assert "comissao_desconto.comissao_percentual" in p.assumidos
    dois = CFG.mesclar({"servicos": {"renovacao": {"comissao_a_mais_pp": 2}}}, "renovacao")
    assert PED.de_apolice(ap, _perfil_auto(), config=dois, comissao_anterior_pct=20).valor(
        "comissao_desconto", "comissao_percentual") == 22.0
    # quem pediu vence · sem per_c (ou 0, ou acima do teto) nada muda
    perfil = _perfil_auto()
    perfil["comissao_desconto"] = {"comissao_percentual": 12}
    assert PED.de_apolice(ap, perfil, config=CONFIG, comissao_anterior_pct=20).valor(
        "comissao_desconto", "comissao_percentual") == 12
    for sem in (None, 0, -3, "x", CFG.teto_da_comissao(CONFIG) + 1):
        assert PED.de_apolice(ap, _perfil_auto(), config=CONFIG, comissao_anterior_pct=sem).valor(
            "comissao_desconto", "comissao_percentual") is None


def test_a_comissao_anterior_no_re_vence_a_do_ramo():
    ficha = _ficha(_COND, objeto={"cep": "88000000"})
    p = PED.de_apolice(reconciliar(_apolice("COND"), ficha), _perfil_cond(), ficha=ficha, config=CONFIG,
                       comissao_anterior_pct=15)
    assert p.com_comissao(CFG.comissao_do_ramo(CONFIG, 16)).valor("comissao_desconto", "comissao_percentual") == 16.0


def test_a_fonte_le_o_per_c_do_documento_e_nada_mais(monkeypatch):
    from app.comercial.fonte_infocap import FonteInfocap

    fonte = FonteInfocap(login="sintetico", senha="sintetica", rotulo="ensaio")
    pedidos = []

    def _dub(rota, params):
        pedidos.append((rota, dict(params)))
        return respostas.pop(0)

    respostas = [{"documentos": [{"nosnum": 1, "per_c": "20,00", "per_r": 5}]}, {"documento": {"per_c": 0}}, {}]
    monkeypatch.setattr(fonte, "_get", _dub)
    assert fonte.comissao_da_corretora(1, 123) == 20.0
    assert fonte.comissao_da_corretora(1, 124) is None                   # 0 não é comissão
    assert fonte.comissao_da_corretora(1, 125) is None                   # 404 = vazio
    assert pedidos[0] == ("/documento", {"codfil": 1, "nosnum": 123})


def test_as_chaves_do_nivelamento_da_noite():
    ren = CONFIG["servicos"]["renovacao"]
    assert ren["teto_por_conta_noite"] == 12 == CFG.teto_por_conta_noite(CONFIG)
    assert ren["antecipar_ate_dias"] == 7 == CFG.antecipar_ate_dias(CONFIG)
    for bloco, chave, esperado in (({"teto_por_conta_noite": 0}, "teto_por_conta_noite", 12),
                                   ({"teto_por_conta_noite": 61}, "teto_por_conta_noite", 12),
                                   ({"teto_por_conta_noite": 30}, "teto_por_conta_noite", 30),
                                   ({"antecipar_ate_dias": 21}, "antecipar_ate_dias", 7),
                                   ({"antecipar_ate_dias": 0}, "antecipar_ate_dias", 0),
                                   ({"comissao_a_mais_pp": 9}, "comissao_a_mais_pp", 1.0),
                                   ({"comissao_a_mais_pp": 1.5}, "comissao_a_mais_pp", 1.5)):
        assert CFG.mesclar({"servicos": {"renovacao": bloco}}, "renovacao")["servicos"]["renovacao"][chave] == esperado
