# -*- coding: utf-8 -*-
"""SPEC-131-0-B3 · F1 — O FIO: o WhatsApp PAREADO (a linha conectada da pessoa NAQUELA corretora) é o número de
trabalho; sem ele, o DIGITADO confirmado; sem nada, nenhum (D-1310B3-01/04).

    integrations (purpose='linha_do_usuario', dono, paired_phone_e164, is_active, channel_status)
      → perfil_do_membro.numero_de_trabalho(db, company_id, user_id) → {e164, origem}
          ├ proposta.membro_para_o_cliente → publicar_renovacao → HTML servido → "Quero renovar" → wa.me/<PAREADO>
          ├ perfil_do_membro.ler_perfil → whatsapp_trabalho.efetivo
          └ perfil_do_membro.situacao_da_equipe → whatsapp_trabalho_origem / _confirmado

🔴 Dublê SÓ na borda (o cliente supabase em memória — o dos testes da 131-B, reutilizado, não copiado); o MOTOR é o do
produto: `estado.linha_do_dono`, `numero_de_trabalho`, `membro_para_o_cliente`, `publicar_renovacao` e o HTML que o
`abrir_compartilhado` serve (CLAUDE.md §9.4). Isolamento com DUAS corretoras e a MESMA pessoa nas duas (§7).
A LINHA DE CONTROLE (sem a linha → o digitado) prova que o guarda consegue diferir (§9.3).
⛔ Números inventados (💭), nomes fictícios (§13.9). Nada é enviado; nada vai ao banco real.
Rodar: cd backend && python -m pytest tests/test_spec1310b3_o_fio.py -q -p no:cacheprovider
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app.services import perfil_do_membro as PM  # noqa: E402
from app.services.multicalculo import proposta as PROP  # noqa: E402
from app.services.linha_do_usuario import estado as EST  # noqa: E402
import test_spec131b_a_pagina_de_renovacao as REN  # noqa: E402
from test_spec131b_perfil_e_ausencia import (A, A1, B, HOJE, NUMERO, NUMERO_B,  # noqa: E402
                                             banco_de_duas_corretoras)

X = NUMERO                       # 💭 o DIGITADO confirmado da pessoa_a1 na corretora_a
Y = "+5511987650001"             # 💭 o PAREADO da linha da pessoa_a1 na corretora_a
Z = NUMERO_B                     # 💭 o DIGITADO confirmado da mesma pessoa_a1 na corretora_b
CONFIRMADO = "2026-10-12T10:00:00+00:00"


def _dig(e164):
    return e164.lstrip("+")


def _linha(cid, uid, *, numero=Y, ativa=True, status="connected", iid="11111111-0000-4000-8000-0000000000l1"):
    return {"id": iid, "company_id": cid, "owner_user_id": uid, "provider": "evolution-go",
            "purpose": "linha_do_usuario", "instance_id": f"linha-{iid[:8]}", "identifier": None, "is_active": ativa,
            "channel_status": status, "paired_phone_e164": numero, "paired_jid": None, "linha_jid": None,
            "linha_lid": None, "linha_conectada_em": "2026-10-15T22:50:00+00:00", "linha_desconectada_em": None,
            "linha_motivo": None, "descartadas_total": 0, "last_seen_at": None, "created_at": "2026-10-15T22:49:00+00:00",
            "token": "cifrado-nunca-sai", "base_url": "https://go.exemplo.test"}


def mundo(*, linha=True, digitado=X, confirmado=True, **kw_linha):
    """As duas corretoras da 131-B: a pessoa_a1 com o digitado X na A (+ a linha conectada Y) e o Z na B."""
    banco = banco_de_duas_corretoras()
    m = next(x for x in banco.tabelas["company_members"] if x["company_id"] == A and x["user_id"] == A1)
    m.update(whatsapp_trabalho_e164=digitado, whatsapp_trabalho_confirmado_em=CONFIRMADO if confirmado else None)
    if linha:
        banco.tabelas["integrations"].append(_linha(A, A1, **kw_linha))
    return banco


def _situacao(banco, cid):
    return {p["user_id"]: p for p in PM.situacao_da_equipe(banco, cid, hoje=HOJE)["pessoas"]}


# =====================================================================================================================
# 1. o fio: a linha conectada da A vira o número de trabalho na A — nos TRÊS leitores
# =====================================================================================================================
def test_o_fio_a_linha_conectada_e_o_numero_de_trabalho_nos_tres_leitores(monkeypatch):
    monkeypatch.delenv(EST.CHAVE_LIGADA, raising=False)          # D-1310B3-04: o número é da pessoa, não da chave
    banco = mundo()
    assert PM.numero_de_trabalho(banco, A, A1) == {"e164": Y, "origem": "linha"}
    assert PROP.membro_para_o_cliente(banco, A, A1)["whatsapp"] == _dig(Y)
    efetivo = PM.ler_perfil(banco, A, A1, hoje=HOJE)["whatsapp_trabalho"]["efetivo"]
    assert efetivo == {"numero": Y, "origem": "linha"}
    p = _situacao(banco, A)[A1]
    assert p["whatsapp_trabalho_origem"] == "linha" and p["whatsapp_trabalho_confirmado"] is True
    assert Y not in json.dumps(PM.situacao_da_equipe(banco, A, hoje=HOJE))     # ⛔ o número nunca sai da situação


def test_isolamento_a_linha_da_a_nunca_vira_o_numero_da_b():
    banco = mundo()
    assert PM.numero_de_trabalho(banco, B, A1) == {"e164": Z, "origem": "digitado"}
    assert PROP.membro_para_o_cliente(banco, B, A1)["whatsapp"] == _dig(Z)
    assert PM.ler_perfil(banco, B, A1, hoje=HOJE)["whatsapp_trabalho"]["efetivo"] == {"numero": Z, "origem": "digitado"}
    assert _situacao(banco, B)[A1]["whatsapp_trabalho_origem"] == "digitado"


def test_a_linha_de_outra_corretora_nao_vale_mesmo_sem_digitado_aqui():
    banco = mundo(linha=False)
    banco.tabelas["integrations"].append(_linha(B, A1))                   # a linha é da B; pergunta-se pela A
    m = next(x for x in banco.tabelas["company_members"] if x["company_id"] == A and x["user_id"] == A1)
    m.update(whatsapp_trabalho_e164=None, whatsapp_trabalho_confirmado_em=None)
    assert PM.numero_de_trabalho(banco, A, A1) == {"e164": None, "origem": None}
    assert "whatsapp" not in PROP.membro_para_o_cliente(banco, A, A1)
    assert _situacao(banco, A)[A1]["whatsapp_trabalho_confirmado"] is False


@pytest.mark.parametrize("caso,kw", [
    ("desconectada", {"status": "disconnected"}),
    ("pareando", {"status": "connecting"}),
    ("inativa", {"ativa": False}),
    ("sem_numero", {"numero": None}),
])
def test_linha_que_nao_esta_conectada_cai_no_digitado(caso, kw):
    banco = mundo(**kw)
    assert PM.numero_de_trabalho(banco, A, A1) == {"e164": X, "origem": "digitado"}, caso
    assert PROP.membro_para_o_cliente(banco, A, A1)["whatsapp"] == _dig(X)
    assert _situacao(banco, A)[A1]["whatsapp_trabalho_origem"] == "digitado"


# =====================================================================================================================
# 2. a LINHA DE CONTROLE e as bordas da regra
# =====================================================================================================================
def test_controle_sem_a_linha_o_numero_e_o_digitado():
    banco = mundo(linha=False)
    assert PM.numero_de_trabalho(banco, A, A1) == {"e164": X, "origem": "digitado"}
    assert PROP.membro_para_o_cliente(banco, A, A1)["whatsapp"] == _dig(X)
    assert PM.ler_perfil(banco, A, A1, hoje=HOJE)["whatsapp_trabalho"]["efetivo"] == {"numero": X, "origem": "digitado"}


def test_digitado_sem_confirmacao_nao_vale_mas_a_linha_vale():
    sem_nada = mundo(linha=False, confirmado=False)
    assert PM.numero_de_trabalho(sem_nada, A, A1) == {"e164": None, "origem": None}
    assert "whatsapp" not in PROP.membro_para_o_cliente(sem_nada, A, A1)
    so_linha = mundo(confirmado=False)
    assert PM.numero_de_trabalho(so_linha, A, A1) == {"e164": Y, "origem": "linha"}
    assert _situacao(so_linha, A)[A1]["whatsapp_trabalho_confirmado"] is True


def test_quem_saiu_da_corretora_nao_tem_numero_nem_com_linha():
    banco = mundo()
    m = next(x for x in banco.tabelas["company_members"] if x["company_id"] == A and x["user_id"] == A1)
    m["status"] = "inactive"
    assert PM.numero_de_trabalho(banco, A, A1) == {"e164": None, "origem": None}
    assert PROP.membro_para_o_cliente(banco, A, A1) == {}


def test_a_leitura_da_linha_que_falha_cai_no_digitado_sem_dado_pessoal_no_log(monkeypatch, caplog):
    def _quebra(*_a, **_k):
        raise RuntimeError(f"timeout lendo {Y}")

    monkeypatch.setattr(EST, "linha_do_dono", _quebra)
    banco = mundo()
    with caplog.at_level(logging.DEBUG):
        assert PM.numero_de_trabalho(banco, A, A1) == {"e164": X, "origem": "digitado"}
        assert PROP.membro_para_o_cliente(banco, A, A1)["whatsapp"] == _dig(X)
        PM.ler_perfil(banco, A, A1, hoje=HOJE)
        _situacao(banco, A)
    log = caplog.text
    assert _dig(Y)[-8:] not in log and _dig(X)[-8:] not in log


def test_sem_as_colunas_do_digitado_a_linha_ainda_confirma_e_o_resto_fica_none():
    banco = mundo()
    banco.colunas_ausentes["company_members"] = {"whatsapp_trabalho_e164"}
    por = _situacao(banco, A)
    assert por[A1]["whatsapp_trabalho_confirmado"] is True and por[A1]["whatsapp_trabalho_origem"] == "linha"
    outros = [p for u, p in por.items() if u != A1]
    assert outros and {p["whatsapp_trabalho_confirmado"] for p in outros} == {None}


# =====================================================================================================================
# 3. o fio ATÉ o HTML servido: o "Quero renovar" da página de renovação abre o PAREADO
# =====================================================================================================================
WHATS_PAREADO_DO_DONO = "5548988887777"          # 💭 o pareado do DONO da renovação (o digitado é REN.WHATS_DONO)


def _com_linha(m, cid, **kw):
    m.banco.semear("integrations", _linha(cid, REN.DONO, numero="+" + WHATS_PAREADO_DO_DONO, **kw))


def test_o_quero_renovar_servido_abre_o_pareado(monkeypatch):
    m = REN.mundo(monkeypatch)
    _com_linha(m, m.beta)
    r = REN._publicar(m)
    dock = REN._dock(REN._servido(m, r["token"]))
    assert f"https://wa.me/{WHATS_PAREADO_DO_DONO}?text=" in dock and REN.WHATS_DONO not in dock
    assert r["modelo"]["renovacao"]["fechar_com"] == "dono"


@pytest.mark.parametrize("caso", ["sem_linha", "linha_de_outra_corretora", "linha_desconectada"])
def test_controle_do_html_sem_linha_conectada_desta_corretora_e_o_digitado(monkeypatch, caso):
    m = REN.mundo(monkeypatch)
    if caso == "linha_de_outra_corretora":
        _com_linha(m, m.alfa)
    elif caso == "linha_desconectada":
        _com_linha(m, m.beta, status="disconnected")
    r = REN._publicar(m)
    doc = REN._servido(m, r["token"])
    assert f"https://wa.me/{REN.WHATS_DONO}?text=" in REN._dock(doc) and WHATS_PAREADO_DO_DONO not in doc


# =====================================================================================================================
# D-1310B3-10 — o pareado vem do JID (📊 15/10: 13 caracteres, sem o 9 do celular) e sai no formato OFICIAL
# =====================================================================================================================
def test_o_pareado_sem_o_nove_ganha_o_nove_e_o_fixo_nao():
    celular_jid = "+551187650001"      # 💭 celular no formato antigo do JID (8 dígitos começando em 8)
    banco = mundo(numero=celular_jid)
    assert PM.numero_de_trabalho(banco, A, A1) == {"e164": "+5511987650001", "origem": "linha"}
    # CONTROLE: um FIXO (começa em 3) não ganha 9 — o guarda consegue diferir
    banco = mundo(numero="+551133334444")
    assert PM.numero_de_trabalho(banco, A, A1) == {"e164": "+551133334444", "origem": "linha"}
