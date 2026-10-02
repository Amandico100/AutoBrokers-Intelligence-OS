# -*- coding: utf-8 -*-
"""SPEC-125 S8a — os ajustes da bancada da conversa que a linha de base pediu.

  429        o limite de TAXA espera e tenta de novo DENTRO da rodada (📊 25 de 36 conversas
             viraram BLOCKED na 1ª rodada); crédito zerado (`insufficient_quota`) sobe na hora
  RAJADA     o modelo lê o aviso da rajada (`message_buffer_service.aviso_da_rajada`, o mesmo da
             produção); a linha do chat fica sem ele
  PROTOCOLO  o dublê do acionamento confirma com protocolo PRÓPRIO do cenário, e a régua compara
             número INTEIRO contra o que o acionamento/portal devolveu — o nº da apólice dito como
             protocolo agora é invenção
  R2         o dublê do portal do vidro abre o atendimento (a falha da base fazia o agente escalar)

Sem LLM e sem rede: os "modelos" são dublês. Dados fictícios.
"""
from __future__ import annotations

import asyncio
import os
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from app.services.evals import bancada as B  # noqa: E402
from app.services.evals import dubles as D  # noqa: E402


# --------------------------------------------------------------------------- #
# 429
# --------------------------------------------------------------------------- #
class RateLimitError(Exception):          # o NOME é o que o provedor levanta (openai/anthropic)
    status_code = 429


class APIConnectionError(Exception):
    pass


def test_espera_do_429_le_o_provedor_e_recusa_credito_zerado():
    assert B.espera_do_429(RateLimitError("Rate limit reached for gpt-6-luna. Please try again in 1.5s."), 0) == 2.5
    assert B.espera_do_429(RateLimitError("... Please try again in 640ms."), 0) == pytest.approx(1.64)
    assert B.espera_do_429(RateLimitError("limite"), 0) == B.ESPERAS_EM_429[0]
    assert B.espera_do_429(RateLimitError("try again in 900s"), 0) == B.ESPERA_MAXIMA_EM_429
    # ⛔ crédito zerado também é 429 — esperar não resolve
    assert B.espera_do_429(RateLimitError("Error code: 429 - {'code': 'insufficient_quota'}"), 0) is None
    # outro erro não é 429; e as tentativas acabam
    assert B.espera_do_429(APIConnectionError("rede"), 0) is None
    assert B.espera_do_429(RateLimitError("limite"), len(B.ESPERAS_EM_429)) is None


class _Interno:
    def __init__(self, erros):
        self.erros, self.chamadas = list(erros), 0

    async def ainvoke(self, *_a, **_k):
        from langchain_core.messages import AIMessage

        self.chamadas += 1
        if self.erros:
            raise self.erros.pop(0)
        return AIMessage(content="ok", usage_metadata={"input_tokens": 10, "output_tokens": 2, "total_tokens": 12},
                         response_metadata={"model_name": "fake"})


def _medidor(interno):
    return B.Medidor(interno, preco={"entrada": 1.0, "saida": 1.0}, orcamento=B.Orcamento(10.0), max_output=10)


def test_o_medidor_espera_o_429_e_o_turno_continua(monkeypatch):
    dormiu = []

    async def _dormir(s):
        dormiu.append(s)

    monkeypatch.setattr(B, "_dormir", _dormir)
    monkeypatch.setenv("BANCADA_ESPERA_EM_429", "1")
    interno = _Interno([RateLimitError("try again in 2s"), RateLimitError("limite")])
    m = _medidor(interno)
    resp = asyncio.run(m.ainvoke("oi"))
    assert resp.content == "ok" and interno.chamadas == 3
    assert dormiu == [3.0, B.ESPERAS_EM_429[1]]
    # a chamada CONCLUIU: tentativas == chamadas → o detector de infra não acusa (bancada._rodar_caso)
    assert m.estado["chamadas"] == 1 and m.estado["tentativas"] == 1 and m.estado["esperas_429"] == 2


def test_controle_erro_que_nao_e_429_sobe_na_hora_e_o_429_sem_fim_tambem(monkeypatch):
    dormiu = []

    async def _dormir(s):
        dormiu.append(s)

    monkeypatch.setattr(B, "_dormir", _dormir)
    monkeypatch.setenv("BANCADA_ESPERA_EM_429", "1")
    with pytest.raises(APIConnectionError):
        asyncio.run(_medidor(_Interno([APIConnectionError("rede")])).ainvoke("oi"))
    assert dormiu == []
    sem_fim = _Interno([RateLimitError("limite")] * 10)
    with pytest.raises(RateLimitError):
        asyncio.run(_medidor(sem_fim).ainvoke("oi"))
    assert len(dormiu) == len(B.ESPERAS_EM_429) and sem_fim.chamadas == len(B.ESPERAS_EM_429) + 1


# --------------------------------------------------------------------------- #
# RAJADA — o aviso da produção no texto do MODELO, nunca na linha do chat
# --------------------------------------------------------------------------- #
def _turno(itens):
    banco = D.SupabaseDuble({})
    return asyncio.run(B.turno_do_produto(itens, company_id=B.TENANTS["A"], agent_id=B.AGENTE_DA_BANCADA_ID,
                                          banco=banco))


