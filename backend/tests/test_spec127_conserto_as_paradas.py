# -*- coding: utf-8 -*-
r"""SPEC-127 CONSERTO ÚNICO — itens 4 a 7: cada parada diz a verdade e tem UM dono.

```
4 · juiz B3  o DOM para ANTES do "Iniciar atendimento" (o GET /apolices não saiu) → stage `pronto_para_iniciar`,
             texto que NÃO afirma cobertura (era `pronto_para_abrir`: "a sua apolice cobre")
5 · RT-P1    `tipo_de_telefone_desconhecido` CONDUZIDO pelo destravador → o vigia NÃO pede uma 2ª continuação
             sobre a mesma parada; destravador off → a tool entrega a parada ao vigia POR ESCRITO (`reler`)
6 · RT-P2    paradas antes da fronteira que vão à equipe: o texto da equipe não promete "pedir de novo" (a
             tool diz "NAO chame de novo") — diz o que dá para fazer: abrir DIRETO no portal
7 · RT-P4    o CEP do cadastro no DOM só com a MESMA cidade E a MESMA UF, as duas presentes (a régua do API-first)
```
Pelo MOTOR (a journey do DOM numa página falsa, a journey API-first e a continuação sobre o HAR, a tool real com
o destravador, o vigia real), dublê só na borda — os dublês das suítes P1/P2/P4. 📊 Sondas que nasceram
vermelhas: `jz127_sondas.py`/format_result (B3), `rt127_probe2.py` (P1, P4). Rodar (de backend/):
python -m pytest -q tests/test_spec127_conserto_as_paradas.py
"""
from __future__ import annotations

import asyncio
import copy
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _c in (str(ROOT), str(ROOT / "tests")):
    if _c not in sys.path:
        sys.path.insert(0, _c)

import test_spec127_p1_o_fio_do_pedido_de_vidro as T  # noqa: E402
import test_spec127_p2_o_dom_para_de_errar_calado as P2  # noqa: E402
import test_spec127_p4_o_fio_do_destravador_no_replay as R4  # noqa: E402
from test_spec124_portal_destrava_o_fio import mundo  # noqa: E402,F401 — o fixture da borda do destravador

from app.services import destravador as DT  # noqa: E402
from app.tasks import vigia_do_portal as V  # noqa: E402
from portal_worker import adaptive as AD  # noqa: E402

PP, AF, VC, RV = T.PP, T.AF, T.VC, T.RV


@pytest.fixture(autouse=True)
def _flag(monkeypatch):
    monkeypatch.setenv("PORTAL_VIDROS_API_FIRST", "1")


# ═════════════════════════════════════════════════════════════════════════════
# 4 · juiz B3 — o DOM no passo 1 não diz "a sua apolice cobre"
# ═════════════════════════════════════════════════════════════════════════════
def test_o_DOM_sem_liberacao_para_antes_do_GET_apolices_e_nao_afirma_cobertura(monkeypatch):
    monkeypatch.delenv("PORTAL_VIDROS_API_FIRST", raising=False)     # hoje o DOM é 100 % (flag desligada)
    r, pagina, _rt, ev = P2._abrir(monkeypatch, confirm=False)
    assert "Iniciar atendimento" not in pagina.cliques                         # o GET /apolices NÃO saiu
    stage = (r.captured or {}).get("stage")
    assert r.status == "needs_human" and stage == "pronto_para_iniciar"
    texto = PP.format_result({"status": r.status, "evidence": {**ev, **(r.captured or {})}})
    para_ele = texto.split("[para a equipe")[0].lower()
    assert "cobre" not in para_ele and "cobertura" not in para_ele and "conferido" not in para_ele
    assert "liberacao interna" in para_ele and "a apolice ainda nao foi consultada" in texto.lower()
    # a classe vem da TABELA: NUNCA sozinho, e o NUNCA é o da confirmação final (a MESMA lista do WhatsApp)
    assert DT.CLASSE_DA_PARADA_DO_PORTAL[stage] == "nunca_sozinho"
    assert DT.NUNCA_DA_PARADA_DO_PORTAL[stage] == ("confirmacao_final", "pessoa")
    assert DT.NUNCA_DA_PARADA_DO_PORTAL[stage][0] in DT.NUNCA_SOZINHO


def test_CONTROLE_a_parada_do_API_first_depois_do_preflight_continua_dizendo_que_cobre():
    """O texto antigo era VERDADE no API-first (o GET /apolices já respondeu): ele fica onde é verdade."""
    assert "cobre" in PP.texto_da_parada("pronto_para_abrir")[0]
    assert PP.texto_da_parada("pronto_para_iniciar")[0] != PP.texto_da_parada("pronto_para_abrir")[0]


# ═════════════════════════════════════════════════════════════════════════════
# 5 · RT-P1 — uma parada, UM processo
# ═════════════════════════════════════════════════════════════════════════════
def _agora():
    return datetime.now(timezone.utc)


