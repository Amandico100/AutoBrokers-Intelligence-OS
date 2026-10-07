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


# =====================================================================================================================
# F2b — o DESENHO APROVADO (D-130A-11, "carteira" v4) sobre o CONTRATO real, e os 8 acabamentos medidos
# =====================================================================================================================
from app.services.artifacts import proposta_apresentacao as AP  # noqa: E402

CONTRATO = json.loads((BACKEND / "tests" / "fixtures" / "proposta" / "modelo_contrato.json").read_text(encoding="utf-8"))
NB = " "


def _A() -> dict:
    return copy.deepcopy(CONTRATO)


def _B() -> dict:
    """A variação B: origem CANAL, anfitriã SEM marca cadastrada, duas corretoras comparadas."""
    b = _A()
    b["origem"] = "canal"
    b["anfitria"] = {"nome": "AutoFleet", "marca_cadastrada": False, "whatsapp": "5547999999999"}
    b["resumo"]["corretoras_comparadas"] = 2
    b["entre_corretoras"] = [{"corretora": "AutoFleet", "melhor_completa": 4784.27, "vencedora": True},
                             {"corretora": "Corretora Que Perdeu", "melhor_completa": 5120.0, "vencedora": False}]
    return b


def _texto(doc: str) -> str:
    """O texto visível aproximado (sem tags, sem o CSS e os scripts), com entidades resolvidas."""
    import html as _h
    corpo = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", doc, flags=re.S)
    return _h.unescape(re.sub(r"<[^>]+>", " ", corpo))


def test_arredondamento_unico_meio_para_cima_em_reais():
    assert AP.reais(375.54) == 376 and AP.reais(2.5) == 3 and AP.reais(3.5) == 4      # nunca o "banqueiro"
    assert AP.reais(5170.54) == 5171 and AP.reais(-0.5) == -1
    assert AP.brl(4784.27) == f"R${NB}4.784,27" and AP.brl(5558.3, False) == f"R${NB}5.558"
    assert AP.brl(None) == "" and AP.brl("x") == "" and AP.brl(float("nan")) == "" and AP.brl(True) == ""


def test_o_contrato_vira_a_pagina_com_as_derivacoes_do_desenho():
    doc = PH.render_proposta(_A())
    t = _texto(doc)
    # juros com NOME e o total; nunca "sem juros" quando a soma não bate (10 × 555,83 = 5.558,30 ≠ 4.784,27)
    assert f"10x de R${NB}555,83" in t and "com juros" in t and f"total R${NB}5.558" in t
    assert "sem juros" not in t
    # a mesma regra de arredondamento no comparar e na FAQ: 5.170,54 − 4.795,00 = 375,54 → 376
    assert f"R${NB}376 menor" in t and f"franquia R${NB}376 menor" in t
    assert f"R${NB}375" not in t
    assert f"R${NB}200{NB}mil + R${NB}200{NB}mil" in t                                  # "R$ 200 mil" não quebra
    assert f"R${NB}1.277 a mais por ano" in t and "(o dobro)" in t
    # a régua: N pontos = o N do texto
    assert doc.count('class="dot') - doc.count('class="dot econ') == len(CONTRATO["ranking"]) == 11
    assert "entre as 11 com cobertura completa" in t
    # o selo do Google com aspas tipográficas; a SUSEP ausente tira a frase (só dado verdadeiro)
    assert "“RESULTA CORRETORA DE SEGUROS”" in t and "'RESULTA" not in t
    assert "registrada na SUSEP" not in t
    # a marca cadastrada: logo embutido e o tema dela
    assert 'src="data:image/png;base64,' in doc and "--p:#1D5579" in doc
    # o "Quero fechar" e o "Quero esta" de cada opção vão pelo /r/ (?fechar=), nunca direto ao wa.me
    for o in CONTRATO["opcoes"]:
        assert f'href="?fechar={o["id"]}"' in doc
    assert 'class="close" id="ab-fechar" href="?fechar=recomendada"' in doc


def test_sem_js_o_rodape_ja_vem_curto_do_servidor():
    doc = PH.render_proposta(_A())
    dock = doc.split('class="dock"')[1].split('class="dock-note"')[0]
    assert "<b>Quero fechar</b>" in dock and f"Bradesco, R${NB}4.784,27" in dock
    assert "Recomendada" not in dock


