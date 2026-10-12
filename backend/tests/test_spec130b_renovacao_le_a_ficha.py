# -*- coding: utf-8 -*-
"""SPEC-130-B · F4 — a RENOVAÇÃO lê a FICHA ÚNICA da apólice.

O fio desta fatia, com o MOTOR real em cada elo (dublê nenhum — nada aqui toca rede, banco ou modelo):

    Apolice (cadastro, sintética) + ApoliceDocumental (o documento, sintético)
      → policy_data_provider.reconciliar            (REAL: o documento vence nas coberturas; o sinal da leitura)
      → multicalculo.pedido.de_apolice(ficha=, config=)  (REAL: AUTO e RE)
      → PedidoDeCalculo.para_dict()                 (o que o robô recebe)
      → contrato.problemas_do_pedido_re             (REAL: o validador que o robô usa antes de montar o corpo)

⛔ Tudo sintético: nenhum CPF, placa, nome ou endereço real. O CPF/CNPJ são os de exemplo dos testes da 129-B.
"""
from __future__ import annotations

import sys
from dataclasses import fields
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.providers.policy_data_provider import (  # noqa: E402
    Apolice, ApoliceDocumental, CampoComOrigem, Cobertura, ItemDeRisco, LinhaDeCoberturaDoDocumento,
    RamoCanonico, SeguradoraCanonica, Sinal, Vigencia, indisponivel_por, normalizar_rotulo, reconciliar,
)
from app.services.multicalculo import config as CFG  # noqa: E402
from app.services.multicalculo import pedido as PED  # noqa: E402
from portal_worker.multicalculo.contrato import problemas_do_pedido_re  # noqa: E402

CPF = "529.982.247-25"          # sintético (o mesmo da 129-B)
CNPJ = "11.222.333/0001-81"     # sintético (exemplo clássico de CNPJ válido)
PORTO = "05886"                 # coenti → "Porto Seguro Cia Seg. Gerais" (contrato.SEGURADORA_ANTERIOR_NO_AGGER)
FIM = date(2026, 11, 1)


# ---------------------------------------------------------------------------------------------------------------------
# as peças sintéticas
# ---------------------------------------------------------------------------------------------------------------------
def _d(v) -> Decimal:
    return Decimal(str(v)).quantize(Decimal("0.01"))


def _cob(rotulo: str, limite, premio, origem: str = "sistema_de_gestao") -> Cobertura:
    return Cobertura(rotulo=rotulo, rotulo_normalizado=normalizar_rotulo(rotulo),
                     limite=CampoComOrigem(valor=_d(limite), origem=origem),
                     franquia=indisponivel_por(),
                     premio=CampoComOrigem(valor=_d(premio), origem=origem))


def _apolice(ramo: str, coberturas=(), *, placa=None, premio_liquido=None) -> Apolice:
    item = None
    if placa is not None:
        item = ItemDeRisco(item=1, placa=CampoComOrigem(valor=placa, origem="sistema_de_gestao"))
    return Apolice(
        apolice_ref="sintetica:1", numero_humano="0000000001",
        seguradora=SeguradoraCanonica(chave="PORT", coenti=PORTO),
        ramo=RamoCanonico(abreviatura=ramo),
        vigencia=Vigencia(inicio=date(2025, 11, 1), fim=FIM, situacao="VIGENTE"),
        coberturas=tuple(coberturas),
        premio_liquido=(CampoComOrigem(valor=_d(premio_liquido), origem="sistema_de_gestao")
                        if premio_liquido is not None else None),
        item_de_risco=item,
    )


def _ficha(linhas=(), *, estado="fechou", objeto=None, tipo="apolice") -> ApoliceDocumental:
    """A ficha do documento. Os 3 campos da 130-B (F1) vão pelo construtor quando o tipo os tem — e por fora quando
    não tem, para o teste valer com e sem eles (o código da F4 os lê de forma tolerante)."""
    extra = {"tipo_documento": tipo, "objeto_do_risco": objeto,
             "leitura": ({"estado": estado, "linhas": len(linhas)} if estado else None)}
    nomes = {f.name for f in fields(ApoliceDocumental)}
    base = ApoliceDocumental(
        linhas=tuple(LinhaDeCoberturaDoDocumento(rotulo=r, limite=_d(l), premio=_d(p), pagina=1)
                     for (r, l, p) in linhas),
        **{k: v for k, v in extra.items() if k in nomes})
    for k, v in extra.items():
        if k not in nomes:
            object.__setattr__(base, k, v)
    return base


