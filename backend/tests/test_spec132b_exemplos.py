# -*- coding: utf-8 -*-
"""SPEC-132-B · fatia E — os EXEMPLOS da página do cliente com a marca REAL e dados fictícios (D-132B-08).

O que estes guardas fecham (cada um consegue ficar VERMELHO — a prova está no próprio teste ou na mutação do relatório):
    · a faixa "Exemplo — dados fictícios" aparece na VENDA e na RENOVAÇÃO, no HTML local e no SERVIDO pelo `/r/`
      (o que `abrir_compartilhado` devolve), com o MESMO visual da venda — e some sem a bandeira
    · sem `--confirmar` nada é escrito no banco (nenhuma linha nova em tabela nenhuma; a escrita LEVANTA)
    · nenhum telefone nem CPF no HTML — e o número da corretora SÓ entra com a escolha explícita
    · a marca é a da corretora do `company_id` (duas corretoras no MESMO banco) e o nome que vem no modelo do contrato
      nunca chega à página
    · o script não tem nome de corretora nem uuid de corretora (CLAUDE.md §13.9)
    · com `--confirmar` publica pelo caminho do produto, sem linha em `multicalculo_pedidos`/`renovacoes`, e rodar de
      novo é VERSÃO nova da mesma peça

Bordas: o banco (o PostgREST em memória da 129-B). Marca, config, renderizador e Hub são REAIS (CLAUDE.md §9.4).
⛔ Nomes fictícios (CLAUDE.md §13.9). Rodar:
    cd backend && .venv/Scripts/python.exe -m pytest tests/test_spec132b_exemplos.py -q -p no:cacheprovider
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
for _p in (str(BACKEND), str(BACKEND / "tests")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app.services.artifacts import proposta_cotacao_html as PV  # noqa: E402
from app.services.artifacts import proposta_html as PH  # noqa: E402
from app.services.artifacts.service import ArtifactService  # noqa: E402
from dubles import mundo_da_proposta as M  # noqa: E402
from scripts import publicar_exemplo_da_pagina as EX  # noqa: E402
from test_spec130a_o_fio import CHROME, texto_visivel  # noqa: E402

BASE = "https://app.exemplo.test"
FAIXA = "Exemplo — dados fictícios"
SCRIPT = BACKEND / "scripts" / "publicar_exemplo_da_pagina.py"
AGORA = datetime(2026, 10, 14, 13, 0, tzinfo=timezone.utc)
CASOS = [("venda", False), ("venda", True), ("renovacao", False)]


def mundo(monkeypatch):
    monkeypatch.setenv("PUBLIC_APP_URL", BASE)
    return M.montar_mundo(monkeypatch, solicitante="beta")


def _retrato(m):
    """Todas as linhas de todas as tabelas do dublê + quantas escritas ele já registrou."""
    return (json.dumps({t: m.banco.linhas(t) for t in sorted(m.banco.tabelas)}, sort_keys=True, default=str),
            len(m.banco.escritas))


def _local(m, tmp_path, company_id, pagina, com_apolice=False, **kw):
    arq = tmp_path / f"{pagina}-{com_apolice}.html"
    r = asyncio.run(EX.gerar_exemplo(m.db, company_id, pagina, com_apolice=com_apolice, saida=arq, agora=AGORA, **kw))
    assert r["arquivo"] == str(arq) and r["bytes"] == len(arq.read_bytes())
    return arq.read_text(encoding="utf-8")


def _publicar(m, company_id, pagina, com_apolice=False, **kw):
    return asyncio.run(EX.gerar_exemplo(m.db, company_id, pagina, com_apolice=com_apolice, confirmar=True,
                                        base_url=BASE, agora=AGORA, **kw))


def _servido(m, token):
    s = ArtifactService(m.banco.visao("rota-publica")).abrir_compartilhado(token, user_agent=CHROME)
    assert s, "o link não abriu"
    return s["html"]


_RE_DATA_URL = re.compile(r"data:[\w.+-]+/[\w.+-]+;base64,[A-Za-z0-9+/=]+")
_RE_TELEFONE = re.compile(r"(?<![\w.-])(?:\+?55[\s-]?)?\(?\d{2}\)?[\s-]?9?\d{4}[\s-]?\d{4}(?![\w-])")
_RE_CPF = re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)")


def telefones_e_documentos(doc: str):
    """Tudo no HTML com cara de telefone ou CPF — fora dos `data:` (o logo em base64) e dos números de dinheiro."""
    sem_logo = _RE_DATA_URL.sub("", doc)
    achados = [x for x in _RE_TELEFONE.findall(sem_logo) if len(re.sub(r"\D", "", x)) >= 10]
    achados += _RE_CPF.findall(sem_logo)
    achados += re.findall(r"wa\.me/\d+|api\.whatsapp\.com/send\?phone=\d+", sem_logo)
    return achados


# =====================================================================================================================
# 1. a faixa — nos dois, local e servida, o mesmo visual; e sem a bandeira, nada
# =====================================================================================================================
@pytest.mark.parametrize("pagina,com_apolice", CASOS)
def test_a_faixa_aparece_no_html_local_e_no_servido(monkeypatch, tmp_path, pagina, com_apolice):
    m = mundo(monkeypatch)
    local = _local(m, tmp_path, m.alfa, pagina, com_apolice)
    pub = _publicar(m, m.alfa, pagina, com_apolice)
    servido = _servido(m, pub["token"])
    for doc in (local, servido):
        assert texto_visivel(doc).count(FAIXA) == 1
        assert re.search(r'<body[^>]*>\s*<div class="exemplo" role="note">', doc), "a faixa não está no topo"
    # a página certa: a renovação é a da renovação; a venda é a da venda
    if pagina == "renovacao":
        txt = texto_visivel(servido)
        assert "a renovação do seu Onix está pronta" in txt
        # a copy da renovação (D-131-42, nunca cruzada): nenhum ranking — o motivo da cotação NÃO pode vir junto
        assert "Menor preço entre as" not in txt and "a melhor das" not in txt.lower()
        assert "Franquia: R$" in txt and "a mais por ano que a opção “Sua renovação”" in txt
    else:
        assert '<body class="venda">' in servido and "Onix" in texto_visivel(servido)
    assert pub["url"] == f"{BASE}/r/{pub['token']}"


def test_sem_a_bandeira_a_renovacao_nao_tem_a_faixa_nem_o_estilo():
    contrato = EX._contrato()
    ren = dict(contrato, situacao="renovacao", opcoes=EX._opcoes_da_renovacao(contrato, premio_de_hoje=4389.24),
               renovacao={"vence_em": "2026-11-03", "seguradora_atual": "Bradesco", "premio_atual": 4389.24})
    sem, com = PH.render_renovacao(ren), PH.render_renovacao(dict(ren, exemplo=True))
    assert FAIXA not in sem and 'class="exemplo"' not in sem and ".exemplo{" not in sem
    assert FAIXA in texto_visivel(com)
    assert PH.render_renovacao(dict(ren, exemplo="sim")) == sem          # só `True` liga (nunca um texto qualquer)


def _regras(css: str, seletor: str):
    return [re.sub(r"\s+", "", r) for r in re.findall(re.escape(seletor) + r"\{[^}]*\}", css)]


def test_a_faixa_da_renovacao_tem_o_mesmo_visual_da_venda():
    assert _regras(PH.CSS_DA_FAIXA_DE_EXEMPLO, ".exemplo") == _regras(PV.CSS_DA_VENDA, ".exemplo")
    assert len(_regras(PV.CSS_DA_VENDA, ".exemplo")) == 2               # a regra da tela e a da impressão
    venda = PV.render_cotacao(dict(EX._contrato(), pagina="venda", situacao="novo_sem_apolice", exemplo=True))
    assert PH.FAIXA_DE_EXEMPLO in venda                                  # o MESMO elemento nas duas páginas


# =====================================================================================================================
# 2. sem --confirmar: nada no banco
# =====================================================================================================================
@pytest.mark.parametrize("pagina,com_apolice", CASOS)
def test_sem_confirmar_nada_e_escrito_no_banco(monkeypatch, tmp_path, pagina, com_apolice):
    m = mundo(monkeypatch)
    antes = _retrato(m)
    _local(m, tmp_path, m.alfa, pagina, com_apolice)
    assert _retrato(m) == antes


def test_o_banco_do_ensaio_recusa_qualquer_escrita(monkeypatch):
    m = mundo(monkeypatch)
    ro = EX.SoLeitura(m.db)
    assert ro.table("brand_profiles").select("company_id").eq("company_id", m.alfa).execute().data   # ler passa
    for acao in ("insert", "upsert", "update"):
        with pytest.raises(EX.EscritaProibida):
            getattr(ro.table("artifacts"), acao)({"x": 1})
    with pytest.raises(EX.EscritaProibida):
        ro.table("artifacts").delete()
    with pytest.raises(EX.EscritaProibida):
        ro.rpc("qualquer")
    # e o caminho de publicar, se alguém o chamasse sem --confirmar, pararia na 1ª escrita
    from app.services.multicalculo import proposta as P

    modelo, ctx, pid = asyncio.run(EX.montar_modelo_de_exemplo(ro, m.alfa, "venda", agora=AGORA))
    with pytest.raises(EX.EscritaProibida):
        P._gravar_e_compartilhar(ro, m.alfa, pid, modelo, ctx, BASE)
    assert not m.banco.linhas("artifacts")


# =====================================================================================================================
# 3. nenhum telefone, nenhum CPF — e o número da corretora só por escolha
# =====================================================================================================================
@pytest.mark.parametrize("pagina,com_apolice", CASOS)
def test_nenhum_telefone_nem_cpf_no_html(monkeypatch, tmp_path, pagina, com_apolice):
    m = mundo(monkeypatch)
    local = _local(m, tmp_path, m.alfa, pagina, com_apolice)
    pub = _publicar(m, m.alfa, pagina, com_apolice)
    for doc in (local, _servido(m, pub["token"])):
        assert telefones_e_documentos(doc) == []
        assert M.WHATS_ALFA not in doc and "3333-0000" not in doc
    for v in m.banco.linhas("artifact_versions"):
        assert M.WHATS_ALFA not in json.dumps(v.get("payload"), ensure_ascii=False)


@pytest.mark.parametrize("pagina", ["venda", "renovacao"])
def test_o_guarda_do_telefone_fica_vermelho_com_o_numero(monkeypatch, tmp_path, pagina):
    """§9.3: o guarda consegue falhar — com a escolha explícita o número da corretora ENTRA, e o guarda o vê."""
    m = mundo(monkeypatch)
    doc = _local(m, tmp_path, m.alfa, pagina, com_whatsapp_da_corretora=True)
    assert f"wa.me/{M.WHATS_ALFA}" in doc and telefones_e_documentos(doc)


# =====================================================================================================================
# 4. a marca é a do company_id — duas corretoras, e nada do modelo do contrato vaza
# =====================================================================================================================
def test_cada_corretora_com_a_sua_marca(monkeypatch, tmp_path):
    m = mundo(monkeypatch)
    alfa = _local(m, tmp_path / "a", m.alfa, "venda")
    beta = _local(m, tmp_path / "b", m.beta, "venda")
    assert M.MARCA_ALFA in texto_visivel(alfa) and M.NOME_BETA not in texto_visivel(alfa)
    # a beta tem a marca só em RASCUNHO: a página usa o nome oficial dela e nunca o rascunho
    assert M.NOME_BETA in texto_visivel(beta) and M.MARCA_BETA not in beta and M.MARCA_ALFA not in beta
    assert M.LOGO_DATA_URL in alfa and M.LOGO_DATA_URL not in beta


@pytest.mark.parametrize("pagina,com_apolice", CASOS)
def test_o_nome_da_anfitria_do_contrato_nunca_chega_a_pagina(monkeypatch, tmp_path, pagina, com_apolice):
    m = mundo(monkeypatch)
    doc = _local(m, tmp_path, m.alfa, pagina, com_apolice)
    nomes = nomes_do_contrato()
    assert nomes and all(n.lower() not in doc.lower() for n in nomes)
    assert any(n.lower() in json.dumps(EX._contrato(), ensure_ascii=False).lower() for n in nomes)   # pode falhar


# =====================================================================================================================
# 5. o script não tem corretora (CLAUDE.md §13.9)
# =====================================================================================================================
def _com_a_primeira_palavra(nomes):
    return sorted({n for n in nomes if n} | {n.split()[0] for n in nomes if n})


def nomes_do_contrato():
    """O nome da anfitriã que o modelo do contrato traz (o dado de onde o exemplo sai) — lido do arquivo, nunca escrito
    aqui: inteiro, a ficha do Google e a 1ª palavra."""
    anf = json.loads(EX.MODELO_DO_CONTRATO.read_text(encoding="utf-8"))["anfitria"]
    return _com_a_primeira_palavra({anf["nome"], *(anf.get("google") or {}).get("fonte", "").split("'")[1:2]})


def nomes_que_nao_podem_aparecer():
    """Os nomes de corretora que o teste CONHECE sem escrevê-los: os do contrato e os do dublê."""
    return _com_a_primeira_palavra(set(nomes_do_contrato()) | {M.NOME_ALFA, M.MARCA_ALFA, M.NOME_BETA, M.MARCA_BETA,
                                                                M.NOME_CANAL})


_RE_UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def corretoras_no_texto(texto: str):
    achados = [n for n in nomes_que_nao_podem_aparecer() if n.lower() in texto.lower()]
    achados += [u for u in _RE_UUID.findall(texto) if u != str(EX.ESPACO_DOS_EXEMPLOS)]
    return achados


def test_o_script_nao_tem_nome_nem_uuid_de_corretora():
    texto = SCRIPT.read_text(encoding="utf-8")
    assert corretoras_no_texto(texto) == []
    # §9.3: o guarda consegue falhar — o nome da anfitriã do contrato, ou um uuid de corretora, colado no script
    anf = json.loads(EX.MODELO_DO_CONTRATO.read_text(encoding="utf-8"))["anfitria"]["nome"]
    assert corretoras_no_texto(texto + f'\nNOME = "{anf}"\n')
    assert corretoras_no_texto(texto + f'\nCOMPANY = "{M.dados_do_canario()["corretoras"]["corretora_a"]}"\n')


# =====================================================================================================================
# 6. --confirmar: o caminho do produto, sem linha falsa, e rodar de novo = versão nova da MESMA peça
# =====================================================================================================================
def test_confirmar_publica_pelo_hub_sem_tocar_no_motor(monkeypatch):
    m = mundo(monkeypatch)
    antes = {t: len(m.banco.linhas(t)) for t in ("multicalculo_pedidos", "multicalculo_calculos",
                                                  "multicalculo_ofertas", "renovacoes")}
    a = _publicar(m, m.alfa, "renovacao")
    b = _publicar(m, m.alfa, "renovacao")
    assert {t: len(m.banco.linhas(t)) for t in antes} == antes                    # nenhuma linha no motor/renovação
    assert a["artifact_id"] == b["artifact_id"] and (a["versao"], b["versao"]) == (1, 2) and a["token"] != b["token"]
    art = next(x for x in m.banco.linhas("artifacts") if str(x["id"]) == a["artifact_id"])
    assert art["company_id"] == m.alfa and art["template_key"] == "proposal.quote"
    assert art["title"].startswith("Exemplo · Renovação do seguro")
    ref = art["subject_ref"]
    assert ref["kind"] == "exemplo_da_pagina" and ref["exemplo"] is True and ref["pagina"] == "renovacao"
    assert ref["pedido_id"] == EX.pedido_do_exemplo(m.alfa, "renovacao")
    assert not any(p["id"] == ref["pedido_id"] for p in m.banco.linhas("multicalculo_pedidos"))
    share = next(s for s in m.banco.linhas("artifact_shares") if s["token"] == b["token"])
    assert share["company_id"] == m.alfa and share["audience_label"] == "cliente"
    # o link vale DIAS_DO_LINK (os dias da página + a folga do link da config)
    v = next(x for x in m.banco.linhas("artifact_versions") if x["artifact_id"] == a["artifact_id"]
             and x["version"] == 2)
    assert v["payload"]["exemplo"] is True and v["payload"]["anfitria"]["nome"] == M.MARCA_ALFA
    fim = datetime.fromisoformat(str(share["expires_at"]))
    assert abs((fim - datetime.now(timezone.utc)).total_seconds() - EX.DIAS_DO_LINK * 86400) < 3600


def test_main_imprime_so_o_link_e_o_tamanho(monkeypatch, capsys, tmp_path):
    m = mundo(monkeypatch)
    assert EX.main(["--company-id", m.alfa, "--pagina", "venda", "--confirmar"], db=m.db) == 0
    linhas = capsys.readouterr().out.strip().splitlines()
    assert len(linhas) == 2 and re.fullmatch(re.escape(BASE) + r"/r/[\w-]{32,}", linhas[0])
    assert re.fullmatch(r"\d+ bytes de HTML", linhas[1])
    arq = tmp_path / "x.html"
    assert EX.main(["--company-id", m.beta, "--pagina", "renovacao", "--saida", str(arq)], db=m.db) == 0
    linhas = capsys.readouterr().out.strip().splitlines()
    assert linhas == [str(arq), f"{len(arq.read_bytes())} bytes de HTML"]


# =====================================================================================================================
# 7. --whatsapp-do-dono: o número FICTÍCIO de quem cuida — só no modelo; a barra aponta para ele
# =====================================================================================================================
DONO_FICTICIO = "+5511900000000"


@pytest.mark.parametrize("pagina", ["venda", "renovacao"])
def test_com_o_whatsapp_do_dono_a_barra_aponta_para_ele(monkeypatch, tmp_path, pagina):
    m = mundo(monkeypatch)
    antes = _retrato(m)
    doc = _local(m, tmp_path, m.alfa, pagina, whatsapp_do_dono_ficticio=DONO_FICTICIO)
    assert '<div class="dock">' in doc                                   # a barra "Quero fechar"/"Quero renovar"
    assert f"wa.me/{DONO_FICTICIO[1:]}" in doc and M.WHATS_ALFA not in doc   # o dono, nunca a corretora
    nome = EX.DONA_FICTICIA if pagina == "renovacao" else EX.CORRETOR_FICTICIO
    assert nome in texto_visivel(doc)                                    # "Quem cuida de você" é ele
    assert _retrato(m) == antes                                          # só no modelo: nenhuma tabela tocada
    with pytest.raises(ValueError):
        EX.whatsapp_do_dono("11900000000")                               # sem +55 / fora do E.164 BR: recusa
    with pytest.raises(SystemExit):
        EX.main(["--company-id", m.alfa, "--pagina", pagina, "--whatsapp-do-dono", "+1 555 0100",
                 "--saida", str(tmp_path / "x.html")], db=m.db)


@pytest.mark.parametrize("pagina", ["venda", "renovacao"])
def test_sem_o_whatsapp_do_dono_nao_ha_barra(monkeypatch, tmp_path, pagina):
    m = mundo(monkeypatch)
    doc = _local(m, tmp_path, m.alfa, pagina)
    assert '<div class="dock">' not in doc and "wa.me/" not in doc