def test_sem_juros_so_quando_a_soma_bate():
    o = {"premio_anual": 4784.27, "parcelas": {"vezes": 10, "valor": 555.83},
         "parcelas_sem_juros": {"vezes": 4, "valor": 1196.07}}                          # 4 × 1196,07 = 4784,28
    pc = AP.parcelas(o)
    assert pc["sem_juros"] == (4, AP.dec(1196.07)) and pc["com_juros"][0] == 10
    o["parcelas_sem_juros"] = {"vezes": 5, "valor": 1000.00}                           # 5.000 ≠ 4.784,27: mentiria
    assert AP.parcelas(o)["sem_juros"] is None
    o2 = {"premio_anual": 1200.0, "parcelas": {"vezes": 12, "valor": 100.0}}
    assert AP.parcelas(o2) == {"sem_juros": (12, AP.dec(100)), "com_juros": None}
    m = _A()
    m["opcoes"][0]["parcelas_sem_juros"] = {"vezes": 4, "valor": 1196.07}
    t = _texto(PH.render_proposta(m))
    assert f"4x de R${NB}1.196,07" in t and "sem juros" in t


def test_etiquetas_pelo_nivel_e_a_frase_quando_nao_ha_ordem():
    rec = {"coberturas": [{"chave": "vidros", "nome": "Vidros", "valor": "Plano X", "nivel": 2}]}
    melhor = {"coberturas": [{"chave": "vidros", "nome": "Vidros", "valor": "Plano Y", "nivel": 3}]}
    pior = {"coberturas": [{"chave": "vidros", "nome": "Vidros", "valor": "Plano Z", "nivel": 1}]}
    sem = {"coberturas": [{"chave": "vidros", "nome": "Vidros", "valor": "Plano W", "nivel": None}]}
    assert AP.comparar_cobertura("vidros", melhor, rec) == ("melhor", "")
    assert AP.comparar_cobertura("vidros", pior, rec) == ("mais simples", "")
    assert AP.comparar_cobertura("vidros", sem, rec) == (None, AP.FRASE_SEM_ORDEM)
    # fato que ordena (dias) sem nível: etiqueta pelo fato
    r15 = {"coberturas": [{"chave": "reserva", "nome": "Carro reserva", "valor": "15 dias", "nivel": None}]}
    r7 = {"coberturas": [{"chave": "reserva", "nome": "Carro reserva", "valor": "Reserva 07 Dias (060)", "nivel": None}]}
    assert AP.comparar_cobertura("reserva", r7, r15)[0] == "mais simples"


def test_o_selo_fica_no_fim_da_linha_do_rotulo_nunca_entre_duas_linhas():
    doc = PH.render_proposta(_A())
    # no cartão: dentro do rótulo (.cn), depois do texto — nunca entre o valor e a nota (.cv/.cx)
    cvs = re.findall(r'<span class="cv">(.*?)</span>(?:</div>|</li>)', doc)
    assert cvs
    for cv in cvs:
        assert 'class="selo' not in cv, cv
    # o selo anda colado à ÚLTIMA palavra do rótulo (`.nw`, sem quebra): nunca sozinho numa linha (crítico final)
    assert re.search(r'<span class="cn">[^<]*<span class="nw">[^< ]+<span class="selo up">', doc)
    # no comparar: o selo FECHA a célula
    celulas = [c for c in re.findall(r'<div class="cell">(.*?)</div>', doc) if 'class="cx"' in c and 'class="selo' in c]
    assert celulas
    for cel in celulas:
        assert cel.index('class="cx"') < cel.index('class="selo'), cel


