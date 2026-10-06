# -*- coding: utf-8 -*-
"""SPEC-130-A · F2a · U5 — a INFRA da página da proposta no Artifact Hub e no /r/.

    o gancho        `Template.renderizador`: `renderizar` usa o gancho quando existe; senão os blocos, igual
    o hash (G16)    vem da CONSTANTE do script e NÃO muda se o HTML guardado mudar (mutação: vermelho)
    kind/hash       `abrir_compartilhado` devolve `kind`, e `csp_script_hashes` SÓ para `proposal`
    a abertura(G17) o robô de prévia (WhatsApp/Facebook/…) não conta `view_count` nem grava `share.viewed`
    o clique        só para opção que EXISTE no modelo; destino = wa.me montado do modelo, nunca da query
    a prévia        og:* sem dado pessoal; PNG 1200×630; dado pessoal não muda UM byte do PNG (controle: o preço muda)
    o escape        `</script>` num texto do modelo não fecha tag nenhuma

⚠️ O pacote `app.services` real importa o produto inteiro (📊 06/10 ≈ 1m40 só no import, langchain/qdrant): aqui
ele é trocado por um pacote vazio com o `__path__` do disco (molde de `test_template_de_artefato_existe.py`), SÓ se
ninguém o importou antes. Os módulos do Hub carregados são os REAIS; o conftest isola o pacote de mentira.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import io
import json
import os
import re
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
if "app.services" not in sys.modules:
    for _n, _p in (("app", ("app",)), ("app.services", ("app", "services"))):
        if _n not in sys.modules:
            _m = types.ModuleType(_n)
            _m.__path__ = [str(BACKEND.joinpath(*_p))]
            sys.modules[_n] = _m

from app.services.artifacts import proposta_html as PH  # noqa: E402
from app.services.artifacts import service as SV  # noqa: E402
from app.services.artifacts.proposta_previa import render_previa_png  # noqa: E402
from app.services.artifacts.templates import CATALOGO, POR_CHAVE  # noqa: E402

CIA = "c1300000-0000-4000-8000-0000000000c1"
OUTRA = "c1300000-0000-4000-8000-0000000000c2"
TOKEN = "tOkEnDaPrOpOsTa_de-teste_0123456789abcdefgh"
TOKEN_REL = "tOkEnDoReLaToRiO_de-teste_0123456789abcdef"
CHROME = ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/129.0.0.0 Mobile Safari/537.36")


# =====================================================================================================================
# o modelo (CONTRATO §5) — com dado pessoal DE PROPÓSITO, para provar que ele não vaza
# =====================================================================================================================
def _modelo(**troca) -> dict:
    m = {
        "origem": "corretora",
        "cliente": {"primeiro_nome": "Mariana", "cpf": "123.456.789-09"},
        "veiculo": {"modelo": "Jeep Compass Limited", "ano": "2018/2019", "placa": "QAZ1B23"},
        "situacao": "novo_sem_apolice",
        "resumo": {"seguradoras_cotadas": 14, "com_preco_comparavel": 11, "com_produto_diferente": 4,
                   "nao_responderam": 2},
        "opcoes": [
            {"id": "recomendada", "rotulo": "Recomendada", "seguradora": "Bradesco", "premio_anual": 4784.27,
             "nota": 91, "motivos": ["a", "b"]},
            {"id": "mais_em_conta", "rotulo": "Mais em conta", "seguradora": "Aliro", "premio_anual": 4210.0,
             "nota": 80, "motivos": ["a", "b"]},
            {"id": "mais_completa", "rotulo": "Mais completa", "seguradora": "Porto", "premio_anual": 5300.5,
             "nota": 85, "motivos": ["a", "b"]},
        ],
        "anfitria": {"nome": "Corretora Anfitriã Exemplo", "whatsapp": "5548999990000",
                     "tema_claro": {"primary": {"fill": "#1D5579", "on": "#FFFFFF"}}},
        "cta": {"whatsapp_url": "https://wa.me/5548999990000",
                "texto_por_opcao": {"recomendada": "Olá! Quero a Recomendada (Bradesco)."}},
        "validade_ate": "2026-10-13",
        "aviso_legal": "Preços sujeitos à análise da seguradora.",
    }
    m.update(troca)
    return m


# =====================================================================================================================
# o banco DUBLÊ — honra eq/is_/limit, registra escritas (quem sabe de tenant é o código)
# =====================================================================================================================
class _Resp:
    def __init__(self, data):
        self.data = data


class _Q:
    def __init__(self, banco, tabela):
        self.b, self.t, self.f, self.op, self.linha, self.um, self.lim = banco, tabela, [], "select", None, False, None

    def select(self, *_a, **_k):
        return self

    def eq(self, c, v):
        self.f.append((c, str(v)))
        return self

    def is_(self, *_a):
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, n):
        self.lim = n
        return self

    def maybe_single(self):
        self.um = True
        return self

    def insert(self, linha):
        self.op, self.linha = "insert", dict(linha)
        return self

    def update(self, linha):
        self.op, self.linha = "update", dict(linha)
        return self

    def upsert(self, linha, **_k):
        self.op, self.linha = "upsert", dict(linha)
        return self

    def _casa(self, l):
        return all(str(l.get(c)) == v for c, v in self.f)

    def execute(self):
        linhas = self.b.tabelas.setdefault(self.t, [])
        self.b.log.append((self.op, self.t, tuple(self.f), copy.deepcopy(self.linha)))
        if self.op == "insert":
            nova = dict(self.linha, id=self.linha.get("id") or f"{self.t}-{len(linhas) + 1}")
            linhas.append(nova)
            return _Resp([copy.deepcopy(nova)])
        if self.op == "upsert":
            linhas.append(dict(self.linha))
            return _Resp([copy.deepcopy(self.linha)])
        if self.op == "update":
            alvo = [l for l in linhas if self._casa(l)]
            for l in alvo:
                l.update(self.linha)
            return _Resp(copy.deepcopy(alvo))
        casam = [copy.deepcopy(l) for l in linhas if self._casa(l)]
        if self.lim:
            casam = casam[: self.lim]
        if self.um:
            return _Resp(casam[0] if casam else None)
        return _Resp(casam)


class Banco:
    def __init__(self):
        self.tabelas: dict = {}
        self.log: list = []

    def table(self, nome):
        return _Q(self, nome)

    def eventos(self, tipo=None):
        return [l for l in self.tabelas.get("artifact_events", []) if tipo is None or l["event_type"] == tipo]


def _amanha():
    return (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()


def _banco_com_links(html_proposta=None, modelo=None) -> Banco:
    """Uma proposta (CIA) e um relatório (CIA), cada um com versão, render pronto e link válido."""
    b = Banco()
    modelo = _modelo() if modelo is None else modelo
    html_proposta = PH.render_proposta(modelo) if html_proposta is None else html_proposta
    b.tabelas["artifacts"] = [
        {"id": "art-p", "company_id": CIA, "kind": "proposal", "title": "Proposta", "subtitle": None,
         "template_key": "proposal.quote"},
        {"id": "art-r", "company_id": CIA, "kind": "report", "title": "Panorama", "subtitle": None,
         "template_key": "executive.panorama"},
    ]
    b.tabelas["artifact_versions"] = [
        {"id": "v-p", "company_id": CIA, "artifact_id": "art-p", "payload": modelo, "status": "published"},
        {"id": "v-r", "company_id": CIA, "artifact_id": "art-r", "payload": {}, "status": "published"},
    ]
    b.tabelas["artifact_renders"] = [
        {"artifact_version_id": "v-p", "format": "html", "status": "ready", "inline_content": html_proposta},
        {"artifact_version_id": "v-r", "format": "html", "status": "ready",
         "inline_content": "<!doctype html><p>RELATORIO</p>"},
    ]
    b.tabelas["artifact_shares"] = [
        {"id": "s-p", "company_id": CIA, "artifact_id": "art-p", "artifact_version_id": "v-p", "token": TOKEN,
         "expires_at": _amanha(), "revoked_at": None, "max_views": None, "view_count": 0, "white_label": True,
         "audience_label": None},
        {"id": "s-r", "company_id": CIA, "artifact_id": "art-r", "artifact_version_id": "v-r", "token": TOKEN_REL,
         "expires_at": _amanha(), "revoked_at": None, "max_views": None, "view_count": 0, "white_label": True,
         "audience_label": None},
    ]
    return b


def _hash_independente(texto: str) -> str:
    return "sha256-" + base64.b64encode(hashlib.sha256(texto.encode("utf-8")).digest()).decode()


def _scripts(documento: str) -> list[tuple[str, str]]:
    """(atributos, conteúdo) de cada <script> do documento."""
    return re.findall(r"<script([^>]*)>(.*?)</script>", documento, flags=re.S)


# =====================================================================================================================
# o hash e o script
# =====================================================================================================================
def test_o_hash_vem_da_constante_e_bate_com_o_calculo_independente():
    assert PH.HASH_DO_SCRIPT == _hash_independente(PH.SCRIPT_DA_PROPOSTA)
    assert re.fullmatch(r"sha256-[A-Za-z0-9+/]{43}=", PH.HASH_DO_SCRIPT)
    assert PH.SCRIPT_DA_PROPOSTA.isascii()
    assert "</script" not in PH.SCRIPT_DA_PROPOSTA.lower()
    # a página funciona sem o script e o script não depende de handler inline (a CSP o bloquearia)
    assert "onclick" not in PH.render_proposta(_modelo()).lower()


def test_a_pagina_tem_UM_script_executavel_identico_a_constante():
    doc = PH.render_proposta(_modelo())
    execs = [c for a, c in _scripts(doc) if "application/json" not in a]
    dados = [c for a, c in _scripts(doc) if "application/json" in a]
    assert execs == [PH.SCRIPT_DA_PROPOSTA]
    assert _hash_independente(execs[0]) == PH.HASH_DO_SCRIPT
    assert len(dados) == 1 and json.loads(dados[0])["opcoes"][0]["id"] == "recomendada"


def test_escape_de_script_nos_dados_e_no_texto():
    ruim = "</script><script>alert(1)</script>"
    m = _modelo()
    m["opcoes"][0]["seguradora"] = ruim
    m["opcoes"][1]["rotulo"] = ruim
    m["aviso_legal"] = ruim
    m["anfitria"]["nome"] = ruim
    doc = PH.render_proposta(m)
    assert "<script>alert" not in doc
    assert doc.lower().count("<script") == 2          # o bloco de dados e o NOSSO script, mais nada
    bloco = [c for a, c in _scripts(doc) if "application/json" in a][0]
    assert "</" not in bloco and "<" not in bloco
    assert json.loads(bloco)["opcoes"][0]["seguradora"] == ruim      # o JSON continua o mesmo para o parse
    assert doc.count(PH.MARCADOR_DA_PREVIA) == 1                     # o texto não forja o marcador


# =====================================================================================================================
# o gancho do Hub
# =====================================================================================================================
def test_so_a_proposta_tem_gancho_e_kind_proposal():
    com_gancho = [t.key for t in CATALOGO if t.renderizador is not None]
    assert com_gancho == ["proposal.quote"]
    tpl = POR_CHAVE["proposal.quote"]
    assert (tpl.kind, tpl.audience, tpl.category) == ("proposal", "client", "client_facing")
    assert tpl.renderizador(_modelo()) == PH.render_proposta(_modelo())
    assert all(t.kind == "report" for t in CATALOGO if t.key != "proposal.quote")


def test_renderizar_usa_o_gancho_e_os_relatorios_continuam_nos_blocos():
    b = Banco()
    modelo = _modelo()
    b.tabelas["artifacts"] = [{"id": "art-p", "company_id": CIA, "title": "P", "template_key": "proposal.quote"},
                              {"id": "art-r", "company_id": CIA, "title": "R", "template_key": "executive.panorama"}]
    marca = {"name": "Solicitante", "palette": {"primary": "#123456", "accent": "#654321"}}
    b.tabelas["artifact_versions"] = [
        {"id": "v-p", "company_id": CIA, "artifact_id": "art-p", "payload": modelo, "brand_snapshot": marca,
         "composition": []},
        {"id": "v-r", "company_id": CIA, "artifact_id": "art-r", "payload": {}, "brand_snapshot": marca,
         "composition": [{"block": "cover", "props": {"eyebrow": "X"}}]},
    ]
    svc = SV.ArtifactService(b)
    rp = svc.renderizar(company_id=CIA, version_id="v-p")
    rr = svc.renderizar(company_id=CIA, version_id="v-r")
    assert rp["html"] == PH.render_proposta(modelo)
    assert rp["diagnostico"]["renderizador"] == "proposal.quote"
    guardado = [l for l in b.tabelas["artifact_renders"] if l["artifact_version_id"] == "v-p"][0]
    assert guardado["inline_content"] == rp["html"] and guardado["status"] == "ready"
    # o relatório: blocos, sem script, como sempre
    assert "renderizador" not in rr["diagnostico"]
    assert 'class="ab-doc"' in rr["html"] and "<script" not in rr["html"].lower()
    assert PH.SCRIPT_DA_PROPOSTA not in rr["html"]


def test_criar_grava_o_kind_do_template(monkeypatch):
    import app.services.brand.capture as CAP
    monkeypatch.setattr(CAP.BrandCaptureService, "snapshot_para_artefato",
                        lambda self, cid: {"name": "X", "palette": {"primary": "#123456"}})
    b = Banco()
    svc = SV.ArtifactService(b)
    svc.criar(company_id=CIA, title="P", template_key="proposal.quote", payload=_modelo(), composition=[])
    svc.criar(company_id=CIA, title="R", template_key="executive.panorama", payload={}, composition=[])
    svc.criar(company_id=CIA, title="D", template_key="proposal.quote", payload={}, composition=[], kind="dossier")
    assert [a["kind"] for a in b.tabelas["artifacts"]] == ["proposal", "report", "dossier"]


# =====================================================================================================================
# kind / hash no link (G16)
# =====================================================================================================================
def test_kind_e_hash_so_para_proposta():
    b = _banco_com_links()
    svc = SV.ArtifactService(b)
    p = svc.abrir_compartilhado(TOKEN, user_agent=CHROME)
    r = svc.abrir_compartilhado(TOKEN_REL, user_agent=CHROME)
    assert p["kind"] == "proposal" and p["csp_script_hashes"] == [PH.HASH_DO_SCRIPT]
    assert r["kind"] == "report" and "csp_script_hashes" not in r
    assert r["html"] == "<!doctype html><p>RELATORIO</p>"


def test_G16_o_hash_nao_muda_se_o_html_guardado_mudar():
    adulterado = PH.render_proposta(_modelo()).replace(PH.SCRIPT_DA_PROPOSTA, "alert('outro script')")
    assert adulterado != PH.render_proposta(_modelo())                         # a mutação existe
    b = _banco_com_links(html_proposta=adulterado)
    r = SV.ArtifactService(b).abrir_compartilhado(TOKEN, user_agent=CHROME)
    guardado = [c for a, c in _scripts(r["html"]) if "application/json" not in a]
    assert guardado == ["alert('outro script')"]
    assert r["csp_script_hashes"] == [PH.HASH_DO_SCRIPT]
    # CONTROLE: o hash do script guardado É diferente — se o código o recalculasse do HTML, daria este
    assert _hash_independente(guardado[0]) not in r["csp_script_hashes"]


def test_og_image_absoluta_entra_na_hora_de_servir(monkeypatch):
    for v in ("PUBLIC_APP_URL", "NEXT_PUBLIC_APP_URL", "SMITH_WEB_URL", "FRONTEND_URL"):
        monkeypatch.delenv(v, raising=False)
    sem_base = SV.ArtifactService(_banco_com_links()).abrir_compartilhado(TOKEN, user_agent=CHROME)
    assert "og:image" not in sem_base["html"]

    monkeypatch.setenv("PUBLIC_APP_URL", "https://app.exemplo.com.br")
    r = SV.ArtifactService(_banco_com_links()).abrir_compartilhado(TOKEN, user_agent=CHROME)
    head = r["html"].split("</head>")[0]
    assert f'<meta property="og:image" content="https://app.exemplo.com.br/r/{TOKEN}/previa.png">' in head
    assert f'<meta property="og:url" content="https://app.exemplo.com.br/r/{TOKEN}">' in head
    assert '<meta name="twitter:card" content="summary_large_image">' in head
    assert PH.MARCADOR_DA_PREVIA not in r["html"]
    # o script continua byte a byte — a costura não toca no que a CSP libera
    assert [c for a, c in _scripts(r["html"]) if "application/json" not in a] == [PH.SCRIPT_DA_PROPOSTA]
    # o relatório não ganha prévia nenhuma
    rel = SV.ArtifactService(_banco_com_links()).abrir_compartilhado(TOKEN_REL, user_agent=CHROME)
    assert "og:image" not in rel["html"]


# =====================================================================================================================
# a abertura — o robô de prévia não conta (G17)
# =====================================================================================================================
ROBOS = [
    "WhatsApp/2.23.20.0 A",
    "WhatsApp/2.24.6.77 i",
    "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
    "Twitterbot/1.0",
    "TelegramBot (like TwitterBot)",
    "Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)",
]


@pytest.mark.parametrize("ua", ROBOS)
def test_o_robo_de_previa_nao_conta_visualizacao(ua):
    b = _banco_com_links()
    r = SV.ArtifactService(b).abrir_compartilhado(TOKEN, user_agent=ua)
    assert r is not None and r["html"]                                   # o robô LÊ a página (a prévia precisa)
    assert b.tabelas["artifact_shares"][0]["view_count"] == 0
    assert b.eventos("share.viewed") == []
    assert len(b.eventos("share.previewed")) == 1


@pytest.mark.parametrize("ua", [CHROME, None, ""])
def test_CONTROLE_a_pessoa_conta_visualizacao(ua):
    b = _banco_com_links()
    SV.ArtifactService(b).abrir_compartilhado(TOKEN, user_agent=ua)
    assert b.tabelas["artifact_shares"][0]["view_count"] == 1
    assert len(b.eventos("share.viewed")) == 1 and b.eventos("share.previewed") == []


# =====================================================================================================================
# o clique — só opção conhecida, destino montado do modelo
# =====================================================================================================================
def test_o_clique_em_opcao_conhecida_registra_e_leva_ao_whatsapp_da_corretora():
    b = _banco_com_links()
    svc = SV.ArtifactService(b)
    d = svc.fechar_compartilhado(TOKEN, "recomendada")
    assert d == "https://wa.me/5548999990000?text=Ol%C3%A1%21%20Quero%20a%20Recomendada%20%28Bradesco%29."
    d2 = svc.fechar_compartilhado(TOKEN, "mais_em_conta")                  # sem texto próprio: o padrão
    assert d2.startswith("https://wa.me/5548999990000?text=") and "Aliro" in d2.replace("%20", " ")
    cliques = b.eventos("share.clicked")
    assert [c["detail"]["opcao"] for c in cliques] == ["recomendada", "mais_em_conta"]
    assert b.tabelas["artifact_shares"][0]["view_count"] == 0             # clicar não é abrir


@pytest.mark.parametrize("opcao", ["inexistente", "https://evil.example/x", "recomendada?x=1", "", None, "a" * 65,
                                   "../recomendada"])
def test_o_clique_em_opcao_desconhecida_nao_redireciona_nem_grava(opcao):
    b = _banco_com_links()
    assert SV.ArtifactService(b).fechar_compartilhado(TOKEN, opcao) is None
    assert b.eventos("share.clicked") == []


def test_o_clique_nao_existe_para_relatorio_nem_para_link_morto():
    b = _banco_com_links()
    svc = SV.ArtifactService(b)
    assert svc.fechar_compartilhado(TOKEN_REL, "recomendada") is None
    b.tabelas["artifact_shares"][0]["revoked_at"] = "2026-10-01T00:00:00+00:00"
    assert svc.fechar_compartilhado(TOKEN, "recomendada") is None
    assert b.eventos("share.clicked") == []


def test_o_destino_vem_do_modelo_e_e_sempre_wa_me():
    m = _modelo()
    m["cta"]["whatsapp_url"] = "https://evil.example/5548999990000"          # URL ruim no modelo → cai no número
    assert PH.destino_do_fechar(m, "recomendada")["destino"].startswith("https://wa.me/5548999990000?text=")
    m["anfitria"]["whatsapp"] = "abc"
    assert PH.destino_do_fechar(m, "recomendada") is None                      # sem número válido, sem destino
    m2 = _modelo()
    m2["cta"] = {"whatsapp_url": "https://api.whatsapp.com/send?phone=5547988887777"}
    assert PH.destino_do_fechar(m2, "mais_completa")["destino"].startswith("https://wa.me/5547988887777?text=")


# =====================================================================================================================
# a prévia — og:* e o PNG sem dado pessoal
# =====================================================================================================================
PESSOAIS = ("Mariana", "123.456.789-09", "12345678909", "QAZ1B23", "Compass", "2018/2019")


def test_a_previa_e_as_og_nao_tem_dado_pessoal():
    p = PH.previa_do_modelo(_modelo())
    assert p["seguradora"] == "Bradesco" and p["preco"] == "R$ 4.784,27" and p["comparadas"] == 11
    assert p["marca"] == "Corretora Anfitriã Exemplo"
    texto = json.dumps(p, ensure_ascii=False)
    head = PH.render_proposta(_modelo()).split("</head>")[0]
    for x in PESSOAIS:
        assert x not in texto and x not in head, x


def _png_wh(png: bytes) -> tuple[int, int]:
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    return int.from_bytes(png[16:20], "big"), int.from_bytes(png[20:24], "big")


def _chunks(png: bytes) -> list[bytes]:
    i, saida = 8, []
    while i < len(png):
        n = int.from_bytes(png[i:i + 4], "big")
        saida.append(png[i + 4:i + 8])
        i += 12 + n
    return saida


def test_o_png_tem_1200x630_e_dado_pessoal_nao_muda_um_byte():
    a = render_previa_png(_modelo())
    assert a is not None and _png_wh(a) == (1200, 630)
    assert not ({b"tEXt", b"iTXt", b"zTXt"} & set(_chunks(a)))              # nenhum texto embutido no arquivo
    outro = _modelo(cliente={"primeiro_nome": "Joaquim", "cpf": "987.654.321-00"},
                    veiculo={"modelo": "Fiat Uno", "ano": "2010", "placa": "ABC1D23"})
    assert render_previa_png(outro) == a
    # CONTROLE: o comparador consegue ver diferença — o preço da recomendada muda os bytes
    caro = _modelo()
    caro["opcoes"][0]["premio_anual"] = 9999.99
    assert render_previa_png(caro) != a


def test_previa_compartilhada_so_para_proposta_e_link_vivo():
    b = _banco_com_links()
    svc = SV.ArtifactService(b)
    png = svc.previa_compartilhada(TOKEN)
    assert png is not None and _png_wh(png) == (1200, 630)
    assert svc.previa_compartilhada(TOKEN_REL) is None
    assert svc.previa_compartilhada("x" * 43) is None
    assert b.tabelas["artifact_shares"][0]["view_count"] == 0 and b.eventos() == []   # a imagem não é visita
    b.tabelas["artifact_shares"][0]["expires_at"] = "2020-01-01T00:00:00+00:00"
    assert svc.previa_compartilhada(TOKEN) is None


def test_o_modelo_de_outra_corretora_nao_e_lido_pelo_link():
    """O link aponta a versão pela empresa DELE: uma versão homônima de outra corretora não serve."""
    b = _banco_com_links()
    for v in b.tabelas["artifact_versions"]:
        if v["id"] == "v-p":
            v["company_id"] = OUTRA
    assert SV.ArtifactService(b).fechar_compartilhado(TOKEN, "recomendada") is None
    assert SV.ArtifactService(b).previa_compartilhada(TOKEN) is None


def test_templates_carrega_sozinho_fora_do_pacote():
    """Guardas do catálogo carregam `templates.py` SOZINHO (sem pacote pai): ele não pode importar relativo no topo."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "templates_solto_130a", BACKEND / "app" / "services" / "artifacts" / "templates.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["templates_solto_130a"] = mod
    try:
        spec.loader.exec_module(mod)
        assert "proposal.quote" in mod.POR_CHAVE
    finally:
        sys.modules.pop("templates_solto_130a", None)


def test_o_route_e_o_script_usam_o_mesmo_parametro_do_fechar():
    rota = (BACKEND.parent / "app" / "r" / "[token]" / "route.ts").read_text(encoding="utf-8")
    assert f"searchParams.get('{PH.PARAMETRO_DO_FECHAR}')" in rota
    assert f'"?{PH.PARAMETRO_DO_FECHAR}="' in PH.SCRIPT_DA_PROPOSTA
    assert f'href="?{PH.PARAMETRO_DO_FECHAR}=recomendada"' in PH.render_proposta(_modelo())
    assert "unsafe-inline'" not in rota.split("script-src")[1].split("\n")[0]