_RESI_LINHAS = (("Incêndio, Raio e Explosão", 100000, 120.50), ("RC Familiar", 10000, 30.00),
                ("Vendaval, Ciclone, Tornado, Granizo", 8000, 40.00))
_COND_LINHAS = (("Incêndio / raio / explosão / fumaça / aeronave", 17600000, 5000.00),
                ("Incêndio de bens dos condôminos", 2000000, 300.00),
                ("RC Síndico", 700000, 200.00))
_EMPR_LINHAS = (("Incêndio / raio / explosão / aeronave / fumaça", 911000, 900.00),
                ("Danos elétricos", 20000, 100.00))


def _perfil_resi():
    return {"segurado": {"cpf_cnpj": CPF, "nome": "Pessoa Sintetica", "nascimento": "1980-02-01"},
            "risco": {"logradouro": "Rua Sintetica", "bairro": "Centro", "cidade": "Cidade Sintetica", "uf": "SC",
                      "tipo_imovel": "casa", "construcao": "superior", "uso": "habitual", "objeto": "predio + conteudo"},
            "renovacao": {"bonus_anterior": 0, "sinistros_anterior": 0}}


def _perfil_cond():
    return {"segurado": {"cpf_cnpj": CNPJ, "nome": "Condominio Sintetico"},
            "risco": {"logradouro": "Rua Sintetica", "bairro": "Centro", "cidade": "Cidade Sintetica", "uf": "SC",
                      "tipo_imovel": "residencial", "estrutura": "vertical", "ano_fundacao": "2005", "blocos": "1",
                      "pavimentos": "5", "elevadores": 0},
            "renovacao": {"bonus_anterior": 5, "sinistros_anterior": 0}}


def _perfil_empr():
    return {"segurado": {"cpf_cnpj": CNPJ, "nome": "Empresa Sintetica"},
            "risco": {"logradouro": "Rua Sintetica", "bairro": "Centro", "cidade": "Cidade Sintetica", "uf": "SC",
                      "pavimento": "terreo", "localizacao": "outros", "construcao": "superior", "objeto": "predio"},
            "renovacao": {"bonus_anterior": 0, "sinistros_anterior": 0}}


CONFIG = CFG.PADRAO_DO_PRODUTO       # 🔴 o reajuste vem da CONFIG (15 % no padrão do produto), nunca do teste


def _reajustada(anterior) -> float:
    return CFG.basica_renovada(CONFIG, 2, anterior)      # o mesmo cálculo, pelo caminho da config


# =====================================================================================================================
# O FIO — RE: reconciliar REAL → de_apolice → o validador do robô
# =====================================================================================================================
def test_fio_residencial_a_basica_vem_da_ficha_reajustada_pela_config_e_o_robo_aceita():
    corp = _apolice("RESI", [_cob("INCENDIO RAIO EXPLOSAO", 90000, 110.00)], premio_liquido=190.50)
    ficha = _ficha(_RESI_LINHAS, estado="fechou", objeto={"cep": "88000-000"})
    apolice = reconciliar(corp, ficha)                                   # o documento vence: 100.000 (não 90.000)
    pedido = PED.de_apolice(apolice, _perfil_resi(), ficha=ficha, config=CONFIG).com_comissao(15.0)
    d = pedido.para_dict()

    assert pedido.ramo == 2
    assert d["risco"]["valor_basica"] == pytest.approx(115000.0) == pytest.approx(_reajustada(100000))
    assert d["risco"]["cep"] == "88000000"                               # o objeto do risco da ficha
    assert "risco.valor_basica" in d["assumidos"]                        # deduzido (anterior + reajuste), não dito
    assert d["renovacao"]["renovacao"] is True
    assert d["renovacao"]["seguradora_anterior"] == "Porto Seguro Cia Seg. Gerais"
    assert d["renovacao"]["vigencia_inicio"] == "2026-11-01" and d["renovacao"]["vigencia_fim"] == "2027-11-01"
    assert d["renovacao"]["numero_apolice_anterior"] == "0000000001"
    assert pedido.faltando() == [] and pedido.sem_codigo() == []
    assert problemas_do_pedido_re(d) == ()                               # 🔴 o validador do ROBÔ aceita
    assert pedido.avisos == frozenset()                                  # a leitura fechou: nada a conferir
    assert "avisos" not in d                                             # o contrato do robô não muda


