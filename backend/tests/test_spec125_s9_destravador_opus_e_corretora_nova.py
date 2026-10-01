# -*- coding: utf-8 -*-
"""SPEC-125 S9 — D8 (Opus 5.5 na 2ª opinião e na reserva do destravador) e D9 (corretora NOVA nasce
com o destravador ligado), pela migration `20261001_06` + o snapshot regerado do banco.

O gatilho em si é provado no banco pelo VERIFY da migration (corretora + agente de teste num bloco
desfeito). Aqui: a ROTA que o resolvedor do produto entrega (snapshot = a verdade do banco quando ele
cai) e a FORMA do gatilho (nunca sobrescreve, sem nome/id de corretora, DEFINER)."""
from __future__ import annotations

import json
import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
SNAP = json.loads((BACKEND / "app" / "factories" / "modelos_snapshot.json").read_text(encoding="utf-8"))
MIGRATION = BACKEND / "supabase" / "migrations" / "20261001_06_spec125_destravador_opus_e_corretora_nova.sql"


def _rota(papel):
    r = SNAP["papeis"][papel]
    return (r["provider"], r["modelo_primario"], r["esforco"], r["provider_reserva"], r["modelo_reserva"],
            r["esforco_reserva"])


def test_D8_a_segunda_opiniao_e_o_opus_5_5_e_a_reserva_continua_de_outro_provedor():
    assert _rota("destravador_segunda") == ("anthropic", "claude-opus-5-5", None, "openai", "gpt-6.1-sol", "high")


def test_D8_a_reserva_do_destravador_e_o_opus_5_5_e_o_primario_nao_mudou():
    assert _rota("destravador") == ("openai", "gpt-6.1-sol", "high", "anthropic", "claude-opus-5-5", None)


def test_D8_quem_decide_e_quem_confere_sao_de_provedores_diferentes_nos_dois_caminhos():
    """D3 da SPEC-123: o primário do destravador e o primário da 2ª opinião são de provedores
    diferentes; e a reserva de cada um é do OUTRO provedor (a 2ª opinião troca de lado junto)."""
    d, s = SNAP["papeis"]["destravador"], SNAP["papeis"]["destravador_segunda"]
    assert d["provider"] != s["provider"]
    assert d["provider"] != d["provider_reserva"] and s["provider"] != s["provider_reserva"]


def _funcao() -> str:
    sql = MIGRATION.read_text(encoding="utf-8")
    m = re.search(r"create or replace function public\.tg_destravador_nasce_ligado\(\).*?end \$\$;", sql, re.S)
    assert m, "a função do gatilho sumiu da migration"
    return m.group(0)


def test_D9_o_gatilho_nunca_sobrescreve_e_le_a_lista_da_propria_cerebro_modos():
    f = _funcao()
    assert "on conflict (company_id, insurer_key, ramo) do nothing" in f
    assert "do update" not in f
    assert re.search(r"from public\.cerebro_modos where modo = 'on'", f), "a lista de seguradoras não é a da tabela"
    assert "security definer" in f and "set search_path" in f


def test_D9_nenhum_nome_nem_id_de_corretora_no_gatilho():
    """CLAUDE.md §13.9: nada de corretora como constante — nem uuid, nem lista de seguradoras escrita."""
    f = _funcao()
    assert not re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", f)
    assert not re.search(r"values\s*\(\s*'(?:allianz|porto|hdi|yelum)'", f, re.I)


def test_D9_CONTROLE_o_guarda_da_forma_consegue_ficar_vermelho():
    """§9.3: o guarda acima pega um gatilho que SOBRESCREVE (o `do update` da 20261001_02)."""
    mutada = _funcao().replace("do nothing", "do update set modo = excluded.modo")
    assert "do update" in mutada and "on conflict (company_id, insurer_key, ramo) do nothing" not in mutada