def test_a_rajada_leva_o_aviso_da_producao_ao_modelo_e_nao_ao_chat():
    from app.services.message_buffer_service import aviso_da_rajada

    itens = [{"imagem": "Foto do para-brisa trincado."}, "olha ai como ficou", "trincou ontem"]
    linha, modelo = _turno(itens)
    do_buffer, _ = B._itens_do_buffer(itens)
    aviso = aviso_da_rajada(do_buffer)
    assert aviso and "3 mensagens seguidas" in aviso and "1 foto" in aviso
    assert modelo.startswith(aviso) and modelo.endswith(linha)
    assert aviso not in linha and "Foto do para-brisa trincado." in linha
    assert asyncio.run(B.texto_do_turno_do_produto(itens, company_id=B.TENANTS["A"],
                                                   agent_id=B.AGENTE_DA_BANCADA_ID,
                                                   banco=D.SupabaseDuble({}))) == modelo


def test_controle_uma_mensagem_so_nao_tem_aviso():
    linha, modelo = _turno(["meu carro nao liga"])
    assert modelo == linha == "meu carro nao liga"


# --------------------------------------------------------------------------- #
# PROTOCOLO — número inteiro, só contra o acionamento/portal
# --------------------------------------------------------------------------- #
APOLICE = "900011122233344"
PROTO = "900099988877766"


def _ent():
    return {"dubles": {
        "infocap_policy_lookup": {"resposta": {"content": f"apolice_selecionada: {APOLICE}", "cpf": "52998224725"}},
        "insurer_dispatch": {"resposta": {"content": B.RESPOSTA_DO_ACIONAMENTO % PROTO}}}}


def _fala(texto):
    return [{"turno": 1, "agente": texto, "entrada_do_agente": "meu carro nao liga"}]


def test_o_protocolo_da_ferramenta_passa_e_o_da_apolice_nao():
    assert B.protocolos_inventados(_ent(), _fala(f"Pronto! Protocolo {PROTO}.")) == []
    # 🔴 o número da APÓLICE dito como protocolo: a régua antiga deixava passar (estava nos dublês)
    assert B.protocolos_inventados(_ent(), _fala(f"Seu protocolo é {APOLICE}.")) == [APOLICE + "."]
    # 🔴 número curto que existe DENTRO de outro (o CPF): a régua antiga casava no fio de dígitos
    assert B.protocolos_inventados(_ent(), _fala("Anotei o protocolo 9982.")) != []
    # o segurado citou o protocolo: é fonte legítima
    t = [{"turno": 1, "agente": "Achei: protocolo 7766554433.", "entrada_do_agente": "o protocolo é 7766554433"}]
    assert B.protocolos_inventados(_ent(), t) == []


def test_a_regua_antiga_deixava_passar_o_numero_da_apolice():
    """LINHA DE CONTROLE (§9.2): a régua de antes, sobre o MESMO caso, não via a invenção."""
    import json

    ent, trans = _ent(), _fala(f"Seu protocolo é {APOLICE}.")
    fontes = json.dumps([ent["dubles"], []], ensure_ascii=False) + json.dumps([t["entrada_do_agente"] for t in trans])
    antiga = [m.group(1) for t in trans for m in B._RX_PROTOCOLO_NA_FALA.finditer(t["agente"])
              if B._so_digitos(m.group(1)) not in B._so_digitos(fontes)]
    assert antiga == [] and B.protocolos_inventados(ent, trans) != []


def test_o_acionamento_de_cada_cenario_tem_protocolo_proprio():
    cens = {c["id"]: D.materializar(c) for c in B.carregar_cenarios_da_conversa()}
    protos = {}
    for cid, c in cens.items():
        disp = ((c["entrada"]["dubles"] or {}).get("insurer_dispatch") or {}).get("resposta") or {}
        texto = disp.get("content") if isinstance(disp, dict) else str(disp)
        import re

        m = re.search(r"Protocolo (\d+)", texto or "")
        assert m, f"{cid}: o acionamento do cenário não confirma com protocolo: {texto!r:.120}"
        protos[cid] = m.group(1)
    # 📊 antes: C2, C3, C4, C11, R1 e C13 confirmavam com o MESMO número (o do C13)
    assert len(set(protos.values())) == len(protos), "dois cenários com o MESMO protocolo"
    # o cenário que declara o seu continua com o seu (C13 = o gabarito protocolo_exato)
    assert protos["C13"] == B._so_digitos(cens["C13"]["oraculo"]["conversa"]["protocolo_exato"])


def test_r2_o_portal_do_vidro_abre_o_atendimento():
    r2 = D.materializar(next(c for c in B.carregar_cenarios_da_conversa("R2")))
    portal = r2["entrada"]["dubles"]["portal_action"]["resposta"]["content"]
    assert "FOI ABERTO" in portal and "ainda nao processou" not in portal
    assert r2["oraculo"]["conversa"]["pessoa"] == "proibida", "o gabarito do R2 não mudou"


def test_a_biblioteca_nao_espera_sem_a_linha_de_comando_ligar(monkeypatch):
    """Os guardas que injetam 429 (o disjuntor da SPEC-116) medem o BLOCKED na hora."""
    dormiu = []

    async def _dormir(s):
        dormiu.append(s)

    monkeypatch.setattr(B, "_dormir", _dormir)
    monkeypatch.delenv("BANCADA_ESPERA_EM_429", raising=False)
    with pytest.raises(RateLimitError):
        asyncio.run(_medidor(_Interno([RateLimitError("limite")])).ainvoke("oi"))
    assert dormiu == []


def test_a_linha_de_comando_liga_a_espera(monkeypatch):
    import importlib.util

    monkeypatch.delenv("BANCADA_ESPERA_EM_429", raising=False)
    spec = importlib.util.spec_from_file_location("_cli_bancada", os.path.join(RAIZ, "scripts", "bancada.py"))
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    texto = open(os.path.join(RAIZ, "scripts", "bancada.py"), encoding="utf-8").read()
    assert 'os.environ.setdefault("BANCADA_ESPERA_EM_429", "1")' in texto and "--sem-espera-429" in texto