def test_fio_condominio_a_basica_nunca_e_o_incendio_dos_condominos_e_nao_conferida_so_marca():
    ficha = _ficha(_COND_LINHAS, estado="nao_fechou", objeto={"cep": "88000-000"})
    apolice = reconciliar(_apolice("COND"), ficha)
    assert apolice.sinal("documento_nao_conferido") is not None          # a F1 acendeu (o motor real)
    pedido = PED.de_apolice(apolice, _perfil_cond(), ficha=ficha, config=CONFIG).com_comissao(15.0)
    d = pedido.para_dict()

    assert pedido.ramo == 16
    assert d["risco"]["valor_basica"] == pytest.approx(CFG.basica_renovada(CONFIG, 16, 17600000))
    assert PED.AVISO_COBERTURAS_NAO_CONFERIDAS in pedido.avisos          # 🔴 MARCADO — o corretor confere
    assert pedido.faltando() == [] and problemas_do_pedido_re(d) == ()   # 🔴 e NÃO recusado só por isso
    # a marca atravessa o que a porta faz com o pedido
    assert PED.AVISO_COBERTURAS_NAO_CONFERIDAS in PED.de_apolice(apolice, _perfil_cond(), ficha=ficha,
                                                                 config=CONFIG).com_comissao(10.0).avisos


def test_fio_empresarial_falta_cep_e_atividade_a_lista_e_explicita_e_a_ficha_completa():
    ficha_sem = _ficha(_EMPR_LINHAS, estado="fechou", objeto=None)
    apolice = reconciliar(_apolice("EMPR"), ficha_sem)
    pedido = PED.de_apolice(apolice, _perfil_empr(), ficha=ficha_sem, config=CONFIG).com_comissao(15.0)
    assert pedido.ramo == 18
    assert {"risco.cep", "risco.atividade"} <= set(pedido.faltando())    # 🔴 nunca adivinhado
    assert "cep" not in pedido.para_dict()["risco"] and "atividade" not in pedido.para_dict()["risco"]
    with pytest.raises(PED.FichaIncompleta) as erro:
        PED.de_apolice(apolice, _perfil_empr(), ficha=ficha_sem, config=CONFIG, exigir_completo=True)
    assert {"risco.cep", "risco.atividade"} <= set(erro.value.faltando)
    assert CPF not in str(erro.value) and "Sintetica" not in str(erro.value)   # nomes, nunca valores

    ficha = _ficha(_EMPR_LINHAS, estado="fechou", objeto={"cep": "88000000", "atividade": "Escritório"})
    apolice = reconciliar(_apolice("EMPR"), ficha)
    pedido = PED.de_apolice(apolice, _perfil_empr(), ficha=ficha, config=CONFIG).com_comissao(15.0)
    d = pedido.para_dict()
    assert d["risco"]["cep"] == "88000000" and d["risco"]["atividade"] == "Escritório"
    assert d["risco"]["valor_basica"] == pytest.approx(CFG.basica_renovada(CONFIG, 18, 911000))
    assert pedido.faltando() == [] and problemas_do_pedido_re(d) == ()


def test_o_perfil_vence_a_ficha_no_que_quem_pediu_disse():
    ficha = _ficha(_RESI_LINHAS, objeto={"cep": "88000000"})
    perfil = _perfil_resi()
    perfil["risco"].update({"cep": "89000-000", "valor_basica": 300000})
    pedido = PED.de_apolice(reconciliar(_apolice("RESI"), ficha), perfil, ficha=ficha, config=CONFIG)
    d = pedido.para_dict()
    assert d["risco"]["cep"] == "89000000" and d["risco"]["valor_basica"] == 300000.0
    assert "risco.valor_basica" not in d["assumidos"]                    # foi DITO: não é assumido