def test_destravador_CONDUZIU_o_tipo_de_telefone_e_o_vigia_nao_abre_um_2o_processo(mundo):  # noqa: F811
    banco, params, ev, _o = R4._montar(mundo, R4._NOVO_TEL, RV.params_do_har(R4._NOVO),
                                       modos=[R4._modo(R4.EMPRESA_A)])
    assert ev["stage"] == "tipo_de_telefone_desconhecido"
    R4._aguardar(R4.EMPRESA_A, banco, params)
    cont = [j for j in banco.jobs if j["journey"] == "continuar_atendimento"]
    assert len(cont) == 1 and cont[0]["params"]["_destravador"]["classe"] == "conduzir"   # o destravador agiu
    origem = banco.jobs[0]
    assert PP.acao_esperada(origem["evidence"]) == ("responder", "tipo_telefone")      # o dono é a tool
    assert V.pedir_releitura(origem, _agora()) is False                               # era True (rt127_probe2)
    assert V.diagnosticar(origem, _agora()) is None                                   # nem alerta falso à equipe


def test_destravador_OFF_a_tool_entrega_a_parada_ao_vigia_por_escrito_e_ele_rele(mundo):  # noqa: F811
    banco, params, _ev, _o = R4._montar(mundo, R4._NOVO_TEL, RV.params_do_har(R4._NOVO),
                                        modos=[R4._modo(R4.EMPRESA_A)], empresa=R4.EMPRESA_B)
    saida = R4._aguardar(R4.EMPRESA_B, banco, params)
    origem = banco.jobs[0]
    assert len(banco.jobs) == 1                                                        # nenhuma continuação
    assert PP.acao_esperada(origem["evidence"])[0] == "reler"                          # a passagem ESCRITA
    assert origem["evidence"].get("entregue_ao_agente") is True
    assert "Nao pergunte nada ao segurado" in saida["content"]                         # o texto de hoje
    assert V.pedir_releitura(origem, _agora()) is True                                 # e o vigia relê


def test_CONTROLE_a_parada_tecnica_que_espera_reler_continua_com_o_vigia():
    agora = _agora()

    def job(stage, acao):
        return {"id": "j", "company_id": "c", "status": "needs_human", "params": {},
                "evidence": {"stage": stage, "entregue_ao_agente": True,
                             "continuacao": {"possivel": True, "etapa": "peca", "acao_esperada": acao,
                                             "emitida_em": agora.isoformat(), "sessao_guardada": True,
                                             "sessao_cifrada": "x"}}}

    assert V.pedir_releitura(job("catalogo_indisponivel", "reler"), agora) is True
    assert V.pedir_releitura(job("agenda_nao_respondeu", "agendar"), agora) is True    # RED B3 da 001.10.1
    assert V.pedir_releitura(job("tipo_de_telefone_desconhecido", "responder:tipo_telefone"), agora) is False
    assert V.pedir_releitura(job("tipo_de_telefone_desconhecido", "reler"), agora) is True


# ═════════════════════════════════════════════════════════════════════════════
# 6 · RT-P2 — a parada que vai à equipe não promete uma repetição que não vem
# ═════════════════════════════════════════════════════════════════════════════
_PROMESSA = ("pedir de novo", "peca de novo", "pode pedir", "vale tentar de novo")


def _sem_promessa(texto: str) -> bool:
    baixo = texto.lower()
    return not any(p in baixo for p in _PROMESSA)


@pytest.mark.parametrize("corpo,status,stage", [
    ({"ApoliceNaoEncontrada": True, "MaisDeUmaApoliceEncontrada": False}, 200, T.ST.PARADA_APOLICE_NAO_ENCONTRADA),
    ({"ApoliceNaoEncontrada": False, "MaisDeUmaApoliceEncontrada": True}, 200, T.ST.PARADA_PREFLIGHT_AMBIGUO),
    ({"Tipo": "RegraDeNegocioExcecao", "Message": "regra nova"}, 400, T.ST.PARADA_REGRA_DESCONHECIDA),
])
def test_o_preflight_que_vai_a_equipe_diz_o_que_fazer_de_verdade(corpo, status, stage):
    _r, ev, page = T._abrir(T._params_completos(), har=T._har_com("/apolices", corpo, status=status))
    assert ev["stage"] == stage and page.escritas() == []
    job = {"status": "needs_human", "evidence": ev}
    equipe = PP.format_result(job).split("[para a equipe, nao mande ao segurado]")[1]
    assert _sem_promessa(equipe) and "DIRETO no portal" in equipe
    # a mesma verdade que a tool dá ao agente na 2ª chamada
    assert "NAO chame de novo" in PP.frase_de_pedido_ja_existente(job)