def test_canal_sem_marca_e_a_perdedora_anonima():
    doc = PH.render_proposta(_B())
    t = _texto(doc)
    assert "Por que o comparador recomenda" in t and "Comparação independente · Quem Cobra Menos" in t
    assert "O que é o Quem Cobra Menos?" in t                                           # o estado de pouco dado
    assert "Corretora Que Perdeu" not in doc and "Outra corretora parceira" in t       # a perdedora não tem nome
    assert "nossa nota" not in t and "nota do comparador" in t
    # sem marca cadastrada: monograma e o tema NEUTRO (nunca a cor de outra corretora)
    assert '<img src="data:' not in doc and ">AF<" in doc
    assert "--p:#2E3740" in doc and "#1D5579" not in doc
    # marca no cadastro mas sem a flag `marca_cadastrada`: continua neutra
    m = _A()
    m["anfitria"]["marca_cadastrada"] = False
    d2 = PH.render_proposta(m)
    assert "#1D5579" not in d2 and '<img src="data:' not in d2


def test_remuneracao_e_comissao_nunca_aparecem():
    m = _A()
    m["mostrar_remuneracao"] = True       # SPEC-130-A.1: o campo saiu do modelo (G9); um modelo sujo não o faz aparecer
    m["comissao"] = 12.34
    m["remuneracao"] = "Remuneração da corretora: 12,34 %"
    for o in m["opcoes"]:
        o["comissao"] = 777.77
    doc = PH.render_proposta(m)
    assert "12,34" not in doc and "12.34" not in doc and "777" not in doc and "emunera" not in doc


def test_o_logo_so_entra_se_for_imagem_data_em_base64():
    m = _A()
    m["anfitria"]["logo_data_url"] = 'javascript:alert(1)//data:image/png;base64,AAAA'
    doc = PH.render_proposta(m)
    assert "javascript:" not in doc and "<img src=" not in doc
    m["anfitria"]["logo_data_url"] = 'data:image/png;base64,AAAA" onerror="x'
    assert "onerror" not in PH.render_proposta(m)


def test_um_modelo_minimo_ou_estranho_nao_derruba_a_pagina():
    for m in ({}, {"opcoes": []}, {"opcoes": [{"id": "x"}]}, {"opcoes": [{"id": "x", "premio_anual": "abc"}]},
              {"ranking": [{"seguradora": "A", "premio_anual": 1}], "opcoes": [{"id": "a", "premio_anual": 1}]}):
        doc = PH.render_proposta(m)
        assert [c for a, c in _scripts(doc) if "application/json" not in a] == [PH.SCRIPT_DA_PROPOSTA]
        palavras = _texto(doc).split()
        assert "None" not in palavras and "nan" not in [p.lower() for p in palavras]


def test_o_destino_do_fechar_leva_a_opcao_os_juros_e_a_validade():
    from urllib.parse import unquote
    d = PH.destino_do_fechar(_A(), "outra_completa")["destino"]
    texto = unquote(d.split("?text=")[1])
    assert texto.startswith('Olá! Aqui é Mariana. Quero fechar o seguro do Compass na opção "Menor franquia": Tokio')
    assert "R$ 6.061,17 por ano (12x de R$ 620,61 com juros, total R$ 7.447)" in texto
    assert "franquia de R$ 4.795,00" in texto and texto.endswith("A proposta vale até 13/10/2026.")


# ---- a régua: rótulos pela LARGURA medida (laudos critico-g D4 / critico-h (a)) -------------------------------------
def _sem_colisao(ticks: list, lo: int, hi: int, largura: float) -> bool:
    """Guarda: as caixas de cada rótulo, com a largura medida dos glifos, guardam ≥ 8 px entre si (número FIXO aqui)."""
    cx = AP.caixas(ticks, lo, hi, largura)
    return all(b[0] - a[1] >= 8 for a, b in zip(cx, cx[1:]))


FAIXAS = [[4168.45, 4784.27, 8460.29], [3730.56, 4157.64, 7520.24], [186.78, 501.51, 1290.0], [1200.0, 1350.0],
          [9800.0, 31000.0, 64000.0], [4000.0, 4999.0], [2500.0, 2600.0, 9100.0]]


@pytest.mark.parametrize("valores", FAIXAS)
def test_os_rotulos_da_regua_nunca_se_atropelam(valores):
    eixo = AP.eixo_da_regua(valores)
    assert eixo is not None and len(eixo["estreito"]) >= 2
    assert _sem_colisao(eixo["estreito"], eixo["lo"], eixo["hi"], AP.LARGURA_ESTREITA_PX)
    assert _sem_colisao(eixo["largo"], eixo["lo"], eixo["hi"], AP.LARGURA_LARGA_PX)
    assert eixo["lo"] <= AP.reais(min(valores)) and eixo["hi"] >= AP.reais(max(valores))


