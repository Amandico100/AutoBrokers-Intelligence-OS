# -*- coding: utf-8 -*-
"""SPEC-129-D · V2 — o lado do APP da VIDA INDIVIDUAL (ramo 91): pedido, porta, madrugada, config, família.

O FIO DESTA FATIA:
    InfoCap /renovacoes (VIND) → madrugada._avaliar (REAL; a chave MULTICALCULO_VIDA_LIGADO decide) → a ficha única
    (dublê na borda: `madrugada.ficha_da_apolice`) + o perfil (`perfil_da_renovacao.montar` REAL sobre a InfoCap na REDE
    dublê) → `pedido.de_apolice` (REAL) → `madrugada.o_que_falta` (a MESMA conta da porta) → `porta.calcular` (REAL,
    banco dublê) → o pedido 91 gravado e cifrado.

O que cada teste prova (o card da fatia, §5 da SPEC):
  (1) chave AUSENTE → a vida segue `ramo_nao_cotado` "renove manualmente", byte a byte (CONTROLE)
  (2) chave ligada + VIND com o PDF lido → pedido 91 com o capital DA APÓLICE
  (3) fumante/renda/esporte sem fonte → `faltando` com os três e o pedido NÃO segue (nunca "não" por padrão)
  (4) PDF sem capital → pendente(falta_dado) "não achei o capital" — nenhum capital inventado
  (5) VGRP continua fora mesmo com a chave (vida em GRUPO ≠ individual, D-129D-07)
  (6) moto, MOBI, API continuam como hoje
  (7) duas corretoras: a config (comissão/agenciamento/reajuste) e a preferência de A não vazam para B

Mutações da SPEC §6 que estes guardas pegam: nº 1 (fumante None → False), nº 2 (capital inventado), nº 4 (chave
ausente e a vida passa), nº 5 (VGRP tratada como VIND). A nº 6 (a preferida escondida) tem guarda aqui também.
⛔ Tudo SINTÉTICO (CPF de exemplo, nomes "SINTETICO"); nenhum nome de corretora (CLAUDE.md §13.9); nenhum dado de
saúde/renda em log (LGPD art. 11 — `test_nada_de_saude_ou_renda_no_log`).
Rodar: cd backend && python -m pytest tests/test_spec129d_app_vida.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import dubles_do_work_os as D  # noqa: E402
import test_spec131a_o_fio as FIO  # noqa: E402
import test_spec131a_o_pedido_da_renovacao as F2T  # noqa: E402
import test_spec131a_o_perfil as PERF  # noqa: E402
from test_spec131a_o_fio import mundo_real  # noqa: E402,F401  (fixture)
from app.providers import policy_data_provider as PDP  # noqa: E402
from app.providers.policy_data_provider import reconciliar  # noqa: E402
from app.services.multicalculo import comparacao as C  # noqa: E402
from app.services.multicalculo import config as CFG  # noqa: E402
from app.services.multicalculo import madrugada as M  # noqa: E402
from app.services.multicalculo import pedido as PED  # noqa: E402
from app.services.multicalculo.porta import (MulticalculoProvider, PedidoIncompleto, RamoNaoSuportado,  # noqa: E402
                                             cpf_hmac)
from app.services.multicalculo.repositorio import RepositorioMulticalculo  # noqa: E402
from dubles.banco_multicalculo import BancoU1, instalar_esquema  # noqa: E402
from portal_worker.multicalculo import contrato as K  # noqa: E402

CHAVE = "MULTICALCULO_VIDA_LIGADO"
CHAVE_HMAC = "chave-hmac-ficticia-129d-0123456789"
CPF = "52998224725"                    # o CPF de exemplo da 129-B (sintético)
FIM = F2T.FIM                          # o fim da vigência anterior das fichas sintéticas (2026-11-01)
#: a frase de HOJE para a vida (`pedido._ramo_do_agger`, antes da 129-D) — o controle byte a byte da chave ausente
FRASE_DE_HOJE = "renovação do ramo 'vida' não implementada (há: auto, residencial, condomínio, empresarial)"
CAPACIDADE_DE_HOJE = {"ramo": 91, "suportado": False,
                      "motivo": "calcula o AUTO (31) e o RE: condomínio (16), residencial (2), empresarial (18)"}


@pytest.fixture
def ligada(monkeypatch):
    monkeypatch.setenv(CHAVE, "1")


@pytest.fixture
def desligada(monkeypatch):
    monkeypatch.delenv(CHAVE, raising=False)


# ---------------------------------------------------------------------------------------------------------------------
# As peças sintéticas — a apólice de VIDA, a ficha (o PDF lido) e o perfil
# ---------------------------------------------------------------------------------------------------------------------
#: 📊 os rótulos das garantias de VIND na InfoCap (BLOCO 0 M2, 15 linhas de 8 itens): MORTE NATURAL · MORTE ACIDENTAL ·
#: INVALIDEZ POR ACIDENTE · INVALIDEZ POR DOENÇA · ASSISTÊNCIA FUNERAL · CONJUGÊ-MORTE. Os valores são sintéticos.
LINHAS_DO_PDF = (("Morte Natural", 250000, None), ("Morte Acidental", 250000, None),
                 ("Invalidez por Acidente", 100000, None), ("Assistência Funeral", 5000, None),
                 ("Cônjuge - Morte", 50000, None))


def ficha_vida(linhas=LINHAS_DO_PDF, sigla="VIND"):
    """(Apolice reconciliada, ApoliceDocumental) — a forma que `madrugada.ficha_da_apolice` devolve no produto."""
    if linhas is None:
        return F2T._apolice(sigla), None
    ficha = F2T._ficha(linhas)
    return reconciliar(F2T._apolice(sigla), ficha), ficha


def perfil_vida(**vida):
    """O que `perfil_da_renovacao.montar` entrega para a vida (o segurado) + o que o CORRETOR respondeu (`vida`)."""
    p = {"segurado": {"cpf": CPF, "nome": "PESSOA SINTETICA DE TESTE", "data_nascimento": "1980-02-01",
                      "sexo": "Feminino", "estado_civil": "Casado(a)", "cep": "88000000",
                      "profissao_texto": "ADVOGADO"}}
    if vida:
        p["vida"] = dict(vida)
    return p


RESPOSTAS_DO_CORRETOR = {"fumante": False, "renda_mensal": "8.500,00", "esporte_radical": False}


def dados_cotacao(**troca):
    """A COTAÇÃO NOVA de vida: os 12 obrigatórios do formulário (📊 fixture `agger_formularios`, vida 12/47)."""
    d = {"segurado": dict(perfil_vida()["segurado"]),
         "vida": {"capital_morte": 300000, "fumante": False, "renda_mensal": Decimal("9000"), "esporte_radical": False,
                  "vigencia_inicio": "2026-11-01", "origem": "cotacao"}}
    for g, v in troca.items():
        d[g] = {**d.get(g, {}), **v}
    return d


# =====================================================================================================================
# (1) A CHAVE AUSENTE — nada muda, byte a byte (o CONTROLE; mutação 4)
# =====================================================================================================================
def test_1_chave_ausente_vida_segue_ramo_nao_cotado_com_a_frase_de_hoje(desligada):
    for sigla in ("VIND", "VGRP", "VIDA", "VIDA INDIVIDUAL"):
        with pytest.raises(PED.RamoIndisponivel) as exc:
            PED._ramo_do_agger(SimpleNamespace(ramo=sigla))
        assert exc.value.motivo == "ramo_nao_cotado" and str(exc.value) == FRASE_DE_HOJE
    with pytest.raises(PED.RamoIndisponivel):
        PED.PedidoDeCalculo.de_dict(dados_cotacao(), ramo=91)
    with pytest.raises(PED.RamoIndisponivel):
        PED.catalogo_do_ramo(91)
    apolice, ficha = ficha_vida()
    with pytest.raises(PED.RamoIndisponivel) as exc:
        PED.de_apolice(apolice, perfil_vida(**RESPOSTAS_DO_CORRETOR), ficha=ficha, config=F2T.CONFIG)
    assert str(exc.value) == FRASE_DE_HOJE
    assert MulticalculoProvider(object()).capacidades(91) == CAPACIDADE_DE_HOJE


def test_1_chave_desligada_depois_de_montar_a_porta_recusa_sem_gravar(mundo, monkeypatch):
    monkeypatch.setenv(CHAVE, "1")
    pedido = PED.PedidoDeCalculo.de_dict(dados_cotacao(), ramo=91)
    monkeypatch.delenv(CHAVE)
    with pytest.raises(RamoNaoSuportado) as exc:
        rodar(mundo.porta.calcular(company_id=mundo.a, pedido=pedido, origem="auxiliar"))
    assert str(exc.value) == ("o ramo 91 não sai pela origem 'auxiliar': o canal calcula só o AUTO (31); o RE sai "
                              "pela carteira da corretora")
    assert mundo.banco.linhas("multicalculo_pedidos") == []


@pytest.mark.parametrize("valor", ["0", "false", "nao", "", "  "])
def test_1_chave_com_valor_falso_e_desligada(monkeypatch, valor):
    monkeypatch.setenv(CHAVE, valor)
    assert PED.vida_ligada() is False
    with pytest.raises(PED.RamoIndisponivel) as exc:
        PED._ramo_do_agger(SimpleNamespace(ramo="VIND"))
    assert str(exc.value) == FRASE_DE_HOJE


def test_1_o_fio_chave_ausente_a_madrugada_deixa_vind_pendente_ramo_nao_cotado(mundo_real, monkeypatch):
    monkeypatch.delenv(CHAVE, raising=False)
    c, _linhas, _rede = PERF._uma_corretora_com_o_perfil(mundo_real, monkeypatch)
    _item, (estado, motivo, pedido, dados) = PERF._avaliar(mundo_real, c, "VIND")
    assert (estado, motivo, pedido, dados) == ("pendente", "ramo_nao_cotado", None, None)


# =====================================================================================================================
# (2) CHAVE LIGADA + VIND com o PDF lido → o pedido 91 com o capital DA APÓLICE
# =====================================================================================================================
def test_2_vind_com_o_pdf_lido_vira_pedido_91_com_o_capital_da_apolice(ligada):
    assert PED._ramo_do_agger(SimpleNamespace(ramo="VIND")) == PED.RAMO_VIDA == 91
    apolice, ficha = ficha_vida()
    pedido = PED.de_apolice(apolice, perfil_vida(**RESPOSTAS_DO_CORRETOR), ficha=ficha, config=F2T.CONFIG)
    assert pedido.ramo == 91
    # 📊 o capital da MORTE é a linha "Morte Natural" do PDF — nunca a "Morte Acidental" nem a do cônjuge
    assert pedido.valor("vida", "capital_morte") == 250000.0
    assert pedido.valor("vida", "vigencia_inicio") == FIM.isoformat()
    assert pedido.valor("vida", "origem") == "renovacao"
    assert "vida.capital_morte" in pedido.assumidos               # deduzido do documento, não dito
    # a renovação de vida é SÓ o "anterior" (o capital e as coberturas da apólice) — nunca a econômica
    assert pedido.opcoes == ("anterior",)
    assert pedido.coberturas_por_opcao["anterior"]["capital_morte"] == 250000.0
    assert pedido.faltando() == [] and pedido.sem_codigo() == []
    claro = pedido.para_dict()
    assert claro["ramo"] == 91 and claro["segurado"]["cpf"] == CPF and claro["vida"]["fumante"] is False
    assert claro["vida"]["renda_mensal"] == 8500.0 and claro["coberturas"] == {} and claro["pacotes"] == {}
    json.dumps(claro)                                             # o que a porta cifra é JSON puro


def test_2_reajuste_do_capital_e_config_da_corretora_padrao_zero(ligada):
    apolice, ficha = ficha_vida()
    cfg = CFG.mesclar({"vida_por_ramo": {"91": {"reajuste_capital_pct": 10}}}, "renovacao")
    pedido = PED.de_apolice(apolice, perfil_vida(**RESPOSTAS_DO_CORRETOR), ficha=ficha, config=cfg)
    assert pedido.valor("vida", "capital_morte") == 275000.0
    assert CFG.reajuste_do_capital_pct(CFG.mesclar(None, "renovacao"), 91) == 0.0     # 🧑 padrão: repete


def test_2_o_fio_a_madrugada_le_a_ficha_e_a_porta_grava_o_pedido_91(mundo_real, monkeypatch, ligada):
    """A madrugada REAL até a porta REAL: o pedido sai com ramo 91, só o `anterior`, CIFRADO e com o capital da ficha."""
    m = mundo_real
    _instalar_vida_no_fio(monkeypatch, perfil=lambda: perfil_vida(**RESPOSTAS_DO_CORRETOR))
    c = FIO.montar_corretora(m, "token-v", renovacoes=FIO.cinco_renovacoes())
    FIO.agger_da_corretora(m, c.id)
    asyncio.run(M.preparar_dia(m.db, c.id, FIO.DIA))
    item = next(x for x in FIO.itens(m, c.id) if x["ramo_sigla"] == "VIND")
    assert (item["estado"], item.get("motivo"), item.get("ramo_agger")) == ("pronta", None, 91)
    cfg = M.carregar_config(m.db, c.id)
    estado, motivo, pedido, _dados = asyncio.run(M._avaliar(m.db, c.id, item, m.fontes[c.id], cfg))
    assert (estado, motivo) == ("pronta", None)
    pid = asyncio.run(M.calcular_na_porta(m.db, c.id, pedido=pedido, renovacao_id=str(item["id"]),
                                          opcoes=["anterior", "franquia_reduzida", "completa_mais"],
                                          dono_user_id=item.get("dono_user_id"), vence_em_dias=10))
    ped = next(p for p in m.banco.linhas("multicalculo_pedidos") if p["id"] == pid)
    assert ped["ramo"] == 91 and ped["opcoes"] == ["anterior"] and ped["servico"] == "renovacao"
    assert CPF not in ped["pedido_cifrado"]
    calcs = [x for x in m.banco.linhas("multicalculo_calculos") if x["pedido_id"] == pid]
    assert [x["opcao"] for x in calcs] == ["anterior"]
    assert calcs[0]["coberturas"]["capital_morte"] == 250000.0
    assert ped["cpf_hmac"] == cpf_hmac(CPF, chave=FIO.CHAVE_HMAC)


def test_2_a_cotacao_nova_de_vida_sai_padrao_e_mais_em_conta_com_o_mesmo_capital(mundo, ligada):
    pedido = PED.PedidoDeCalculo.de_dict(dados_cotacao(vida={"coberturas_extras": {"isAppInvalidez": 100000}}),
                                         ramo=91)
    aberto = rodar(mundo.porta.calcular(company_id=mundo.b, pedido=pedido, origem="auxiliar"))
    calcs = {c["opcao"]: c for c in mundo.banco.linhas("multicalculo_calculos") if c["pedido_id"] == aberto.pedido_id}
    assert list(calcs) == ["padrao", "economica"]
    assert calcs["padrao"]["coberturas"] == {"capital_morte": 300000.0, "isAppInvalidez": 100000.0}
    # "mais em conta" = só a morte com o MESMO capital — nunca capital menor sem o corretor pedir (§4)
    assert calcs["economica"]["coberturas"] == {"capital_morte": 300000.0}
    assert MulticalculoProvider(object()).capacidades(91)["suportado"] is True


def test_2_o_capital_e_sempre_o_do_pedido_mesmo_com_coberturas_explicitas(mundo, ligada):
    pedido = PED.PedidoDeCalculo.de_dict(dados_cotacao(), ramo=91)
    aberto = rodar(mundo.porta.calcular(company_id=mundo.b, pedido=pedido, origem="auxiliar", opcoes=("padrao",),
                                        coberturas={"padrao": {"capital_morte": 1.0, "isAppInvalidez": 5000}}))
    calc = next(c for c in mundo.banco.linhas("multicalculo_calculos") if c["pedido_id"] == aberto.pedido_id)
    assert calc["coberturas"]["capital_morte"] == 300000.0


def test_2_o_canal_nunca_pede_vida(mundo, ligada):
    pedido = PED.PedidoDeCalculo.de_dict(dados_cotacao(), ramo=91)
    with pytest.raises(RamoNaoSuportado):
        rodar(mundo.porta.calcular(company_id=mundo.canal, pedido=pedido, corretoras=[mundo.a], origem="canal"))
    assert mundo.banco.linhas("multicalculo_pedidos") == []


def test_2_recalcular_vida_e_recusado_nunca_a_comissao_inventada(mundo, ligada):
    pedido = PED.PedidoDeCalculo.de_dict(dados_cotacao(), ramo=91)
    aberto = rodar(mundo.porta.calcular(company_id=mundo.b, pedido=pedido, origem="auxiliar"))
    calc = next(c for c in mundo.banco.linhas("multicalculo_calculos") if c["pedido_id"] == aberto.pedido_id)
    for c in mundo.banco.linhas("multicalculo_calculos"):
        if c["id"] == calc["id"]:
            c.update(negocio_ref="neg-1", versao=1)
    with pytest.raises(RamoNaoSuportado):
        rodar(mundo.porta.recalcular(company_id=mundo.b, calculo_id=calc["id"],
                                     ajuste={"tipo": "comissao", "valor": 20}))


# =====================================================================================================================
# (3) FUMANTE · RENDA · ESPORTE sem fonte → `faltando` com os três; o pedido NÃO segue (mutação 1)
# =====================================================================================================================
def test_3_sem_as_respostas_o_pedido_aponta_as_tres_e_nunca_presume_nao(ligada):
    apolice, ficha = ficha_vida()
    pedido = PED.de_apolice(apolice, perfil_vida(), ficha=ficha, config=F2T.CONFIG)
    for campo in ("fumante", "renda_mensal", "esporte_radical"):
        assert pedido.valor("vida", campo) is None             # 🔴 mutação 1: None NUNCA vira False
        assert f"vida.{campo}" in pedido.faltando()
    assert pedido.faltando() == ["vida.fumante", "vida.renda_mensal", "vida.esporte_radical"]
    with pytest.raises(PED.FichaIncompleta) as exc:
        PED.de_apolice(apolice, perfil_vida(), ficha=ficha, config=F2T.CONFIG, exigir_completo=True)
    assert exc.value.faltando == ["vida.fumante", "vida.renda_mensal", "vida.esporte_radical"]


def test_3_o_falso_dito_pelo_corretor_e_resposta_nao_falta(ligada):
    """Controle da mutação 1: `False` dito é RESPOSTA (o corretor perguntou); só o `None` falta."""
    pedido = PED.PedidoDeCalculo.de_dict(dados_cotacao(vida={"fumante": "não", "esporte_radical": "Não"}), ramo=91)
    assert pedido.valor("vida", "fumante") is False and pedido.valor("vida", "esporte_radical") is False
    assert pedido.faltando() == []
    sim = PED.PedidoDeCalculo.de_dict(dados_cotacao(vida={"fumante": "sim"}), ramo=91)
    assert sim.valor("vida", "fumante") is True


def test_3_a_porta_recusa_sem_as_tres_e_nada_e_gravado(mundo, ligada):
    d = dados_cotacao()
    for k in ("fumante", "renda_mensal", "esporte_radical"):
        d["vida"].pop(k)
    pedido = PED.PedidoDeCalculo.de_dict(d, ramo=91)
    with pytest.raises(PedidoIncompleto) as exc:
        rodar(mundo.porta.calcular(company_id=mundo.a, pedido=pedido, origem="auxiliar"))
    assert list(exc.value.campos) == ["vida.fumante", "vida.renda_mensal", "vida.esporte_radical"]
    assert mundo.banco.linhas("multicalculo_pedidos") == [] and mundo.banco.linhas("multicalculo_calculos") == []


def test_3_o_fio_a_madrugada_deixa_pendente_com_as_tres_perguntas(mundo_real, monkeypatch, ligada):
    m = mundo_real
    _instalar_vida_no_fio(monkeypatch, perfil=perfil_vida)
    c = FIO.montar_corretora(m, "token-v", renovacoes=FIO.cinco_renovacoes())
    asyncio.run(M.preparar_dia(m.db, c.id, FIO.DIA))
    item = next(x for x in FIO.itens(m, c.id) if x["ramo_sigla"] == "VIND")
    assert (item["estado"], item["motivo"]) == ("pendente", "falta_dado")
    cfg = M.carregar_config(m.db, c.id)
    estado, motivo, pedido, dados = asyncio.run(M._avaliar(m.db, c.id, item, m.fontes[c.id], cfg))
    assert (estado, motivo, pedido) == ("pendente", "falta_dado", None)
    assert dados["faltando"] == ["vida.fumante", "vida.renda_mensal", "vida.esporte_radical"]
    assert dados["perguntas"] == [PED.PERGUNTA_DE_VIDA["vida.fumante"], PED.PERGUNTA_DE_VIDA["vida.renda_mensal"],
                                  PED.PERGUNTA_DE_VIDA["vida.esporte_radical"]]
    assert [p for p in m.banco.linhas("multicalculo_pedidos") if p.get("ramo") == 91] == []


def test_3_o_perfil_da_vida_sai_da_infocap_e_nunca_deduz_sexo_nem_saude(monkeypatch, ligada):
    """`perfil_da_renovacao.montar` REAL sobre a InfoCap na rede (as rotas medidas): o segurado vem do cadastro; o
    sexo vazio NÃO é deduzido pelo nome na vida (mortalidade muda o preço — nunca presumir); fumante/renda/esporte
    nunca aparecem (nenhuma rota os tem, 📊 BLOCO 0 M2: 0/22)."""
    cli = {**PERF.cliente(), "profissao": "ADVOGADO", "cod_profissao": "123"}
    perfil, nao, _rede = PERF._montar(monkeypatch, ramo="VIND", cli=cli, itens=[_item_vida()])
    assert perfil["segurado"] == {"cpf": CPF, "nome": "PESSOA SINTETICA DE TESTE", "data_nascimento": "1980-02-01",
                                  "sexo": "Feminino", "estado_civil": "Casado(a)", "cep": "88000000",
                                  "profissao_texto": "ADVOGADO", "profissao_codigo_infocap": "123"}
    assert "vida" not in perfil and not any(k.startswith("vida.") for k in nao)
    sem_sexo = {**cli, "sexo": "", "estado_civil": "AMASIADO"}
    perfil2, _nao2, _rede2 = PERF._montar(monkeypatch, ramo="VIND", cli=sem_sexo, itens=[_item_vida()])
    assert "sexo" not in perfil2["segurado"] and "estado_civil" not in perfil2["segurado"]


# =====================================================================================================================
# (4) O PDF SEM CAPITAL → pendente(falta_dado) "não achei o capital" — nenhum capital inventado (mutação 2)
# =====================================================================================================================
@pytest.mark.parametrize("linhas", [None, (), (("Assistência Funeral", 5000, None), ("Morte Acidental", 90000, None)),
                                    (("Cônjuge - Morte", 50000, None),)])
def test_4_sem_a_linha_da_morte_no_pdf_o_capital_falta_e_nunca_e_inventado(ligada, linhas):
    apolice, ficha = ficha_vida(linhas)
    pedido = PED.de_apolice(apolice, perfil_vida(**RESPOSTAS_DO_CORRETOR), ficha=ficha, config=F2T.CONFIG)
    assert pedido.valor("vida", "capital_morte") is None          # 🔴 mutação 2
    assert pedido.faltando() == ["vida.capital_morte"]
    assert pedido.coberturas_por_opcao == {} and "vida.capital_morte" not in pedido.assumidos
    assert PED.PERGUNTA_DE_VIDA["vida.capital_morte"] == "renove manualmente — não achei o capital da apólice atual"


def test_4_duas_mortes_com_capitais_diferentes_nunca_escolhe(ligada):
    apolice, ficha = ficha_vida((("Morte Natural", 250000, None), ("Morte", 300000, None)))
    pedido = PED.de_apolice(apolice, perfil_vida(**RESPOSTAS_DO_CORRETOR), ficha=ficha, config=F2T.CONFIG)
    assert pedido.valor("vida", "capital_morte") is None and PED.AVISO_CAPITAL_AMBIGUO in pedido.avisos


def test_4_o_fio_sem_capital_a_madrugada_pergunta_pelo_capital(mundo_real, monkeypatch, ligada):
    m = mundo_real
    _instalar_vida_no_fio(monkeypatch, perfil=lambda: perfil_vida(**RESPOSTAS_DO_CORRETOR), linhas=None)
    c = FIO.montar_corretora(m, "token-v", renovacoes=FIO.cinco_renovacoes())
    asyncio.run(M.preparar_dia(m.db, c.id, FIO.DIA))
    item = next(x for x in FIO.itens(m, c.id) if x["ramo_sigla"] == "VIND")
    cfg = M.carregar_config(m.db, c.id)
    estado, motivo, _pedido, dados = asyncio.run(M._avaliar(m.db, c.id, item, m.fontes[c.id], cfg))
    assert (estado, motivo) == ("pendente", "falta_dado")
    assert dados["faltando"] == ["vida.capital_morte"]
    assert dados["perguntas"] == ["renove manualmente — não achei o capital da apólice atual"]


# =====================================================================================================================
# (5) VGRP continua FORA mesmo com a chave — vida em GRUPO não é o pedido individual (D-129D-07, mutação 5)
# =====================================================================================================================
@pytest.mark.parametrize("sigla", ["VGRP", "vgrp", "VIDA EM GRUPO"])
def test_5_vgrp_e_ramo_nao_cotado_mesmo_com_a_chave(ligada, sigla):
    assert PDP.subfamilia_de_vida(sigla) == "vida_grupo"
    with pytest.raises(PED.RamoIndisponivel) as exc:
        PED._ramo_do_agger(SimpleNamespace(ramo=sigla))
    assert exc.value.motivo == "ramo_nao_cotado" and "grupo" in str(exc.value) and "renove manualmente" in str(exc.value)


def test_5_a_familia_da_conversa_nao_muda_e_as_subfamilias_nao_se_cruzam():
    """A conversa ("minha apólice de vida") continua achando VIND E VGRP (`familia_de_ramo` igual a antes); a
    separação é DENTRO da família, para o multicálculo. Cada sinônimo de subfamília é da família vida e de UMA só."""
    assert PDP.familia_de_ramo("VGRP") == PDP.familia_de_ramo("VIND") == "vida"
    ind, grp = (set(map(PDP.normalizar_rotulo, PDP.SUBFAMILIAS_DE_VIDA[k])) for k in ("vida_individual", "vida_grupo"))
    assert not ind & grp
    assert ind | grp <= set(map(PDP.normalizar_rotulo, PDP.FAMILIAS_DE_RAMO["vida"]))
    assert PDP.subfamilia_de_vida("VIND") == "vida_individual" and PDP.subfamilia_de_vida("VIDA") is None


def test_5_vida_sem_dizer_qual_nunca_vira_individual(ligada):
    with pytest.raises(PED.RamoIndisponivel) as exc:
        PED._ramo_do_agger(SimpleNamespace(ramo="VIDA"))
    assert exc.value.motivo == "ramo_nao_cotado"


def test_5_o_fio_vgrp_fica_pendente_na_madrugada_com_a_chave(mundo_real, monkeypatch, ligada):
    m = mundo_real
    _instalar_vida_no_fio(monkeypatch, perfil=lambda: perfil_vida(**RESPOSTAS_DO_CORRETOR))
    linhas = FIO.cinco_renovacoes() + [FIO.linha_renov(910009, "VGRP", FIO.DIA + FIO.timedelta(days=10))]
    c = FIO.montar_corretora(m, "token-v", renovacoes=linhas)
    asyncio.run(M.preparar_dia(m.db, c.id, FIO.DIA))
    item = next(x for x in FIO.itens(m, c.id) if x["ramo_sigla"] == "VGRP")
    assert (item["estado"], item["motivo"]) == ("pendente", "ramo_nao_cotado")


# =====================================================================================================================
# (6) MOTO · MOBI · API continuam como hoje, com a chave ligada (D-129D-02/03/01)
# =====================================================================================================================
@pytest.mark.parametrize("sigla,motivo", [("MOBI", "ramo_desconhecido"), ("API", "ramo_desconhecido"),
                                          ("APC", "ramo_desconhecido"), ("FROTA", "ramo_nao_cotado")])
def test_6_mobi_api_e_frota_iguais_com_a_chave(monkeypatch, sigla, motivo):
    saidas = []
    for valor in (None, "1"):
        if valor is None:
            monkeypatch.delenv(CHAVE, raising=False)
        else:
            monkeypatch.setenv(CHAVE, valor)
        with pytest.raises(PED.RamoIndisponivel) as exc:
            PED._ramo_do_agger(SimpleNamespace(ramo=sigla))
        saidas.append((exc.value.motivo, str(exc.value)))
    assert saidas[0] == saidas[1] and saidas[0][0] == motivo


def test_6_moto_continua_ramo_nao_cotado_com_a_chave(monkeypatch, ligada):
    it = {**PERF.item_auto(), "categoria": "Moto"}             # 📊 BLOCO 0 M1b: o rótulo da InfoCap é "Moto"
    perfil, _nao, _rede = PERF._montar(monkeypatch, itens=[it])
    apolice, ficha = FIO.ficha_sintetica("AUTO")
    with pytest.raises(PED.RamoIndisponivel) as exc:
        PED.de_apolice(apolice, perfil=perfil, ficha=ficha, config=F2T.CONFIG)
    assert exc.value.motivo == "ramo_nao_cotado" and "moto" in str(exc.value).lower()


def test_6_auto_e_re_continuam_iguais_com_a_chave(monkeypatch):
    saidas = []
    for valor in (None, "1"):
        if valor is None:
            monkeypatch.delenv(CHAVE, raising=False)
        else:
            monkeypatch.setenv(CHAVE, valor)
        saidas.append([PED._ramo_do_agger(SimpleNamespace(ramo=s)) for s in ("AUTO", "RESI", "COND", "EMPR")])
        apolice, ficha = FIO.ficha_sintetica("RESI")
        saidas.append(PED.de_apolice(apolice, F2T._perfil_resi(), ficha=ficha, config=F2T.CONFIG).para_dict())
    assert saidas[0] == saidas[2] == [31, 2, 16, 18] and saidas[1] == saidas[3]


# =====================================================================================================================
# (7) DUAS CORRETORAS — a config de vida e a preferência de A não vazam para B
# =====================================================================================================================
def test_7_comissao_e_agenciamento_de_vida_sao_os_de_cada_corretora(mundo, ligada):
    from app.services import portal_vault

    claros = {}
    for corretora in (mundo.a, mundo.b):
        pedido = PED.PedidoDeCalculo.de_dict(dados_cotacao(), ramo=91)
        aberto = rodar(mundo.porta.calcular(company_id=corretora, pedido=pedido, origem="auxiliar"))
        ped = next(p for p in mundo.banco.linhas("multicalculo_pedidos") if p["id"] == aberto.pedido_id)
        assert ped["ramo"] == 91 and ped["company_id"] == corretora and CPF not in ped["pedido_cifrado"]
        claros[corretora] = json.loads(portal_vault.decrypt(ped["pedido_cifrado"]))
    # A configurou comissão 20 e agenciamento 30 de vida; B não configurou: NADA vai no item (o robô lê o do Agger
    # da corretora, D-129D-08) — nunca a `comissao.entrada` do auto, nunca um número inventado
    assert claros[mundo.a]["comissao_desconto"] == {"comissao_percentual": 20.0, "agenciamento_percentual": 30.0}
    assert claros[mundo.b]["comissao_desconto"] == {}
    assert CFG.comissao_de_vida(CFG.mesclar(None), 91) is None
    assert CFG.agenciamento_de_vida(CFG.mesclar(None), 91) is None


def test_7_comissao_de_vida_fora_da_regua_e_recusada(mundo, ligada):
    pedido = PED.PedidoDeCalculo.de_dict(dados_cotacao(comissao_desconto={"comissao_percentual": 500}), ramo=91)
    with pytest.raises(PedidoIncompleto) as exc:
        rodar(mundo.porta.calcular(company_id=mundo.b, pedido=pedido, origem="auxiliar"))
    assert list(exc.value.campos) == ["comissao_desconto.comissao_percentual"]
    cfg = CFG.mesclar({"vida_por_ramo": {"91": {"comissao_pct": 0, "agenciamento_pct": 150,
                                                "reajuste_capital_pct": -5}}})
    assert CFG.comissao_de_vida(cfg, 91) is None and CFG.agenciamento_de_vida(cfg, 91) is None
    assert CFG.reajuste_do_capital_pct(cfg, 91) == 0.0


def test_7_a_preferida_de_vida_de_a_e_marcada_nunca_esconde_e_nao_vaza_para_b(mundo):
    cfg_a = rodar(mundo.porta._carregar_cfg(mundo.a, None))
    cfg_b = rodar(mundo.porta._carregar_cfg(mundo.b, None))
    assert CFG.preferencias_do_ramo(cfg_a, 91) == ["Seguradora Beta"] and CFG.preferencias_do_ramo(cfg_b, 91) == []
    estados = [{"calculo_id": "c1", "corretora_company_id": mundo.a, "opcao": "padrao"}]
    ofertas = [{"id": "o1", "calculo_id": "c1", "seguradora": "Seguradora Alfa", "premio_total": 900.0,
                "coberturas": {"capital_morte": 300000}},
               {"id": "o2", "calculo_id": "c1", "seguradora": "Seguradora Beta", "premio_total": 1100.0,
                "coberturas": {"capital_morte": 300000}}]
    qa = C.comparar(ofertas, estados=estados, config=cfg_a, ramo=91)
    linhas = {l["seguradora"]: l for l in qa.ranking()}
    assert set(linhas) == {"Seguradora Alfa", "Seguradora Beta"}          # 🔴 mutação 6: nunca esconde
    assert linhas["Seguradora Beta"]["preferida"] is True and linhas["Seguradora Alfa"]["preferida"] is False
    assert [l["seguradora"] for l in qa.ranking()][0] == "Seguradora Alfa"  # o preço manda; a preferência marca
    qb = C.comparar(ofertas, estados=[{**estados[0], "corretora_company_id": mundo.b}], config=cfg_b, ramo=91)
    assert not any(l["preferida"] for l in qb.ranking())


def test_7_a_preferencia_de_vida_e_editavel_pela_tela():
    assert CFG.erros_da_edicao(preferencias_de_seguradoras={"91": ["Seguradora Beta"]}) == []


# =====================================================================================================================
# LGPD art. 11 — saúde e renda nunca em log nem no repr
# =====================================================================================================================
def test_nada_de_saude_ou_renda_no_log(mundo, ligada, caplog):
    caplog.set_level(logging.DEBUG)
    pedido = PED.PedidoDeCalculo.de_dict(dados_cotacao(vida={"renda_mensal": "12.345,67", "fumante": True}), ramo=91)
    rodar(mundo.porta.calcular(company_id=mundo.a, pedido=pedido, origem="auxiliar"))
    texto = caplog.text + repr(pedido) + str(pedido)
    for proibido in ("12345", "12.345", "fumante", "renda", CPF, "PESSOA SINTETICA"):
        assert proibido not in texto, proibido


def test_o_catalogo_de_vida_e_o_do_contrato_quando_a_v1_o_expuser(ligada):
    """O contrato V1 ↔ V2 (§3 da SPEC). Enquanto o portal_worker não expõe `CAMPOS_DO_PEDIDO_VIDA`, vale o §3; quando
    expuser, os NOMES têm de ser os mesmos (um catálogo só — a costura V3 fica vermelha se divergirem)."""
    assert {g: tuple(c) for g, c in PED.CAMPOS_DO_PEDIDO_VIDA.items()} == {
        "segurado": ("cpf", "nome", "data_nascimento", "sexo", "estado_civil", "cep", "profissao_texto",
                     "profissao_codigo_infocap"),
        "vida": ("capital_morte", "coberturas_extras", "fumante", "renda_mensal", "esporte_radical",
                 "vigencia_inicio", "origem"),
        "comissao_desconto": ("comissao_percentual", "agenciamento_percentual")}
    do_contrato = getattr(K, "CAMPOS_DO_PEDIDO_VIDA", None)
    if do_contrato is not None:
        assert {g: tuple(c[0] if isinstance(c, (tuple, list)) else c for c in cs) for g, cs in do_contrato.items()} \
            == {g: tuple(c) for g, c in PED.CAMPOS_DO_PEDIDO_VIDA.items()}
    assert int(getattr(K, "RAMO_VIDA", 91)) == PED.RAMO_VIDA == 91


# =====================================================================================================================
# O mundo da porta (o molde da 129-C): duas corretoras + o canal, a porta REAL sobre o banco dublê
# =====================================================================================================================
def rodar(coro):
    return asyncio.run(coro)


@pytest.fixture
def mundo(monkeypatch):
    from cryptography.fernet import Fernet

    instalar_esquema(monkeypatch, com_porta=True)
    monkeypatch.setenv("PORTAL_VAULT_KEY", Fernet.generate_key().decode())
    monkeypatch.delenv("PORTAL_VAULT_KEY_ANTERIOR", raising=False)
    relogio = D.Relogio(datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc))
    banco = BancoU1(relogio)
    canal, a, b = (str(uuid4()) for _ in range(3))
    banco.semear("companies", {"id": canal, "company_kind": "platform_canal", "is_technical": True})
    for c in (a, b):
        banco.semear("companies", {"id": c, "company_kind": "client"})
        banco.semear("multicalculo_adesoes", {"canal_company_id": canal, "corretora_company_id": c, "ativa": True})
    # a corretora A configurou a vida: comissão 20, agenciamento 30 e a "Seguradora Beta" como a preferida
    banco.semear("multicalculo_config", {"company_id": a, "config": {
        "vida_por_ramo": {"91": {"comissao_pct": 20, "agenciamento_pct": 30}},
        "preferencias_de_seguradoras": {"91": ["Seguradora Beta"]}}})
    porta = MulticalculoProvider(RepositorioMulticalculo(banco.visao("smith-api")),
                                 ambiente={"MULTICALCULO_HMAC_KEY": CHAVE_HMAC}, agora=relogio.agora)
    return SimpleNamespace(banco=banco, relogio=relogio, porta=porta, canal=canal, a=a, b=b)


# ---------------------------------------------------------------------------------------------------------------------
# O fio da madrugada (o mundo REAL da 131-A): a ficha e o perfil de VIND entram nas BORDAS do fixture
# ---------------------------------------------------------------------------------------------------------------------
def _item_vida():
    """📊 BLOCO 0 M2: o item de VIND (8/22 o têm) — nomseg, cpf, datnas, cod_profissao, garantias."""
    return {"codfil": 1, "nosnum": 0, "item": 1, "cancelado": "F", "nomseg": "PESSOA SINTETICA DE TESTE",
            "cpf": CPF, "datnas": "01/02/1980", "cod_profissao": "123", "seguro_conjuge": "F", "garantias": []}


def _instalar_vida_no_fio(monkeypatch, *, perfil, linhas=LINHAS_DO_PDF):
    original = FIO.ficha_sintetica

    def ficha(sigla: str):
        if sigla in ("VIND", "VGRP"):
            return ficha_vida(linhas, sigla)
        return original(sigla)

    monkeypatch.setattr(FIO, "ficha_sintetica", ficha)
    monkeypatch.setitem(FIO.PERFIL_SINTETICO, "VIND", perfil)
    monkeypatch.setitem(FIO.PERFIL_SINTETICO, "VGRP", perfil)