def test_a_API_que_piscou_ao_recomecar_a_abertura_tambem_nao_promete_repeticao():
    banco = T.Banco([], sem_no_job="local.cidade_servico")
    banco.table("portal_jobs").insert({
        "company_id": T.EMPRESA, "portal_key": "vidros_lanternas", "journey": "abrir_atendimento",
        "params": T._params_completos(confirm=True), "status": "queued", "idempotency_key": "k-origem",
        "session_id": T.SESSAO}).execute()
    banco.table("portal_jobs").select("*").eq("id", "job-1").execute()
    cid, uf = T.INFOCAP["client"]["cidade"], T.INFOCAP["client"]["estado"]
    linha = PP.montar_job_de_continuacao(company_id=T.EMPRESA, job_origem=copy.deepcopy(banco.jobs[0]),
                                         operacao="responder", pedido_key="k-origem", protocolo="k-origem",
                                         confirm=True, respostas={"cidade_servico": {"uf": uf, "cidade": cid}},
                                         extra="job-1")
    page = RV.PaginaDeReplay(T._har_com("/apolices", {}, status=503))          # a API piscou
    ev: dict = {}
    r = asyncio.run(VC.continuar_atendimento(page, {**linha["params"], "_runtime": T.RT(True)}, ev))
    ev = T._evidencia_do_worker(r, ev)
    assert ev["stage"] == T.ST.PARADA_ABERTURA_SEM_RESPOSTA and page.escritas() == []
    job = {"status": r.status, "evidence": ev}
    assert PP.continuacao_possivel(ev) is False
    equipe = PP.format_result(job).split("[para a equipe, nao mande ao segurado]")[1]
    assert _sem_promessa(equipe) and "DIRETO no portal" in equipe
    assert _sem_promessa(r.message or "")


def test_toda_parada_antes_da_fronteira_que_vai_a_equipe_tem_a_mesma_verdade():
    da_equipe = [st for st, (ele, _eq) in PP._PARADAS.items()
                 if PP._A_EQUIPE_RESOLVE_ANTES in ele and st not in PP.ESTAGIOS_ANTES_DA_FRONTEIRA]
    assert {"pedido_incompleto", "cadastro_da_corretora_incompleto", "apolice_nao_encontrada",
            "preflight_ambiguo", "regra_do_portal_desconhecida",
            "abertura_sem_resposta_do_portal"} <= set(da_equipe)
    for st in da_equipe:
        equipe = PP._PARADAS[st][1]
        assert _sem_promessa(equipe), st
        assert PP._ESTE_PEDIDO_NAO_SE_REPETE in equipe, st


# ═════════════════════════════════════════════════════════════════════════════
# 7 · RT-P4 — o CEP: UMA régua, dois consumidores
# ═════════════════════════════════════════════════════════════════════════════
_TELA = {"inputs": [{"id": "estado", "label": "Selecione o estado onde deseja ser atendido.", "value": ""},
                    {"id": "cidade", "label": "Escolha a cidade disponível para atendimento.", "value": ""},
                    {"id": "cep", "label": "CEP (opcional)", "value": ""}]}


def _cep_no_dom(local):
    return [f for f in AD.fatos_da_tela(_TELA, {"local": local}) if f["de"] == "cep"]


@pytest.mark.parametrize("cadastro_uf,servico_uf", [("", "SP"), ("SC", ""), ("", "")])
def test_UF_ausente_de_qualquer_lado_o_CEP_do_cadastro_nao_vai_em_NENHUM_caminho(cadastro_uf, servico_uf):
    local = {"cidade": "Sao Jose", "estado": cadastro_uf, "cep": "88100000",
             "cidade_servico": {"cidade": "SAO JOSE", "uf": servico_uf}}
    assert "cep" not in AD.local_do_servico({"local": local})                  # o DOM (era True: rt127_probe2)
    assert _cep_no_dom(local) == []                                            # e a tela não recebe o CEP
    assert AF.cep_do_servico(local) == ("", "ausente")                        # o API-first


def test_CONTROLE_mesma_cidade_e_mesma_UF_o_CEP_vai_nos_dois_caminhos():
    local = {"cidade": "Sao Jose", "estado": "SC", "cep": "88100000",
             "cidade_servico": {"cidade": "SÃO JOSÉ", "uf": "SC"}}
    assert AD.local_do_servico({"local": local})["cep"] == "88100000"
    assert [f["valor"] for f in _cep_no_dom(local)] == ["88100000"]
    assert AF.cep_do_servico(local) == ("88100000", "cadastro_na_mesma_cidade")
    # o CEP do PRÓPRIO serviço vence, nos dois
    outro = {**local, "cidade_servico": {"cidade": "Joinville", "uf": "SC", "cep": "89201-000"}}
    assert AD.local_do_servico({"local": outro})["cep"] == AF.cep_do_servico(outro)[0] == "89201000"