def test_MUTACAO_sem_a_folga_a_regua_do_contrato_atropela(monkeypatch):
    vals = [x["premio_anual"] for x in CONTRATO["ranking"]] + [4168.45]
    monkeypatch.setattr(AP, "FOLGA_MIN_PX", -1000)
    eixo = AP.eixo_da_regua(vals)
    assert not _sem_colisao(eixo["estreito"], eixo["lo"], eixo["hi"], AP.LARGURA_ESTREITA_PX)   # o guarda FICA vermelho


# =====================================================================================================================
# F2b — o navegador de verdade (Chromium/Playwright) com a CSP REAL do /r/. Sem navegador na máquina: pulado,
# com o motivo. As medidas são as dos laudos (390×844, dpr 2).
# =====================================================================================================================
def _csp_do_servidor() -> str:
    """A CSP que `app/r/[token]/route.ts` manda para uma proposta (frame-ancestors não vale em <meta>)."""
    return (f"default-src 'none'; script-src '{PH.HASH_DO_SCRIPT}'; img-src 'self' data:; style-src 'unsafe-inline'; "
            "font-src 'self' data:; base-uri 'none'; form-action 'none'")


def test_a_csp_do_teste_e_a_do_route():
    rota = (BACKEND.parent / "app" / "r" / "[token]" / "route.ts").read_text(encoding="utf-8")
    for d in ("default-src 'none'", "img-src 'self' data:", "style-src 'unsafe-inline'", "font-src 'self' data:",
              "base-uri 'none'", "form-action 'none'"):
        assert f'"{d}"' in rota, d


@pytest.fixture(scope="module")
def navegador():
    sync = pytest.importorskip("playwright.sync_api")
    try:
        pw = sync.sync_playwright().start()
        br = pw.chromium.launch()
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"Chromium do Playwright indisponível: {e}")
    yield br
    br.close()
    pw.stop()


_MEDIR = r"""() => {
  const vis = e => !!e && e.checkVisibility({opacityProperty: true, visibilityProperty: true});
  const ticks = [...document.querySelectorAll('.tick')].filter(vis).map(e => { const b = e.getBoundingClientRect(); return [b.left, b.right]; });
  const want = [...document.querySelectorAll('.want')].map(e => ({sw: e.scrollWidth, cw: e.clientWidth, h: e.offsetHeight}));
  let rec = 0; const H = window.innerHeight;
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (w.nextNode()) {
    const n = w.currentNode; const m = (n.textContent.match(/Recomendada/g) || []).length;
    if (!m || !vis(n.parentElement)) continue;
    const r = document.createRange(); r.selectNodeContents(n);
    const b = r.getBoundingClientRect();
    if (b.width > 0 && b.bottom > 0 && b.top < H && b.left < window.innerWidth && b.right > 0) rec += m;
  }
  const dock = document.querySelector('.dock');
  const alfa = dock ? ((getComputedStyle(dock).backgroundColor.match(/\/\s*([\d.]+)\)$/) || [0, '1'])[1]) : null;
  return {sw: document.documentElement.scrollWidth, ticks, want, rec, dockAlpha: alfa,
          passTops: [...document.querySelectorAll('.pass')].map(s => Math.round(s.getBoundingClientRect().top)),
          vazio: (() => { const r = document.querySelector('.regua'), p = document.querySelector('.pass');
                          return r && p ? Math.round(r.getBoundingClientRect().top - p.getBoundingClientRect().bottom) : null; })(),
          font: document.fonts.check('16px "Instrument Sans"')};
}"""


