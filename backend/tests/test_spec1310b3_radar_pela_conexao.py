# -*- coding: utf-8 -*-
"""SPEC-131-0-B3 · F5 — o Raio-X e o Radar leem a fonte pela CONEXÃO da corretora.

📊 15/10/2026, produção, linha do WhatsApp do Founder: *"quais renovações tenho essa
semana?"* → *"a conexão com a InfoCap está sem credencial configurada"*. As duas tools
chamavam `FonteInfocap.para_empresa(slug)`, que lê `CORP_INFOCAP_{SLUG}_*` pelo NOME da
corretora — e corretora nova não tem (nem deve ter: CLAUDE.md §13.9) essa variável.

O FIO (CLAUDE.md §9.4 — o teste chama o MOTOR): a TOOL real (`_arun`), o resolver real
da SPEC-094 (`_abrir` → `_resolve_infocap_connection` → `_credencial` → gate de conta),
a cifra real do produto (`EncryptionService`, Fernet) e a `FonteInfocap` real. Só a
BORDA é dublê: o banco (um cliente assíncrono em memória com `tenant_connections`), a
rede (`urllib.request.urlopen`), o Redis (um dicionário) e a publicação da peça.

⛔ Nenhuma chamada real: a rede inteira é o dublê. ⛔ Logins e senhas são de fixture
(`*.invalid`) e nunca vão para a saída.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import types
import urllib.parse
import urllib.request

import pytest

EMPRESA_A = "aaaaaaaa-0000-4000-8000-00000000000a"
EMPRESA_B = "bbbbbbbb-0000-4000-8000-00000000000b"   # SEM conexão
EMPRESA_C = "cccccccc-0000-4000-8000-00000000000c"   # outra conexão, outra conta
CONEXAO_A = "11111111-0000-4000-8000-0000000000a1"
CONEXAO_C = "33333333-0000-4000-8000-0000000000c3"
TEMPLATE = "99999999-0000-4000-8000-000000000099"
BASE = "https://fonte-dubla.invalid"

LOGIN_A, SENHA_A = "conta-alfa@fixture.invalid", "senha-alfa-fixture"
LOGIN_C, SENHA_C = "conta-gama@fixture.invalid", "senha-gama-fixture"
LOGIN_LEGADO = "conta-legada@fixture.invalid"

VENDEDOR_A, VENDEDOR_C = "Vendedora Alfa", "Vendedor Gama"


# --------------------------------------------------------------------------- o banco
class _Resultado:
    """O `execute()` dos dois dialetos: `.data` direto (síncrono) e `await` (assíncrono)."""

    def __init__(self, data):
        self.data = data

    def __await__(self):
        if False:  # pragma: no cover
            yield
        return self


class _Consulta:
    def __init__(self, banco, tabela):
        self.banco, self.tabela, self.filtros = banco, tabela, []

    def select(self, *_a, **_k):
        return self

    def update(self, *_a, **_k):
        self.banco.escritas.append(self.tabela)
        return self

    def eq(self, coluna, valor):
        self.filtros.append((coluna, valor))
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        self.banco.leituras.append((self.tabela, tuple(self.filtros)))
        linhas = [dict(l) for l in self.banco.tabelas.get(self.tabela, [])
                  if all(str(l.get(c)) == str(v) for c, v in self.filtros)]
        return _Resultado(linhas)


class _Banco:
    """Cliente assíncrono em memória. `.client` existe e não é o síncrono do supabase-py,
    então `_banco_do_resolver` o deixa passar INTACTO — o mesmo critério da produção."""

    def __init__(self, tabelas):
        self.tabelas, self.leituras, self.escritas = tabelas, [], []
        self.client = self

    def table(self, nome):
        return _Consulta(self, nome)


def _conexao(cid, empresa, cifra):
    return {"id": cid, "company_id": empresa, "connector_template_id": TEMPLATE,
            "connection_config": {"base_url": BASE}, "encrypted_secret_ref": cifra,
            "status": "connected", "health_status": "healthy", "metadata": {},
            "connector_templates": {"slug": "infocap"}}


# --------------------------------------------------------------------------- a rede
def _renovacao(nosnum, vendedor, premio, dias):
    return {"nosnum": nosnum, "cliente": "Segurado de fixture", "codcli": "1",
            "seguradora": "SEGURADORA X", "ramo": "AUTO", "fimvig": "20/10/2026",
            "dias_a_vencer": dias, "pretot": premio, "tipdoc": "A", "cancelado": "F",
            "fone": "", "email": "",
            "prod_docs": [{"ordem": 1, "produtor": vendedor, "cod_pro": "7",
                           "val_r": premio / 10, "per_r": 10}]}


def _documento(nosnum, premio):
    return {"nosnum": nosnum, "cliente": "Segurado de fixture", "codcli": "1",
            "seguradora": "SEGURADORA X", "ramo": "AUTO", "inivig": "10/03/2025",
            "fimvig": "10/03/2026", "pretot": premio, "val_c": premio / 5,
            "base_c": premio, "nosnum_ren": ""}


CARTEIRAS = {
    LOGIN_A: {"/renovacoes": [_renovacao("A-001", VENDEDOR_A, 1000.0, 3),
                              _renovacao("A-002", VENDEDOR_A, 2000.0, 5)],
              "/documentos_bi": [_documento("A-001", 1000.0), _documento("A-002", 2000.0)]},
    LOGIN_C: {"/renovacoes": [_renovacao("C-001", VENDEDOR_C, 7000.0, 4)],
              "/documentos_bi": [_documento("C-001", 7000.0)]},
    LOGIN_LEGADO: {"/renovacoes": [_renovacao("L-001", "Vendedor Legado", 500.0, 2)],
                   "/documentos_bi": [_documento("L-001", 500.0)]},
}


class _Http:
    """O dublê da API na borda: `/login` devolve um token por conta; cada GET devolve a
    carteira DAQUELA conta. Guarda quais contas logaram (para o teste, nunca para log)."""

    def __init__(self):
        self.logins, self.gets = [], []

    def __call__(self, req, timeout=None):  # noqa: ARG002
        url = req.full_url
        caminho = urllib.parse.urlparse(url).path
        if not url.startswith(BASE + "/"):
            raise AssertionError("a fonte tentou sair para fora do dublê")
        if caminho == "/login":
            email = json.loads(req.data)["email"]
            self.logins.append(email)
            return _RespostaHttp({"token": "tok:" + email})
        conta = (req.get_header("Authorization") or "").split("tok:", 1)[-1]
        self.gets.append((conta, caminho))
        chave = "renovacoes" if caminho == "/renovacoes" else "documentos"
        return _RespostaHttp({"header": {}, chave: CARTEIRAS.get(conta, {}).get(caminho, [])})


class _RespostaHttp:
    def __init__(self, corpo):
        self._corpo = json.dumps(corpo).encode("utf-8")

    def read(self):
        return self._corpo

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False


# --------------------------------------------------------------------------- o arreio
@pytest.fixture()
def arreio(monkeypatch):
    from app.agents.tools import relatorios_comerciais as rel
    from app.comercial import fonte_infocap as F
    from app.core.config import settings
    from app.providers import infocap_analytics_provider as P
    from app.services import encryption_service as enc

    # ⛔ Nenhuma variável CORP_INFOCAP_* e nenhum legado: a fonte TEM de vir da conexão.
    for nome in list(os.environ):
        if nome.startswith("CORP_INFOCAP_"):
            monkeypatch.delenv(nome, raising=False)
    monkeypatch.delenv("COMERCIAL_RESOLVER_LEGADO", raising=False)

    # A cifra REAL do produto, com uma chave de teste.
    monkeypatch.setattr(settings, "ENCRYPTION_KEY",
                        base64.b64encode(os.urandom(32)).decode(), raising=False)
    monkeypatch.setattr(enc, "_encryption_service", None)
    cifra = lambda login, senha: enc.get_encryption_service().encrypt(  # noqa: E731
        json.dumps({"username": login, "password": senha, "aplicacao": "0"}))

    banco = _Banco({
        "connector_templates": [{"id": TEMPLATE, "slug": "infocap"}],
        "tenant_connections": [_conexao(CONEXAO_A, EMPRESA_A, cifra(LOGIN_A, SENHA_A)),
                               _conexao(CONEXAO_C, EMPRESA_C, cifra(LOGIN_C, SENHA_C))],
        "companies": [{"id": EMPRESA_A, "company_name": "Legadoteste Corretora"}],
    })

    http = _Http()
    monkeypatch.setattr(urllib.request, "urlopen", http)

    cache: dict = {}
    monkeypatch.setattr(F, "_cache_ler", lambda chave: cache.get(chave))
    monkeypatch.setattr(F, "_cache_gravar", lambda chave, valor: cache.__setitem__(chave, valor))

    publicadas: list = []

    def _publicar(supabase, company_id, **kw):  # noqa: ARG001
        publicadas.append(dict(kw, company_id=company_id))
        return "artifact-%d" % len(publicadas)

    monkeypatch.setattr(rel, "_publicar", _publicar)
    P.esquecer_contas()
    yield types.SimpleNamespace(rel=rel, banco=banco, http=http, cache=cache,
                                publicadas=publicadas, P=P)
    P.esquecer_contas()


def _radar(arreio, empresa, periodo="esta semana"):
    tool = arreio.rel.RadarDeRenovacoesTool(company_id=empresa, supabase=arreio.banco)
    return asyncio.run(tool._arun(periodo))


def _vendedores(publicada):
    return {v["nome"] for v in publicada["payload"]["por_vendedor"]}


# --------------------------------------------------------------------------- o fio
def test_1_o_radar_responde_pela_conexao_sem_nenhuma_variavel_de_ambiente(arreio):
    assert not [n for n in os.environ if n.startswith("CORP_INFOCAP_")]
    resposta = _radar(arreio, EMPRESA_A)
    assert resposta.startswith("RELATORIO_PRONTO"), resposta[:300]
    assert len(arreio.publicadas) == 1
    assert _vendedores(arreio.publicadas[0]) == {VENDEDOR_A}
    assert arreio.publicadas[0]["company_id"] == EMPRESA_A


def test_2_o_login_usado_e_o_da_conexao_da_corretora(arreio):
    _radar(arreio, EMPRESA_A)
    assert arreio.http.logins, "a fonte nem chegou a logar"
    assert set(arreio.http.logins) == {LOGIN_A}
    assert {conta for conta, _ in arreio.http.gets} == {LOGIN_A}
    # e a conexão foi lida COM o filtro da corretora (CLAUDE.md §7)
    filtros = [f for t, f in arreio.banco.leituras if t == "tenant_connections"]
    assert filtros and all(("company_id", EMPRESA_A) in f for f in filtros)


def test_3_corretora_sem_conexao_ouve_uma_frase_legivel_e_nao_ve_nada_da_outra(arreio):
    _radar(arreio, EMPRESA_A)                     # A leu primeiro: o cache está quente
    logins_antes, gets_antes = len(arreio.http.logins), len(arreio.http.gets)
    resposta = _radar(arreio, EMPRESA_B)
    assert resposta.startswith("RELATORIO_SEM_CONEXAO"), resposta[:300]
    assert "Personalização → Conectores" in resposta
    assert "CORP_INFOCAP" not in resposta
    assert VENDEDOR_A not in resposta and LOGIN_A not in resposta
    assert EMPRESA_A not in resposta and CONEXAO_A not in resposta
    assert "/dashboard/entregas/" not in resposta
    # nenhuma chamada nova à fonte, nenhuma peça nova
    assert (len(arreio.http.logins), len(arreio.http.gets)) == (logins_antes, gets_antes)
    assert len(arreio.publicadas) == 1


def test_4_duas_corretoras_com_o_mesmo_periodo_nao_leem_a_carteira_uma_da_outra(arreio):
    _radar(arreio, EMPRESA_A)
    _radar(arreio, EMPRESA_C)                     # o mesmo período, o mesmo cache
    assert [p["company_id"] for p in arreio.publicadas] == [EMPRESA_A, EMPRESA_C]
    assert _vendedores(arreio.publicadas[0]) == {VENDEDOR_A}
    assert _vendedores(arreio.publicadas[1]) == {VENDEDOR_C}
    # a chave do cache leva company_id:connection_id — e as duas são DIFERENTES
    chaves = list(arreio.cache)
    assert any(f"{EMPRESA_A}:{CONEXAO_A}" in c for c in chaves)
    assert any(f"{EMPRESA_C}:{CONEXAO_C}" in c for c in chaves)
    assert set(arreio.http.logins) == {LOGIN_A, LOGIN_C}


def test_5_o_raio_x_tambem_le_pela_conexao(arreio):
    tool = arreio.rel.RaioXComercialTool(company_id=EMPRESA_A, supabase=arreio.banco)
    resposta = asyncio.run(tool._arun("2025"))
    assert resposta.startswith("RELATORIO_PRONTO"), resposta[:300]
    assert set(arreio.http.logins) == {LOGIN_A}
    sem = arreio.rel.RaioXComercialTool(company_id=EMPRESA_B, supabase=arreio.banco)
    recusa = asyncio.run(sem._arun("2025"))
    assert recusa.startswith("RELATORIO_SEM_CONEXAO"), recusa[:300]
    assert "CORP_INFOCAP" not in recusa


# --------------------------------------------------------------------------- controles
def test_6_controle_a_variavel_sem_a_bandeira_nao_e_caminho(arreio, monkeypatch):
    """Se a env por NOME ainda fosse o caminho, B (sem conexão) leria com ela. Não lê."""
    monkeypatch.setenv("CORP_INFOCAP_LEGADOTESTE_LOGIN", LOGIN_LEGADO)
    monkeypatch.setenv("CORP_INFOCAP_LEGADOTESTE_PASSWORD", "senha-legada-fixture")
    monkeypatch.setenv("CORP_INFOCAP_LEGADOTESTE_BASE_URL", BASE)
    arreio.banco.tabelas["companies"].append(
        {"id": EMPRESA_B, "company_name": "Legadoteste Filial"})
    resposta = _radar(arreio, EMPRESA_B)
    assert resposta.startswith("RELATORIO_SEM_CONEXAO"), resposta[:300]
    assert arreio.http.logins == []


def test_7_controle_com_a_bandeira_legada_o_caminho_antigo_continua(arreio, monkeypatch):
    monkeypatch.setenv("COMERCIAL_RESOLVER_LEGADO", "1")
    monkeypatch.setenv("CORP_INFOCAP_LEGADOTESTE_LOGIN", LOGIN_LEGADO)
    monkeypatch.setenv("CORP_INFOCAP_LEGADOTESTE_PASSWORD", "senha-legada-fixture")
    monkeypatch.setenv("CORP_INFOCAP_LEGADOTESTE_BASE_URL", BASE)
    resposta = _radar(arreio, EMPRESA_A)
    assert resposta.startswith("RELATORIO_PRONTO"), resposta[:300]
    assert set(arreio.http.logins) == {LOGIN_LEGADO}
    assert _vendedores(arreio.publicadas[0]) == {"Vendedor Legado"}
    # o legado NÃO consulta a conexão: é só a variável, atrás da bandeira
    assert not [t for t, _ in arreio.banco.leituras if t == "tenant_connections"]


# ---------------------------------------------------------------------------------------------------------------------
# a semana — a 1ª pergunta do Founder pela linha ("quais renovações tenho essa semana?") caía no padrão de 90 dias
# ---------------------------------------------------------------------------------------------------------------------
def test_a_semana_e_de_segunda_a_domingo():
    from datetime import date as _d

    from app.comercial import calculos as C

    quinta = _d(2026, 10, 15)
    p = C.entender_periodo("Oi, quais renovações tenho essa semana?", hoje=quinta, padrao_dias_futuro=90)
    assert (p.inicio, p.fim, p.e_padrao) == (_d(2026, 10, 12), _d(2026, 10, 18), False), p
    p = C.entender_periodo("e na próxima semana?", hoje=quinta, padrao_dias_futuro=90)
    assert (p.inicio, p.fim) == (_d(2026, 10, 19), _d(2026, 10, 25)), p
    p = C.entender_periodo("semana passada", hoje=quinta)
    assert (p.inicio, p.fim) == (_d(2026, 10, 5), _d(2026, 10, 11)), p
    p = C.entender_periodo("próximas 2 semanas", hoje=quinta, padrao_dias_futuro=90)
    assert (p.inicio, p.fim) == (quinta, _d(2026, 10, 29)), p
    # CONTROLE: sem período no texto, o padrão de 90 dias continua (o guarda consegue diferir)
    p = C.entender_periodo("quais renovações eu tenho?", hoje=quinta, padrao_dias_futuro=90)
    assert p.e_padrao and p.fim == _d(2027, 1, 13), p
