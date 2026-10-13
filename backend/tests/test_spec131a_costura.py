# -*- coding: utf-8 -*-
"""SPEC-131-A · F4 — A COSTURA: a saída REAL de uma fatia é a entrada da outra, sem dublê entre elas.

    ficha sintética (a borda: a InfoCap HTTP do detalhe) + perfil sintético (a borda que o produto AINDA não tem)
      → pedido.de_apolice REAL (F2: o ramo, as 3 opções da ficha, a comissão anterior)
      → madrugada.preparar_dia / calcular_dia REAIS (F1)
      → porta.calcular REAL (F3: prioridade 7, política 'madrugada', renovacao_id, qual_agger)
      → banco dublê com as travas das migrations (CHECK de opções, FK do renovacao_id)
      → o "motor" (borda Agger) fecha → madrugada.acompanhar DERIVA o estado do item

E os consertos da costura, cada um com a linha de controle que prova que o guarda consegue ficar vermelho:
    · sem o perfil (o produto hoje) o item é `pendente(falta_dado)` com os NOMES do que falta — nunca `pronta`
    · UM pedido aberto por renovação (a janela de crash F1×F3) · o desvio cancela o aberto antes de abrir o novo
    · `ramo_desconhecido` aceito em todo lugar · `licenca_agger_vencida` vira motivo e o aviso das 06:45 avisa antes
    · `servicos.renovacao.prosseguir_aceites` registrado e intacto depois de a tela regravar a config

⛔ Dados sintéticos (CPF/CNPJ de exemplo, "Pessoa Sintetica"); nenhum nome de corretora (CLAUDE.md §13.9).
Rodar: cd backend && PYTHONIOENCODING=utf-8 python -m pytest tests/test_spec131a_costura.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import timedelta
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import test_spec131a_o_fio as FIO  # noqa: E402
from test_spec131a_o_fio import mundo_real  # noqa: E402,F401  (fixture)
from app.services.multicalculo import madrugada as M  # noqa: E402
from app.services.multicalculo import pedido as P  # noqa: E402
from app.services.multicalculo import renovacao as R  # noqa: E402

DIA = FIO.DIA
PROIBIDAS = {"economica", "minima"}


def _corretora(m, renovacoes=None):
    c = FIO.montar_corretora(m, "token-a", renovacoes=renovacoes or FIO.cinco_renovacoes())
    FIO.agger_da_corretora(m, c.id)
    return c


def _preparar_e_calcular(m, c):
    asyncio.run(M.preparar_dia(m.db, c.id, DIA))
    return asyncio.run(M.calcular_dia(m.db, c.id, DIA))


def _calculos(m, pedido_id):
    return [x for x in m.banco.linhas("multicalculo_calculos") if x["pedido_id"] == pedido_id]


# =====================================================================================================================
# 1. A SAÍDA DE UMA FATIA É A ENTRADA DA OUTRA
# =====================================================================================================================
def test_a_ficha_vira_pedido_real_que_a_porta_real_grava_e_o_estado_e_derivado(mundo_real):
    m = mundo_real
    c = _corretora(m)
    r = _preparar_e_calcular(m, c)
    assert r["disparados"] == 3, r
    por_sigla = {x["ramo_sigla"]: x for x in FIO.itens(m, c.id)}
    assert (por_sigla["VIND"]["estado"], por_sigla["VIND"]["motivo"]) == ("pendente", "ramo_nao_cotado")
    assert (por_sigla["XYZW"]["estado"], por_sigla["XYZW"]["motivo"]) == ("pendente", "ramo_desconhecido")

    pedidos = FIO.pedidos_da_renovacao(m, c.id)
    assert {p["ramo"] for p in pedidos} == {31, 2, 16}
    for p in pedidos:
        item = next(x for x in FIO.itens(m, c.id) if x["id"] == p["renovacao_id"])
        assert item["estado"] == "calculando" and item["pedido_id"] == p["id"]
        assert (p["servico"], p["politica_de_sessao"]) == ("renovacao", "madrugada")
        assert p["opcoes"] and set(p["opcoes"]) <= FIO.OPCOES_DA_RENOVACAO and not set(p["opcoes"]) & PROIBIDAS
        calcs = _calculos(m, p["id"])
        assert {x["prioridade"] for x in calcs} == {7}
        assert sorted(x["opcao"] for x in calcs) == sorted(p["opcoes"])
        assert all(isinstance(x["coberturas"], dict) and x["coberturas"] for x in calcs), "cálculo sem coberturas"
    # o que de_apolice (F2) montou é o que a porta (F3) gravou: o `anterior` do AUTO é o da FICHA (FICHA_A, R$ 100 mil)
    auto = next(p for p in pedidos if p["ramo"] == 31)
    anterior = next(x for x in _calculos(m, auto["id"]) if x["opcao"] == "anterior")["coberturas"]
    assert anterior["isDanosMateriais"] == 100000 and anterior["isDanosCorporais"] == 100000
    # RE: a Básica reajustada da ficha e as extras do condomínio chegam ao cálculo (nunca a típica disfarçada)
    cond = next(p for p in pedidos if p["ramo"] == 16)
    ant_cond = next(x for x in _calculos(m, cond["id"]) if x["opcao"] == "anterior")["coberturas"]
    assert ant_cond["isValorSindico"] == 700000

    # o motor (borda Agger) fecha → a releitura DERIVA (pull, nunca callback)
    FIO.fechar_com_ofertas(m.banco, [p["id"] for p in pedidos])
    contagem = M.acompanhar(m.db, c.id, por="teste.costura")
    assert contagem == {"calculadas": 3, "falharam": 0, "em_voo": 0}
    assert sorted(x["estado"] for x in FIO.itens(m, c.id)) == ["calculada"] * 3 + ["pendente"] * 2


def test_sem_o_perfil_o_item_e_pendente_com_os_nomes_do_que_falta_e_nada_vai_a_porta(mundo_real, monkeypatch):
    """O PRODUTO HOJE (`perfil_do_segurado` → None): a ficha não traz CPF, nascimento, condutor… — o item nunca é
    `pronta` para depois cair na porta; é `pendente(falta_dado)` às 00:30, com os NOMES no evento, e nenhum pedido."""
    m = mundo_real
    c = _corretora(m)

    async def sem_perfil(*_a, **_k):
        return None

    monkeypatch.setattr(M, "perfil_do_segurado", sem_perfil)
    _preparar_e_calcular(m, c)
    assert FIO.pedidos_da_renovacao(m, c.id) == []
    for sigla in ("AUTO", "RESI", "COND"):
        item = next(x for x in FIO.itens(m, c.id) if x["ramo_sigla"] == sigla)
        assert (item["estado"], item["motivo"]) == ("pendente", "falta_dado"), (sigla, item["estado"])
        ev = [e for e in m.banco.linhas("renovacao_eventos") if e["renovacao_id"] == item["id"]][-1]
        assert "segurado.cpf_cnpj" in ev["dados"]["faltando"], ev["dados"]
        assert all("." in n and " " not in n for n in ev["dados"]["faltando"])        # só nomes, nunca valores
    # CONTROLE: o mesmo pedido COM o perfil — a régua que acusou é a mesma que libera
    apolice, ficha = FIO.ficha_sintetica("AUTO")
    cfg = M.carregar_config(m.db, c.id)
    assert M.o_que_falta(M.de_apolice(apolice, ficha=ficha, config=cfg, perfil=FIO.PERFIL_SINTETICO["AUTO"]())) == []
    sem = M.de_apolice(apolice, ficha=ficha, config=cfg, perfil=None)
    assert "segurado.cpf_cnpj" in M.o_que_falta(sem)


# =====================================================================================================================
# 2. UM PEDIDO ABERTO POR RENOVAÇÃO
# =====================================================================================================================
def _item_pronto(m, c, sigla="AUTO"):
    asyncio.run(M.preparar_dia(m.db, c.id, DIA))
    return next(x for x in FIO.itens(m, c.id) if x["ramo_sigla"] == sigla)


def _pedir_direto(m, c, item, **kw):
    apolice, ficha = FIO.ficha_sintetica(item["ramo_sigla"])
    pedido = M.de_apolice(apolice, ficha=ficha, config=M.carregar_config(m.db, c.id),
                          perfil=FIO.PERFIL_SINTETICO[item["ramo_sigla"]]())
    return asyncio.run(M.calcular_na_porta(m.db, c.id, pedido=pedido, renovacao_id=item["id"], opcoes=[],
                                           dono_user_id=item.get("dono_user_id"), vence_em_dias=10, **kw))


def test_a_janela_de_crash_nao_duplica_o_pedido_e_o_desvio_cancela_o_aberto(mundo_real):
    m = mundo_real
    c = _corretora(m)
    item = _item_pronto(m, c)
    um = _pedir_direto(m, c, item)
    # o processo caiu ANTES de gravar o estado: o item segue `pronta`, sem pedido_id — e a próxima volta pede de novo
    assert next(x for x in FIO.itens(m, c.id) if x["id"] == item["id"])["estado"] == "pronta"
    dois = _pedir_direto(m, c, item)
    assert dois == um and len(FIO.pedidos_da_renovacao(m, c.id)) == 1
    # o desvio das 06:15: o aberto é CANCELADO e o novo sai no Agger da corretora — nunca dois em voo
    tres = _pedir_direto(m, c, item, forcar_corretora_motivo=M.MOTIVO_DO_DESVIO)
    assert tres != um
    estados = {p["id"]: p["status"] for p in FIO.pedidos_da_renovacao(m, c.id)}
    assert estados == {um: "cancelado", tres: "aberto"}
    assert {x["status"] for x in _calculos(m, um)} == {"cancelado"}
    # CONTROLE: outra renovação NÃO é confundida com esta (o filtro é o renovacao_id, não a corretora)
    outro = next(x for x in FIO.itens(m, c.id) if x["ramo_sigla"] == "RESI")
    assert _pedir_direto(m, c, outro) not in (um, tres)


# =====================================================================================================================
# 3. OS MOTIVOS QUE ATRAVESSAM AS FATIAS
# =====================================================================================================================
def test_ramo_desconhecido_e_aceito_em_todo_lugar(mundo_real):
    m = mundo_real
    c = _corretora(m)
    with pytest.raises(P.RamoIndisponivel) as e:
        P.de_apolice(FIO.ficha_sintetica("XYZW")[0], config=M.carregar_config(m.db, c.id))   # F2 REAL
    assert M.motivo_da_excecao(e.value) == ("pendente", "ramo_desconhecido")                  # F1
    assert R.motivo_valido("ramo_desconhecido") and "ramo_desconhecido" in R.MOTIVOS_DE_PENDENCIA
    assert "ramo_desconhecido" in R.MOTIVOS_NAO_COTAVEIS and "renove manualmente" in R.frase_do_motivo(
        "ramo_desconhecido")
    asyncio.run(M.preparar_dia(m.db, c.id, DIA))                                              # o banco aceita (CHECK)
    item = next(x for x in FIO.itens(m, c.id) if x["ramo_sigla"] == "XYZW")
    assert (item["estado"], item["motivo"]) == ("pendente", "ramo_desconhecido")


def test_a_licenca_vencida_vira_motivo_humano_e_o_aviso_avisa_antes_de_vencer(mundo_real, monkeypatch):
    from portal_worker.multicalculo import motor as MOT

    calc = {"status": "falhou", "erro": MOT.MOTIVO_LICENCA_VENCIDA}                 # o texto REAL do motor (F3)
    assert M.estado_derivado([calc], 0, False) == ("falhou", "licenca_agger_vencida")
    assert "licença do Agger venceu" in R.frase_do_motivo("licenca_agger_vencida")
    # CONTROLE: um erro qualquer NÃO vira esse motivo
    assert M._motivo_do_calculo({"status": "falhou", "erro": "timeout no portal"}) == "calculo_falhou"

    import dubles_do_work_os as D

    # a coluna `motivo` de `multicalculo_eventos` (o motor F3 grava a licença nela; 📊 existe no banco, 12/10)
    monkeypatch.setitem(D.ESQUEMA, "multicalculo_eventos", {**D.ESQUEMA["multicalculo_eventos"],
                                                          "motivo": ("text", True, None)})
    m = mundo_real
    c = _corretora(m)
    (conta,) = [x["id"] for x in m.banco.linhas("portal_accounts") if x["company_id"] == c.id]

    def evento(dias, quando):
        limite = (DIA + timedelta(days=dias)).isoformat()
        m.banco.semear("multicalculo_eventos", {
            "calculo_id": str(uuid.uuid4()), "pedido_id": str(uuid.uuid4()), "company_id": c.id,
            "solicitante_company_id": c.id, "tipo": "licenca_agger", "chave": f"licenca_agger|{conta}|{quando}",
            "motivo": f"dataLimiteCalculo={limite} · licenca={limite}", "criado_em": f"{quando}T03:00:00+00:00"})

    evento(30, "2026-10-01")                     # o antigo dizia 30 dias…
    evento(5, "2026-10-12")                      # …o ÚLTIMO diz 5: é ele que vale
    assert M.licencas_do_agger(m.db, c.id, DIA) == {"vencendo": 1, "vencidas": 0, "menor_prazo_dias": 5}
    M.avisar_dia(m.db, c.id, DIA)
    (aviso,) = [p for p in FIO.avisos(m, c.id) if p.get("user_id") is None]
    assert "licença do Agger vence em até 7 dias em 1 conta" in aviso["summary_text"]
    # CONTROLE: outra corretora não vê a licença desta
    outra = FIO.montar_corretora(m, "token-b", renovacoes=FIO.cinco_renovacoes(base=920000))
    assert M.licencas_do_agger(m.db, outra.id, DIA) == {"vencendo": 0, "vencidas": 0}


# =====================================================================================================================
# 4. O ACEITE DO PROSSEGUIR SOBREVIVE À TELA
# =====================================================================================================================
def test_prosseguir_aceites_e_registrado_validado_e_a_tela_nao_o_apaga():
    import test_spec1310_f4_servicos as F4S
    from app.api import servicos_da_corretora as S
    from app.services.multicalculo import config as CFG

    conta = "abcdef01-0000-4000-8000-000000000001"
    assert CFG.PADRAO_DO_PRODUTO["servicos"]["renovacao"]["prosseguir_aceites"] == []      # desligada por padrão
    lida = CFG.mesclar({"servicos": {"renovacao": {"prosseguir_aceites": [conta.upper()]}}}, "renovacao")
    assert lida["servicos"]["renovacao"]["prosseguir_aceites"] == [conta]
    # ⛔ um aceite que não é id não liga ninguém
    assert CFG.mesclar({"servicos": {"renovacao": {"prosseguir_aceites": ["todo mundo"]}}},
                       "renovacao")["servicos"]["renovacao"]["prosseguir_aceites"] == []
    # a tela "Serviços" regrava a renovação (só as chaves que edita) — o aceite fica
    banco = F4S.Banco(multicalculo_config=[{"company_id": F4S.A, "atualizado_em": "v1", "config": {
        "servicos": {"renovacao": {"modo": "calcular", "prosseguir_aceites": [conta]}}}}])
    S.gravar(banco, F4S.A, versao="v1", servicos={"renovacao": {"modo": "calcular_entregar"}})
    linha = next(x for x in banco.tabelas["multicalculo_config"] if x["company_id"] == F4S.A)
    assert linha["config"]["servicos"]["renovacao"] == {"modo": "calcular_entregar", "prosseguir_aceites": [conta]}
    # CONTROLE: se a tela EDITASSE a chave, a regravação a apagaria — por isso ela NÃO é editável pela tela
    assert "prosseguir_aceites" not in CFG.EDITAVEL_POR_SERVICO["renovacao"]


# =====================================================================================================================
# 5. O QUE O CANÁRIO REAL ACHOU (13/10) — a ficha do produto e o ramo antes da ficha
# =====================================================================================================================
def test_a_ficha_do_produto_chama_o_detalhe_com_a_chave_interna_e_o_cliente_assincrono(monkeypatch):
    """📊 canário 13/10: com o cliente SÍNCRONO do worker e sem a chave interna, o conector do detalhe recusava e TODO
    item virava `sem_conexao`. A ficha agora chama como o chat chama (`infocap_tool.py`)."""
    import app.core.database as DB
    from app.providers.infocap_policy_provider import InfoCapProvider

    vistos = {}
    assincrono = object()

    async def cliente():
        return assincrono

    async def detalhe(self, **kw):
        vistos.update(kw)
        return {"status": "blocked_missing_credentials"}           # sem pack: a ficha recusa com SemConexao

    monkeypatch.setattr(DB, "create_async_supabase_client", cliente)
    monkeypatch.setattr(InfoCapProvider, "detail", detalhe)
    monkeypatch.setenv("BACKEND_INTERNAL_API_KEY", "chave-interna-de-teste")
    with pytest.raises(M.SemConexao):
        asyncio.run(M.ficha_da_apolice(object(), "c1310000-0000-4000-8000-000000000001",
                                       {"codfil": 1, "nosnum": "910001"}, None))
    assert vistos["internal_key"] == "chave-interna-de-teste" and vistos["db"] is assincrono
    assert vistos["policy_ref"] == "infocap:1:910001" and vistos["document_evidence_requested"] is True


def test_o_ramo_da_lista_decide_antes_da_ficha(mundo_real, monkeypatch):
    """📊 canário 13/10: o MOBI virava `sem_conexao` (a ficha falhou primeiro) e contava como COTÁVEL. Agora o ramo
    que ninguém reconhece não lê a ficha. CONTROLE: o AUTO com a ficha quebrada continua `sem_conexao`."""
    m = mundo_real
    c = _corretora(m, renovacoes=[FIO.linha_renov(930001, "MOBI", DIA + timedelta(days=5)),
                                  FIO.linha_renov(930002, "AUTO", DIA + timedelta(days=5))])

    async def ficha_quebrada(*_a, **_k):
        raise RuntimeError("a InfoCap do detalhe caiu")

    monkeypatch.setattr(M, "ficha_da_apolice", ficha_quebrada)
    asyncio.run(M.preparar_dia(m.db, c.id, DIA))
    por = {x["ramo_sigla"]: (x["estado"], x["motivo"]) for x in FIO.itens(m, c.id)}
    assert por == {"MOBI": ("pendente", "ramo_desconhecido"), "AUTO": ("pendente", "sem_conexao")}