def _abrir(navegador, doc: str, largura: int = 390, js: bool = True, esquema: str = "light"):
    ctx = navegador.new_context(viewport={"width": largura, "height": 844 if largura < 600 else 900}, device_scale_factor=2,
                                java_script_enabled=js, color_scheme=esquema)
    pg = ctx.new_page()
    erros: list = []
    pg.on("console", lambda m: erros.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: erros.append(f"pageerror: {e}"))
    meta = f'<meta http-equiv="Content-Security-Policy" content="{_csp_do_servidor()}">'
    pg.set_content(doc.replace("<head>", "<head>\n" + meta, 1), wait_until="load")
    pg.wait_for_timeout(800)                                         # a animação de entrada dos cartões (0,6 s + 0,14 s)
    return ctx, pg, erros


def _defeitos(med: dict) -> list:
    """Os acabamentos medidos dos laudos critico-g/critico-h, como lista de defeitos (vazia = verde)."""
    d = []
    if med["sw"] > 390:
        d.append(f"rolagem horizontal: {med['sw']}")
    for a, b in zip(med["ticks"], med["ticks"][1:]):
        if b[0] - a[1] < 8:
            d.append(f"rótulos da régua a {b[0] - a[1]:.1f} px")
    for w in med["want"]:
        if w["sw"] > w["cw"] or w["h"] < 44:
            d.append(f"'Quero esta' cortado ou baixo: {w}")
    if med["rec"] != 1:
        d.append(f"'Recomendada' {med['rec']}x na 1ª tela")
    if med["dockAlpha"] is not None and float(med["dockAlpha"]) < 0.96:
        d.append(f"rodapé translúcido: {med['dockAlpha']}")
    if max(med["passTops"]) - min(med["passTops"]) > 3:
        d.append(f"cartões desalinhados no topo: {med['passTops']}")
    if med["vazio"] is not None and med["vazio"] > 48:
        d.append(f"vazio entre o cartão e a régua: {med['vazio']} px")
    return d


@pytest.mark.parametrize("cenario,esquema,js", [("A", "light", True), ("A", "dark", True), ("A", "light", False),
                                                ("B", "light", True), ("B", "dark", True), ("B", "light", False)])
def test_390_os_acabamentos_medidos_e_a_csp_real(navegador, cenario, esquema, js):
    doc = PH.render_proposta(_A() if cenario == "A" else _B())
    ctx, pg, erros = _abrir(navegador, doc, js=js, esquema=esquema)
    try:
        med = pg.evaluate(_MEDIR)
        assert erros == []                                           # nenhum bloqueio da CSP, nenhum erro de script
        assert med["font"] is True                                   # a fonte embutida carregou sob font-src data:
        assert len(med["ticks"]) >= 2 and len(med["want"]) == 3
        assert _defeitos(med) == []
        assert pg.evaluate("document.documentElement.classList.contains('no-js')") is (not js)
    finally:
        ctx.close()


def test_390_o_cabecalho_do_comparar_gruda_e_o_fechar_acompanha_o_cartao(navegador):
    ctx, pg, erros = _abrir(navegador, PH.render_proposta(_A()))
    try:
        pg.click("#tab-2")
        pg.wait_for_timeout(900)
        assert pg.evaluate("document.querySelector('#ab-fechar').getAttribute('href')") == "?fechar=economica"
        assert pg.evaluate("document.querySelector('#close-sub').textContent") == f"Bradesco, R${NB}4.168,45"
        fim = pg.evaluate("(() => { const t = document.querySelector('#track'); return [t.scrollLeft, t.scrollWidth - t.clientWidth]; })()")
        assert abs(fim[0] - fim[1]) <= 1                             # o último cartão encosta no FIM (snap end)
        pg.click("#comparar > summary")
        pg.evaluate("document.querySelector('.cmp-grid').scrollIntoView()")
        pg.evaluate("window.scrollBy(0, 600)")
        pg.wait_for_timeout(150)
        topo = pg.evaluate("document.querySelector('.cmp-head').getBoundingClientRect().top")
        assert -1 <= topo <= 1, topo                                 # GRUDOU no topo da tela
        assert pg.evaluate("document.documentElement.scrollWidth") <= 390
        assert erros == []
    finally:
        ctx.close()


