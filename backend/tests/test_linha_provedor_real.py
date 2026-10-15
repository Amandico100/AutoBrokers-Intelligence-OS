"""15/10 (canário do Founder) — a linha do usuário tem de montar o PROVEDOR REAL, não só o dublê.

📊 O que aconteceu: o pareamento funcionou, mas as boas-vindas e toda resposta morriam com `ProviderConfigError` — a
leitura da linha (`estado._CAMPOS`) não trazia `base_url`, e o `EvolutionGoProvider` exige `base_url` e `token`. Os testes da
SPEC-131-0-B2 não sentiam porque o provedor era dublê. Este guarda monta o provedor REAL a partir de uma linha lida só com
as colunas que `estado` pede (o mesmo recorte do banco) e fica VERMELHO se faltar o que o provedor exige.
"""
from __future__ import annotations

import pytest

from app.services.linha_do_usuario import estado as E
from app.services.whatsapp.exceptions import ProviderConfigError
from app.services.whatsapp.providers.evolution_go import EvolutionGoProvider

_LINHA_DO_BANCO = {
    "id": "11111111-1111-4111-8111-111111111111", "company_id": "22222222-2222-4222-8222-222222222222",
    "owner_user_id": "33333333-3333-4333-8333-333333333333", "provider": "evolution-go", "purpose": "linha_do_usuario",
    "instance_id": "ab-lu-teste", "identifier": "ab-lu-teste", "is_active": True, "channel_status": "connected",
    "paired_phone_e164": "+5511900000001", "paired_jid": "5511900000001:2@s.whatsapp.net", "token": "tok-de-teste",
    "base_url": "https://go.exemplo.invalid", "webhook_token_hash": "x", "agent_id": None,
}


def _so_as_colunas_que_estado_le(linha: dict) -> dict:
    campos = {c.strip() for c in E._CAMPOS.split(",")}
    return {k: v for k, v in linha.items() if k in campos}


def test_a_linha_crua_traz_o_que_o_provedor_real_exige():
    lida = _so_as_colunas_que_estado_le(_LINHA_DO_BANCO)
    assert "base_url" in lida and "token" in lida, "estado._CAMPOS não lê base_url/token — o provedor real não monta"
    EvolutionGoProvider(lida)  # não pode levantar ProviderConfigError


def test_linha_de_controle_sem_base_url_o_provedor_real_recusa():
    # §9.3: prova que o guarda CONSEGUE ficar vermelho — sem base_url o provedor real recusa
    sem = {k: v for k, v in _LINHA_DO_BANCO.items() if k != "base_url"}
    with pytest.raises(ProviderConfigError):
        EvolutionGoProvider(sem)
