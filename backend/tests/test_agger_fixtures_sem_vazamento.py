# -*- coding: utf-8 -*-
"""G1 — nenhuma fixture do Agger vaza (SPEC-128 U1). Lê SÓ a fixture: roda em
qualquer máquina, sem o intake.

Para TODA fixture em `backend/tests/fixtures/agger/`:
  1. `tem_vazamento(...) == []` em toda profundidade (o redator ÚNICO);
  2. todo caminho de folha ⊂ a lista branca (`leitor_agger.lista_branca_do_arquivo`);
  3. nenhuma chave de identidade de conta ou de credencial;
  4. nenhuma razão social de pessoa jurídica que não seja seguradora conhecida;
  5. 🔴 (conserto B1) nenhuma URL — com esquema, `www.` ou `host.dominio/caminho` — e nenhuma
     chave/assinatura (`AIza…`, `AKIA…`, `key=`/`token=`/`signature=`…) no TEXTO INTEIRO do
     arquivo. 📊 04/10: uma seguradora devolveu a URL interna com `?key=` e a chave de API
     dentro da mensagem de erro (texto MANTIDO); os guardas por chave não a viam.

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

from portal_worker.redaction import (  # noqa: E402
    redigir_texto, sem_url_nem_chave, tem_url_ou_chave, tem_vazamento,
)
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
# 🔴 B1 — escritos AQUI, não importados: mutar o redator não cega este guarda.
RE_URL_OU_CHAVE = re.compile(
    r"(?i)https?:[\\/]{2}|\bwww\.|(?<![\w@./-])(?:[a-z0-9-]+\.)+[a-z]{2,}(?::\d+)?[\\/]+[^\s\"]*|"
    r"AIza[0-9A-Za-z_\-]{35}|AKIA[0-9A-Z]{16}|"
    r"(?<![a-z0-9_])(?:api_?key|access_token|key|token|signature|sig|secret)=")


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


def url_ou_chave_no_texto(texto: str) -> list:
    """Varredura do TEXTO inteiro (não por folha): o que casa, por TIPO — nunca o valor."""
    tipos = set()
    for m in RE_URL_OU_CHAVE.finditer(texto):
        s = m.group(0)
        tipos.add("chave_api" if s.startswith("AIza") else "chave_aws" if s.startswith("AKIA")
                  else "parametro_secreto" if s.endswith("=") else "url")
    return sorted(tipos)


def problemas(fx) -> list:
    """O que esta fixture tem de errado. [] = limpa."""
    saida = []
    # B1: o texto INTEIRO (regex própria deste guarda) + cada folha pelo redator único
    url = set(url_ou_chave_no_texto(json.dumps(fx, ensure_ascii=False)))
    url |= {t for _c, f in _folhas(fx) for t in tem_url_ou_chave(f)}
    if url:
        saida.append(f"URL/chave em texto: {sorted(url)}")
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


@pytest.mark.parametrize("arq", sorted(FIX.glob("*.json")), ids=lambda p: p.name)
def test_arquivo_inteiro_sem_url_nem_chave(arq):
    """B1: o ARQUIVO como está no disco (inclusive o MANIFESTO), não a árvore lida."""
    assert url_ou_chave_no_texto(arq.read_text(encoding="utf-8")) == []


# valores SINTÉTICOS com a forma exata (nenhum segredo real neste arquivo)
_CHAVE_FALSA = "AIza" + "Sy" + "0" * 33
_AWS_FALSA = "AKIA" + "Z" * 16


def test_redator_unico_conhece_url_e_chave():
    msg = f"Erro ao executar servico: 105 - Read terminated for https://api.seg.exemplo/v1/x?key={_CHAVE_FALSA}"
    limpa = sem_url_nem_chave(msg)
    assert "<removido:url>" in limpa and "Read terminated" in limpa and "AIza" not in limpa
    assert "exemplo" not in sem_url_nem_chave("veja www.exemplo.com.br/a?b=1 e arquivos.exemplo.com/x/y.pdf")
    assert sem_url_nem_chave("arquivos.exemplo.com/x/y.pdf") == "<removido:url>"
    # fora de URL: a chave e o parâmetro secreto saem pelo redator ÚNICO (redigir_texto/tem_vazamento)
    for suja in (f"chave {_CHAVE_FALSA} solta", f"credencial {_AWS_FALSA}", "access_token=abc123 fim",
                 "X-Amz-Signature=deadbeef", "api_key=zzz", "?token=t0k"):
        assert tem_url_ou_chave(suja), suja
        assert tem_vazamento(suja), suja
        assert not tem_url_ou_chave(redigir_texto(suja)), suja
        assert url_ou_chave_no_texto(suja), suja          # a regex PRÓPRIA do guarda também vê
    # CONTROLE: nome de variável em log NÃO é segredo; texto comum e valor monetário passam intactos
    for limpo in ("company_id='c1' portal_key='vidros'", "Azul Auto Roubo", "R$ 1.234,56 em 10x",
                  "Itau Seg. S.A./Ltda", "GOL 1.0 MI/ TOTAL FLEX"):
        assert sem_url_nem_chave(limpo) == limpo and redigir_texto(limpo) == limpo, limpo
        assert url_ou_chave_no_texto(limpo) == [] and tem_url_ou_chave(limpo) == [], limpo


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
    # 🔴 B1: o caso REAL de 04/10 (forma exata, valor sintético) e as suas variações
    "url_com_key_em_erro": lambda fx: _um_item(fx).setdefault("erros", []).append(
        f"Erro ao executar servico: 105 - Read terminated for https://api.seg.exemplo/v1/p?key={_CHAVE_FALSA}"),
    "url_sem_esquema_em_alerta": lambda fx: _um_item(fx).setdefault("alertas", []).append(
        "Baixe em arquivos.seg.exemplo/cotacao/123/doc"),
    "chave_api_solta_em_rotulo": lambda fx: _um_item(fx).__setitem__("seguradoraTxt", f"Seg {_CHAVE_FALSA}"),
    "token_em_parametro": lambda fx: _um_item(fx).setdefault("erros", []).append("falhou: access_token=abc"),
}


@pytest.mark.parametrize("nome", sorted(MUTACOES))
def test_controle_copia_mutada_reprova(nome):
    limpa = json.loads((FIX / "gravacao_r1.json").read_text(encoding="utf-8"))
    assert problemas(limpa) == []          # a mesma fixture, sem mutação, passa
    suja = copy.deepcopy(limpa)
    MUTACOES[nome](suja)
    assert problemas(suja) != [], f"a mutação {nome} passou pelo guarda"


# ---------------------------------------------------------------------------
# O GERADOR sobre um bruto SINTÉTICO (roda em qualquer máquina, sem intake)
# ---------------------------------------------------------------------------
def _gerador():
    sys.path.insert(0, str(BACKEND / "scripts"))
    import agger_fixtures_saneadas as G
    return G


_HOST = "https://api.multicalculo.net/calculo"


def _pedido(t, versao, cliente="Fulano Auto Teste"):
    return {"t": t, "t0": t, "m": "POST", "u": f"{_HOST}/calcularV2", "s": 200,
            "req": json.dumps({"cotacao": {"customerName": cliente, "ramo": 31}}),
            "body": json.dumps({"idIntegracao": "778899", "versao": versao})}


def _rodada(t, versao, itens):
    return {"t": t, "t0": t, "m": "GET", "u": f"{_HOST}/cotacao/calculos/778899/{versao}", "s": 200,
            "req": None, "body": json.dumps(itens)}


def _item(**k):
    base = {"seguradora": 7, "seguradoraTxt": "Azul", "retorno": True}
    base.update(k)
    return base


def test_gerador_liga_rodada_por_id_e_versao():
    """P5: dois recálculos SIMULTÂNEOS no mesmo negócio (E7) — a rodada da v3 fica no cálculo da v3."""
    G = _gerador()
    regs = [_pedido(0.0, 3), _pedido(1.0, 4),
            _rodada(2.0, 3, [_item(erros=["tente novamente mais tarde"])]),
            _rodada(3.0, 4, [_item(erros=["tente novamente mais tarde"])])]
    fx, _meta = G.sanear(regs, "vivo_sintetico", "conta_a")
    assert [c["resposta_pedido"]["corpo"]["versao"] for c in fx["calculos"]] == [3, 4]
    assert [[r["versao"] for r in c["rodadas"]] for c in fx["calculos"]] == [[3], [4]]


def test_gerador_tira_url_e_nao_troca_palavra_do_ramo():
    """B1 + P3/P4: a URL com `key=` sai do erro; "Auto" de "Azul Auto Roubo" continua "Auto"
    (📊 04/10 virava <nome> em 495 folhas da vivo_conta_b); a parte de NOME de verdade sai."""
    G = _gerador()
    url = f"https://api.seg.exemplo/v1/p?key={_CHAVE_FALSA}"
    regs = [_pedido(0.0, 1),
            _rodada(1.0, 1, [_item(erros=[f"Read terminated for {url}", "ligar para Fulano"],
                                   resultados=[{"premio": 100.0, "identificacao": "Azul Auto Roubo"}])])]
    fx, _meta = G.sanear(regs, "vivo_sintetico", "conta_a")
    item = fx["calculos"][0]["rodadas"][0]["corpo"][0]
    assert item["erros"] == ["Read terminated for <removido:url>", "ligar para <nome>"]
    assert item["resultados"][0]["identificacao"] == "Azul Auto Roubo"
    assert problemas(fx) == []