def test_1280_tres_colunas_alinhadas_sem_rolagem_e_com_o_rotulo(navegador):
    ctx, pg, erros = _abrir(navegador, PH.render_proposta(_A()), largura=1280)
    try:
        assert pg.evaluate("document.documentElement.scrollWidth") <= 1280
        tops = pg.evaluate("[...document.querySelectorAll('.pass')].map(p => Math.round(p.getBoundingClientRect().top))")
        assert len(tops) == 3 and len(set(tops)) == 1
        # UM nome para o 1º cartão (crítico final): o selo com o RÓTULO aparece sem as abas (≥ 1024 px)
        assert pg.evaluate("getComputedStyle(document.querySelector('.badge.b1')).display") != "none"
        assert pg.evaluate("document.querySelector('.badge.b1').textContent") == "Recomendada"
        assert erros == []
    finally:
        ctx.close()


def test_MUTACOES_os_guardas_do_navegador_ficam_vermelhos(navegador):
    """Um fator por vez, no documento renderizado: cada guarda consegue falhar (CLAUDE.md §9.3)."""
    base = PH.render_proposta(_A())
    extra = "</style>\n<style>"
    mutacoes = {
        # os rótulos de 1 em 1 mil no celular (como antes): colidem
        "régua": base.replace('class="ticks n"', 'class="ticks X"').replace('class="ticks w"', 'class="ticks n"'),
        # o botão de antes: sem padding e encolhido no pé do cartão
        "quero esta": base.replace(extra, ".want{padding:0!important;min-height:30px!important}"
                                   ".sec.foot{align-self:end!important}" + extra, 1),
        # o selo do 1º cartão volta a aparecer debaixo da aba que já diz "Recomendada" (o nome repetido na 1ª tela)
        "recomendada": base.replace(extra, ".badge.b1{display:inline-flex!important}" + extra, 1),
        # o rodapé translúcido de antes (88 %)
        "rodapé": base.replace(extra, ".dock{background:color-mix(in srgb, var(--canvas) 88%, transparent)!important}"
                               + extra, 1),
        # os cartões alinhados pelo PÉ (como antes): os vizinhos descem
        "topo": base.replace(extra, ".pass{transform-origin:50% 100%!important}" + extra, 1),
        # o trilho com a altura do cartão mais alto e o 1º curto (como antes): o vazio de ~120 px
        "vazio": base.replace(extra, ".track{align-items:flex-start!important}" + extra, 1),
    }
    for nome, doc in mutacoes.items():
        assert doc != base, nome                                     # a mutação foi aplicada
        ctx, pg, _ = _abrir(navegador, doc)
        try:
            assert _defeitos(pg.evaluate(_MEDIR)) != [], f"o guarda de '{nome}' não ficou vermelho"
        finally:
            ctx.close()
    # CONTROLE: o documento sem mutação passa no mesmo guarda, na mesma rodada
    ctx, pg, _ = _abrir(navegador, base)
    try:
        assert _defeitos(pg.evaluate(_MEDIR)) == []
    finally:
        ctx.close()


# ---- contraste AA (WCAG 1.4.3) dos pares de cor que a página usa, claro e escuro, com e sem marca --------------------
PARES_AA = [("ink-strong", "canvas"), ("ink", "surface"), ("ink-muted", "canvas"), ("ink-muted", "surface"),
            ("ink-muted", "surface-2"), ("pass1-on", "pass1"), ("pass2-on", "pass2"), ("pass3-on", "pass3"),
            ("badge-on", "badge"), ("cta-on", "cta"), ("p-text", "surface"), ("pos", "pos-bg"), ("neg", "neg-bg")]


def _variaveis(bloco: str) -> dict:
    return dict(re.findall(r"--([a-z0-9-]+):(#[0-9A-Fa-f]{6})", bloco))


@pytest.mark.parametrize("cenario", ["A", "B"])
def test_contraste_AA_nos_dois_temas(cenario):
    anf = (_A() if cenario == "A" else _B())["anfitria"]
    css = AP.css_do_tema(anf)
    claro = _variaveis(css.split("@media")[0])
    escuro = _variaveis(css.split(":root:not")[1])
    for nome, v in (("claro", claro), ("escuro", escuro)):
        for frente, fundo in PARES_AA:
            r = AP.contraste(v[frente], v[fundo])
            assert r >= 4.5, f"{cenario} {nome}: {frente} sobre {fundo} = {r:.2f}"
