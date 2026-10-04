# -*- coding: utf-8 -*-
"""G1 — nenhuma fixture do Agger vaza (SPEC-128 U1). Lê SÓ a fixture: roda em
qualquer máquina, sem o intake.

Para TODA fixture em `backend/tests/fixtures/agger/`:
  1. `tem_vazamento(...) == []` em toda profundidade (o redator ÚNICO);
  2. todo caminho de folha ⊂ a lista branca (`leitor_agger.lista_branca_do_arquivo`);
  3. nenhuma chave de identidade de conta ou de credencial;
  4. nenhuma razão social de pessoa jurídica que não seja seguradora conhecida.

🔴 LINHAS DE CONTROLE (CLAUDE.md §9.3): cópias MUTADAS em memória TÊM de
reprovar — `"senha":"x"` aninhado · um CPF · um caminho fora da lista · um nome
de corretora — e a fixture limpa TEM de passar. Sem isso o guarda é carimbo.
"""
from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from portal_worker.redaction import tem_vazamento  # noqa: E402
from portal_worker.multicalculo.leitor_agger import (  # noqa: E402
    caminho_permitido, caminhos_de, lista_branca_do_arquivo,
)

FIX = BACKEND / "tests" / "fixtures" / "agger"
FIXTURES = sorted(p for p in FIX.glob("*.json") if p.name != "MANIFESTO.json")

# chaves que NUNCA aparecem numa fixture, em nenhuma profundidade
CHAVES_PROIBIDAS = {
    "login", "senha", "loginws", "senhaws", "usuario", "usuarioid", "corretoraid",
    "corretora", "customername", "customerip", "customerid", "authorization", "token",
    "susep", "portosusep", "segsusep", "email_usuario", "idintegracaocfg", "razaosocial",
    "cnpj", "codcorretor", "codigocorretor", "bradescocodcorretor", "libertycodigocorretor",
}
# palavras de seguradora conhecidas — "Seguros"/"S.A." ao lado delas é rótulo de produto
SEGURADORAS_CONHECIDAS = (
    "porto", "itau", "mitsui", "sumitomo", "azul", "aliro", "allianz", "bradesco", "hdi",
    "mapfre", "tokio", "zurich", "liberty", "yelum", "sura", "ezze", "darwin", "youse",
    "suhai", "sancor", "sompo", "justos", "pier", "generali", "sulamerica", "mobi",
)
CATALOGO_DE_SEGURADORAS = "seguradoras_renovacao[].corpo[].nome"
RE_PJ = re.compile(r"(?i)\b(ltda|eireli|corretora|corretagem|s\.\s?a\.|s/a)(?![a-z])")
# "Fulano Seguros" (nome próprio + "Seguros", maiúsculo) — "não oferecemos seguro" não é razão social
RE_SEGUROS = re.compile(r"\b[A-Z][\w&.-]*(?:\s+(?:de\s+)?[A-Z][\w&.-]*)*\s+Seguros\b")


def _folhas(v, caminho=""):
    if isinstance(v, dict):
        for k, s in v.items():
            yield from _folhas(s, f"{caminho}.{k}")
    elif isinstance(v, list):
        for s in v:
            yield from _folhas(s, caminho + "[]")
    elif isinstance(v, str):
        yield caminho, v


def _chaves(v):
    if isinstance(v, dict):
        for k, s in v.items():
            yield str(k)
            yield from _chaves(s)
    elif isinstance(v, list):
        for s in v:
            yield from _chaves(s)


def problemas(fx) -> list:
    """O que esta fixture tem de errado. [] = limpa."""
    saida = []
    vaz = tem_vazamento(fx)
    if vaz:
        saida.append(f"tem_vazamento: {vaz}")
    lb = lista_branca_do_arquivo()
    fora = sorted({c for c in caminhos_de(fx) if not caminho_permitido(c, lb)})
    if fora:
        saida.append(f"fora da lista branca: {fora[:5]}")
    ruins = sorted({k for k in _chaves(fx) if k.lower() in CHAVES_PROIBIDAS})
    if ruins:
        saida.append(f"chave de identidade/credencial: {ruins}")
    for caminho, texto in _folhas(fx):
        if caminho.endswith(CATALOGO_DE_SEGURADORAS):
            continue  # 📊 o catálogo do Agger: razões sociais de SEGURADORAS ("ITAU Seg. S.A.")
        baixo = texto.lower()
        if RE_PJ.search(texto) or (RE_SEGUROS.search(texto)
                                   and not any(s in baixo for s in SEGURADORAS_CONHECIDAS)):
            saida.append(f"razão social de PJ desconhecida em {caminho}")
            break
    return saida


def test_ha_fixtures():
    rotulos = {p.stem for p in FIXTURES}
    assert {"gravacao_r1", "gravacao_r2", "gravacao_config"} <= rotulos


@pytest.mark.parametrize("arq", FIXTURES, ids=lambda p: p.stem)
def test_fixture_limpa_passa(arq):  # CONTROLE: a limpa TEM de passar
    fx = json.loads(arq.read_text(encoding="utf-8"))
    assert problemas(fx) == []


def test_manifesto_sem_vazamento_e_sem_caminho_de_cliente():
    man = json.loads((FIX / "MANIFESTO.json").read_text(encoding="utf-8"))
    assert tem_vazamento(man) == []
    texto = json.dumps(man, ensure_ascii=False)
    assert "intake" not in texto.lower() and ".har" not in texto.lower()
    assert set(man["fixtures"]) == {p.stem for p in FIXTURES}
    for rot, meta in man["fixtures"].items():
        assert re.fullmatch(r"(gravacao|vivo)_[a-z0-9_]+", rot)
        assert re.fullmatch(r"[0-9a-f]{64}", meta["sha256_do_bruto"])
        assert meta["conta"] in ("conta_a", "conta_b")


def _um_item(fx):
    """o 1º item de seguradora da 1ª rodada (onde um vazamento faria mais estrago)."""
    return fx["calculos"][0]["rodadas"][0]["corpo"][0]


MUTACOES = {
    "senha_aninhada": lambda fx: _um_item(fx).setdefault("resultados", []).append(
        {"coberturas": {"detalhe": {"senha": "x"}}}),
    "cpf_em_texto": lambda fx: _um_item(fx).setdefault("erros", []).append(
        "Segurado 111.111.111-11 com restrição"),
    "caminho_fora_da_lista": lambda fx: _um_item(fx).__setitem__("observacaoInterna", "nota"),
    "nome_de_corretora": lambda fx: _um_item(fx).setdefault("erros", []).append(
        "Fulano Corretora de Seguros Ltda"),
    "uuid_de_conta_como_chave": lambda fx: _um_item(fx).__setitem__("corretoraId", "<id#0001>"),
}


@pytest.mark.parametrize("nome", sorted(MUTACOES))
def test_controle_copia_mutada_reprova(nome):
    limpa = json.loads((FIX / "gravacao_r1.json").read_text(encoding="utf-8"))
    assert problemas(limpa) == []          # a mesma fixture, sem mutação, passa
    suja = copy.deepcopy(limpa)
    MUTACOES[nome](suja)
    assert problemas(suja) != [], f"a mutação {nome} passou pelo guarda"