# =====================================================================================================================
# nunca adivinhar a básica
# =====================================================================================================================
def test_duas_basicas_diferentes_nao_escolhe_marca_e_fica_faltando():
    linhas = (("Incêndio, Raio e Explosão - Prédio", 300000, 100.0),
              ("Incêndio, Raio e Explosão - Conteúdo", 80000, 40.0))
    ficha = _ficha(linhas, objeto={"cep": "88000000"})
    pedido = PED.de_apolice(reconciliar(_apolice("RESI"), ficha), _perfil_resi(), ficha=ficha, config=CONFIG)
    assert "risco.valor_basica" in pedido.faltando()
    assert PED.AVISO_BASICA_AMBIGUA in pedido.avisos
    assert "valor_basica" not in pedido.para_dict()["risco"]


def test_sem_cobertura_basica_na_ficha_fica_faltando():
    ficha = _ficha((("RC Familiar", 10000, 30.0),), objeto={"cep": "88000000"})
    pedido = PED.de_apolice(reconciliar(_apolice("RESI"), ficha), _perfil_resi(), ficha=ficha, config=CONFIG)
    assert "risco.valor_basica" in pedido.faltando()


def test_o_reajuste_e_o_da_config_da_corretora_e_sem_regra_nada_e_inventado():
    ficha = _ficha(_RESI_LINHAS, objeto={"cep": "88000000"})
    apolice = reconciliar(_apolice("RESI"), ficha)
    dez = {"renovacao": {"reajuste_basica_pct": {"2": 10.0}}}
    assert PED.de_apolice(apolice, _perfil_resi(), ficha=ficha, config=dez).valor("risco", "valor_basica") \
        == pytest.approx(110000.0)
    sem_regra = {"renovacao": {"reajuste_basica_pct": {}}}
    pedido = PED.de_apolice(apolice, _perfil_resi(), ficha=ficha, config=sem_regra)
    assert "risco.valor_basica" in pedido.faltando()                     # nem a anterior "sem reajuste"
    assert PED.AVISO_SEM_REGRA_DE_REAJUSTE in pedido.avisos
    with pytest.raises(TypeError):
        PED.de_apolice(apolice, _perfil_resi(), ficha=ficha)             # RE sem config: recusa clara


def test_so_o_cadastro_sem_documento_lido_marca_coberturas_do_cadastro():
    corp = _apolice("RESI", [_cob("INCENDIO RAIO EXPLOSAO", 90000, 110.0)])
    pedido = PED.de_apolice(reconciliar(corp, None), {**_perfil_resi(), "risco": {**_perfil_resi()["risco"],
                                                                                   "cep": "88000000"}},
                            config=CONFIG)
    assert pedido.valor("risco", "valor_basica") == pytest.approx(CFG.basica_renovada(CONFIG, 2, 90000))
    assert PED.AVISO_COBERTURAS_DO_CADASTRO in pedido.avisos


def test_documento_que_nao_e_a_apolice_marca():
    ficha = _ficha(_RESI_LINHAS, objeto={"cep": "88000000"}, tipo="endosso")
    pedido = PED.de_apolice(reconciliar(_apolice("RESI"), ficha), _perfil_resi(), ficha=ficha, config=CONFIG)
    assert PED.AVISO_DOCUMENTO_NAO_E_A_APOLICE in pedido.avisos


def test_ficha_sem_os_campos_da_130b_e_tolerada():
    """Uma ficha de antes da F1 (sem `leitura`/`objeto_do_risco`/`tipo_documento`) não quebra."""
    velha = SimpleNamespace(linhas=())
    pedido = PED.de_apolice(_apolice("RESI", [_cob("Incêndio, Raio e Explosão", 50000, 10)]), _perfil_resi(),
                            ficha=velha, config=CONFIG)
    assert pedido.ramo == 2 and "risco.cep" in pedido.faltando()


def test_ramo_sem_renovacao_recusa_com_o_tipo_certo():
    with pytest.raises(PED.RamoIndisponivel):
        PED.de_apolice(_apolice("VIDA"), {})


