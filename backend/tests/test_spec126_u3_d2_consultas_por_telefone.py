# -*- coding: utf-8 -*-
"""SPEC-126 U3 · D2 — o mesmo celular, muitas apólices: UM aviso ao grupo DA corretora (G4).

    D2: o mesmo celular pedindo acionamento ou informação de MAIS DE 2 apólices
    diferentes em 5 dias → aviso ao grupo de suporte DA corretora, SEM bloquear o
    atendimento. Por `company_id`; nada atravessa corretora.
    D-126-C (nota 88): as apólices do PRÓPRIO titular que fala contam como UMA.

Pelo MOTOR (CLAUDE.md §9.4): `nodes.tool_node` REAL → `InfocapPolicyLookupTool._arun`
REAL → `invocation_recorder` REAL grava `tool_invocations` (o gravador ÚNICO; nenhuma
tabela nova) → a consulta seguinte LÊ essas linhas (`consultas_por_telefone`) →
`o_grupo_so_o_que_importa.enviar_ao_grupo` REAL (a porta única). Dublês só na BORDA:
provedor de apólices, banco em memória, Redis em memória, destino do grupo, canal de
WhatsApp (captura o que sairia) e a contagem de `platform_sends`.

🔴 Dois tenants REAIS (dois `company_id`) com o MESMO telefone.
"""
from __future__ import annotations

import asyncio
import json
import types

import pytest

from app.atendimento import consultas_por_telefone as CT
from tests.test_spec126_u3_d1_parente_aciona import (  # noqa: F401 — a borda é fixture
    EMPRESA_A, EMPRESA_B, SESSAO_A, SESSAO_B, borda, consultar_pelo_motor,
    o_que_o_modelo_le, resultado_found)

CPFS = ["52998224725", "11144477735", "39053344705", "71428793860"]   # fictícios, DV válido
APOLICES = ["7000000000011", "7000000000022", "7000000000033", "7000000000044"]


class _RedisDeMentira:
    def __init__(self):
        self.d: dict = {}

    async def set(self, k, v, ex=None, nx=False):
        if nx and k in self.d:
            return None
        self.d[k] = v
        return True

    async def get(self, k):
        return self.d.get(k)

    async def delete(self, *ks):
        for k in ks:
            self.d.pop(k, None)


@pytest.fixture
def grupo(borda, monkeypatch):
    """As bordas do aviso: destino por corretora, canal, Redis e a contagem. Devolve a lista
    de `(destino, texto)` que SAIRIAM."""
    import app.core.redis as R
    import app.services.dispatch_router as DR
    import app.services.integration_service as IS
    import app.services.platform_outbound as PO
    import app.services.whatsapp_service as WS

    enviados: list = []
    redis = _RedisDeMentira()

    async def _redis():
        return redis

    async def _destino(empresa):
        return {"destino": "grupo-da-%s" % empresa}

    async def _contar(*_a, **_k):
        return None

    monkeypatch.setattr(R, "get_async_redis_client", _redis)
    monkeypatch.setattr(DR, "resolver_destino_de_suporte", _destino)
    monkeypatch.setattr(IS, "get_integration_service", lambda *_a, **_k: types.SimpleNamespace(
        get_whatsapp_integration=lambda *_a, **_k: {"id": "integ"}))
    monkeypatch.setattr(WS, "get_whatsapp_service", lambda *_a, **_k: types.SimpleNamespace(
        send_message=lambda alvo, texto, integ, **_k: enviados.append((alvo, texto))))
    monkeypatch.setattr(PO, "record_platform_send", _contar)
    return enviados


def _consulta(prov, i: int, *, empresa=EMPRESA_A, sessao=SESSAO_A, falas=None):
    """A i-ésima apólice distinta, consultada pelo motor com o CPF solto (não dito como "meu")."""
    prov.sequencia.append(resultado_found(APOLICES[i]))
    return consultar_pelo_motor(falas or ["bom dia, preciso de um guincho", CPFS[i]], CPFS[i],
                                empresa=empresa, sessao=sessao)


