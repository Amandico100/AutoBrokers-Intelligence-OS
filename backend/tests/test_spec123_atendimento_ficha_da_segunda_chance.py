# -*- coding: utf-8 -*-
"""SPEC-123 F7 (costura do gerente) — a segunda chance não trava a fase da ficha.

A segunda chance devolve SEGUNDA_CHANCE_DO_HANDOFF e ninguém é chamado; mas
`nodes._gravar_ficha_do_turno` marca `fase='com_humano'` a QUALQUER retorno de
`request_human_agent` (nodes.py ~2262). A fase é pegajosa (`derivar_fase`) e o
prompt mostra "Fase: com_humano" ao modelo no turno seguinte.

Copiar para backend/tests/test_spec123_atendimento_ficha_da_segunda_chance.py
junto com o conserto de 3 linhas em nodes.py. Hoje: 1 VERMELHO (o defeito), 1 verde (controle).
"""
import asyncio
import os
import sys
import types

import pytest

from tests.test_spec123_atendimento_segunda_chance import (  # noqa: E402
    X, _banco, _conversa, _Embrulho, borda)  # noqa: F401


def _fase_depois(resultado, monkeypatch):
    import app.agents.nodes as N
    import app.core.database as dbreal

    cid = "c-fase-0001"
    b = _banco(_conversa(cid))
    monkeypatch.setattr(dbreal, "get_supabase_client", lambda: _Embrulho(b))
    asyncio.new_event_loop().run_until_complete(N._gravar_ficha_do_turno(
        {"company_id": X, "session_id": "ses-" + cid}, "request_human_agent",
        {"reason": "não sei responder"}, resultado))
    return ((b.tabelas["conversations"][0].get("ficha_atendimento")) or {}).get("fase")


def test_a_segunda_chance_nao_trava_a_fase_em_com_humano(borda, monkeypatch):
    from app.agents.tools.human_handoff import SEGUNDA_CHANCE_DO_HANDOFF
    assert _fase_depois(SEGUNDA_CHANCE_DO_HANDOFF, monkeypatch) != "com_humano"


def test_controle_handoff_de_verdade_trava_a_fase(borda, monkeypatch):
    from app.agents.honestidade_do_handoff import SUCESSO_DO_HANDOFF
    assert _fase_depois(SUCESSO_DO_HANDOFF, monkeypatch) == "com_humano"