# =====================================================================================================================
# AUTO — o objeto do risco da ficha preenche o que o perfil não tem; o controle de hoje não muda
# =====================================================================================================================
def _perfil_auto():
    return {"segurado": {"cpf_cnpj": CPF, "nome": "Pessoa Sintetica", "nascimento": "1980-02-01", "sexo": "F",
                         "estado_civil": 1, "cep": "88000-000"},
            "veiculo": {"fipe": "009999-1", "ano_fabricacao": 2019, "combustivel": "flex"},
            "renovacao": {"bonus_anterior": 4}, "condutor": {"tempo_habilitacao": 15}}


def test_auto_a_ficha_da_chassi_e_ano_e_o_cadastro_vence_na_placa():
    ficha = _ficha((), objeto={"placa": "ZZZ9Z99", "chassi": "9bw zzz377vt000001", "ano_modelo": "2020"})
    apolice = reconciliar(_apolice("AUTO", placa="AAA1A11"), ficha)
    pedido = PED.de_apolice(apolice, _perfil_auto(), ficha=ficha)
    d = pedido.para_dict()
    assert d["veiculo"]["placa"] == "AAA1A11"                            # o cadastro (endosso troca o carro)
    assert d["veiculo"]["chassi"] == "9BWZZZ377VT000001" and d["veiculo"]["ano_modelo"] == 2020
    assert PED.AVISO_PLACA_DIVERGE in pedido.avisos
    assert pedido.faltando() == []

    sem_item = PED.de_apolice(reconciliar(_apolice("AUTO"), ficha), _perfil_auto(), ficha=ficha)
    assert sem_item.valor("veiculo", "placa") == "ZZZ9Z99" and PED.AVISO_PLACA_DIVERGE not in sem_item.avisos


def test_auto_o_perfil_vence_a_ficha():
    ficha = _ficha((), objeto={"chassi": "9BWZZZ377VT000001", "ano_modelo": 2018})
    perfil = _perfil_auto()
    perfil["veiculo"]["ano_modelo"] = 2021
    pedido = PED.de_apolice(_apolice("AUTO", placa="AAA1A11"), perfil, ficha=ficha)
    assert pedido.valor("veiculo", "ano_modelo") == 2021


def test_auto_controle_sem_ficha_e_o_pedido_de_hoje():
    """🔴 A linha de controle: sem `ficha`, o AUTO sai byte a byte como antes da F4 (sem avisos, mesmo dict)."""
    perfil = _perfil_auto()
    perfil["veiculo"].update({"ano_modelo": 2020, "chassi": "9BWZZZ377VT000001"})
    pedido = PED.de_apolice(_apolice("AUTO", placa="AAA1A11"), perfil)
    assert pedido.avisos == frozenset()
    d = pedido.para_dict()
    assert set(d) == {"ramo", "seguradoras", "assumidos", *PED._CATALOGO}
    assert d["veiculo"]["placa"] == "AAA1A11" and pedido.faltando() == []
    assert CPF not in repr(pedido) and "Sintetica" not in repr(pedido)


def test_auto_com_ficha_nao_conferida_marca_mas_nao_recusa():
    ficha = _ficha((("Casco", 50000, 10.0),), estado="nao_fechou", objeto={"chassi": "9BWZZZ377VT000001"})
    apolice = reconciliar(_apolice("AUTO", placa="AAA1A11"), ficha)
    perfil = _perfil_auto()
    perfil["veiculo"]["ano_modelo"] = 2020
    pedido = PED.de_apolice(apolice, perfil, ficha=ficha)
    assert PED.AVISO_COBERTURAS_NAO_CONFERIDAS in pedido.avisos and pedido.faltando() == []


def test_o_sinal_da_apolice_basta_sem_a_ficha():
    """A porta pode entregar só a `Apolice` já reconciliada: o sinal da F1 nela já marca o pedido."""
    apolice = _apolice("RESI", [_cob("Incêndio, Raio e Explosão", 50000, 10)])
    from dataclasses import replace
    apolice = replace(apolice, sinais=(Sinal("documento_nao_conferido", {"estado": "nao_fechou"}),))
    perfil = _perfil_resi()
    perfil["risco"]["cep"] = "88000000"
    pedido = PED.de_apolice(apolice, perfil, config=CONFIG)
    assert PED.AVISO_COBERTURAS_NAO_CONFERIDAS in pedido.avisos