def _invocacoes(banco, empresa):
    return [l for l in banco.tabelas.get("tool_invocations", []) if l.get("company_id") == empresa]


# =========================================================================== #
# O GRAVADOR ÚNICO é chamado no caminho da consulta — e grava só pseudônimo
# =========================================================================== #
def test_o_recorder_de_tool_invocations_grava_o_rastro_da_consulta(borda, grupo):
    banco, prov = borda
    _consulta(prov, 0)
    linhas = _invocacoes(banco, EMPRESA_A)
    assert len(linhas) == 1, "o tool_node não chamou o gravador de tool_invocations"
    linha = linhas[0]
    assert linha["trace_id"].startswith(SESSAO_A + "|"), linha["trace_id"]
    rastro = (linha.get("output_summary") or {}).get(CT.CHAVE_DO_RASTRO)
    assert rastro and rastro["apolice_final"] == APOLICES[0][-4:], linha.get("output_summary")
    bruto = json.dumps(linha, default=str)
    assert CPFS[0] not in bruto and APOLICES[0] not in bruto, "documento CRU em tool_invocations"


def test_o_rastro_nao_aceita_documento_cru():
    """A lista fechada confere a FORMA — um CPF de 11 dígitos não é hash nem final."""
    assert CT.rastro_seguro({"apolice_hash": CPFS[0], "apolice_final": CPFS[0]}) is None
    r = CT.rastro_seguro({"apolice_hash": "a" * 24, "apolice_final": CPFS[0], "cpf": CPFS[0]})
    assert r == {"apolice_hash": "a" * 24, "titular_proprio": False, "apolice_final": ""}


# =========================================================================== #
# G4 — 2 → nenhum aviso; a 3ª → UM aviso, ao grupo DA corretora; a 4ª → não repete
# =========================================================================== #
def test_g4_a_terceira_apolice_distinta_avisa_uma_vez_o_grupo_da_dona(borda, grupo):
    banco, prov = borda
    _consulta(prov, 0)
    _consulta(prov, 1)
    assert grupo == [], "2 apólices distintas NÃO avisam (D2: mais de 2)"

    saida = _consulta(prov, 2)
    assert len(grupo) == 1, grupo
    destino, texto = grupo[0]
    assert destino == "grupo-da-%s" % EMPRESA_A
    for apolice in APOLICES[:3]:
        assert "final %s" % apolice[-4:] in texto, texto
        assert apolice not in texto, "apólice INTEIRA no aviso"
    for cpf in CPFS:
        assert cpf not in texto, "CPF no aviso ao grupo"
    assert "NÃO foi bloqueado" in texto
    # ⛔ o atendimento NÃO foi bloqueado: a 3ª consulta respondeu normalmente, com a apólice
    assert saida.get("infocap_policy_context"), "a 3ª consulta tem de seguir normal"
    assert APOLICES[2] in o_que_o_modelo_le(saida), "o titular da 3ª consulta perdeu a resposta"

    _consulta(prov, 3)
    assert len(grupo) == 1, "a mesma janela não gera um segundo aviso (idempotência)"


def test_g4_o_mesmo_titular_com_tres_apolices_nao_avisa(borda, grupo):
    """D-126-C: "meu cpf é…" + auto, casa e vida do MESMO titular = UMA."""
    _, prov = borda
    for i in range(3):
        prov.sequencia.append(resultado_found(APOLICES[i]))
        consultar_pelo_motor(["preciso de ajuda com o meu seguro", f"meu cpf é {CPFS[0]}"], CPFS[0])
    assert grupo == [], grupo


def test_g4_dois_tenants_o_mesmo_telefone_nao_se_somam(borda, grupo):
    """🔴 CLAUDE.md §7: A tem 2, B tem 1 → B NÃO vê A. A 3ª de A avisa SÓ o grupo de A."""
    banco, prov = borda
    _consulta(prov, 0)
    _consulta(prov, 1)
    _consulta(prov, 2, empresa=EMPRESA_B, sessao=SESSAO_B)
    assert grupo == [], "a contagem de B somou as consultas de A: %r" % (grupo,)
    assert len(_invocacoes(banco, EMPRESA_B)) == 1 and len(_invocacoes(banco, EMPRESA_A)) == 2

    _consulta(prov, 3)
    assert [d for d, _t in grupo] == ["grupo-da-%s" % EMPRESA_A], grupo


def test_g4_falha_do_aviso_nao_derruba_o_turno(borda, grupo, monkeypatch):
    import app.services.whatsapp_service as WS

    def _explode(*_a, **_k):
        raise RuntimeError("canal fora do ar")

    monkeypatch.setattr(WS, "get_whatsapp_service", lambda *_a, **_k: types.SimpleNamespace(
        send_message=_explode))
    _, prov = borda
    for i in range(3):
        saida = _consulta(prov, i)
    assert saida.get("infocap_policy_context"), "o turno caiu junto com o aviso"
    assert "nao consegui consultar" not in o_que_o_modelo_le(saida).lower()


# =========================================================================== #
# A decisão PURA — a régua do D2
# =========================================================================== #
def _r(apolice=None, titular=None, proprio=False, final=""):
    return {"apolice_hash": apolice, "titular_hash": titular, "titular_proprio": proprio,
            "apolice_final": final}


@pytest.mark.parametrize("anteriores,atual,avisa,distintas", [
    ([], _r("a" * 24), False, 1),
    ([_r("a" * 24)], _r("b" * 24), False, 2),
    ([_r("a" * 24), _r("b" * 24)], _r("c" * 24), True, 3),
    ([_r("a" * 24), _r("a" * 24)], _r("a" * 24), False, 1),             # a MESMA, 3 vezes
    ([_r("a" * 24, "f" * 24, True), _r("b" * 24, "f" * 24, True)],
     _r("c" * 24, "f" * 24, True), False, 1),                            # o próprio titular
    ([_r("a" * 24), _r("b" * 24)], None, False, 2),                      # consulta sem apólice
    # o acionamento (sem a marca de próprio) da apólice que a consulta disse "minha" = a MESMA
    ([_r("a" * 24, "f" * 24, True), _r("b" * 24, "f" * 24, True)],
     _r("a" * 24, "f" * 24, False), False, 1),
    ([_r("a" * 24, "f" * 24, True), _r("b" * 24, "f" * 24, True)],
     _r("c" * 24, None, False), False, 2),                                # outra pessoa: soma
])
def test_decidir(anteriores, atual, avisa, distintas):
    d = CT.decidir([{"rastro": r, "quando": "2026-10-0%dT10:00:00+00:00" % (i + 1)}
                    for i, r in enumerate(anteriores)], atual)
    assert (d["avisar"], d["distintas"]) == (avisa, distintas), d


def test_as_constantes_sao_as_da_D2():
    assert CT.LIMITE_DE_APOLICES == 2 and CT.JANELA_DIAS == 5
    fonte = open(CT.__file__, encoding="utf-8").read()
    for nome in ("LIMITE_DE_APOLICES = 2", "JANELA_DIAS = 5"):
        antes = fonte[: fonte.index(nome)].splitlines()[-3:]
        assert any("constante_justificada" in l and "D2" in l for l in antes), (nome, antes)


def test_a_mesma_apolice_tem_pseudonimos_diferentes_em_duas_corretoras(borda):
    a = CT.rastro_da_apolice(EMPRESA_A, documento=CPFS[0], numero_apolice=APOLICES[0])
    b = CT.rastro_da_apolice(EMPRESA_B, documento=CPFS[0], numero_apolice=APOLICES[0])
    assert a["apolice_hash"] != b["apolice_hash"] and a["titular_hash"] != b["titular_hash"]
    assert asyncio.run(CT.conferir_e_avisar(None, company_id="", session_id=SESSAO_A,
                                            rastro=a))["avisou"] is False
